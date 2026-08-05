"""Triage an email by priority: 'action', 'fyi', or 'ignore'.

Same single-label approach as categorise: plain-text reply normalised against the fixed
set of priorities.
"""

from __future__ import annotations

from ..providers.llm.base import get_llm
from .common import format_email_for_llm

# The three priority buckets and what they mean (given to the model as definitions).
PRIORITIES = ("action", "fyi", "ignore")

_INSTRUCTION = (
    "Triage the email below into exactly one priority:\n"
    "- action: the recipient must personally do or reply to something (a real task, "
    "deadline, question, or request directed at them).\n"
    "- fyi: worth reading but needs no action (updates, confirmations, receipts).\n"
    "- ignore: promotional, newsletter, or noise that can be skipped.\n"
    "Reply with ONLY one word: action, fyi, or ignore."
)

_DEFAULT_PRIORITY = "fyi"  # safe middle ground if the reply is unrecognised


def _match_priority(reply: str) -> str | None:
    cleaned = reply.strip().strip(".\"'` \n").lower()
    if cleaned in PRIORITIES:
        return cleaned
    for p in PRIORITIES:
        if p in cleaned:
            return p
    return None


def triage_one(
    *, from_addr: str, subject: str, body_text: str, snippet: str = "", heavy: bool = False
) -> str:
    llm = get_llm("triage", heavy=heavy)
    prompt = (
        f"{_INSTRUCTION}\n\n"
        f"{format_email_for_llm(from_addr=from_addr, subject=subject, body_text=body_text, snippet=snippet)}"
    )
    reply = llm.invoke(prompt).content
    return _match_priority(reply) or _DEFAULT_PRIORITY
