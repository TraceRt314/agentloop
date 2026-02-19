"""Dashboard API — unified view of MC tasks, agents, missions, system status."""

import time
from typing import Optional

from fastapi import APIRouter, Depends
from sqlmodel import Session, select, func

from ..database import get_session
from ..models import (
    Agent, AgentStatus, Project, Proposal, ProposalStatus,
    Mission, MissionStatus, Step, StepStatus, Event,
)
from ..integrations.mission_control import (
    get_boards, get_board_tasks, BOARD_PROJECT_MAP, mc_get,
)

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/overview")
def dashboard_overview(session: Session = Depends(get_session)):
    """Full dashboard overview — agents, projects, missions, MC tasks, system health."""
    
    # Agents
    agents = session.exec(select(Agent)).all()
    agent_summary = [
        {
            "id": str(a.id),
            "name": a.name,
            "role": a.role,
            "status": a.status.value,
            "current_action": a.current_action.value,
            "position_x": a.position_x,
            "position_y": a.position_y,
        }
        for a in agents
    ]
    
    # Projects
    projects = session.exec(select(Project)).all()
    
    # Missions
    active_missions = session.exec(
        select(Mission).where(Mission.status == MissionStatus.ACTIVE)
    ).all()
    completed_missions = session.exec(
        select(func.count(Mission.id)).where(Mission.status == MissionStatus.COMPLETED)
    ).one()
    
    # Proposals
    pending_proposals = session.exec(
        select(Proposal).where(Proposal.status == ProposalStatus.PENDING)
    ).all()
    
    # Steps
    running_steps = session.exec(
        select(Step).where(Step.status == StepStatus.RUNNING)
    ).all()
    
    # Recent events
    recent_events = session.exec(
        select(Event).order_by(Event.created_at.desc()).limit(20)  # type: ignore
    ).all()
    
    return {
        "timestamp": time.time(),
        "agents": agent_summary,
        "projects": [{"name": p.name, "slug": p.slug, "id": str(p.id)} for p in projects],
        "missions": {
            "active": len(active_missions),
            "completed": completed_missions,
            "items": [
                {"id": str(m.id), "title": m.title, "status": m.status.value}
                for m in active_missions
            ],
        },
        "proposals": {
            "pending": len(pending_proposals),
            "items": [
                {"id": str(p.id), "title": p.title, "priority": p.priority.value, "status": p.status.value}
                for p in pending_proposals
            ],
        },
        "steps": {
            "running": len(running_steps),
            "items": [
                {"id": str(s.id), "title": s.title, "type": s.step_type.value, "status": s.status.value}
                for s in running_steps
            ],
        },
        "recent_events": [
            {"type": e.event_type, "created_at": e.created_at.isoformat() if e.created_at else None}
            for e in recent_events
        ],
    }


@router.get("/mc/boards")
def mc_boards():
    """Proxy — get all Mission Control boards with task counts."""
    boards = get_boards()
    result = []
    for b in boards:
        board_id = b.get("id", "")
        tasks = get_board_tasks(board_id)
        project_slug = BOARD_PROJECT_MAP.get(board_id, "unknown")
        
        # Count by status
        status_counts = {}
        for t in tasks:
            s = t.get("status", "unknown")
            status_counts[s] = status_counts.get(s, 0) + 1
        
        result.append({
            "id": board_id,
            "name": b.get("name", ""),
            "description": b.get("description", ""),
            "project_slug": project_slug,
            "task_count": len(tasks),
            "status_counts": status_counts,
        })
    return {"boards": result}


@router.get("/mc/boards/{board_id}/tasks")
def mc_board_tasks(board_id: str):
    """Proxy — get tasks for a specific MC board."""
    tasks = get_board_tasks(board_id)
    return {"board_id": board_id, "tasks": tasks, "total": len(tasks)}


@router.get("/system")
def system_status():
    """System health — check all services."""
    import httpx
    
    services = {
        "agentloop_api": {"url": "http://localhost:8080/healthz", "status": "unknown"},
        "mission_control": {"url": "http://localhost:8002/healthz", "status": "unknown"},
        "openclaw_gateway": {"url": "http://localhost:18789", "status": "unknown"},
    }
    
    for name, svc in services.items():
        try:
            r = httpx.get(svc["url"], timeout=3)
            svc["status"] = "healthy" if r.status_code == 200 else f"error:{r.status_code}"
        except Exception:
            svc["status"] = "offline"
    
    return {
        "timestamp": time.time(),
        "services": services,
    }
