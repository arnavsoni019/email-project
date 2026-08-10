"""A one-slot background job runner for the long operations the UI triggers.

Syncing hits the network and enrichment runs the local model at seconds-per-email, so
neither can answer an HTTP request inside a browser's patience. Both therefore run on a
worker thread while the request returns immediately; the UI polls ``GET /api/job``.

Deliberately *one* slot: two concurrent syncs would race on the same SQLite rows and on
Gmail's historyId, and there is exactly one user. Starting a job while one runs is
refused rather than queued.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Callable

# Guards every read/write of _state below. Uvicorn serves requests from a thread pool,
# so the status endpoint and the worker genuinely touch this concurrently.
_lock = threading.Lock()

_state: dict[str, Any] = {
    "state": "idle",  # idle | running | done | error
    "kind": None,     # sync | process
    "phase": "",      # human-readable step, shown in the UI
    "done": 0,
    "total": 0,
    "error": None,
    "started": None,
    "finished": None,
}


def status() -> dict[str, Any]:
    """A snapshot of the current job. Copied so callers can't mutate live state."""
    with _lock:
        return dict(_state)


def is_running() -> bool:
    with _lock:
        return _state["state"] == "running"


def progress(*, phase: str | None = None, done: int | None = None, total: int | None = None) -> None:
    """Called from inside a job to report where it has got to."""
    with _lock:
        if phase is not None:
            _state["phase"] = phase
        if done is not None:
            _state["done"] = done
        if total is not None:
            _state["total"] = total


def start(kind: str, fn: Callable[[], None]) -> bool:
    """Run ``fn`` on a worker thread. Returns False if a job is already running."""
    with _lock:
        if _state["state"] == "running":
            return False
        _state.update(
            state="running", kind=kind, phase="starting", done=0, total=0,
            error=None, started=int(time.time()), finished=None,
        )

    def runner() -> None:
        try:
            fn()
            with _lock:
                _state.update(state="done", phase="finished", finished=int(time.time()))
        except Exception as exc:  # surfaced to the UI rather than dying silently
            with _lock:
                _state.update(
                    state="error", phase="failed", error=f"{type(exc).__name__}: {exc}",
                    finished=int(time.time()),
                )

    # daemon=True so a hung job never blocks server shutdown.
    threading.Thread(target=runner, name=f"mailorg-{kind}", daemon=True).start()
    return True
