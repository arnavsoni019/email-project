"""Run the Tier 1 pipelines over stored messages and write results back to SQLite.

Fills the LLM-derived columns designed in Phase 0 (category / tldr / priority) and
stamps processed_at. By default only processes messages not yet processed; --all
re-processes everything (e.g. after tweaking prompts).

    python -m mailorg.pipelines.run            # process new messages
    python -m mailorg.pipelines.run --limit 20 # cap how many
    python -m mailorg.pipelines.run --all      # redo everything
"""

from __future__ import annotations

import argparse
import sqlite3
import time

from ..db import get_conn, init_db
from .categorise import categorise_one
from .summarise import summarise_one
from .triage import triage_one


def _select_messages(conn: sqlite3.Connection, *, all_: bool, limit: int | None) -> list[sqlite3.Row]:
    where = "" if all_ else "WHERE processed_at IS NULL"
    sql = f"SELECT id, from_addr, subject, body_text, snippet FROM messages {where} ORDER BY ts DESC"
    if limit is not None:
        sql += f" LIMIT {int(limit)}"
    return conn.execute(sql).fetchall()


def process_message(conn: sqlite3.Connection, row: sqlite3.Row) -> tuple[str, str, str]:
    """Run all three pipelines for one message and persist the results."""
    kwargs = dict(
        from_addr=row["from_addr"],
        subject=row["subject"],
        body_text=row["body_text"],
        snippet=row["snippet"],
    )
    category = categorise_one(**kwargs)
    tldr = summarise_one(**kwargs)
    priority = triage_one(**kwargs)

    conn.execute(
        "UPDATE messages SET category = ?, tldr = ?, priority = ?, processed_at = ? WHERE id = ?",
        (category, tldr, priority, int(time.time()), row["id"]),
    )
    return category, priority, tldr


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Tier 1 LLM pipelines over stored email.")
    parser.add_argument("--all", action="store_true", help="re-process all messages, not just new ones")
    parser.add_argument("--limit", type=int, default=None, help="max messages to process")
    args = parser.parse_args()

    conn = get_conn()
    init_db(conn)
    rows = _select_messages(conn, all_=args.all, limit=args.limit)
    total = len(rows)
    if total == 0:
        print("Nothing to process (all messages already enriched). Use --all to redo.")
        return

    print(f"Processing {total} message(s) with the local model...\n")
    for i, row in enumerate(rows, 1):
        category, priority, tldr = process_message(conn, row)
        conn.commit()  # persist each so a crash never loses completed work
        subject = (row["subject"] or "")[:45]
        print(f"{i:>3}/{total}  [{priority:<6}] [{category:<11}] {subject:<45} | {tldr[:60]}")

    conn.close()
    print(f"\nDone. Enriched {total} message(s).")


if __name__ == "__main__":
    main()
