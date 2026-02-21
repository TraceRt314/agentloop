"""LLM provider — thin wrapper around OpenAI SDK.

Works out-of-the-box with Ollama (localhost:11434/v1) and any
OpenAI-compatible endpoint (OpenAI, OpenRouter, Together, etc.).
"""

import logging
from typing import Optional

from openai import OpenAI

from agentloop.config import settings

logger = logging.getLogger(__name__)

# Provider presets: base_url templates for known providers
_PROVIDER_DEFAULTS: dict[str, str] = {
    "ollama": "http://localhost:11434/v1",
    "openai": "https://api.openai.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
}


class LLMProvider:
    """Stateless LLM client using the OpenAI SDK."""

    def __init__(self) -> None:
        provider = settings.llm_provider
        self.model = settings.llm_model

        # Resolve base_url: explicit setting wins, then provider preset
        if settings.llm_base_url:
            self.base_url = settings.llm_base_url
        else:
            self.base_url = _PROVIDER_DEFAULTS.get(provider, _PROVIDER_DEFAULTS["ollama"])

        # API key: Ollama doesn't need one, but the SDK requires a non-empty string
        api_key = settings.llm_api_key or "ollama"

        self._client = OpenAI(base_url=self.base_url, api_key=api_key)
        logger.info(
            "LLM provider ready: model=%s base_url=%s",
            self.model, self.base_url,
        )

    @property
    def available(self) -> bool:
        """Quick health check — try a tiny request."""
        try:
            self._client.models.list()
            return True
        except Exception:
            return False

    def chat(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Send a chat completion and return the assistant text."""
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return response.choices[0].message.content or ""


# Module-level singleton (created on first import)
_instance: Optional[LLMProvider] = None


def get_provider() -> LLMProvider:
    """Return (and lazily create) the singleton LLMProvider."""
    global _instance
    if _instance is None:
        _instance = LLMProvider()
    return _instance
