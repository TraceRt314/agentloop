"""SSE stream listener for Mission Control real-time events.

Subscribes to MC's ``/boards/{id}/tasks/stream`` and
``/boards/{id}/approvals/stream`` endpoints and feeds events
back into AgentLoop's orchestration pipeline.
"""

import asyncio
import json
import logging
from typing import Callable, Dict, Optional

import httpx

from ..config import settings

logger = logging.getLogger(__name__)

# Active stream tasks keyed by board_id
_active_streams: Dict[str, asyncio.Task] = {}


def _sse_headers() -> dict:
    headers = {"Accept": "text/event-stream"}
    if settings.mc_token:
        headers["Authorization"] = f"Bearer {settings.mc_token}"
    if settings.mc_org_id:
        headers["X-Organization-Id"] = settings.mc_org_id
    return headers


async def _listen_sse(
    url: str,
    on_event: Callable[[str, dict], None],
    label: str = "sse",
) -> None:
    """Connect to an SSE endpoint and dispatch parsed events.

    Reconnects automatically on error with exponential backoff
    (capped at 60 s).
    """
    backoff = 1.0

    while True:
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream(
                    "GET", url, headers=_sse_headers()
                ) as response:
                    response.raise_for_status()
                    logger.info("SSE connected: %s", label)
                    backoff = 1.0  # reset on success

                    event_type = ""
                    data_lines: list[str] = []

                    async for line in response.aiter_lines():
                        if line.startswith("event:"):
                            event_type = line[6:].strip()
                        elif line.startswith("data:"):
                            data_lines.append(line[5:].strip())
                        elif line == "":
                            # End of event block
                            if data_lines:
                                raw = "\n".join(data_lines)
                                try:
                                    payload = json.loads(raw)
                                except json.JSONDecodeError:
                                    payload = {"raw": raw}
                                try:
                                    on_event(event_type or "message", payload)
                                except Exception:
                                    logger.exception("SSE handler error (%s)", label)
                            event_type = ""
                            data_lines = []

        except httpx.HTTPStatusError as exc:
            logger.warning("SSE %s HTTP %s — retrying in %.0fs", label, exc.response.status_code, backoff)
        except (httpx.ConnectError, httpx.ReadError, httpx.RemoteProtocolError) as exc:
            logger.debug("SSE %s connection lost (%s) — retrying in %.0fs", label, type(exc).__name__, backoff)
        except asyncio.CancelledError:
            logger.info("SSE %s cancelled", label)
            return
        except Exception:
            logger.exception("SSE %s unexpected error — retrying in %.0fs", label, backoff)

        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, 60.0)


# ─── Public API ───

def _handle_task_event(board_id: str, event_type: str, payload: dict) -> None:
    """Process a task-stream SSE event.

    Interesting events:
      - task.created  → may want to create a Proposal
      - task.updated  → status changed externally
      - task.comment  → informational
    """
    task_id = payload.get("id") or payload.get("task_id", "")
    title = payload.get("title", "")
    status = payload.get("status", "")
    logger.info(
        "MC task event [%s] board=%s task=%s title=%s status=%s",
        event_type, board_id[:8], str(task_id)[:8], title[:40], status,
    )

    # If a task was just created or moved to inbox, trigger a sync
    if event_type in ("task.created", "task.updated") and status in ("inbox", "in_progress"):
        _schedule_sync(board_id)


def _handle_approval_event(board_id: str, event_type: str, payload: dict) -> None:
    """Process an approval-stream SSE event."""
    logger.info(
        "MC approval event [%s] board=%s payload_keys=%s",
        event_type, board_id[:8], list(payload.keys()),
    )


_sync_callback: Optional[Callable[[str], None]] = None


def set_sync_callback(cb: Callable[[str], None]) -> None:
    """Register a callback that triggers an MC sync for a board.

    Called from main.py at startup so the stream module can request
    an immediate orchestration sync when new tasks arrive.
    """
    global _sync_callback
    _sync_callback = cb


def _schedule_sync(board_id: str) -> None:
    if _sync_callback:
        try:
            _sync_callback(board_id)
        except Exception:
            logger.exception("Sync callback failed for board %s", board_id)


async def start_board_streams(board_id: str) -> None:
    """Start SSE listeners for a single board (tasks + approvals)."""
    base = settings.mc_base_url

    if board_id in _active_streams:
        return

    async def _run_both() -> None:
        await asyncio.gather(
            _listen_sse(
                f"{base}/api/v1/boards/{board_id}/tasks/stream",
                lambda et, p: _handle_task_event(board_id, et, p),
                label=f"tasks/{board_id[:8]}",
            ),
            _listen_sse(
                f"{base}/api/v1/boards/{board_id}/approvals/stream",
                lambda et, p: _handle_approval_event(board_id, et, p),
                label=f"approvals/{board_id[:8]}",
            ),
        )

    task = asyncio.create_task(_run_both())
    _active_streams[board_id] = task
    logger.info("Started SSE streams for board %s", board_id[:8])


async def start_all_board_streams() -> None:
    """Start SSE listeners for every board in the BOARD_MAP config."""
    from .mission_control import BOARD_PROJECT_MAP

    if not settings.mc_token:
        logger.info("MC token not set — skipping SSE streams")
        return

    for board_id in BOARD_PROJECT_MAP:
        await start_board_streams(board_id)


async def stop_all_streams() -> None:
    """Cancel all running SSE stream tasks."""
    for board_id, task in _active_streams.items():
        task.cancel()
        logger.info("Stopped SSE stream for board %s", board_id[:8])
    _active_streams.clear()
