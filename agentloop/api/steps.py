"""Step management API endpoints."""

from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from sqlmodel import select

from ..database import get_session
from ..models import Step, StepStatus
from ..schemas import (
    Step as StepSchema,
    StepClaim,
    StepComplete,
    StepFail,
    StepUpdate,
    Event as EventSchema,
    EventCreate,
)

router = APIRouter(prefix="/api/v1/steps", tags=["steps"])


@router.get("/", response_model=List[StepSchema])
def list_steps(
    mission_id: UUID = None,
    status: StepStatus = None,
    step_type: str = None,
    claimed_by_agent_id: UUID = None,
    limit: int = 100,
    session: Session = Depends(get_session),
):
    """List steps with optional filtering."""
    query = select(Step).order_by(Step.order_index.asc(), Step.created_at.asc())
    
    if mission_id:
        query = query.where(Step.mission_id == mission_id)
    if status:
        query = query.where(Step.status == status)
    if step_type:
        query = query.where(Step.step_type == step_type)
    if claimed_by_agent_id:
        query = query.where(Step.claimed_by_agent_id == claimed_by_agent_id)
    
    query = query.limit(limit)
    result = session.exec(query)
    return result.all()


@router.get("/{step_id}", response_model=StepSchema)
def get_step(
    step_id: UUID,
    session: Session = Depends(get_session),
):
    """Get a specific step by ID."""
    step = session.get(Step, step_id)
    if not step:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Step not found"
        )
    return step


@router.patch("/{step_id}", response_model=StepSchema)
def update_step(
    step_id: UUID,
    step_update: StepUpdate,
    session: Session = Depends(get_session),
):
    """Update a step."""
    step = session.get(Step, step_id)
    if not step:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Step not found"
        )
    
    update_data = step_update.model_dump(exclude_unset=True)
    
    # Handle status changes with side effects
    if "status" in update_data:
        new_status = update_data["status"]
        if new_status == StepStatus.RUNNING and step.status != StepStatus.RUNNING:
            step.started_at = datetime.utcnow()
        elif new_status in [StepStatus.COMPLETED, StepStatus.FAILED] and step.status not in [StepStatus.COMPLETED, StepStatus.FAILED]:
            step.completed_at = datetime.utcnow()
    
    for field, value in update_data.items():
        setattr(step, field, value)
    
    session.commit()
    session.refresh(step)
    return step


@router.post("/{step_id}/claim", response_model=StepSchema)
def claim_step(
    step_id: UUID,
    claim_data: StepClaim,
    session: Session = Depends(get_session),
):
    """Claim a step for an agent."""
    step = session.get(Step, step_id)
    if not step:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Step not found"
        )
    
    if step.status != StepStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Step is not available for claiming (status: {step.status})"
        )
    
    if step.claimed_by_agent_id and step.claimed_by_agent_id != claim_data.agent_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Step is already claimed by another agent"
        )
    
    step.claimed_by_agent_id = claim_data.agent_id
    step.status = StepStatus.CLAIMED
    
    session.commit()
    session.refresh(step)
    
    # Create event for step claimed
    from ..api.events import create_event
    event_data = EventCreate(
        event_type="step.claimed",
        source_agent_id=claim_data.agent_id,
        project_id=(session.get(step.mission.project_id)),  # Get project_id from mission
        payload={
            "step_id": str(step.id),
            "mission_id": str(step.mission_id),
            "agent_id": str(claim_data.agent_id),
        }
    )
    create_event(event_data, session)
    
    return step


@router.post("/{step_id}/complete", response_model=StepSchema)
def complete_step(
    step_id: UUID,
    completion_data: StepComplete,
    session: Session = Depends(get_session),
):
    """Mark a step as completed."""
    step = session.get(Step, step_id)
    if not step:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Step not found"
        )
    
    if step.status not in [StepStatus.CLAIMED, StepStatus.RUNNING]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Step cannot be completed from status: {step.status}"
        )
    
    step.status = StepStatus.COMPLETED
    step.output = completion_data.output
    step.completed_at = datetime.utcnow()
    step.error = None  # Clear any previous errors
    
    session.commit()
    session.refresh(step)
    
    # Create event for step completed
    from ..api.events import create_event
    # Get project_id through mission relationship
    mission = session.get(step.mission)
    event_data = EventCreate(
        event_type="step.completed",
        source_agent_id=step.claimed_by_agent_id,
        project_id=mission.project_id if mission else None,
        payload={
            "step_id": str(step.id),
            "mission_id": str(step.mission_id),
            "step_type": step.step_type,
            "output": completion_data.output,
            "metadata": completion_data.metadata or {},
        }
    )
    create_event(event_data, session)
    
    return step


@router.post("/{step_id}/fail", response_model=StepSchema)
def fail_step(
    step_id: UUID,
    failure_data: StepFail,
    session: Session = Depends(get_session),
):
    """Mark a step as failed."""
    step = session.get(Step, step_id)
    if not step:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Step not found"
        )
    
    if step.status not in [StepStatus.CLAIMED, StepStatus.RUNNING]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Step cannot be failed from status: {step.status}"
        )
    
    step.status = StepStatus.FAILED
    step.error = failure_data.error
    step.completed_at = datetime.utcnow()
    
    session.commit()
    session.refresh(step)
    
    # Create event for step failed
    from ..api.events import create_event
    # Get project_id through mission relationship
    mission = session.get(step.mission)
    event_data = EventCreate(
        event_type="step.failed",
        source_agent_id=step.claimed_by_agent_id,
        project_id=mission.project_id if mission else None,
        payload={
            "step_id": str(step.id),
            "mission_id": str(step.mission_id),
            "step_type": step.step_type,
            "error": failure_data.error,
            "metadata": failure_data.metadata or {},
        }
    )
    create_event(event_data, session)
    
    return step


@router.post("/{step_id}/start", response_model=StepSchema)
def start_step(
    step_id: UUID,
    session: Session = Depends(get_session),
):
    """Start a claimed step."""
    step = session.get(Step, step_id)
    if not step:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Step not found"
        )
    
    if step.status != StepStatus.CLAIMED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Step cannot be started from status: {step.status}"
        )
    
    step.status = StepStatus.RUNNING
    step.started_at = datetime.utcnow()
    
    session.commit()
    session.refresh(step)
    return step