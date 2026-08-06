"""FastAPI JSON API for the mailorg web UI.

Read paths query the SQLite store directly. Write paths reuse the existing engine
(``mailorg.sync``, ``mailorg.pipelines.run``) so there is one implementation of each
behaviour. Nothing here can reach a cloud model: every LLM call still goes through
``get_llm()``, which enforces ``Settings.may_use_cloud()``.

Run with:  uvicorn mailorg.web.api:app --reload --port 8000
"""

from __future__ import annotations

import json
import sqlite3
import time
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ..config import get_settings
from ..db import get_conn, init_db
from ..textclean import clean_body

app = FastAPI(title="mailorg", version="0.1.0")

# The Vite dev server runs on a different port during development, so the browser
# needs CORS permission to call this API. Both are on localhost only.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    conn = get_conn()
    try:
        init_db(conn)  # applies migrations too
    finally:
        conn.close()


# --- helpers ----------------------------------------------------------------
def _rel_time(ts: int | None) -> str:
    """Compact relative time the UI shows in list rows ('2h', '1d')."""
    if not ts:
        return ""
    delta = max(0, int(time.time()) - ts)
    if delta < 3600:
        return f"{max(1, delta // 60)}m"
    if delta < 86400:
        return f"{delta // 3600}h"
    return f"{delta // 86400}d"


def _exact_time(ts: int | None) -> str:
    """Full timestamp revealed on hover."""
    if not ts:
        return ""
    return time.strftime("%a, %d %b, %I:%M %p", time.localtime(ts))


def _sender(row: sqlite3.Row) -> str:
    """Human-readable sender: the display name, else a guess from the domain.

    Falling back to the domain ("ship-confirm@ajio.com" -> "Ajio") reads far better in
    the list than the local part, which is usually a no-reply mailbox name.
    """
    name = (row["from_name"] or "").strip() if "from_name" in row.keys() else ""
    if name:
        return name
    addr = row["from_addr"] or ""
    if "@" not in addr:
        return addr or "(unknown)"
    domain = addr.split("@")[1]
    labels = [p for p in domain.split(".") if p not in {"com", "net", "org", "co", "in", "io"}]
    return labels[-1].title() if labels else domain


def _row_to_summary(row: sqlite3.Row) -> dict[str, Any]:
    """Shape a message row the way the inbox list needs it."""
    return {
        "id": row["id"],
        "threadId": row["thread_id"],
        "sender": _sender(row),
        "email": row["from_addr"],
        "subject": row["subject"] or "(no subject)",
        "tldr": row["tldr"] or row["snippet"] or "",
        "cat": row["category"] or "",
        "prio": row["priority"] or "fyi",
        "time": _rel_time(row["ts"]),
        "exact": _exact_time(row["ts"]),
        "unread": bool(row["is_unread"]),
        "processed": row["processed_at"] is not None,
    }


# --- messages ---------------------------------------------------------------
@app.get("/api/messages")
def list_messages(
    prio: str | None = None,
    cat: str | None = None,
    q: str | None = None,
    limit: int = 200,
) -> dict[str, Any]:
    """Inbox list, newest first, with optional priority/category/search filters."""
    sql = "SELECT * FROM messages WHERE 1=1"
    params: list[Any] = []
    if prio:
        sql += " AND priority = ?"
        params.append(prio)
    if cat:
        sql += " AND category = ?"
        params.append(cat)
    if q:
        sql += " AND (subject LIKE ? OR tldr LIKE ? OR from_addr LIKE ? OR from_name LIKE ?)"
        needle = f"%{q}%"
        params += [needle, needle, needle, needle]
    sql += " ORDER BY ts DESC LIMIT ?"
    params.append(limit)

    conn = get_conn()
    try:
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()
    return {"messages": [_row_to_summary(r) for r in rows]}


@app.get("/api/messages/{message_id}")
def get_message(message_id: str) -> dict[str, Any]:
    """Full message, plus the earlier messages in its thread."""
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="message not found")
        earlier_rows = conn.execute(
            "SELECT * FROM messages WHERE thread_id = ? AND id != ? ORDER BY ts DESC",
            (row["thread_id"], message_id),
        ).fetchall()
    finally:
        conn.close()

    data = _row_to_summary(row)
    data.update(
        {
            # Cleaned for reading; the faithful extraction stays in the DB so a future
            # "show original" toggle has something to fall back to.
            "body": clean_body(row["body_text"] or ""),
            "body_raw_len": len(row["body_text"] or ""),
            "to": json.loads(row["to_addrs"] or "[]"),
            "cc": json.loads(row["cc_addrs"] or "[]"),
            "n": len(earlier_rows) + 1,
            "earlier": [
                {
                    "who": _sender(r),
                    "line": (r["tldr"] or r["snippet"] or "")[:160],
                    "when": _rel_time(r["ts"]),
                }
                for r in earlier_rows
            ],
        }
    )
    return data


# --- stats ------------------------------------------------------------------
@app.get("/api/stats")
def stats() -> dict[str, Any]:
    """Sidebar counts: per-priority and per-category, plus sync metadata."""
    settings = get_settings()
    conn = get_conn()
    try:
        prio_counts = {
            r["priority"]: r["n"]
            for r in conn.execute(
                "SELECT priority, COUNT(*) n FROM messages WHERE priority IS NOT NULL GROUP BY priority"
            )
        }
        cat_counts = {
            r["category"]: r["n"]
            for r in conn.execute(
                "SELECT category, COUNT(*) n FROM messages WHERE category IS NOT NULL GROUP BY category"
            )
        }
        total = conn.execute("SELECT COUNT(*) n FROM messages").fetchone()["n"]
        unprocessed = conn.execute(
            "SELECT COUNT(*) n FROM messages WHERE processed_at IS NULL"
        ).fetchone()["n"]
        sync_rows = {r["key"]: r["value"] for r in conn.execute("SELECT key, value FROM sync_state")}
    finally:
        conn.close()

    return {
        "total": total,
        "unprocessed": unprocessed,
        "priorities": [
            {"id": "action", "t": "Needs Action", "k": prio_counts.get("action", 0)},
            {"id": "fyi", "t": "FYI", "k": prio_counts.get("fyi", 0)},
            {"id": "ignore", "t": "Ignore", "k": prio_counts.get("ignore", 0)},
        ],
        # Preserve the configured category order so the sidebar is stable.
        "categories": [{"n": c, "k": cat_counts.get(c, 0)} for c in settings.categories],
        "account": sync_rows.get("email_address", ""),
    }


# --- settings ---------------------------------------------------------------
class SettingsPatch(BaseModel):
    cloud_enabled: bool | None = None
    cloud_allowed_tasks: list[str] | None = None


@app.get("/api/settings")
def read_settings() -> dict[str, Any]:
    """Expose the privacy gate and model config. Never returns the API key."""
    s = get_settings()
    ollama_ok = False
    try:
        ollama_ok = httpx.get(f"{s.ollama_host}/api/version", timeout=2).status_code == 200
    except Exception:
        ollama_ok = False
    return {
        "cloud_enabled": s.cloud_enabled,
        "cloud_allowed_tasks": sorted(s.cloud_allowed_tasks),
        "model_light": s.model_light,
        "model_heavy": s.model_heavy,
        "ollama_host": s.ollama_host,
        "ollama_connected": ollama_ok,
        "categories": s.categories,
    }


# --- actions (propose -> approve queue) -------------------------------------
class ActionCreate(BaseModel):
    type: str
    target_id: str
    payload: dict[str, Any] | None = None
    rationale: str | None = None


@app.get("/api/actions")
def list_actions(status: str | None = None) -> dict[str, Any]:
    sql = "SELECT * FROM actions"
    params: list[Any] = []
    if status:
        sql += " WHERE status = ?"
        params.append(status)
    sql += " ORDER BY created_ts DESC"
    conn = get_conn()
    try:
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()
    return {
        "actions": [
            {
                "id": r["id"],
                "type": r["type"],
                "targetId": r["target_id"],
                "payload": json.loads(r["payload"] or "{}"),
                "status": r["status"],
                "rationale": r["rationale"] or "",
                "createdTs": r["created_ts"],
            }
            for r in rows
        ]
    }


@app.post("/api/actions")
def create_action(action: ActionCreate) -> dict[str, Any]:
    """Queue a proposed action. Never touches Gmail — approval happens in Phase 5."""
    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO actions (type, target_id, payload, rationale, created_ts) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                action.type,
                action.target_id,
                json.dumps(action.payload or {}),
                action.rationale,
                int(time.time()),
            ),
        )
        conn.commit()
        return {"id": cur.lastrowid, "status": "proposed"}
    finally:
        conn.close()


@app.post("/api/actions/{action_id}/decide")
def decide_action(action_id: int, approve: bool) -> dict[str, Any]:
    """Approve or reject a proposal.

    Phase 3 only records the decision; applying approved actions to Gmail is Phase 5,
    so nothing in the mailbox changes yet.
    """
    conn = get_conn()
    try:
        row = conn.execute("SELECT id FROM actions WHERE id = ?", (action_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="action not found")
        status = "approved" if approve else "rejected"
        conn.execute(
            "UPDATE actions SET status = ?, decided_ts = ? WHERE id = ?",
            (status, int(time.time()), action_id),
        )
        conn.commit()
        return {"id": action_id, "status": status}
    finally:
        conn.close()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
