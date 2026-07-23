"""SQLite storage layer for mailorg.

The whole database is a single local file (``data/mailorg.db``) — no server, nothing
listening on a port. That keeps the app fully local/private and simple to reason about.

``init_db()`` is idempotent (``CREATE TABLE IF NOT EXISTS``), so it is safe to call on
every startup. LLM-derived columns on ``messages`` (category/tldr/priority) start NULL
and are filled in later as pipelines process each email.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .config import get_settings

# --- Schema -----------------------------------------------------------------
# Timestamps are stored as INTEGER unix-epoch seconds (portable, easy to sort).
# List-valued fields (to_addrs, label_ids, ...) are stored as JSON text.
SCHEMA = """
CREATE TABLE IF NOT EXISTS threads (
    id               TEXT PRIMARY KEY,      -- Gmail thread id
    subject          TEXT,
    last_message_ts  INTEGER,
    num_messages     INTEGER DEFAULT 0,
    summary          TEXT,                  -- LLM thread summary (Phase 2), nullable
    category         TEXT,
    priority         TEXT
);

CREATE TABLE IF NOT EXISTS messages (
    id             TEXT PRIMARY KEY,        -- Gmail message id
    thread_id      TEXT,
    from_addr      TEXT,
    to_addrs       TEXT,                    -- JSON array
    cc_addrs       TEXT,                    -- JSON array
    subject        TEXT,
    snippet        TEXT,                    -- Gmail's short preview
    body_text      TEXT,                    -- extracted plain-text body
    ts             INTEGER,                 -- unix epoch seconds
    label_ids      TEXT,                    -- JSON array of Gmail label ids
    is_unread      INTEGER DEFAULT 0,       -- 0/1 boolean
    size_estimate  INTEGER,
    -- LLM-derived, filled in by Phase 2 pipelines; NULL until processed:
    category       TEXT,
    tldr           TEXT,
    priority       TEXT,                    -- 'action' | 'fyi' | 'ignore'
    processed_at   INTEGER,
    FOREIGN KEY (thread_id) REFERENCES threads(id)
);

CREATE INDEX IF NOT EXISTS idx_messages_thread   ON messages(thread_id);
CREATE INDEX IF NOT EXISTS idx_messages_ts       ON messages(ts);
CREATE INDEX IF NOT EXISTS idx_messages_category ON messages(category);

-- Key/value store for sync bookkeeping, e.g. Gmail History API 'historyId'.
CREATE TABLE IF NOT EXISTS sync_state (
    key    TEXT PRIMARY KEY,
    value  TEXT
);

-- Category taxonomy (seeded from Settings.categories; user-editable later).
CREATE TABLE IF NOT EXISTS categories (
    name         TEXT PRIMARY KEY,
    description  TEXT,
    color        TEXT
);

-- Propose->approve queue. The agent INSERTs 'proposed' rows and never mutates Gmail
-- directly; an executor applies a row only after the user approves it (Phase 5).
CREATE TABLE IF NOT EXISTS actions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    type        TEXT NOT NULL,             -- 'label' | 'archive' | 'draft' | ...
    target_id   TEXT,                      -- message or thread id
    payload     TEXT,                      -- JSON: action-specific details
    status      TEXT NOT NULL DEFAULT 'proposed',  -- proposed|approved|rejected|applied|failed
    rationale   TEXT,                      -- why the agent proposed it (for the UI)
    created_ts  INTEGER NOT NULL,
    decided_ts  INTEGER,
    result      TEXT
);

CREATE INDEX IF NOT EXISTS idx_actions_status ON actions(status);
"""


def get_conn(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Open (creating parent dirs as needed) a connection to the SQLite database.

    Rows come back as ``sqlite3.Row`` so columns are accessible by name
    (``row["subject"]``). WAL journal mode allows reads during writes.
    """
    path = Path(db_path) if db_path is not None else get_settings().db_path
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db(conn: sqlite3.Connection | None = None) -> None:
    """Create tables (idempotent) and seed the category taxonomy from settings."""
    own_conn = conn is None
    if own_conn:
        conn = get_conn()
    try:
        conn.executescript(SCHEMA)
        conn.executemany(
            "INSERT OR IGNORE INTO categories(name) VALUES (?)",
            [(c,) for c in get_settings().categories],
        )
        conn.commit()
    finally:
        if own_conn:
            conn.close()


if __name__ == "__main__":
    # Allow `python -m mailorg.db` to initialise the database from the CLI.
    init_db()
    print(f"Initialised database at {get_settings().db_path}")
