"""WebSocket endpoint for real-time agent UI updates."""

import asyncio
import json
from datetime import datetime
from typing import Set
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlmodel import select

from ..database import get_sync_session
from ..models import Agent, Event, Mission, Step

router = APIRouter()

# Connected clients
_clients: Set[WebSocket] = set()


async def broadcast(event_type: str, data: dict):
    """Broadcast event to all connected WebSocket clients."""
    message = json.dumps({"type": event_type, "data": data, "ts": datetime.utcnow().isoformat()})
    dead = set()
    for ws in _clients:
        try:
            await ws.send_text(message)
        except Exception:
            dead.add(ws)
    _clients -= dead


@router.websocket("/api/v1/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time UI updates."""
    await websocket.accept()
    _clients.add(websocket)
    try:
        # Send initial state
        with get_sync_session() as session:
            agents = session.exec(select(Agent)).all()
            agent_states = [
                {
                    "id": str(a.id),
                    "name": a.name,
                    "role": a.role,
                    "status": a.status.value,
                    "project_id": str(a.project_id),
                    "position_x": a.position_x,
                    "position_y": a.position_y,
                    "target_x": a.target_x,
                    "target_y": a.target_y,
                    "current_action": a.current_action.value,
                    "avatar": a.avatar,
                }
                for a in agents
            ]
        await websocket.send_text(json.dumps({
            "type": "init",
            "data": {"agents": agent_states},
            "ts": datetime.utcnow().isoformat(),
        }))

        # Keep connection alive, handle incoming messages
        while True:
            data = await websocket.receive_text()
            # Client can send ping/pong or commands
            msg = json.loads(data)
            if msg.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        pass
    finally:
        _clients.discard(websocket)
