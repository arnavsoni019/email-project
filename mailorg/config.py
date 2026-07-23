"""Central, typed configuration for mailorg.

Everything configurable lives here as one validated ``Settings`` object. Values come
from environment variables / a local ``.env`` file (see ``.env.example``). Because the
fields are typed, a bad value fails at startup rather than surfacing as a mysterious bug
later.

This module is also where the **privacy policy** is enforced: cloud LLM use is gated by
a global switch (``cloud_enabled``) *and* a per-task allowlist (``cloud_allowed_tasks``).
Both must permit a task before any of its text may leave the machine.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repository root (two levels up from this file: mailorg/config.py -> repo root).
REPO_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """All runtime configuration, loaded from the environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- Local LLM (Ollama) -------------------------------------------------
    # Reachable over the shared network at localhost even from the Flatpak sandbox.
    ollama_host: str = "http://localhost:11434"
    # Two-tier split sized around the RTX 4060's 8 GB VRAM.
    model_light: str = "gemma4:e4b"   # resident, used for bulk work (categorise/triage)
    model_heavy: str = "gemma4:12b"   # loaded on demand for harder single tasks
    embed_model: str = "nomic-embed-text"  # Phase 4 (RAG) — not pulled yet

    # ---- Storage ------------------------------------------------------------
    db_path: Path = REPO_ROOT / "data" / "mailorg.db"

    # ---- Privacy / cloud opt-in ---------------------------------------------
    # Master switch. When False, NOTHING may ever call the cloud, regardless of the
    # allowlist below. Default False = 100% local.
    cloud_enabled: bool = False
    # Per-task allowlist. Even with cloud_enabled=True, only these task names may use
    # the cloud (e.g. {"draft", "qa"}). Empty = nothing is cloud-eligible.
    cloud_allowed_tasks: set[str] = Field(default_factory=set)
    # Only read when a cloud task actually runs (Phase 6).
    anthropic_api_key: str | None = None

    # ---- Gmail (OAuth) ------------------------------------------------------
    # Path to the OAuth "installed app" client secrets downloaded from Google Cloud.
    google_client_secrets: Path = REPO_ROOT / "data" / "client_secret.json"
    # Where the user's OAuth token is cached after first login.
    google_token_path: Path = REPO_ROOT / "data" / "token.json"
    # Start read-only (Phase 1). Phase 5 adds gmail.modify (labels/archive) and
    # gmail.compose (drafts) — widen scopes only when those phases land.
    gmail_scopes: list[str] = Field(
        default_factory=lambda: ["https://www.googleapis.com/auth/gmail.readonly"]
    )

    # ---- Category taxonomy --------------------------------------------------
    # Starting set from the plan; adjustable. Used by the categorise pipeline (Phase 2).
    categories: list[str] = Field(
        default_factory=lambda: [
            "Work",
            "Personal",
            "Finance",
            "Receipts",
            "Travel",
            "Newsletters",
            "Social",
            "Urgent",
        ]
    )

    def may_use_cloud(self, task: str) -> bool:
        """Return True only if BOTH the master switch and the allowlist permit ``task``.

        This is the single choke point every cloud call must pass through.
        """
        return self.cloud_enabled and task in self.cloud_allowed_tasks


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (read the environment once per process)."""
    return Settings()
