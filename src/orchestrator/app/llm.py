"""LiteLLM gateway client — routes model calls through the on-prem LiteLLM proxy."""
from __future__ import annotations

import litellm
from app.config import settings

litellm.api_base = settings.litellm_api_base
litellm.api_key  = settings.litellm_api_key


async def chat(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 4096,
) -> str:
    """Single chat completion via LiteLLM proxy."""
    response = await litellm.acompletion(
        model=model or settings.default_model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content or ""
