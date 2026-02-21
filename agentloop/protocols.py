"""Centralized protocols for pluggable backends."""

from typing import Any, Dict, Iterator, Optional, Protocol, runtime_checkable


@runtime_checkable
class StepDispatcher(Protocol):
    """Protocol for step dispatch backends (e.g. OpenClaw)."""

    def dispatch(self, step_id: str, work_prompt: str, timeout: int,
                 agent_config: Optional[Dict[str, Any]] = None) -> dict: ...


@runtime_checkable
class ChatDispatcher(Protocol):
    """Protocol for chat dispatch backends."""

    def send(self, session_id: str, message: str, timeout: int) -> dict: ...

    def extract_text(self, result: dict) -> str: ...

    @property
    def available(self) -> bool: ...

    def stream_send(self, session_id: str, message: str,
                    provider: Optional[Any] = None) -> Iterator[str]:
        """Yield text chunks from a streaming chat response."""
        ...
