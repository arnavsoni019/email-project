"""Shared helpers for the Tier 1 pipelines (categorise / summarise / triage)."""

from __future__ import annotations

# Local models are slower and have limited context; a few thousand chars of body is
# plenty to classify/summarise an email and keeps each call fast.
BODY_CHAR_LIMIT = 2000


def format_email_for_llm(
    *, from_addr: str, subject: str, body_text: str, snippet: str = ""
) -> str:
    """Render an email into a compact prompt block, truncating long bodies."""
    body = (body_text or snippet or "").strip()
    if len(body) > BODY_CHAR_LIMIT:
        body = body[:BODY_CHAR_LIMIT] + "\n...[truncated]"
    return (
        f"From: {from_addr or '(unknown)'}\n"
        f"Subject: {subject or '(no subject)'}\n"
        f"Body:\n{body or '(empty)'}"
    )
