"""OpenClaw integration helpers."""

import httpx
from typing import Any, Dict, Optional

from ..config import settings


class OpenClawClient:
    """Client for interacting with OpenClaw APIs."""
    
    def __init__(self, base_url: str = None, token: str = None):
        self.base_url = base_url or settings.openclaw_base_url
        self.token = token or settings.openclaw_token
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.token}"} if self.token else {},
        )
    
    async def spawn_subagent(
        self,
        task_description: str,
        context: Dict[str, Any] = None,
        timeout_seconds: int = 300
    ) -> Dict[str, Any]:
        """Spawn an OpenClaw sub-agent to execute a task."""
        payload = {
            "task": task_description,
            "context": context or {},
            "timeout": timeout_seconds,
        }
        
        try:
            response = await self.client.post("/api/v1/subagents/spawn", json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            raise RuntimeError(f"Failed to spawn sub-agent: {str(e)}")
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Sub-agent spawn failed with status {e.response.status_code}: {e.response.text}")
    
    async def get_subagent_status(self, subagent_id: str) -> Dict[str, Any]:
        """Get the status of a sub-agent."""
        try:
            response = await self.client.get(f"/api/v1/subagents/{subagent_id}/status")
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            raise RuntimeError(f"Failed to get sub-agent status: {str(e)}")
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Status request failed with status {e.response.status_code}: {e.response.text}")
    
    async def send_message(
        self,
        channel: str,
        message: str,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """Send a message through OpenClaw."""
        payload = {
            "channel": channel,
            "message": message,
            "metadata": metadata or {},
        }
        
        try:
            response = await self.client.post("/api/v1/messages/send", json=payload)
            response.raise_for_status()
            return True
        except Exception as e:
            # Don't fail if messaging doesn't work
            return False
    
    async def create_cron_job(
        self,
        schedule: str,
        command: str,
        description: str = None
    ) -> Dict[str, Any]:
        """Create a cron job in OpenClaw."""
        payload = {
            "schedule": schedule,
            "command": command,
            "description": description or "AgentLoop orchestration task",
        }
        
        try:
            response = await self.client.post("/api/v1/cron/create", json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            raise RuntimeError(f"Failed to create cron job: {str(e)}")
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Cron creation failed with status {e.response.status_code}: {e.response.text}")
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


class OpenClawWebhooks:
    """Webhook handlers for OpenClaw integration."""
    
    @staticmethod
    def generate_orchestrator_cron_command(api_base_url: str) -> str:
        """Generate the cron command for orchestrator ticks."""
        return f"curl -X POST {api_base_url}/api/v1/orchestrator/tick"
    
    @staticmethod
    def generate_agent_work_cron_command(api_base_url: str, agent_id: str) -> str:
        """Generate the cron command for agent work cycles."""
        return f"curl -X POST {api_base_url}/api/v1/orchestrator/work-cycle/{agent_id}"
    
    @staticmethod
    def generate_setup_script(
        api_base_url: str,
        orchestrator_schedule: str = "*/5 * * * *",  # Every 5 minutes
        agents_schedule: str = "*/10 * * * *",      # Every 10 minutes
    ) -> str:
        """Generate shell script to set up OpenClaw cron jobs."""
        script_lines = [
            "#!/bin/bash",
            "# AgentLoop OpenClaw integration setup script",
            "",
            "echo 'Setting up AgentLoop cron jobs...'",
            "",
            "# Orchestrator tick (every 5 minutes)",
            f'openclaw cron add "{orchestrator_schedule}" "curl -X POST {api_base_url}/api/v1/orchestrator/tick" --description "AgentLoop orchestrator tick"',
            "",
            "# Note: Add agent work cycle cron jobs manually for each agent:",
            "# openclaw cron add \"*/10 * * * *\" \"curl -X POST {api_base_url}/api/v1/orchestrator/work-cycle/AGENT_ID\" --description \"AgentLoop agent work cycle\"",
            "",
            "echo 'Cron jobs set up successfully!'",
            "echo 'You can list them with: openclaw cron list'",
            "",
        ]
        
        return "\n".join(script_lines)


# Global client instance
openclaw_client = OpenClawClient()