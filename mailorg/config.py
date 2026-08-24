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
    # Benchmarked on the 4060 (8 GB): qwen3.5:9b fits 100% in VRAM at 2.3 s/email, vs
    # gemma4:e4b 12.6 s and gemma4:12b-it-qat 92.4 s (the latter two spill or thrash).
    # Its reasoning mode must stay OFF for bulk work — see get_light_llm().
    model_light: str = "qwen3.5:9b"          # resident, used for bulk work (categorise/triage)
    model_heavy: str = "gemma4:12b-it-qat"   # on-demand; revisit once Phase 4 Ask exists
    embed_model: str = "nomic-embed-text"    # Phase 4 (RAG) — 768-dim vectors

    # ---- Storage ------------------------------------------------------------
    db_path: Path = REPO_ROOT / "data" / "mailorg.db"
    # ChromaDB persists the vector index here. SQLite stays the system of record; this
    # is a derived index that can be deleted and rebuilt at any time.
    chroma_path: Path = REPO_ROOT / "data" / "chroma"

    # ---- RAG tuning ---------------------------------------------------------
    # How many chunks to retrieve per question. Too few misses the answer; too many
    # dilutes the prompt and slows the (already slow) heavy model.
    rag_top_k: int = 6

    # ---- Privacy / cloud opt-in ---------------------------------------------
    # Master switch. When False, NOTHING may ever call the cloud, regardless of the
    # allowlist below. Default False = 100% local.
    cloud_enabled: bool = False
    # Per-task allowlist. Even with cloud_enabled=True, only these task names may use
    # the cloud (e.g. {"draft", "ask"}). Empty = nothing is cloud-eligible.
    cloud_allowed_tasks: set[str] = Field(default_factory=set)

    # OpenRouter, DeepSeek, Together and most hosted providers speak the OpenAI wire
    # format, so one client covers them all and switching provider is an .env edit.
    cloud_base_url: str = "https://openrouter.ai/api/v1"
    # Namespaced on OpenRouter ("deepseek/deepseek-chat"); a bare id direct from a vendor.
    cloud_model: str = "deepseek/deepseek-chat"
    # Read only when a cloud task actually runs. Never returned by the API.
    cloud_api_key: str | None = None
    # Sent by OpenRouter for attribution in its dashboard; harmless elsewhere.
    cloud_app_title: str = "mailorg"

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

    # ---- Agent actions (Phase 5) --------------------------------------------
    # When True (the default) the executor computes exactly what it *would* send to
    # Gmail and records it, without calling the API. Going live is a deliberate act:
    # it also requires widening gmail_scopes to gmail.modify and re-authenticating.
    actions_dry_run: bool = True
    # Ceiling on how many approved actions one executor run may apply. A bug that
    # proposes badly should be able to touch a handful of messages, not the mailbox.
    actions_batch_limit: int = 25
    # Whether the proposer may suggest draft replies. Off: the rule that produced them
    # ("priority is action") conflates needing attention with needing a written reply,
    # and every draft it generated targeted an unattended mailbox. Turn back on once a
    # model can be asked directly whether a reply is wanted (Phase 6).
    propose_drafts: bool = False

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
