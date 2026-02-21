"""LLM provider — thin wrapper around OpenAI SDK.

Works out-of-the-box with Ollama (localhost:11434/v1) and any
OpenAI-compatible endpoint (OpenAI, OpenRouter, Together, etc.).
"""

import logging
from typing import Any, Dict, Optional

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

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> None:
        provider = provider or settings.llm_provider
        self.model = model or settings.llm_model
        self.provider_name = provider

        # Resolve base_url: explicit param > setting > provider preset
        if base_url:
            self.base_url = base_url
        elif provider == settings.llm_provider and settings.llm_base_url:
            self.base_url = settings.llm_base_url
        else:
            self.base_url = _PROVIDER_DEFAULTS.get(provider, _PROVIDER_DEFAULTS["ollama"])

        # API key: Ollama doesn't need one, but the SDK requires a non-empty string
        key = api_key or settings.llm_api_key or "ollama"

        self._client = OpenAI(base_url=self.base_url, api_key=key)
        logger.info(
            "LLM provider ready: provider=%s model=%s base_url=%s",
            provider, self.model, self.base_url,
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

# Cache for per-agent providers keyed by (provider, model, base_url)
_config_cache: dict[tuple[str, str, str], LLMProvider] = {}


def get_provider() -> LLMProvider:
    """Return (and lazily create) the singleton LLMProvider."""
    global _instance
    if _instance is None:
        _instance = LLMProvider()
    return _instance


def for_config(config: Dict[str, Any]) -> LLMProvider:
    """Return a provider for the given agent config, with caching.

    If config has llm_provider/llm_model/llm_base_url overrides,
    returns a cached provider with those settings. Otherwise returns
    the global singleton.
    """
    provider = config.get("llm_provider", "").strip()
    model = config.get("llm_model", "").strip()
    base_url = config.get("llm_base_url", "").strip()
    api_key = config.get("llm_api_key", "").strip()

    # No overrides → use global singleton
    if not provider and not model and not base_url:
        return get_provider()

    cache_key = (
        provider or settings.llm_provider,
        model or settings.llm_model,
        base_url or "",
    )

    if cache_key not in _config_cache:
        _config_cache[cache_key] = LLMProvider(
            provider=provider or None,
            model=model or None,
            base_url=base_url or None,
            api_key=api_key or None,
        )

    return _config_cache[cache_key]
