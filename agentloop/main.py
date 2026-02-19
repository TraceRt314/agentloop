"""Main FastAPI application for AgentLoop."""

import logging
import sys
import time
from typing import Dict
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

from .api import agents, chat, context, events, missions, projects, proposals, steps, triggers, websocket, simulation, dashboard
from .config import settings
from .database import create_db_and_tables, engine, get_session, run_migrations
from .engine.orchestrator import OrchestrationEngine
from .schemas import OrchestrationResult, WorkCycleResult


def _configure_logging() -> None:
    """Set up application-level logging."""
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    fmt = "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s"
    logging.basicConfig(
        level=level,
        format=fmt,
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stderr,
        force=True,
    )
    # Quiet noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("watchfiles").setLevel(logging.WARNING)


_configure_logging()
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="AgentLoop",
    description="Multi-agent closed-loop orchestration system",
    version="0.1.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(agents.router)
app.include_router(projects.router)
app.include_router(proposals.router)
app.include_router(missions.router)
app.include_router(steps.router)
app.include_router(events.router)
app.include_router(triggers.router)
app.include_router(websocket.router)
app.include_router(simulation.router)
app.include_router(dashboard.router)
app.include_router(context.router)
app.include_router(chat.router)

# Global orchestrator instance
orchestrator = OrchestrationEngine()


@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup."""
    run_migrations()

    # Wire SSE sync callback so new MC tasks trigger immediate sync
    from .integrations.mc_streams import set_sync_callback, start_all_board_streams

    def _sync_board(board_id: str) -> None:
        """Trigger an orchestrator tick when SSE detects a new task."""
        try:
            with Session(engine) as session:
                orchestrator._sync_mission_control(session)
        except Exception:
            logger.warning("SSE-triggered sync failed for board %s", board_id)

    set_sync_callback(_sync_board)

    # Start SSE listeners for Mission Control boards
    try:
        await start_all_board_streams()
    except Exception:
        logger.warning("Could not start MC SSE streams (will fall back to polling)")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    from .integrations.mc_streams import stop_all_streams
    await stop_all_streams()


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "AgentLoop",
        "version": "0.1.0",
        "description": "Multi-agent closed-loop orchestration system",
        "status": "running",
    }


@app.get("/healthz")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": time.time()}


@app.get("/api/v1/health")
def deep_health_check(session: Session = Depends(get_session)):
    """Deep health check: DB, MC, stuck missions, agent activity."""
    from .integrations.mission_control import mc_get
    from .models import Agent, AgentStatus, Mission, MissionStatus, Step, StepStatus
    from sqlmodel import select, func
    from datetime import datetime, timedelta

    checks: dict = {}

    # 1. Database
    try:
        count = session.exec(select(func.count(Agent.id))).one()
        checks["database"] = {"status": "ok", "agents": count}
    except Exception as e:
        checks["database"] = {"status": "error", "error": str(e)}

    # 2. Mission Control connectivity
    try:
        result = mc_get("/healthz")
        checks["mission_control"] = {
            "status": "ok" if result else "unreachable",
        }
    except Exception as e:
        checks["mission_control"] = {"status": "error", "error": str(e)}

    # 3. Stuck missions (failed steps, no pending)
    try:
        active = session.exec(
            select(Mission).where(Mission.status == MissionStatus.ACTIVE)
        ).all()
        stuck = 0
        for m in active:
            steps = session.exec(select(Step).where(Step.mission_id == m.id)).all()
            has_failed = any(s.status == StepStatus.FAILED for s in steps)
            has_pending = any(
                s.status in (StepStatus.PENDING, StepStatus.RUNNING, StepStatus.CLAIMED)
                for s in steps
            )
            if has_failed and not has_pending:
                stuck += 1
        checks["missions"] = {
            "active": len(active),
            "stuck": stuck,
            "status": "warning" if stuck > 0 else "ok",
        }
    except Exception as e:
        checks["missions"] = {"status": "error", "error": str(e)}

    # 4. Agent heartbeats
    try:
        stale_cutoff = datetime.utcnow() - timedelta(minutes=10)
        active_agents = session.exec(
            select(Agent).where(Agent.status == AgentStatus.ACTIVE)
        ).all()
        stale = [a.name for a in active_agents if a.last_seen_at and a.last_seen_at < stale_cutoff]
        checks["agents"] = {
            "total_active": len(active_agents),
            "stale": stale,
            "status": "warning" if stale else "ok",
        }
    except Exception as e:
        checks["agents"] = {"status": "error", "error": str(e)}

    # 5. SSE streams
    from .integrations.mc_streams import _active_streams
    checks["sse_streams"] = {
        "active_boards": len(_active_streams),
        "status": "ok" if _active_streams else "inactive",
    }

    overall = "healthy"
    for c in checks.values():
        if c.get("status") == "error":
            overall = "degraded"
            break
        if c.get("status") == "warning":
            overall = "warning"

    return {
        "status": overall,
        "timestamp": time.time(),
        "checks": checks,
    }


# Orchestrator endpoints
@app.post("/api/v1/orchestrator/tick", response_model=OrchestrationResult)
def orchestrator_tick(
    session: Session = Depends(get_session),
):
    """Run one orchestration cycle."""
    try:
        result = orchestrator.tick(session)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Orchestration failed: {str(e)}")


@app.post("/api/v1/orchestrator/work-cycle/{agent_id}", response_model=WorkCycleResult)
def agent_work_cycle(
    agent_id: UUID,
    session: Session = Depends(get_session),
):
    """Run a work cycle for a specific agent."""
    try:
        result = orchestrator.work_cycle(agent_id, session)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Work cycle failed: {str(e)}")


@app.get("/api/v1/orchestrator/status")
async def orchestrator_status():
    """Get orchestrator status."""
    return {
        "status": "running",
        "version": "0.1.0",
        "uptime": time.time(),
    }


# Admin/debug endpoints (only in debug mode)
if settings.debug:
    @app.post("/api/v1/admin/reset-db")
    async def reset_database():
        """Reset the database (debug only)."""
        create_db_and_tables()
        return {"status": "Database reset complete"}
    
    @app.get("/api/v1/admin/config")
    async def get_config():
        """Get current configuration (debug only)."""
        return {
            "database_url": settings.database_url,
            "debug": settings.debug,
            "agents_dir": settings.agents_dir,
            "projects_dir": settings.projects_dir,
        }


# CLI function for running the server
def cli():
    """Command-line interface for running AgentLoop."""
    import uvicorn
    
    uvicorn.run(
        "agentloop.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    cli()