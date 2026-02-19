"""OpenClaw gateway integration via CLI subprocess.

Uses `openclaw agent` CLI which handles authentication, session management,
and agent execution synchronously — bypassing the WebSocket scope issue.
"""

import json
import logging
import shutil
import subprocess
from typing import Any, Dict, Optional

from ..config import settings

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 300  # 5 minutes


class GatewayError(Exception):
    """Raised when a gateway CLI call fails."""


class GatewayClient:
    """Client for the OpenClaw gateway via the `openclaw agent` CLI.

    The CLI handles auth, sessions, and agent dispatch internally.
    Each call is synchronous (subprocess.run) — perfect for the
    sync worker engine.
    """

    def __init__(self, timeout: int = None):
        self.timeout = timeout or settings.step_timeout_seconds
        self._binary = shutil.which("openclaw")
        if not self._binary:
            logger.warning("openclaw CLI not found in PATH")

    @property
    def available(self) -> bool:
        return self._binary is not None

    @staticmethod
    def step_session_key(step_id: str) -> str:
        """Deterministic session key for a step execution.

        Session IDs must not contain colons — use hyphens only.
        """
        return f"agentloop-step-{step_id}"

    def run_agent(
        self,
        session_id: str,
        message: str,
        timeout: int = None,
    ) -> Dict[str, Any]:
        """Run the openclaw agent CLI and return parsed JSON result.

        Args:
            session_id: Unique session identifier for this execution.
            message: The prompt/instruction to send to the agent.
            timeout: Max seconds to wait (defaults to self.timeout).

        Returns:
            Parsed JSON response from the CLI.

        Raises:
            GatewayError: If the CLI fails, times out, or returns bad JSON.
        """
        if not self.available:
            raise GatewayError("openclaw CLI not found in PATH")

        effective_timeout = timeout or self.timeout

        cmd = [
            self._binary,
            "agent",
            "--session-id", session_id,
            "--message", message,
            "--json",
        ]

        logger.info(
            "Dispatching to openclaw agent: session=%s timeout=%ds",
            session_id, effective_timeout,
        )
        logger.debug("Prompt length: %d chars", len(message))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=effective_timeout + 10,  # buffer over agent timeout
            )
        except subprocess.TimeoutExpired:
            raise GatewayError(
                f"openclaw agent timed out after {effective_timeout}s "
                f"(session={session_id})"
            )

        if result.returncode != 0:
            stderr = result.stderr.strip()[:500] if result.stderr else "no stderr"
            raise GatewayError(
                f"openclaw agent exited {result.returncode}: {stderr}"
            )

        # Parse the JSON output
        stdout = result.stdout.strip()
        if not stdout:
            raise GatewayError("openclaw agent returned empty output")

        try:
            data = json.loads(stdout)
        except json.JSONDecodeError as e:
            # Sometimes the CLI prints non-JSON before the JSON blob
            # Try to find the last JSON object in output
            last_brace = stdout.rfind("{")
            if last_brace >= 0:
                try:
                    data = json.loads(stdout[last_brace:])
                except json.JSONDecodeError:
                    raise GatewayError(
                        f"Failed to parse CLI output as JSON: {e}"
                    ) from e
            else:
                raise GatewayError(
                    f"Failed to parse CLI output as JSON: {e}"
                ) from e

        logger.info(
            "openclaw agent completed: session=%s status=%s",
            session_id, data.get("status", "unknown"),
        )

        return data

    def dispatch_step(
        self,
        step_id: str,
        work_prompt: str,
        timeout: int = None,
    ) -> Dict[str, Any]:
        """Dispatch a step for execution via the CLI.

        Args:
            step_id: The AgentLoop step UUID.
            work_prompt: Full prompt including callback instructions.
            timeout: Max seconds to wait.

        Returns:
            Parsed JSON response from the agent.
        """
        session_id = self.step_session_key(step_id)
        return self.run_agent(session_id, work_prompt, timeout=timeout)

    def health_check(self) -> bool:
        """Quick check: is the openclaw CLI available and responsive?"""
        if not self.available:
            return False
        try:
            result = self.run_agent(
                session_id="agentloop-healthcheck",
                message="Reply with exactly: PONG",
                timeout=30,
            )
            return result.get("status") == "ok"
        except GatewayError:
            return False

    def extract_response_text(self, result: Dict[str, Any]) -> str:
        """Extract the agent's text response from CLI JSON output.

        The CLI returns:
        {"runId": "...", "status": "ok", "result": {"payloads": [{"text": "..."}]}}
        """
        try:
            payloads = result.get("result", {}).get("payloads", [])
            texts = [p["text"] for p in payloads if "text" in p]
            return "\n".join(texts) if texts else ""
        except (KeyError, TypeError):
            return str(result.get("result", ""))


# Global singleton
gateway_client = GatewayClient()
