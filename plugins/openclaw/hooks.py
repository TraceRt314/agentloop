"""OpenClaw plugin hooks.

Registers the OpenClaw step and chat dispatchers with the WorkerEngine
on startup.
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class OpenClawDispatcher:
    """StepDispatcher implementation backed by the OpenClaw CLI."""

    def dispatch(self, step_id: str, work_prompt: str, timeout: int,
                 agent_config: Optional[Dict[str, Any]] = None) -> dict:
        from agentloop.integrations.openclaw import gateway_client

        result = gateway_client.dispatch_step(
            step_id, work_prompt, timeout=timeout, agent_config=agent_config,
        )
        # Embed extracted text so the worker can read it generically
        result["_response_text"] = gateway_client.extract_response_text(result)
        return result


class OpenClawChatDispatcher:
    """ChatDispatcher implementation backed by the OpenClaw CLI."""

    def send(self, session_id: str, message: str, timeout: int) -> dict:
        from agentloop.integrations.openclaw import gateway_client
        return gateway_client.run_agent(
            session_id=session_id, message=message, timeout=timeout,
        )

    def stream_send(self, session_id: str, message: str, provider=None):
        """Stream via LLM provider (OpenClaw CLI doesn't support streaming)."""
        from plugins.llm.provider import get_provider

        llm = provider or get_provider()
        yield from llm.chat_stream(prompt=message)

    def extract_text(self, result: dict) -> str:
        from agentloop.integrations.openclaw import gateway_client
        return gateway_client.extract_response_text(result)

    @property
    def available(self) -> bool:
        from agentloop.integrations.openclaw import gateway_client
        return gateway_client.available


def on_startup(**kwargs):
    """Register the OpenClaw dispatchers with WorkerEngine."""
    from agentloop.engine.worker import WorkerEngine

    WorkerEngine.set_dispatcher(OpenClawDispatcher())
    WorkerEngine.set_chat_dispatcher(OpenClawChatDispatcher())
    logger.info("openclaw plugin: registered step + chat dispatchers")


HOOKS = {
    "on_startup": on_startup,
}
