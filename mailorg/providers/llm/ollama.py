"""Local two-tier LLM access via Ollama, wrapped as LangChain chat models.

Two tiers, sized around the RTX 4060's 8 GB VRAM:
  * light (gemma4:e4b)  — small, stays resident, used for bulk per-email work.
  * heavy (gemma4:12b)  — larger, loaded on demand for harder single-shot tasks.

Uses ``langchain_ollama.ChatOllama``, which talks to Ollama's REST API
(``settings.ollama_host``, reachable at localhost even from the Flatpak sandbox).
"""

from __future__ import annotations

from functools import lru_cache

from langchain_ollama import ChatOllama

from ...config import get_settings


@lru_cache
def get_light_llm(temperature: float = 0.0) -> ChatOllama:
    """The small, resident model — used for bulk per-email pipelines."""
    settings = get_settings()
    return ChatOllama(
        model=settings.model_light,
        base_url=settings.ollama_host,
        temperature=temperature,
    )


@lru_cache
def get_heavy_llm(temperature: float = 0.0) -> ChatOllama:
    """The larger, on-demand model — used for harder single-shot tasks."""
    settings = get_settings()
    return ChatOllama(
        model=settings.model_heavy,
        base_url=settings.ollama_host,
        temperature=temperature,
    )
