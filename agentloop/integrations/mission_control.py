"""Mission Control integration — sync tasks/boards with AgentLoop."""

import httpx
import logging
from typing import Any, Dict, List, Optional

from ..config import settings

logger = logging.getLogger(__name__)


def _headers() -> dict:
    headers = {"Content-Type": "application/json"}
    if settings.mc_token:
        headers["Authorization"] = f"Bearer {settings.mc_token}"
    if settings.mc_org_id:
        headers["X-Organization-Id"] = settings.mc_org_id
    return headers


def mc_get(path: str) -> Optional[dict]:
    """GET from Mission Control API."""
    try:
        r = httpx.get(f"{settings.mc_base_url}{path}", headers=_headers(), timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.warning("MC GET %s failed: %s", path, e)
        return None


def mc_post(path: str, data: dict) -> Optional[dict]:
    """POST to Mission Control API."""
    try:
        r = httpx.post(
            f"{settings.mc_base_url}{path}", headers=_headers(), json=data, timeout=10
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.warning("MC POST %s failed: %s", path, e)
        return None


def mc_patch(path: str, data: dict) -> Optional[dict]:
    """PATCH Mission Control API."""
    try:
        r = httpx.patch(
            f"{settings.mc_base_url}{path}", headers=_headers(), json=data, timeout=10
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.warning("MC PATCH %s failed: %s", path, e)
        return None


# ─── Board / Task Operations ───

def get_boards() -> List[dict]:
    """Get all boards from Mission Control."""
    data = mc_get("/api/v1/boards")
    return data.get("items", []) if data else []


def get_board_tasks(board_id: str, status: str = None) -> List[dict]:
    """Get tasks for a board, optionally filtered by status."""
    path = f"/api/v1/boards/{board_id}/tasks"
    if status:
        path += f"?status={status}"
    data = mc_get(path)
    return data.get("items", []) if data else []


def update_task_status(board_id: str, task_id: str, status: str) -> Optional[dict]:
    """Update a task's status in Mission Control."""
    return mc_patch(f"/api/v1/boards/{board_id}/tasks/{task_id}", {"status": status})


def create_task(
    board_id: str, title: str, description: str = "", priority: str = "medium"
) -> Optional[dict]:
    """Create a new task in Mission Control."""
    return mc_post(
        f"/api/v1/boards/{board_id}/tasks",
        {"title": title, "description": description, "priority": priority},
    )


# ─── Sync Logic ───

def _load_board_project_map() -> dict:
    """Load board-to-project mapping from config.

    Set AGENTLOOP_BOARD_MAP as a JSON string in .env, e.g.:
    AGENTLOOP_BOARD_MAP={"uuid-1":"project-slug-1","uuid-2":"project-slug-2"}

    Falls back to an empty dict if not configured.
    """
    import json
    import os
    raw = os.environ.get("AGENTLOOP_BOARD_MAP", "")
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Invalid AGENTLOOP_BOARD_MAP JSON, using empty map")
    return {}


# Lazy-loaded on first access
BOARD_PROJECT_MAP = _load_board_project_map()


def sync_tasks_for_project(board_id: str) -> List[dict]:
    """Fetch all inbox/open tasks from MC for a project board."""
    tasks = get_board_tasks(board_id)
    return [t for t in tasks if t.get("status") in ("inbox", "in_progress")]


def mark_task_in_progress(board_id: str, task_id: str) -> bool:
    """Mark a MC task as in_progress when an agent claims it."""
    result = update_task_status(board_id, task_id, "in_progress")
    return result is not None


def mark_task_done(board_id: str, task_id: str) -> bool:
    """Mark a MC task as done when a mission completes."""
    result = update_task_status(board_id, task_id, "done")
    return result is not None


def report_agent_activity(
    board_id: str, task_id: str, agent_name: str, action: str
) -> bool:
    """Log agent activity back to MC as a task comment."""
    result = mc_post(
        f"/api/v1/boards/{board_id}/tasks/{task_id}/comments",
        {"content": f"[AgentLoop] {agent_name}: {action}"},
    )
    return result is not None
