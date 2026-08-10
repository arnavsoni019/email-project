"""Fetch the original text/html for messages synced before it was stored.

Phase 1–4 kept only the flattened text. Rendering the email the way Gmail does needs
the HTML part, and re-syncing everything would be wasteful — the rest of each row is
already correct. This re-fetches only the messages missing ``body_html`` and updates
that one column.

    python -m mailorg.backfill_html              # every message missing HTML
    python -m mailorg.backfill_html --limit 40   # only the newest N

Safe to interrupt and re-run: each message commits on its own, and finished ones are
skipped on the next pass.
"""

from __future__ import annotations

import argparse

from .db import get_conn, init_db
from .providers.email.gmail import GmailProvider


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill original HTML bodies from Gmail.")
    parser.add_argument("--limit", type=int, default=None, help="only the newest N messages")
    args = parser.parse_args()

    conn = get_conn()
    init_db(conn)  # ensures the body_html column exists before we write to it
    sql = "SELECT id, subject FROM messages WHERE body_html IS NULL OR body_html = '' ORDER BY ts DESC"
    if args.limit:
        sql += f" LIMIT {int(args.limit)}"
    rows = conn.execute(sql).fetchall()

    if not rows:
        print("Nothing to backfill — every message already has its HTML.")
        conn.close()
        return

    provider = GmailProvider()
    provider.authenticate()
    print(f"Backfilling HTML for {len(rows)} message(s)...\n")

    filled = plain_only = 0
    for i, row in enumerate(rows, 1):
        try:
            msg = provider.get_message(row["id"])
        except Exception as exc:  # one bad message must not abort the run
            print(f"{i:>3}/{len(rows)}  SKIP {row['id']}: {type(exc).__name__}: {exc}")
            continue
        conn.execute("UPDATE messages SET body_html = ? WHERE id = ?", (msg.body_html, row["id"]))
        conn.commit()
        if msg.body_html:
            filled += 1
        else:
            plain_only += 1
        print(f"{i:>3}/{len(rows)}  {len(msg.body_html):>7} chars  {(row['subject'] or '')[:52]}")

    conn.close()
    # A genuinely plain-text email (a real person writing to you) has no HTML part at
    # all; that is not a failure, and the reader falls back to the text view.
    print(f"\nDone. {filled} with HTML, {plain_only} plain-text only.")


if __name__ == "__main__":
    main()
