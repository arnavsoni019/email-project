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

from ..agents.executor import (
    DemoStoreRefused,
    DryRunActive,
    WriteScopeMissing,
    apply_one,
    ensure_can_write,
)
from ..agents.proposer import _DRAFT_INSTRUCTION, _REVISE_INSTRUCTION, _can_reply
from ..config import get_settings, is_demo_store
from ..db import get_conn, init_db
from ..htmlmail import sanitize
from ..pipelines.common import format_email_for_llm
from ..providers.llm.base import get_llm
from ..privacy import effective_cloud, set_cloud_preference
from ..providers.llm.cloud import cloud_is_configured
from ..pipelines.run import _select_messages, process_message
from ..providers.email.gmail import GmailProvider
from ..rag.index import build_index
from ..rag.qa import ask
from ..sync import sync
from ..textclean import clean_body
from . import jobs

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
# The inbox shows a recent working set rather than the whole archive: enrichment is
# re-run over the newest N messages, so anything older still carries results from an
# earlier model and would make the list inconsistent to judge.
DEFAULT_LIMIT = 40


@app.get("/api/messages")
def list_messages(
    prio: str | None = None,
    cat: str | None = None,
    q: str | None = None,
    limit: int = DEFAULT_LIMIT,
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
def get_message(message_id: str, images: bool = False) -> dict[str, Any]:
    """Full message, plus the earlier messages in its thread.

    Args:
        images: load remote images in the HTML body. Off by default — remote images in
            marketing mail are tracking pixels that report the open back to the sender.
            The render frame runs no JavaScript, so this cannot be a client-side toggle;
            the UI re-requests with images=true instead.
    """
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

    raw_html = row["body_html"] if "body_html" in row.keys() else ""
    safe_html, blocked_images = sanitize(raw_html or "", allow_remote_images=images)

    data = _row_to_summary(row)
    data.update(
        {
            # Cleaned for reading; the faithful extraction stays in the DB so a future
            # "show original" toggle has something to fall back to.
            "body": clean_body(row["body_text"] or ""),
            "body_raw_len": len(row["body_text"] or ""),
            # The email as its sender designed it, stripped of anything executable.
            # Empty for genuinely plain-text mail, which the UI falls back to.
            "html": safe_html,
            "blockedImages": blocked_images,
            "imagesLoaded": images,
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
        # Counted over the same working set the inbox lists, so the sidebar numbers
        # always add up to what the user can actually see.
        recent = f"(SELECT * FROM messages ORDER BY ts DESC LIMIT {DEFAULT_LIMIT})"
        prio_counts = {
            r["priority"]: r["n"]
            for r in conn.execute(
                f"SELECT priority, COUNT(*) n FROM {recent} WHERE priority IS NOT NULL GROUP BY priority"
            )
        }
        cat_counts = {
            r["category"]: r["n"]
            for r in conn.execute(
                f"SELECT category, COUNT(*) n FROM {recent} WHERE category IS NOT NULL GROUP BY category"
            )
        }
        total = conn.execute(f"SELECT COUNT(*) n FROM {recent}").fetchone()["n"]
        unprocessed = conn.execute(
            f"SELECT COUNT(*) n FROM {recent} WHERE processed_at IS NULL"
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

    enabled, tasks, has_ceiling = effective_cloud(s)
    return {
        # Live values (the .env ceiling narrowed by the UI switch), not raw .env.
        "cloud_enabled": enabled,
        "cloud_allowed_tasks": sorted(tasks),
        # What the switch is *permitted* to turn on, so the UI can grey out the rest
        # and explain an inert toggle rather than dropping clicks silently.
        "cloud_allowed_ceiling": sorted(s.cloud_allowed_tasks),
        "cloud_configurable": has_ceiling,
        # Enough to show where text would go. The key itself is never returned.
        "cloud_model": s.cloud_model,
        "cloud_base_url": s.cloud_base_url,
        "cloud_key_present": cloud_is_configured(),
        "model_light": s.model_light,
        "model_heavy": s.model_heavy,
        "ollama_host": s.ollama_host,
        "ollama_connected": ollama_ok,
        "categories": s.categories,
    }


@app.put("/api/settings")
def update_settings(patch: SettingsPatch) -> dict[str, Any]:
    """Flip the cloud switch from the UI.

    Cannot grant more than ``.env`` permits: ``set_cloud_preference`` intersects with
    ``cloud_allowed_tasks`` on write, and ``effective_cloud`` intersects again on read.
    """
    set_cloud_preference(enabled=patch.cloud_enabled, tasks=patch.cloud_allowed_tasks)
    return read_settings()


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


def _build_draft_payload(conn: sqlite3.Connection, target_id: str) -> dict[str, Any]:
    """Write the reply now, so the queue card shows text a human can actually judge.

    Drafting at propose time rather than at execute time is the whole point of
    propose->approve: approving a draft you have not read is not a review. It costs a
    few seconds on the click, which is why the button reports a drafting state.
    """
    row = conn.execute(
        "SELECT thread_id, from_addr, subject, body_text, snippet FROM messages WHERE id = ?",
        (target_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="message not found")

    to = (row["from_addr"] or "").strip()
    if not _can_reply(to):
        raise HTTPException(
            status_code=400,
            detail=f"{to or 'this sender'} is an unattended mailbox — a reply would bounce.",
        )

    block = format_email_for_llm(
        from_addr=row["from_addr"], subject=row["subject"],
        body_text=row["body_text"], snippet=row["snippet"],
    )
    body = str(get_llm("draft", heavy=True).invoke(f"{_DRAFT_INSTRUCTION}\n\n{block}").content).strip()
    if not body:
        raise HTTPException(status_code=502, detail="the model returned an empty draft")

    return {"threadId": row["thread_id"], "to": to, "body": body}


@app.post("/api/actions")
def create_action(action: ActionCreate) -> dict[str, Any]:
    """Queue a proposed action. Never touches Gmail — the executor applies it later."""
    conn = get_conn()
    try:
        payload = dict(action.payload or {})
        # A draft with no body is the one proposal that cannot be reviewed and cannot be
        # applied: create_draft() would happily produce a Gmail draft addressed to the
        # literal string "None". Fill it in here instead of discovering it at write time.
        if action.type == "draft" and not payload.get("body"):
            payload = {**_build_draft_payload(conn, action.target_id), **payload}

        cur = conn.execute(
            "INSERT INTO actions (type, target_id, payload, rationale, created_ts) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                action.type,
                action.target_id,
                json.dumps(payload),
                action.rationale,
                int(time.time()),
            ),
        )
        conn.commit()
        return {"id": cur.lastrowid, "status": "proposed"}
    finally:
        conn.close()


# --- inbox draft composer -----------------------------------------------------
# Generation and revision persist nothing: a reply you are still working on is not a
# proposal, and half-written drafts should not accumulate in the approval queue. Only
# /save writes a row, and it writes one that is already approved — you reviewed the text
# in the composer, so a second approval would be reviewing your own edit.
class DraftRequest(BaseModel):
    target_id: str


class ReviseRequest(BaseModel):
    target_id: str
    draft: str
    feedback: str


class DraftSaveRequest(BaseModel):
    target_id: str
    body: str


def _message_for_draft(conn: sqlite3.Connection, target_id: str) -> sqlite3.Row:
    row = conn.execute(
        "SELECT thread_id, from_addr, subject, body_text, snippet FROM messages WHERE id = ?",
        (target_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="message not found")
    return row


@app.post("/api/draft")
def generate_draft(req: DraftRequest) -> dict[str, Any]:
    """Write a first reply. Nothing is stored — the composer holds it."""
    conn = get_conn()
    try:
        return {"body": _build_draft_payload(conn, req.target_id)["body"]}
    finally:
        conn.close()


@app.post("/api/draft/revise")
def revise_draft(req: ReviseRequest) -> dict[str, Any]:
    """Apply one instruction to an existing draft, preserving the rest."""
    feedback = (req.feedback or "").strip()
    if not feedback:
        raise HTTPException(status_code=400, detail="say what should change")
    if not (req.draft or "").strip():
        raise HTTPException(status_code=400, detail="there is no draft to revise")

    conn = get_conn()
    try:
        row = _message_for_draft(conn, req.target_id)
    finally:
        conn.close()

    block = format_email_for_llm(
        from_addr=row["from_addr"], subject=row["subject"],
        body_text=row["body_text"], snippet=row["snippet"],
    )
    prompt = (
        f"{_REVISE_INSTRUCTION}\n\n{block}\n\n"
        f"Your current reply:\n{req.draft.strip()}\n\n"
        f"The change to make:\n{feedback}"
    )
    body = str(get_llm("draft", heavy=True).invoke(prompt).content).strip()
    if not body:
        raise HTTPException(status_code=502, detail="the model returned an empty revision")
    return {"body": body}


@app.post("/api/draft/save")
def save_draft(req: DraftSaveRequest) -> dict[str, Any]:
    """Save the composed reply into Gmail as a draft. Never sends.

    Routed through ``executor.apply_one`` rather than the Gmail provider so the write
    still passes the executor's guards and lands in the ``actions`` audit trail.
    """
    body = (req.body or "").strip()
    if not body:
        raise HTTPException(status_code=400, detail="the draft is empty")

    # Before writing any row. An approved row created for a save that then turns out to
    # be forbidden would sit in the queue armed for the next --live run.
    try:
        ensure_can_write()
    except DemoStoreRefused as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except DryRunActive as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except WriteScopeMissing as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    conn = get_conn()
    try:
        row = _message_for_draft(conn, req.target_id)
        to = (row["from_addr"] or "").strip()
        if not _can_reply(to):
            raise HTTPException(
                status_code=400,
                detail=f"{to or 'this sender'} is an unattended mailbox — a reply would bounce.",
            )
        cur = conn.execute(
            "INSERT INTO actions (type, target_id, payload, status, rationale, created_ts, decided_ts) "
            "VALUES ('draft', ?, ?, 'approved', ?, ?, ?)",
            (
                req.target_id,
                json.dumps({"threadId": row["thread_id"], "to": to, "body": body}),
                "Composed and reviewed in the reading pane.",
                int(time.time()), int(time.time()),
            ),
        )
        conn.commit()
        action_id = cur.lastrowid
    finally:
        conn.close()

    try:
        # apply_one re-checks and marks the row 'failed' if Gmail itself rejects it, so
        # a genuine attempt stays in the audit trail rather than vanishing.
        result = apply_one(int(action_id))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"{type(exc).__name__}: {exc}") from exc
    return {"actionId": action_id, "draftId": result.get("draftId"), "to": to}


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


# --- long-running jobs: sync from Gmail, enrich with the local model -----------
class SyncRequest(BaseModel):
    full: bool = False
    max_messages: int | None = 50
    # Enriching straight after syncing is what the Sync button means to a user;
    # new mail with no TL;DR would otherwise appear as blank rows.
    process: bool = True


class ProcessRequest(BaseModel):
    all: bool = False
    limit: int | None = None


def _run_process(*, all_: bool, limit: int | None) -> None:
    """Enrich messages, reporting progress. Mirrors ``pipelines.run.main``'s loop.

    The loop lives here rather than calling ``main()`` because ``main`` parses argv and
    prints to stdout; the per-message work itself is the shared ``process_message``.
    """
    conn = get_conn()
    try:
        init_db(conn)
        rows = _select_messages(conn, all_=all_, limit=limit)
        jobs.progress(phase="enriching", done=0, total=len(rows))
        for i, row in enumerate(rows, 1):
            process_message(conn, row)
            conn.commit()  # persist each, so a crash never loses completed work
            jobs.progress(done=i)
    finally:
        conn.close()


@app.post("/api/sync")
def start_sync(req: SyncRequest) -> dict[str, Any]:
    """Fetch new mail from Gmail, then (by default) enrich whatever arrived."""
    # Syncing into the demo store would pull the owner's real mail — real senders, real
    # subjects — into the synthetic mailbox, which is the exact disclosure the demo
    # exists to prevent, and it cannot be undone without reseeding.
    if is_demo_store():
        raise HTTPException(
            status_code=409,
            detail="This is the demo mailbox. Syncing would pull your real mail into it. "
                   "Run scripts/demo.sh real to switch back first.",
        )

    def work() -> None:
        conn = get_conn()
        try:
            init_db(conn)
            jobs.progress(phase="contacting Gmail")
            provider = GmailProvider()
            sync(provider, conn, full=req.full, max_messages=req.max_messages)
        finally:
            conn.close()
        if req.process:
            _run_process(all_=False, limit=None)

    if not jobs.start("sync", work):
        raise HTTPException(status_code=409, detail="a job is already running")
    return jobs.status()


@app.post("/api/process")
def start_process(req: ProcessRequest) -> dict[str, Any]:
    """Run the Tier 1 pipelines over stored messages. No network, no mailbox writes."""
    if not jobs.start("process", lambda: _run_process(all_=req.all, limit=req.limit)):
        raise HTTPException(status_code=409, detail="a job is already running")
    return jobs.status()


@app.get("/api/job")
def job_status() -> dict[str, Any]:
    """Poll target for the UI's progress indicator."""
    return jobs.status()


# --- semantic search / Q&A (Phase 4) ----------------------------------------
class IndexRequest(BaseModel):
    rebuild: bool = False
    limit: int | None = DEFAULT_LIMIT


class AskRequest(BaseModel):
    question: str
    k: int | None = None


@app.post("/api/index")
def start_index(req: IndexRequest) -> dict[str, Any]:
    """Embed messages into the vector store. Local-only; no mailbox writes."""

    def work() -> None:
        jobs.progress(phase="embedding")
        build_index(
            rebuild=req.rebuild,
            limit=req.limit,
            progress=lambda done, total: jobs.progress(done=done, total=total),
        )

    if not jobs.start("index", work):
        raise HTTPException(status_code=409, detail="a job is already running")
    return jobs.status()


@app.post("/api/ask")
def ask_question(req: AskRequest) -> dict[str, Any]:
    """Answer a question from indexed mail, returning the sources it drew on.

    Synchronous on purpose: unlike sync/enrichment this is one call the user is actively
    waiting on, and it returns in seconds rather than minutes.
    """
    if not req.question.strip():
        raise HTTPException(status_code=422, detail="question is required")
    return ask(req.question, k=req.k)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
