"""The vector store: Ollama embeddings + a persistent ChromaDB collection.

**Embeddings** turn text into a fixed-length list of numbers (768 here) positioned so
that semantically similar text lands nearby. That is what lets "when is my package
arriving?" match "Out for delivery" despite sharing no words.

**ChromaDB** is a local vector database: it holds those vectors plus metadata and
answers nearest-neighbour queries. It runs in-process and writes to
``settings.chroma_path`` — nothing leaves the machine, so the privacy guarantee is
unchanged. There is no ``get_llm()``-style cloud gate here because embedding never has a
cloud path: the model is always local.

Both accessors are cached so the model handle and the Chroma client are created once
per process rather than per call.
"""

from __future__ import annotations

from functools import lru_cache

from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

from ..config import get_settings

# One named collection keeps the door open for others later (e.g. attachments).
COLLECTION = "messages"


@lru_cache
def get_embeddings() -> OllamaEmbeddings:
    """The local embedding model (nomic-embed-text, 768 dimensions)."""
    settings = get_settings()
    return OllamaEmbeddings(model=settings.embed_model, base_url=settings.ollama_host)


@lru_cache
def get_store() -> Chroma:
    """The persistent Chroma collection, created on first use."""
    settings = get_settings()
    settings.chroma_path.mkdir(parents=True, exist_ok=True)
    return Chroma(
        collection_name=COLLECTION,
        embedding_function=get_embeddings(),
        persist_directory=str(settings.chroma_path),
    )


def indexed_message_ids() -> set[str]:
    """Message ids already present in the index.

    Used to make indexing incremental — re-running should embed only what is new, since
    embedding is the slow part.
    """
    store = get_store()
    # include=[] asks Chroma for ids only; fetching documents/embeddings here would pull
    # the whole corpus into memory for no reason.
    got = store.get(include=["metadatas"])
    return {m["message_id"] for m in (got.get("metadatas") or []) if m and "message_id" in m}


def reset_index() -> None:
    """Drop every vector. Safe: SQLite is the system of record, so this is rebuildable."""
    store = get_store()
    got = store.get(include=[])
    ids = got.get("ids") or []
    if ids:
        store.delete(ids=ids)
