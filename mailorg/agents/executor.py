"""Apply approved actions to Gmail — or, by default, describe what it would apply.

    python -m mailorg.agents.executor            # dry run: shows the exact API calls
    python -m mailorg.agents.executor --live     # actually applies (needs write scope)

This is the only place in mailorg that can modify the mailbox, and it is guarded four
ways:

1. **Approval.** Only rows with ``status='approved'`` are eligible. The agent cannot
   approve its own proposals; that transition only happens from the UI.
2. **Dry run by default** (``settings.actions_dry_run``). The live path additionally
   requires ``gmail.modify`` in ``gmail_scopes`` and a re-authentication, so it cannot
   be reached by flipping one flag.
3. **Batch ceiling** (``settings.actions_batch_limit``). A bad proposal run should be
   able to touch a handful of messages, not the whole mailbox.
4. **Reversibility.** Only archive/label/draft are expressible. Nothing here deletes,
   marks spam, or sends mail. Note this is a property of *this code*, not of the OAuth
   grant: ``gmail.modify`` also permits sending, and Google offers no label-only write
   scope. The guarantee is that no send call exists anywhere in the codebase — which is
   why every write must funnel through ``_apply_live`` rather than calling the provider
   directly.

Each applied action stores what was done in ``actions.result``, including the undo
payload captured at propose time, so a reversal is a lookup rather than a guess.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import time
from typing import Any

from ..config import Settings, get_settings
from ..db import get_conn, init_db

MODIFY_SCOPE = "https://www.googleapis.com/auth/gmail.modify"


class WriteScopeMissing(RuntimeError):
    """Raised when a live run is attempted without Gmail write permission."""


class DryRunActive(RuntimeError):
    """Raised when a single action is applied while ``actions_dry_run`` is set."""


class DemoStoreRefused(RuntimeError):
    """Raised when a live write is attempted while pointed at the demo mailbox."""


def _refuse_demo_store(settings: Settings) -> None:
    """Never write to the real mailbox on behalf of synthetic proposals.

    ``DB_PATH`` selects which mailbox is *read*, but Gmail credentials always point at
    the real account — so a live run against the demo store would file replies to
    invented people into the owner's actual Gmail. Checked here rather than in the web
    layer so the CLI is covered by the same rule.
    """
    if "demo" in settings.db_path.name.lower():
        raise DemoStoreRefused(
            f"Refusing to write to Gmail while reading {settings.db_path}. These are "
            "synthetic proposals; applying them would put them in your real mailbox."
        )


def _require_live_preconditions(settings: Settings) -> None:
    """Every check that must pass before any Gmail write, in one place."""
    _refuse_demo_store(settings)
    if MODIFY_SCOPE not in settings.gmail_scopes:
        raise WriteScopeMissing(
            "Live execution needs Gmail write access. Add "
            f"'{MODIFY_SCOPE}' to GMAIL_SCOPES and re-authenticate "
            "(delete data/token.json, then run a sync to consent again)."
        )


def _label_name(conn: sqlite3.Connection, action: sqlite3.Row, payload: dict[str, Any]) -> str | None:
    """The label to apply, falling back to the message's category.

    Proposals raised from the UI's "Label" button carry only a rationale — the browser
    never sends a payload — so ``labelName`` is absent on those rows. Deriving it from
    the stored category makes them applicable instead of failing with a KeyError at the
    moment of writing to the mailbox, which is the worst possible time to discover it.
    """
    name = payload.get("labelName")
    if name:
        return str(name)
    row = conn.execute(
        "SELECT category FROM messages WHERE id = ?", (action["target_id"],)
    ).fetchone()
    category = (row["category"] or "").strip() if row else ""
    return f"mailorg/{category}" if category else None


def _describe(action: sqlite3.Row, payload: dict[str, Any], label: str | None = None) -> str:
    """The exact Gmail operation this action represents, in one readable line."""
    if action["type"] == "archive":
        return f"users.messages.modify(id={action['target_id']}, removeLabelIds=['INBOX'])"
    if action["type"] == "label":
        return f"users.messages.modify(id={action['target_id']}, addLabelIds=['{label or payload.get('labelName')}'])"
    if action["type"] == "draft":
        n = len(payload.get("body") or "")
        return f"users.drafts.create(threadId={payload.get('threadId')}, to={payload.get('to')}, body={n} chars)"
    return f"unknown action type {action['type']!r}"


def _apply_live(
    provider: Any, action: sqlite3.Row, payload: dict[str, Any], label: str | None = None
) -> dict[str, Any]:
    """Perform the real Gmail call. Only reached with --live and the modify scope."""
    kind = action["type"]
    if kind == "archive":
        provider.modify_message(action["target_id"], remove_label_ids=["INBOX"])
        return {"removed": ["INBOX"], "undo": {"addLabelIds": ["INBOX"]}}
    if kind == "label":
        name = label or payload.get("labelName")
        if not name:
            raise ValueError(
                "no label name on the proposal and the message has no category to "
                "derive one from"
            )
        label_id = provider.ensure_label(name)
        provider.modify_message(action["target_id"], add_label_ids=[label_id])
        return {"added": [name], "labelId": label_id, "undo": {"removeLabelIds": [label_id]}}
    if kind == "draft":
        to = (payload.get("to") or "").strip()
        body = (payload.get("body") or "").strip()
        # Fail closed. Python's email library accepts a None recipient and stores the
        # literal string "None", so an incomplete payload would otherwise produce a real
        # Gmail draft addressed to nobody rather than an error.
        if not to:
            raise ValueError("draft has no recipient; refusing to create it")
        if not body:
            raise ValueError("draft has no body; refusing to create an empty draft")
        draft_id = provider.create_draft(
            thread_id=payload.get("threadId"), to=to, body=body
        )
        # A draft is created, never sent; deleting it is the undo.
        return {"draftId": draft_id, "undo": {"deleteDraft": draft_id}}
    raise ValueError(f"unsupported action type {kind!r}")


def run(*, live: bool = False, settings: Settings | None = None) -> dict[str, Any]:
    """Execute approved actions. Returns a summary including the planned calls."""
    settings = settings or get_settings()
    dry_run = settings.actions_dry_run and not live

    provider = None
    if not dry_run:
        _require_live_preconditions(settings)
        from ..providers.email.gmail import GmailProvider  # imported only on the live path

        provider = GmailProvider(settings)
        provider.authenticate()

    conn = get_conn()
    try:
        init_db(conn)
        rows = conn.execute(
            "SELECT * FROM actions WHERE status = 'approved' ORDER BY created_ts LIMIT ?",
            (settings.actions_batch_limit,),
        ).fetchall()

        planned, applied, failed = [], 0, 0
        for action in rows:
            payload = json.loads(action["payload"] or "{}")
            label = _label_name(conn, action, payload) if action["type"] == "label" else None
            description = _describe(action, payload, label)
            planned.append({"id": action["id"], "type": action["type"], "call": description})

            if dry_run:
                continue
            try:
                result = _apply_live(provider, action, payload, label)
                conn.execute(
                    "UPDATE actions SET status='applied', result=? WHERE id=?",
                    (json.dumps({"call": description, **result, "appliedTs": int(time.time())}), action["id"]),
                )
                applied += 1
            except Exception as exc:
                conn.execute(
                    "UPDATE actions SET status='failed', result=? WHERE id=?",
                    (json.dumps({"call": description, "error": f"{type(exc).__name__}: {exc}"}), action["id"]),
                )
                failed += 1
            conn.commit()

        return {
            "dryRun": dry_run,
            "eligible": len(rows),
            "applied": applied,
            "failed": failed,
            "planned": planned,
        }
    finally:
        conn.close()


def ensure_can_write(settings: Settings | None = None) -> None:
    """Raise if a live write is not permitted right now. No network, no side effects.

    Callers that create an action row before applying it must call this *first*.
    Inserting an ``approved`` row and only then discovering that writing is refused
    leaves an armed proposal behind that the next ``--live`` run would apply — the
    opposite of what the user was told when their save failed.
    """
    settings = settings or get_settings()
    if settings.actions_dry_run:
        raise DryRunActive(
            "ACTIONS_DRY_RUN is on, so nothing is written to Gmail. Set "
            "ACTIONS_DRY_RUN=false in .env to let this save."
        )
    _require_live_preconditions(settings)


def apply_one(action_id: int, *, settings: Settings | None = None) -> dict[str, Any]:
    """Apply one already-approved action immediately, and record the result.

    This exists so the Inbox composer can save a reply the user has just read and edited
    without a second trip through the approval queue. It deliberately routes through
    ``_apply_live`` rather than calling the provider, so the four guards, the undo
    payload and the ``actions`` audit trail all still apply — the review step is skipped,
    the machinery is not.

    ``actions_dry_run`` is honoured rather than bypassed: a project with two different
    safety regimes is one where nobody can say what a flag means.
    """
    settings = settings or get_settings()
    ensure_can_write(settings)

    from ..providers.email.gmail import GmailProvider

    provider = GmailProvider(settings)
    provider.authenticate()

    conn = get_conn()
    try:
        init_db(conn)
        action = conn.execute("SELECT * FROM actions WHERE id = ?", (action_id,)).fetchone()
        if action is None:
            raise ValueError(f"action {action_id} not found")
        if action["status"] != "approved":
            raise ValueError(f"action {action_id} is {action['status']!r}, not approved")

        payload = json.loads(action["payload"] or "{}")
        label = _label_name(conn, action, payload) if action["type"] == "label" else None
        description = _describe(action, payload, label)
        try:
            result = _apply_live(provider, action, payload, label)
        except Exception as exc:
            conn.execute(
                "UPDATE actions SET status='failed', result=? WHERE id=?",
                (json.dumps({"call": description, "error": f"{type(exc).__name__}: {exc}"}), action_id),
            )
            conn.commit()
            raise
        conn.execute(
            "UPDATE actions SET status='applied', result=? WHERE id=?",
            (json.dumps({"call": description, **result, "appliedTs": int(time.time())}), action_id),
        )
        conn.commit()
        return {"id": action_id, "call": description, **result}
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply approved mailbox actions.")
    parser.add_argument("--live", action="store_true", help="actually call Gmail (needs write scope)")
    args = parser.parse_args()

    summary = run(live=args.live)
    mode = "DRY RUN — nothing was sent to Gmail" if summary["dryRun"] else "LIVE"
    print(f"{mode}. {summary['eligible']} approved action(s).\n")
    for p in summary["planned"]:
        print(f"  #{p['id']:<4} {p['type']:<8} {p['call']}")
    if not summary["dryRun"]:
        print(f"\nApplied {summary['applied']}, failed {summary['failed']}.")
    elif summary["eligible"]:
        print("\nRe-run with --live to apply (requires gmail.modify and re-authentication).")


if __name__ == "__main__":
    main()
