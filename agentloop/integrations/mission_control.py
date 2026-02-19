"""Mission Control integration — sync tasks/boards with AgentLoop."""

import httpx
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

MC_BASE = "http://localhost:8002"
MC_TOKEN = "xnvLdACuZP3iIZk2owZFyAWCt1bYNIk2DJrqOgf/4u1NSjGi4YbJ2m31IwZEgSnV"


def _headers() -> dict:
    return {"Authorization": f"Bearer {MC_TOKEN}", "Content-Type": "application/json"}


def mc_get(path: str) -> Optional[dict]:
    """GET from Mission Control API."""
    try:
        r = httpx.get(f"{MC_BASE}{path}", headers=_headers(), timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.warning(f"MC GET {path} failed: {e}")
        return None


def mc_post(path: str, data: dict) -> Optional[dict]:
    """POST to Mission Control API."""
    try:
        r = httpx.post(f"{MC_BASE}{path}", headers=_headers(), json=data, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.warning(f"MC POST {path} failed: {e}")
        return None


def mc_patch(path: str, data: dict) -> Optional[dict]:
    """PATCH Mission Control API."""
    try:
        r = httpx.patch(f"{MC_BASE}{path}", headers=_headers(), json=data, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.warning(f"MC PATCH {path} failed: {e}")
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


def create_task(board_id: str, title: str, description: str = "", priority: str = "medium") -> Optional[dict]:
    """Create a new task in Mission Control."""
    return mc_post(f"/api/v1/boards/{board_id}/tasks", {
        "title": title,
        "description": description,
        "priority": priority,
    })


# ─── Sync Logic ───

# Map MC board IDs to AgentLoop project slugs
BOARD_PROJECT_MAP = {
    "f961ea63-1619-47e1-9925-c54bcae17a08": "playdel",
    "2d7eb924-ae02-428c-beee-e148830b0cae": "blackcat",
    "3221facb-38eb-4539-9159-7d55df200e21": "mitheithel",
    "5c2d5641-ce08-42ba-81f1-2e5c49d950ad": "problyx",
    "c8ad0829-e973-4e74-9903-cf9361cd0d85": "gptstonks",
    "c5c5dc10-e54b-4cce-92cc-2d3c07a3bf24": "polymarket-bot",
}


def sync_tasks_for_project(board_id: str) -> List[dict]:
    """Fetch all inbox/open tasks from MC for a project board.
    
    Returns list of task dicts that can feed into AgentLoop proposals.
    """
    tasks = get_board_tasks(board_id)
    # Filter to actionable tasks
    actionable = [t for t in tasks if t.get("status") in ("inbox", "in_progress")]
    return actionable


def mark_task_in_progress(board_id: str, task_id: str) -> bool:
    """Mark a MC task as in_progress when an agent claims it."""
    result = update_task_status(board_id, task_id, "in_progress")
    return result is not None


def mark_task_done(board_id: str, task_id: str) -> bool:
    """Mark a MC task as done when a mission completes."""
    result = update_task_status(board_id, task_id, "done")
    return result is not None


def report_agent_activity(board_id: str, task_id: str, agent_name: str, action: str) -> bool:
    """Log agent activity back to MC as a task comment/update."""
    # MC may not have a comment endpoint, so we update the description
    result = mc_patch(f"/api/v1/boards/{board_id}/tasks/{task_id}", {
        "description": f"[AgentLoop] {agent_name}: {action}",
    })
    return result is not None
