"""Main FastAPI application for AgentLoop."""

import time
from typing import Dict
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

from .api import agents, events, missions, projects, proposals, steps, triggers, websocket
from .config import settings
from .database import create_db_and_tables, get_session
from .engine.orchestrator import OrchestrationEngine
from .schemas import OrchestrationResult, WorkCycleResult

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

# Global orchestrator instance
orchestrator = OrchestrationEngine()


@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup."""
    # Create database tables
    create_db_and_tables()


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