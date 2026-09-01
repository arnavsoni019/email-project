"""Propose mailbox actions for human approval.

    python -m mailorg.agents.proposer --limit 40

Design choice worth naming: candidate actions are chosen by **rules over the triage
output**, and the model is used only to *justify* them and to draft reply text. The
alternative — letting the model pick freely from the whole action space — is more
agentic but less predictable, and every extra degree of freedom here is a degree of
freedom to propose something surprising against a real mailbox. The rules are legible,
the rationale is still in plain language, and the human still approves each one.

Only reversible actions are ever proposed:
  * ``archive`` — removes the INBOX label; re-adding it restores the message.
  * ``label``   — adds a label; removing it undoes this.
  * ``draft``   — creates a Gmail draft. Never sends. Drafts can be deleted.

Deleting, marking spam, and sending are deliberately not expressible.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import time
from typing import Any, Callable

from ..config import get_settings
from ..db import get_conn, init_db
from ..pipelines.common import format_email_for_llm
from ..providers.llm.base import get_llm

# Messages older than this are stale enough that archiving noise is uncontroversial.
ARCHIVE_MIN_AGE_HOURS = 24

# Senders that cannot receive a reply. Drafting one wastes the heavy model and, worse,
# invites the user to answer a machine — the first proposer run offered to reply to an
# automated MEGA security notice. Triage marks such mail "action" because it *does* want
# something from you, but the something is never a reply.
_NO_REPLY_RE = re.compile(
    r"(?:^|[.\-_])(?:no[-_.]?reply|do[-_.]?not[-_.]?reply|donotreply|noreply|"
    r"notifications?|alerts?|mailer|bounce|postmaster|automated)(?:[.\-_@]|$)",
    re.I,
)


def _can_reply(from_addr: str) -> bool:
    """False when the sender is an unattended mailbox."""
    return bool(from_addr) and not _NO_REPLY_RE.search(from_addr)


# Subjects implying something is still pending on the owner's side. Triage can mark
# these "ignore" because the *body* reads like marketing, but archiving something that
# says "confirm your application" is the kind of mistake that costs a real opportunity.
# Archiving is reversible, but only if you notice — so bias toward leaving it alone.
_PENDING_SUBJECT_RE = re.compile(
    r"\b(?:confirm|verify|verification|action required|respond|reply|complete your|"
    r"pending|awaiting|expires?|expiring|deadline|last (?:day|chance)|due|overdue|"
    r"reminder|renew|approve|sign|otp|password|security alert)\b",
    re.I,
)

_RATIONALE_INSTRUCTION = (
    "In ONE short sentence, explain to the mailbox owner why this email can be {verb}. "
    "Be concrete about what the email is. No preamble, no greeting, one sentence only."
)

# "on the owner's behalf" used to be in the first line, and the model read it as a
# third party: replies came back saying "I'll confirm with the owner and get back to
# you", which is what an outsourced assistant writes, not what the recipient writes.
# Casting the model AS the recipient, and banning third-person self-reference outright,
# is what fixed it.
_DRAFT_INSTRUCTION = (
    "You are the person who received the email below. Write your reply to it, in the "
    "first person, as yourself.\n"
    "Rules:\n"
    "- 2-4 sentences. No subject line, no signature block, no placeholders like [Name].\n"
    "- Never refer to yourself in the third person, and never mention 'the owner', "
    "'the user', or an assistant. You are the one sending this reply.\n"
    "- Answer what was actually asked. If it asks something you cannot know from the "
    "email itself, say you will check and come back with an answer.\n"
    "- Match the sender's register: relaxed with friends and family, plain and direct "
    "with colleagues.\n"
    "- Reply with the message body only."
)


def _existing_keys(conn: sqlite3.Connection) -> set[tuple[str, str]]:
    """(type, target_id) pairs already queued or applied.

    Without this, every run would re-propose the same archive for the same email and
    the queue would fill with duplicates. Rejected proposals are included: a rejection
    is a decision, and re-asking would be nagging.
    """
    rows = conn.execute("SELECT type, target_id FROM actions")
    return {(r["type"], r["target_id"]) for r in rows}


def _candidates(conn: sqlite3.Connection, limit: int | None) -> list[sqlite3.Row]:
    sql = (
        "SELECT id, thread_id, from_addr, from_name, subject, body_text, snippet, "
        "category, priority, tldr, ts FROM messages "
        "WHERE processed_at IS NOT NULL ORDER BY ts DESC"
    )
    if limit is not None:
        sql += f" LIMIT {int(limit)}"
    return conn.execute(sql).fetchall()


def _plan(
    row: sqlite3.Row, now: int, *, own_addr: str = "", propose_drafts: bool = False
) -> tuple[str, dict[str, Any]] | None:
    """Decide which single action, if any, to propose for this message."""
    priority = (row["priority"] or "").lower()
    age_hours = (now - (row["ts"] or now)) / 3600
    from_addr = (row["from_addr"] or "").strip().lower()
    subject = row["subject"] or ""

    # Mail you sent yourself is a deliberate act — a note, a file, a reminder. Triage
    # sees no call to action and marks it "ignore"; archiving it would file away the
    # very thing you parked in the inbox on purpose.
    is_self = bool(own_addr) and from_addr == own_addr.strip().lower()

    if (
        priority == "ignore"
        and age_hours >= ARCHIVE_MIN_AGE_HOURS
        and not is_self
        and not _PENDING_SUBJECT_RE.search(subject)
    ):
        # Undo data is captured now, while we know the pre-change state.
        return "archive", {"removeLabelIds": ["INBOX"], "undo": {"addLabelIds": ["INBOX"]}}

    # Drafting is off by default. "Needs your attention" is not "needs your words":
    # every draft the first run produced targeted a robot (LinkedIn invitations, an
    # automated MEGA alert, a postal-ballot notice). Deciding whether a reply is
    # genuinely wanted is a judgement call this rule cannot make — revisit when a
    # stronger model can be asked directly (Phase 6).
    if propose_drafts and priority == "action" and not is_self and _can_reply(from_addr):
        return "draft", {"threadId": row["thread_id"], "to": row["from_addr"]}

    if priority in {"action", "fyi"} and row["category"] and not is_self:
        name = f"mailorg/{row['category']}"
        return "label", {"labelName": name, "undo": {"removeLabelName": name}}

    return None


def propose_all(
    *, limit: int | None = None, progress: Callable[[int, int], None] | None = None
) -> dict[str, int]:
    """Queue proposals for messages that do not already have one."""
    settings = get_settings()
    conn = get_conn()
    try:
        init_db(conn)
        now = int(time.time())
        rows = _candidates(conn, limit)
        seen = _existing_keys(conn)
        # The synced account, so mail the owner sent themselves can be recognised.
        own = conn.execute("SELECT value FROM sync_state WHERE key='email_address'").fetchone()
        own_addr = own["value"] if own else ""

        planned: list[tuple[sqlite3.Row, str, dict[str, Any]]] = []
        for row in rows:
            plan = _plan(row, now, own_addr=own_addr, propose_drafts=settings.propose_drafts)
            if plan and (plan[0], row["id"]) not in seen:
                planned.append((row, plan[0], plan[1]))

        counts = {"archive": 0, "label": 0, "draft": 0}
        for i, (row, kind, payload) in enumerate(planned, 1):
            email_block = format_email_for_llm(
                from_addr=row["from_addr"], subject=row["subject"],
                body_text=row["body_text"], snippet=row["snippet"],
            )
            if kind == "draft":
                # Drafting is the one genuinely generative task here, so it gets the
                # heavy model; the rationale sentences do not need it.
                body = str(get_llm("draft", heavy=True).invoke(
                    f"{_DRAFT_INSTRUCTION}\n\n{email_block}").content).strip()
                payload = {**payload, "body": body}
                rationale = "Needs a personal reply; a draft is ready for you to edit."
            else:
                verb = "archived" if kind == "archive" else f"labelled {payload['labelName']}"
                rationale = str(get_llm("propose").invoke(
                    f"{_RATIONALE_INSTRUCTION.format(verb=verb)}\n\n{email_block}").content).strip()
                rationale = " ".join(rationale.split())[:220]

            conn.execute(
                "INSERT INTO actions (type, target_id, payload, rationale, created_ts) "
                "VALUES (?, ?, ?, ?, ?)",
                (kind, row["id"], json.dumps(payload), rationale, now),
            )
            conn.commit()  # each proposal persists on its own, so a crash loses nothing
            counts[kind] += 1
            if progress:
                progress(i, len(planned))

        return {"considered": len(rows), "proposed": sum(counts.values()), **counts}
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Queue mailbox action proposals.")
    parser.add_argument("--limit", type=int, default=None, help="only the newest N messages")
    args = parser.parse_args()

    def report(done: int, total: int) -> None:
        print(f"  {done}/{total}", flush=True)

    stats = propose_all(limit=args.limit, progress=report)
    print(
        f"\nProposed {stats['proposed']} action(s) from {stats['considered']} message(s): "
        f"{stats['archive']} archive, {stats['label']} label, {stats['draft']} draft.\n"
        "Nothing has changed in Gmail — approve them in the Queue screen."
    )


if __name__ == "__main__":
    main()
