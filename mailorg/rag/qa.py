"""Answer natural-language questions about the mailbox, grounded in retrieved email.

The flow is: embed the question -> retrieve the nearest chunks from Chroma -> hand the
model *only* those chunks -> require it to cite them by number.

Citations are the point. A model asked about email from memory will invent plausible
details; one given numbered sources and told to cite them can be checked. Anything it
claims should be traceable to an email the user can open, so every answer ships with the
sources it drew from.

Model choice: this goes through ``get_llm("ask", heavy=True)``, so it uses
``settings.model_heavy``. Retrieval takes under a second; the generation is the slow
part, and a careful answer is worth more than a fast wrong one for a question asked a
few times a day.
"""

from __future__ import annotations

import re
from typing import Any

from ..config import get_settings
from ..providers.llm.base import get_llm
from .store import get_store

_INSTRUCTION = (
    "You answer questions about the user's email using ONLY the numbered sources below.\n"
    "Rules:\n"
    "- Cite every claim with the source number in square brackets, e.g. [2].\n"
    "- If the sources do not contain the answer, say so plainly. Do not guess.\n"
    "- Be concise: two or three sentences unless the question needs a list.\n"
    "- Refer to senders and subjects by name; do not mention 'sources' or 'context'."
)

# Chroma returns cosine distance (lower = closer). Beyond this, chunks are noise and
# including them only invites the model to answer from something irrelevant.
_MAX_DISTANCE = 1.35

_CITE_RE = re.compile(r"\[(\d+)\]")


def _gather(question: str, k: int) -> list[dict[str, Any]]:
    """Retrieve chunks and collapse them to one entry per message.

    Long emails produce several chunks; without deduping, one email could occupy every
    citation slot and crowd out the rest of the mailbox.
    """
    hits = get_store().similarity_search_with_score(question, k=k * 2)
    by_message: dict[str, dict[str, Any]] = {}
    for doc, distance in hits:
        if distance > _MAX_DISTANCE:
            continue
        mid = doc.metadata.get("message_id")
        if not mid:
            continue
        if mid in by_message:
            # Same email, another chunk: keep the text, it adds context.
            by_message[mid]["text"] += "\n" + doc.page_content
            continue
        by_message[mid] = {
            "message_id": mid,
            "sender": doc.metadata.get("sender", ""),
            "subject": doc.metadata.get("subject", ""),
            "category": doc.metadata.get("category", ""),
            "ts": doc.metadata.get("ts", 0),
            "distance": distance,
            "text": doc.page_content,
        }
        if len(by_message) >= k:
            break
    return sorted(by_message.values(), key=lambda s: s["distance"])


def ask(question: str, *, k: int | None = None) -> dict[str, Any]:
    """Answer ``question`` from the indexed mailbox.

    Returns the answer plus the sources it was given, flagging which were actually cited
    so the UI can show the evidence the model really used.
    """
    question = (question or "").strip()
    if not question:
        return {"question": question, "answer": "", "sources": []}

    k = k or get_settings().rag_top_k
    sources = _gather(question, k)
    if not sources:
        return {
            "question": question,
            "answer": "I couldn't find anything in your indexed mail about that.",
            "sources": [],
        }

    blocks = "\n\n".join(
        f"[{i}] {s['text'][:1200]}" for i, s in enumerate(sources, 1)
    )
    prompt = f"{_INSTRUCTION}\n\nSources:\n{blocks}\n\nQuestion: {question}\nAnswer:"

    answer = str(get_llm("ask", heavy=True).invoke(prompt).content).strip()

    cited = {int(n) for n in _CITE_RE.findall(answer) if n.isdigit()}
    return {
        "question": question,
        "answer": answer,
        "sources": [
            {
                "n": i,
                "messageId": s["message_id"],
                "sender": s["sender"],
                "subject": s["subject"],
                "category": s["category"],
                "ts": s["ts"],
                "distance": round(s["distance"], 3),
                "cited": i in cited,
            }
            for i, s in enumerate(sources, 1)
        ],
    }
