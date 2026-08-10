"""Build the vector index from the SQLite message store.

    python -m mailorg.rag.index            # embed anything not yet indexed
    python -m mailorg.rag.index --rebuild  # drop and redo everything
    python -m mailorg.rag.index --limit 40 # only the newest N messages

What gets embedded matters more than any tuning knob. Each chunk is prefixed with the
sender and subject so that header-only questions ("anything from ICICI?") still match,
and the body is passed through ``clean_body`` first — raw bodies are roughly half
click-tracking URLs, and embedding that noise drags every vector toward a meaningless
centre.
"""

from __future__ import annotations

import argparse
import sqlite3
from typing import Callable, Iterable

from langchain_core.documents import Document

from ..db import get_conn, init_db
from ..textclean import clean_body
from .store import get_store, indexed_message_ids, reset_index

# Short emails stay whole: one vector per email keeps retrieval clean and citation
# obvious. Only long ones are split, so a relevant paragraph isn't averaged away by
# 3000 characters of unrelated text.
CHUNK_THRESHOLD = 1200
CHUNK_SIZE = 900
CHUNK_OVERLAP = 150


def _split(text: str) -> list[str]:
    """Split long text on paragraph boundaries, with overlap to avoid cutting facts.

    Overlap matters: without it, a sentence straddling a boundary appears in neither
    chunk in full, and the fact it carries becomes unretrievable.
    """
    if len(text) <= CHUNK_THRESHOLD:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        if end < len(text):
            # Prefer a paragraph break, then a sentence break, then a hard cut.
            for sep in ("\n\n", "\n", ". "):
                cut = text.rfind(sep, start + CHUNK_SIZE // 2, end)
                if cut != -1:
                    end = cut + len(sep)
                    break
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(end - CHUNK_OVERLAP, start + 1)
    return chunks


def _documents_for(row: sqlite3.Row) -> list[Document]:
    """Turn one message row into the chunks that will be embedded."""
    sender = (row["from_name"] or "").strip() or (row["from_addr"] or "")
    subject = (row["subject"] or "(no subject)").strip()
    body = clean_body(row["body_text"] or "") or (row["snippet"] or "")

    docs: list[Document] = []
    for i, chunk in enumerate(_split(body)):
        docs.append(
            Document(
                # The header prefix is repeated per chunk so every vector carries the
                # "who/what" context, not just the first one.
                page_content=f"From: {sender}\nSubject: {subject}\n\n{chunk}",
                metadata={
                    "message_id": row["id"],
                    "thread_id": row["thread_id"] or "",
                    "sender": sender,
                    "subject": subject,
                    "category": row["category"] or "",
                    "priority": row["priority"] or "",
                    "ts": row["ts"] or 0,
                    "chunk": i,
                },
                id=f"{row['id']}:{i}",
            )
        )
    return docs


def _select(conn: sqlite3.Connection, limit: int | None) -> list[sqlite3.Row]:
    sql = "SELECT * FROM messages ORDER BY ts DESC"
    if limit is not None:
        sql += f" LIMIT {int(limit)}"
    return conn.execute(sql).fetchall()


def build_index(
    *,
    rebuild: bool = False,
    limit: int | None = None,
    progress: Callable[[int, int], None] | None = None,
) -> dict[str, int]:
    """Embed messages into Chroma. Returns counts for reporting."""
    if rebuild:
        reset_index()

    conn = get_conn()
    try:
        init_db(conn)
        rows = _select(conn, limit)
    finally:
        conn.close()

    already = set() if rebuild else indexed_message_ids()
    todo = [r for r in rows if r["id"] not in already]

    store = get_store()
    chunks = 0
    for i, row in enumerate(todo, 1):
        docs = _documents_for(row)
        if docs:
            # Explicit ids make this idempotent: re-embedding a message overwrites its
            # vectors instead of duplicating them.
            store.add_documents(docs, ids=[d.id for d in docs])
            chunks += len(docs)
        if progress:
            progress(i, len(todo))

    return {"considered": len(rows), "embedded": len(todo), "chunks": chunks, "skipped": len(rows) - len(todo)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the mailorg vector index.")
    parser.add_argument("--rebuild", action="store_true", help="drop the index and redo everything")
    parser.add_argument("--limit", type=int, default=None, help="only the newest N messages")
    args = parser.parse_args()

    def report(done: int, total: int) -> None:
        print(f"  {done}/{total} embedded", flush=True)

    stats = build_index(rebuild=args.rebuild, limit=args.limit, progress=report)
    print(
        f"\nDone. {stats['embedded']} message(s) -> {stats['chunks']} chunk(s); "
        f"{stats['skipped']} already indexed."
    )


if __name__ == "__main__":
    main()
