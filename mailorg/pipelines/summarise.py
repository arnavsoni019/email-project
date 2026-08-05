"""Produce a one-line TL;DR of an email, for a scannable inbox list.

Plain-text output (a sentence is naturally free-text), with light cleanup: collapse to a
single line and cap length so the inbox stays tidy.
"""

from __future__ import annotations

from ..providers.llm.base import get_llm
from .common import format_email_for_llm

_INSTRUCTION = (
    "Summarise the following email in ONE short, factual sentence (max 20 words). "
    "Capture what it is and any action it asks for. Do not add a preamble like "
    "'This email'. Reply with the sentence only."
)

_MAX_CHARS = 200


def summarise_one(
    *, from_addr: str, subject: str, body_text: str, snippet: str = "", heavy: bool = False
) -> str:
    llm = get_llm("summarise", heavy=heavy)
    prompt = (
        f"{_INSTRUCTION}\n\n"
        f"{format_email_for_llm(from_addr=from_addr, subject=subject, body_text=body_text, snippet=snippet)}"
    )
    reply = llm.invoke(prompt).content.strip()
    # Collapse any stray newlines into one line and trim to a sane length.
    one_line = " ".join(reply.split())
    if len(one_line) > _MAX_CHARS:
        one_line = one_line[:_MAX_CHARS].rstrip() + "…"
    return one_line
