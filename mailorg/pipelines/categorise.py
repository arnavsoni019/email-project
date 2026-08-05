"""Categorise an email into exactly one of the configured categories.

Design note: for a *single-label* answer, small local models are more reliable when
asked for a plain word than when forced to emit JSON. So we take the model's text reply
and normalise it against the allowed category list ourselves, rather than using
``with_structured_output`` (which we reserve for multi-field extraction in Phase 4).
"""

from __future__ import annotations

from ..config import Settings, get_settings
from ..providers.llm.base import get_llm
from .common import format_email_for_llm

_INSTRUCTION = (
    "You are an email classifier. Choose the SINGLE category that best fits the email "
    "below, considering the sender, subject, and body.\n"
    "Reply with ONLY the category word — no punctuation, no explanation."
)

_DEFAULT_CATEGORY = "Personal"  # used only when the reply matches no known category


def _match_category(reply: str, categories: list[str]) -> str | None:
    """Map a free-text model reply to one of ``categories`` (case-insensitive)."""
    cleaned = reply.strip().strip(".\"'` \n").lower()
    by_lower = {c.lower(): c for c in categories}
    # Exact match first.
    if cleaned in by_lower:
        return by_lower[cleaned]
    # Otherwise, the reply may be a short phrase containing the category word.
    for lower, original in by_lower.items():
        if lower in cleaned:
            return original
    return None


def categorise_one(
    *, from_addr: str, subject: str, body_text: str, snippet: str = "",
    settings: Settings | None = None, heavy: bool = False,
) -> str:
    settings = settings or get_settings()
    categories = settings.categories
    llm = get_llm("categorise", heavy=heavy)

    prompt = (
        f"{_INSTRUCTION}\n\nAllowed categories: {', '.join(categories)}\n\n"
        f"{format_email_for_llm(from_addr=from_addr, subject=subject, body_text=body_text, snippet=snippet)}"
    )
    reply = llm.invoke(prompt).content
    return _match_category(reply, categories) or _DEFAULT_CATEGORY
