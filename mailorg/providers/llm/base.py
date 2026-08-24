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
from ...privacy import may_use_cloud
from .ollama import get_heavy_llm, get_light_llm


def get_llm(task: str, *, heavy: bool = False, settings: Settings | None = None) -> BaseChatModel:
    """Return a chat model for ``task``.

    Args:
        task: logical task name (e.g. "categorise", "summarise", "draft"). Used only to
            consult the cloud allowlist — it does not change the local model chosen.
        heavy: use the larger local model (gemma4:12b) instead of the light one.
    """
    settings = settings or get_settings()

    # The gate combines .env with the UI switch; .env is the ceiling (see mailorg.privacy).
    if may_use_cloud(task, settings):
        # Imported lazily so the cloud client is never even constructed — and its
        # dependency never required — on a purely local install.
        from .cloud import get_cloud_llm

        return get_cloud_llm()

    # Default, private path: 100% local.
    return get_heavy_llm() if heavy else get_light_llm()
