"""Sync orchestration: pull mail via an EmailProvider into the local SQLite store.

SQLite is the system of record (every message + threads + sync bookmark + action queue).
Phase 4 later builds a ChromaDB *index* of embeddings that references these rows for
semantic search — it does not replace this store.

Two modes:
  * backfill    — first run (or forced): list messages and fetch each.
  * incremental — subsequent runs: fetch only what changed since the stored historyId.

Re-syncing a known message updates its raw fields but PRESERVES the LLM-derived columns
(category/tldr/priority/processed_at), so enrichment work is never lost.
"""

from __future__ import annotations

import argparse
import json
import sqlite3

from .db import get_conn, init_db
from .providers.email.base import EmailMessage, EmailProvider
from .providers.email.gmail import GmailProvider

# Only these raw columns are overwritten on conflict. LLM columns are omitted on purpose.
_UPSERT_MESSAGE = """
INSERT INTO messages
    (id, thread_id, from_addr, from_name, to_addrs, cc_addrs, subject, snippet, body_text,
     body_html, ts, label_ids, is_unread, size_estimate)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(id) DO UPDATE SET
    thread_id     = excluded.thread_id,
    from_addr     = excluded.from_addr,
    from_name     = excluded.from_name,
    to_addrs      = excluded.to_addrs,
    cc_addrs      = excluded.cc_addrs,
    subject       = excluded.subject,
    snippet       = excluded.snippet,
    body_text     = excluded.body_text,
    body_html     = excluded.body_html,
    ts            = excluded.ts,
    label_ids     = excluded.label_ids,
    is_unread     = excluded.is_unread,
    size_estimate = excluded.size_estimate
"""

# Recompute a thread's aggregate fields from its messages; preserve LLM columns
# (summary/category/priority) by not touching them.
_REFRESH_THREAD = """
INSERT INTO threads (id, subject, last_message_ts, num_messages)
VALUES (
    ?,
    (SELECT subject FROM messages WHERE thread_id = ? ORDER BY ts LIMIT 1),
    (SELECT MAX(ts) FROM messages WHERE thread_id = ?),
    (SELECT COUNT(*) FROM messages WHERE thread_id = ?)
)
ON CONFLICT(id) DO UPDATE SET
    subject         = excluded.subject,
    last_message_ts = excluded.last_message_ts,
    num_messages    = excluded.num_messages
"""


# --- sync_state helpers -----------------------------------------------------
def get_sync_value(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM sync_state WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def set_sync_value(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO sync_state (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )


# --- persistence ------------------------------------------------------------
def upsert_message(conn: sqlite3.Connection, msg: EmailMessage) -> None:
    conn.execute(
        _UPSERT_MESSAGE,
        (
            msg.id,
            msg.thread_id,
            msg.from_addr,
            msg.from_name,
            json.dumps(msg.to_addrs),
            json.dumps(msg.cc_addrs),
            msg.subject,
            msg.snippet,
            msg.body_text,
            msg.body_html,
            msg.ts,
            json.dumps(msg.label_ids),
            1 if msg.is_unread else 0,
            msg.size_estimate,
        ),
    )


def ensure_thread(conn: sqlite3.Connection, thread_id: str) -> None:
    """Insert a stub thread row if absent, so message FKs are satisfied on insert.

    Aggregate fields (subject/last_message_ts/num_messages) are filled in later by
    refresh_thread(); LLM columns (summary/category/priority) are left untouched.
    """
    conn.execute("INSERT OR IGNORE INTO threads (id) VALUES (?)", (thread_id,))


def refresh_thread(conn: sqlite3.Connection, thread_id: str) -> None:
    remaining = conn.execute(
        "SELECT COUNT(*) AS n FROM messages WHERE thread_id = ?", (thread_id,)
    ).fetchone()["n"]
    if remaining == 0:
        conn.execute("DELETE FROM threads WHERE id = ?", (thread_id,))
    else:
        conn.execute(_REFRESH_THREAD, (thread_id, thread_id, thread_id, thread_id))


# --- sync modes -------------------------------------------------------------
def _backfill(
    provider: EmailProvider,
    conn: sqlite3.Connection,
    *,
    label_ids: list[str] | None,
    max_messages: int | None,
) -> int:
    touched_threads: set[str] = set()
    count = 0
    for message_id in provider.list_message_ids(label_ids=label_ids, max_results=max_messages):
        msg = provider.get_message(message_id)
        ensure_thread(conn, msg.thread_id)
        upsert_message(conn, msg)
        touched_threads.add(msg.thread_id)
        count += 1
        if count % 25 == 0:
            conn.commit()
            print(f"  ...{count} messages")
    for thread_id in touched_threads:
        refresh_thread(conn, thread_id)
    conn.commit()
    return count


def _incremental(
    provider: EmailProvider, conn: sqlite3.Connection, start_history_id: str
) -> tuple[int, str | None, bool]:
    changes = provider.list_history(start_history_id)
    if changes.history_too_old:
        return 0, None, True  # signal caller to backfill

    touched_threads: set[str] = set()
    count = 0
    for message_id in changes.added_message_ids:
        try:
            msg = provider.get_message(message_id)
        except Exception:
            continue  # message may have been deleted between history and fetch
        ensure_thread(conn, msg.thread_id)
        upsert_message(conn, msg)
        touched_threads.add(msg.thread_id)
        count += 1

    for message_id in changes.deleted_message_ids:
        row = conn.execute(
            "SELECT thread_id FROM messages WHERE id = ?", (message_id,)
        ).fetchone()
        if row:
            touched_threads.add(row["thread_id"])
            conn.execute("DELETE FROM messages WHERE id = ?", (message_id,))

    for thread_id in touched_threads:
        refresh_thread(conn, thread_id)
    conn.commit()
    return count, changes.new_history_id, False


def sync(
    provider: EmailProvider,
    conn: sqlite3.Connection,
    *,
    full: bool = False,
    label_ids: list[str] | None = None,
    max_messages: int | None = None,
) -> None:
    """Run a sync. Chooses backfill vs incremental based on stored state."""
    provider.authenticate()
    email_addr, current_history_id = provider.get_profile()
    print(f"Account: {email_addr}")
    set_sync_value(conn, "email_address", email_addr)

    stored_history_id = get_sync_value(conn, "history_id")

    if full or not stored_history_id:
        print("Backfilling..." if not stored_history_id else "Forced full backfill...")
        n = _backfill(provider, conn, label_ids=label_ids, max_messages=max_messages)
        set_sync_value(conn, "history_id", current_history_id)
        conn.commit()
        print(f"Backfill complete: {n} messages. historyId={current_history_id}")
        return

    print(f"Incremental sync since historyId={stored_history_id}...")
    n, new_history_id, too_old = _incremental(provider, conn, stored_history_id)
    if too_old:
        print("Stored historyId expired; falling back to full backfill.")
        n = _backfill(provider, conn, label_ids=label_ids, max_messages=max_messages)
        set_sync_value(conn, "history_id", current_history_id)
        conn.commit()
        print(f"Backfill complete: {n} messages. historyId={current_history_id}")
        return

    set_sync_value(conn, "history_id", new_history_id or current_history_id)
    conn.commit()
    print(f"Incremental complete: {n} new/changed messages. historyId={new_history_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync Gmail into the local mailorg DB.")
    parser.add_argument("--full", action="store_true", help="force a full backfill")
    parser.add_argument(
        "--max", type=int, default=None, metavar="N",
        help="cap messages fetched during backfill (handy for a first smoke test)",
    )
    parser.add_argument(
        "--label", action="append", default=None, metavar="LABEL_ID",
        help="Gmail label id to backfill (repeatable). Defaults to INBOX.",
    )
    args = parser.parse_args()

    conn = get_conn()
    init_db(conn)  # ensure schema exists
    provider = GmailProvider()
    label_ids = args.label if args.label else ["INBOX"]
    try:
        sync(provider, conn, full=args.full, label_ids=label_ids, max_messages=args.max)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
