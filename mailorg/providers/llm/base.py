"""The single entry point for obtaining an LLM — and the privacy choke point.

Every pipeline calls ``get_llm(task, ...)`` instead of constructing a model directly.
That guarantees there is exactly ONE place where local-vs-cloud is decided, gated by
``Settings.may_use_cloud(task)``. Cloud can never be reached unless both the master
switch and the per-task allowlist permit it.

Returns a LangChain ``BaseChatModel`` so callers can uniformly use ``.invoke()`` and
``.with_structured_output()`` regardless of which backend answered.
"""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel

from ...config import Settings, get_settings
from .ollama import get_heavy_llm, get_light_llm


def get_llm(task: str, *, heavy: bool = False, settings: Settings | None = None) -> BaseChatModel:
    """Return a chat model for ``task``.

    Args:
        task: logical task name (e.g. "categorise", "summarise", "draft"). Used only to
            consult the cloud allowlist — it does not change the local model chosen.
        heavy: use the larger local model (gemma4:12b) instead of the light one.
    """
    settings = settings or get_settings()

    if settings.may_use_cloud(task):
        # Phase 6 will wire langchain-anthropic here, behind this exact gate.
        raise NotImplementedError(
            f"Task {task!r} is cloud-eligible, but the cloud backend is not wired until "
            "Phase 6. Disable it via CLOUD_ENABLED / CLOUD_ALLOWED_TASKS to run locally."
        )

    # Default, private path: 100% local.
    return get_heavy_llm() if heavy else get_light_llm()
