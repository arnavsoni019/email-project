"""Optional cloud LLM, reached only through the privacy gate in ``base.get_llm``.

One client covers OpenRouter, DeepSeek, Together and most hosted providers, because
they all speak the OpenAI wire format. Which one is used is ``cloud_base_url`` plus
``cloud_model`` in ``.env`` — changing provider is configuration, not code.

Nothing here decides *whether* the cloud may be used. That decision belongs to
``mailorg.privacy.may_use_cloud`` and happens before this module is imported, so the
gate cannot be bypassed by calling a factory directly.

Note that unlike the local path, every call here sends the text of an email to a third
party. The gate is per-task for exactly that reason: bulk enrichment (408 calls over the
whole mailbox) can stay local while a handful of judgement calls go out.
"""

from __future__ import annotations

from functools import lru_cache

from langchain_openai import ChatOpenAI

from ...config import get_settings


class CloudNotConfigured(RuntimeError):
    """Raised when a cloud task is permitted but no API key is set."""


@lru_cache
def get_cloud_llm(temperature: float = 0.0) -> ChatOpenAI:
    """The configured cloud chat model.

    Raises:
        CloudNotConfigured: if no API key is present. Raised rather than silently
            falling back to the local model, because a silent fallback would make the
            Settings screen lie about where text is going.
    """
    settings = get_settings()
    if not settings.cloud_api_key:
        raise CloudNotConfigured(
            "A cloud task was permitted but CLOUD_API_KEY is not set. "
            "Add it to .env, or clear CLOUD_ALLOWED_TASKS to stay local."
        )

    return ChatOpenAI(
        model=settings.cloud_model,
        base_url=settings.cloud_base_url,
        api_key=settings.cloud_api_key,
        temperature=temperature,
        # OpenRouter shows these in its dashboard; other providers ignore them.
        default_headers={
            "HTTP-Referer": "http://localhost:5173",
            "X-Title": settings.cloud_app_title,
        },
    )


def cloud_is_configured() -> bool:
    """True if a key is present. Used by the UI to explain why the switch is inert."""
    return bool(get_settings().cloud_api_key)
