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
    """The small, resident model — used for bulk per-email pipelines.

    ``reasoning=False`` matters enormously here. Qwen3.5 is a reasoning model: left at
    its default it writes a long internal monologue before answering, which measured
    0.7s vs 11.4s on the same prompt — and on harder emails it sometimes spent 180s
    deliberating and returned an empty summary. Tier 1 asks for one word or one
    sentence, so there is nothing worth deliberating about.
    """
    settings = get_settings()
    return ChatOllama(
        model=settings.model_light,
        base_url=settings.ollama_host,
        temperature=temperature,
        reasoning=False,
    )


@lru_cache
def get_heavy_llm(temperature: float = 0.0) -> ChatOllama:
    """The larger, on-demand model — used for harder single-shot tasks.

    ``reasoning=False`` for the same reason as the light model, but the failure here was
    sneakier: on a long RAG prompt gemma4:12b-it-qat generated 370 tokens, stopped with
    ``done_reason=length``, and returned an EMPTY string — the whole budget went into an
    unterminated reasoning block that Ollama then discarded. Raising ``num_predict`` only
    bought more tokens to waste; disabling reasoning produced a correct cited answer in
    18.8s. An empty answer is worse than a shallow one, so this stays off.
    """
    settings = get_settings()
    return ChatOllama(
        model=settings.model_heavy,
        base_url=settings.ollama_host,
        temperature=temperature,
        reasoning=False,
    )
