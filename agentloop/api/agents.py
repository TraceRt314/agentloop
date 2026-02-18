"""Agent management API endpoints."""

from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from sqlmodel import select

from ..database import get_session
from ..models import Agent, Step
from ..schemas import (
    Agent as AgentSchema,
    AgentCreate,
    AgentHeartbeat,
    AgentUpdate,
    AgentWork,
    Step as StepSchema,
)

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


@router.get("/", response_model=List[AgentSchema])
def list_agents(
    project_id: UUID = None,
    status: str = None,
    session: Session = Depends(get_session),
):
    """List all agents with optional filtering."""
    query = select(Agent)
    
    if project_id:
        query = query.where(Agent.project_id == project_id)
    if status:
        query = query.where(Agent.status == status)
    
    result = session.exec(query)
    return result.all()


@router.post("/", response_model=AgentSchema, status_code=status.HTTP_201_CREATED)
def create_agent(
    agent_data: AgentCreate,
    session: Session = Depends(get_session),
):
    """Create a new agent."""
    agent = Agent(**agent_data.model_dump())
    session.add(agent)
    session.commit()
    session.refresh(agent)
    return agent


@router.get("/{agent_id}", response_model=AgentSchema)
def get_agent(
    agent_id: UUID,
    session: Session = Depends(get_session),
):
    """Get a specific agent by ID."""
    agent = session.get(Agent, agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    return agent


@router.patch("/{agent_id}", response_model=AgentSchema)
def update_agent(
    agent_id: UUID,
    agent_update: AgentUpdate,
    session: Session = Depends(get_session),
):
    """Update an agent."""
    agent = session.get(Agent, agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    update_data = agent_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(agent, field, value)
    
    session.commit()
    session.refresh(agent)
    return agent


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent(
    agent_id: UUID,
    session: Session = Depends(get_session),
):
    """Delete an agent."""
    agent = session.get(Agent, agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    session.delete(agent)
    session.commit()


@router.post("/{agent_id}/heartbeat")
def agent_heartbeat(
    agent_id: UUID,
    heartbeat_data: AgentHeartbeat,
    session: Session = Depends(get_session),
):
    """Record agent heartbeat."""
    agent = session.get(Agent, agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    agent.last_seen_at = datetime.utcnow()
    agent.status = heartbeat_data.status
    
    # Update config with heartbeat metadata if provided
    if heartbeat_data.metadata:
        agent.config.update(heartbeat_data.metadata)
    
    session.commit()
    return {"status": "ok", "timestamp": agent.last_seen_at}


@router.get("/{agent_id}/work", response_model=AgentWork)
def get_agent_work(
    agent_id: UUID,
    limit: int = 10,
    session: Session = Depends(get_session),
):
    """Get available work for an agent."""
    agent = session.get(Agent, agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    # Find unclaimed steps or steps assigned to this agent
    query = (
        select(Step)
        .join(Step.mission)
        .where(
            (Step.claimed_by_agent_id.is_(None)) |
            (Step.claimed_by_agent_id == agent_id)
        )
        .where(Step.status.in_(["pending", "claimed"]))
        .where(Step.mission.has(project_id=agent.project_id))
        .order_by(Step.created_at.asc())
        .limit(limit)
    )
    
    result = session.exec(query)
    available_steps = result.all()
    
    # Build context for the agent
    context = {
        "agent": {
            "id": str(agent.id),
            "name": agent.name,
            "role": agent.role,
            "config": agent.config,
        },
        "project_id": str(agent.project_id),
        "available_steps_count": len(available_steps),
    }
    
    return AgentWork(
        steps=[StepSchema.model_validate(step) for step in available_steps],
        context=context,
    )