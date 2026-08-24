"""The single decision point for whether a task may leave this machine.

``Settings`` carries the values from ``.env``, but the user also needs a switch in the
UI. Those two sources are combined here, with one rule that is not negotiable:

    **`.env` sets the ceiling; the UI switch can only stay under it.**

So ``CLOUD_ALLOWED_TASKS=ask,draft`` means the UI can enable *ask*, *draft*, both, or
neither — never *summarise*. A stored preference can therefore never widen what the
machine's owner configured, which matters because the store is a local SQLite file that
any code in the process can write.

Everything routes through ``may_use_cloud``; ``providers.llm.base.get_llm`` is its only
caller, so there is exactly one place where local-vs-cloud is decided.
"""

from __future__ import annotations

import json
import sqlite3

from .config import Settings, get_settings
from .db import get_conn

# Keys in the app_config table.
_ENABLED_KEY = "cloud_enabled"
_TASKS_KEY = "cloud_allowed_tasks"


def _read(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM app_config WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def effective_cloud(settings: Settings | None = None) -> tuple[bool, set[str], bool]:
    """Resolve the live cloud policy.

    Returns:
        (enabled, allowed_tasks, ceiling_allows_anything)

    ``ceiling_allows_anything`` tells the UI whether the switch can do anything at all,
    so it can explain an inert toggle instead of silently ignoring clicks.
    """
    settings = settings or get_settings()
    ceiling = set(settings.cloud_allowed_tasks)

    enabled = settings.cloud_enabled
    tasks = set(ceiling)
    try:
        conn = get_conn()
        try:
            raw_enabled = _read(conn, _ENABLED_KEY)
            raw_tasks = _read(conn, _TASKS_KEY)
        finally:
            conn.close()
        if raw_enabled is not None:
            enabled = raw_enabled == "1"
        if raw_tasks is not None:
            # Intersect, never union: the stored preference narrows, never widens.
            tasks = set(json.loads(raw_tasks)) & ceiling
    except Exception:
        # A missing or unreadable store must fail closed to the .env values, never open.
        pass

    return enabled, tasks, bool(ceiling)


def set_cloud_preference(*, enabled: bool | None, tasks: list[str] | None) -> None:
    """Persist the UI switch. Values are clamped to the .env ceiling on write as well
    as on read, so a stale row can never grant more than configured."""
    settings = get_settings()
    ceiling = set(settings.cloud_allowed_tasks)

    conn = get_conn()
    try:
        if enabled is not None:
            conn.execute(
                "INSERT INTO app_config (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (_ENABLED_KEY, "1" if enabled else "0"),
            )
        if tasks is not None:
            allowed = sorted(set(tasks) & ceiling)
            conn.execute(
                "INSERT INTO app_config (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (_TASKS_KEY, json.dumps(allowed)),
            )
        conn.commit()
    finally:
        conn.close()


def may_use_cloud(task: str, settings: Settings | None = None) -> bool:
    """True only if the master switch is on AND ``task`` is allowed by both layers."""
    enabled, tasks, _ = effective_cloud(settings)
    return enabled and task in tasks
