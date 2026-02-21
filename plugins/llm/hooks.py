"""LLM plugin hooks.

Registers generic LLM step and chat dispatchers with the WorkerEngine
on startup.  Uses the OpenAI-compatible SDK so it works with Ollama,
OpenAI, OpenRouter, and any compatible endpoint.
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class LLMStepDispatcher:
    """StepDispatcher implementation backed by a generic LLM."""

    def dispatch(self, step_id: str, work_prompt: str, timeout: int,
                 agent_config: Optional[Dict[str, Any]] = None) -> dict:
        from .provider import for_config, get_provider

        if agent_config:
            provider = for_config(agent_config)
            system = agent_config.get("system_prompt")
        else:
            provider = get_provider()
            system = None

        try:
            text = provider.chat(prompt=work_prompt, system=system)
            return {"status": "ok", "_response_text": text}
        except Exception as e:
            logger.error("LLM dispatch failed for step %s: %s", step_id, e)
            return {"status": "error", "error": str(e), "_response_text": ""}


class LLMChatDispatcher:
    """ChatDispatcher implementation backed by a generic LLM."""

    def send(self, session_id: str, message: str, timeout: int) -> dict:
        from .provider import get_provider

        provider = get_provider()
        try:
            text = provider.chat(prompt=message)
            return {"status": "ok", "text": text}
        except Exception as e:
            logger.error("LLM chat failed for session %s: %s", session_id, e)
            return {"status": "error", "error": str(e), "text": ""}

    def extract_text(self, result: dict) -> str:
        return result.get("text", "")

    @property
    def available(self) -> bool:
        from .provider import get_provider
        try:
            return get_provider().available
        except Exception:
            return False


def on_startup(**kwargs):
    """Register the LLM dispatchers with WorkerEngine."""
    from agentloop.engine.worker import WorkerEngine

    WorkerEngine.set_dispatcher(LLMStepDispatcher())
    WorkerEngine.set_chat_dispatcher(LLMChatDispatcher())
    logger.info("llm plugin: registered step + chat dispatchers")


HOOKS = {
    "on_startup": on_startup,
}
