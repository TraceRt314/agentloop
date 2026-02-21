"""Dashboard API — unified view of agents, missions, system status."""

import logging
import subprocess
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from sqlmodel import Session, select, func

from ..database import get_session
from ..models import (
    Agent, AgentStatus, Project, Proposal, ProposalStatus,
    Mission, MissionStatus, Step, StepStatus, Event,
)
from ..config import settings

logger = logging.getLogger(__name__)

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


@router.get("/system")
def system_status():
    """System health — check all services."""
    import httpx
    
    gw_http = settings.openclaw_gateway_url.replace("ws://", "http://").replace("wss://", "https://")
    services = {
        "agentloop_api": {"url": f"{settings.api_base_url}/healthz", "status": "unknown"},
        "mission_control": {"url": f"{settings.mc_base_url}/healthz", "status": "unknown"},
        "openclaw_gateway": {"url": gw_http, "status": "unknown"},
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


def _check_openai_provider(base_url: str, api_key: str) -> str:
    """Ping an OpenAI-compatible endpoint via models.list()."""
    try:
        from openai import OpenAI
        client = OpenAI(base_url=base_url, api_key=api_key or "ollama")
        client.models.list()
        return "healthy"
    except Exception as e:
        logger.debug("Provider check failed for %s: %s", base_url, e)
        return "offline"


def _check_openclaw() -> str:
    """Ping the OpenClaw gateway via CLI."""
    try:
        result = subprocess.run(
            ["openclaw", "agent", "--session-id", "health-check", "--message", "PING", "--json"],
            capture_output=True, text=True, timeout=10,
        )
        return "healthy" if result.returncode == 0 else "offline"
    except Exception:
        return "offline"


_PROVIDER_DEFAULTS: dict[str, str] = {
    "ollama": "http://localhost:11434/v1",
    "openai": "https://api.openai.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
}


@router.get("/health")
def llm_health(session: Session = Depends(get_session)):
    """LLM provider health — check each unique provider used by agents."""
    agents = session.exec(select(Agent)).all()

    # Collect unique providers: key = (provider, model, base_url)
    seen: dict[tuple[str, str, str], Dict[str, Any]] = {}

    # Always include the global default
    global_provider = settings.llm_provider
    global_model = settings.llm_model
    global_base_url = settings.llm_base_url or _PROVIDER_DEFAULTS.get(global_provider, "")
    seen[(global_provider, global_model, global_base_url)] = {
        "provider": global_provider,
        "model": global_model,
        "base_url": global_base_url,
        "source": "global",
    }

    # Scan agent configs for overrides
    for agent in agents:
        cfg = agent.config or {}
        p = cfg.get("llm_provider", "").strip() or global_provider
        m = cfg.get("llm_model", "").strip() or global_model
        b = cfg.get("llm_base_url", "").strip() or _PROVIDER_DEFAULTS.get(p, global_base_url)
        key = (p, m, b)
        if key not in seen:
            seen[key] = {"provider": p, "model": m, "base_url": b, "source": "agent"}

    # Check each provider
    providers: List[Dict[str, Any]] = []
    for (p, m, b), info in seen.items():
        if p == "openclaw":
            status = _check_openclaw()
        else:
            status = _check_openai_provider(b, settings.llm_api_key)
        providers.append({**info, "status": status})

    # Build agent list with their provider info
    agent_list = []
    for agent in agents:
        cfg = agent.config or {}
        p = cfg.get("llm_provider", "").strip() or global_provider
        m = cfg.get("llm_model", "").strip() or global_model
        agent_list.append({
            "id": str(agent.id),
            "name": agent.name,
            "role": agent.role,
            "provider": p,
            "model": m,
            "status": agent.status.value,
        })

    return {
        "timestamp": time.time(),
        "providers": providers,
        "agents": agent_list,
    }
