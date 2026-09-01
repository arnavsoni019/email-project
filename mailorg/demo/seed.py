"""Build the demo mailbox.

    DB_PATH=data/demo.db CHROMA_PATH=data/demo_chroma \
        python -m mailorg.demo.seed --index

Safety
------
This script **refuses to run** unless both ``DB_PATH`` and ``CHROMA_PATH`` point at
something with "demo" in the name. The real mailbox is never opened, so no bug here can
overwrite, read or leak it — the protection is structural rather than a promise.

``--index`` also embeds the demo mail so the Ask screen works. That needs Ollama and
``nomic-embed-text``; skip it if you only want the Inbox, Digest and Queue screens.
"""

from __future__ import annotations

import argparse
import json
import sys
import time

from ..config import get_settings
from ..db import get_conn, init_db
from .data import ACTIONS, DRAFT_BODIES, MESSAGES, PERSONA_EMAIL, PERSONA_NAME

CATEGORY_COLORS = {
    "Work": "#1f6feb", "Personal": "#8250df", "Finance": "#1a7f37",
    "Receipts": "#9a6700", "Travel": "#0969da", "Newsletters": "#57606a",
    "Social": "#bf3989", "Urgent": "#cf222e",
}


def _guard() -> None:
    """Refuse to touch anything that is not obviously a demo store."""
    s = get_settings()
    problems = []
    if "demo" not in s.db_path.name.lower():
        problems.append(f"DB_PATH points at {s.db_path} — expected a path containing 'demo'")
    if "demo" not in str(s.chroma_path).lower():
        problems.append(f"CHROMA_PATH points at {s.chroma_path} — expected a path containing 'demo'")
    if problems:
        print("Refusing to seed. This looks like your real mailbox:\n", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        print(
            "\nRun it as:\n"
            "  DB_PATH=data/demo.db CHROMA_PATH=data/demo_chroma \\\n"
            "      python -m mailorg.demo.seed --index",
            file=sys.stderr,
        )
        raise SystemExit(2)


def seed() -> dict[str, int]:
    """Wipe and rebuild the demo tables. Returns counts."""
    now = int(time.time())
    conn = get_conn()
    try:
        init_db(conn)
        # Demo store only (see _guard), so a clean slate is safe and keeps reruns
        # idempotent instead of stacking duplicate rows.
        for table in ("actions", "messages", "threads", "sync_state", "categories", "app_config"):
            conn.execute(f"DELETE FROM {table}")

        for name, color in CATEGORY_COLORS.items():
            conn.execute(
                "INSERT INTO categories (name, description, color) VALUES (?, ?, ?)",
                (name, f"{name} mail", color),
            )

        ids: list[str] = []
        for i, m in enumerate(MESSAGES):
            mid = f"demo{i:04d}"
            tid = f"demothread{i:04d}"
            ts = now - int(m["h"] * 3600)
            ids.append(mid)

            labels = ["INBOX"] + (["UNREAD"] if m["unread"] else [])
            body = m["body"]
            html = m.get("html", "")

            conn.execute(
                "INSERT INTO threads (id, subject, last_message_ts, num_messages, summary,"
                " category, priority) VALUES (?, ?, ?, 1, ?, ?, ?)",
                (tid, m["subj"], ts, m["tldr"], m["cat"], m["prio"]),
            )
            conn.execute(
                "INSERT INTO messages (id, thread_id, from_addr, from_name, to_addrs,"
                " cc_addrs, subject, snippet, body_text, ts, label_ids, is_unread,"
                " size_estimate, category, tldr, priority, processed_at, body_html)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    mid, tid, m["addr"], m["name"], json.dumps([PERSONA_EMAIL]),
                    json.dumps([]), m["subj"], m["snippet"], body, ts,
                    json.dumps(labels), 1 if m["unread"] else 0,
                    len(body) + len(html) + 800, m["cat"], m["tldr"], m["prio"],
                    ts + 90, html,
                ),
            )

        for fragment, kind, status, rationale in ACTIONS:
            matches = [i for i, m in enumerate(MESSAGES) if fragment in m["subj"]]
            if len(matches) != 1:
                raise SystemExit(
                    f"ACTIONS fragment {fragment!r} matched {len(matches)} subjects "
                    f"({[MESSAGES[i]['subj'] for i in matches]}). Fragments must be unique."
                )
            idx = matches[0]
            target = ids[idx]
            msg = MESSAGES[idx]
            if kind == "label":
                payload: dict = {
                    "labelName": f"mailorg/{msg['cat']}",
                    "undo": {"removeLabelName": f"mailorg/{msg['cat']}"},
                }
            elif kind == "archive":
                payload = {"removeLabelIds": ["INBOX"], "undo": {"addLabelIds": ["INBOX"]}}
            else:
                body = DRAFT_BODIES.get(fragment)
                if not body:
                    raise SystemExit(
                        f"draft proposal {fragment!r} has no entry in DRAFT_BODIES. "
                        "The executor refuses a draft with no body, so seeding one "
                        "would queue an action that can never be applied."
                    )
                payload = {
                    "threadId": f"demothread{idx:04d}", "to": msg["addr"], "body": body,
                }

            created = now - int(MESSAGES[idx]["h"] * 3600) + 1800
            decided = created + 600 if status in {"approved", "applied", "rejected"} else None
            result = (
                json.dumps({"call": f"users.messages.modify(id={target}, removeLabelIds=['INBOX'])",
                            "removed": ["INBOX"], "appliedTs": decided})
                if status == "applied" else None
            )
            conn.execute(
                "INSERT INTO actions (type, target_id, payload, status, rationale,"
                " created_ts, decided_ts, result) VALUES (?,?,?,?,?,?,?,?)",
                (kind, target, json.dumps(payload), status, rationale, created, decided, result),
            )

        # The UI prints this in the header — seeding it is what keeps the real
        # account address off the screen recording.
        for key, value in (
            ("email_address", PERSONA_EMAIL),
            ("account_name", PERSONA_NAME),
            ("history_id", "9928431"),
            ("last_sync_ts", str(now - 240)),
        ):
            conn.execute("INSERT INTO sync_state (key, value) VALUES (?, ?)", (key, value))

        conn.commit()
        return {"messages": len(MESSAGES), "actions": len(ACTIONS)}
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the demo mailbox.")
    parser.add_argument("--index", action="store_true", help="also build the vector index (needs Ollama)")
    args = parser.parse_args()

    _guard()
    s = get_settings()
    counts = seed()
    print(f"Seeded {counts['messages']} messages and {counts['actions']} actions into {s.db_path}")
    print(f"Account shown in the UI: {PERSONA_EMAIL}")

    if args.index:
        from ..rag.index import build_index

        print("\nEmbedding for Ask (nomic-embed-text)...")
        res = build_index(rebuild=True, progress=lambda i, n: print(f"  {i}/{n}", end="\r"))
        print(f"\nIndexed {res['embedded']} messages into {res['chunks']} chunks.")


if __name__ == "__main__":
    main()
