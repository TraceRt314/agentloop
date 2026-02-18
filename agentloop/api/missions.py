"""Mission management API endpoints."""

from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from sqlmodel import select

from ..database import get_session
from ..models import Mission, MissionStatus, Step
from ..schemas import (
    Mission as MissionSchema,
    MissionCreate,
    MissionUpdate,
    Step as StepSchema,
    StepCreate,
)

router = APIRouter(prefix="/api/v1/missions", tags=["missions"])


@router.get("/", response_model=List[MissionSchema])
def list_missions(
    project_id: UUID = None,
    status: MissionStatus = None,
    assigned_agent_id: UUID = None,
    limit: int = 100,
    session: Session = Depends(get_session),
):
    """List missions with optional filtering."""
    query = select(Mission).order_by(Mission.created_at.desc())
    
    if project_id:
        query = query.where(Mission.project_id == project_id)
    if status:
        query = query.where(Mission.status == status)
    if assigned_agent_id:
        query = query.where(Mission.assigned_agent_id == assigned_agent_id)
    
    query = query.limit(limit)
    result = session.exec(query)
    return result.all()


@router.post("/", response_model=MissionSchema, status_code=status.HTTP_201_CREATED)
def create_mission(
    mission_data: MissionCreate,
    session: Session = Depends(get_session),
):
    """Create a new mission."""
    mission = Mission(**mission_data.model_dump())
    mission.status = MissionStatus.PLANNED
    
    session.add(mission)
    session.commit()
    session.refresh(mission)
    return mission


@router.get("/{mission_id}", response_model=MissionSchema)
def get_mission(
    mission_id: UUID,
    session: Session = Depends(get_session),
):
    """Get a specific mission by ID."""
    mission = session.get(Mission, mission_id)
    if not mission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mission not found"
        )
    return mission


@router.patch("/{mission_id}", response_model=MissionSchema)
def update_mission(
    mission_id: UUID,
    mission_update: MissionUpdate,
    session: Session = Depends(get_session),
):
    """Update a mission."""
    mission = session.get(Mission, mission_id)
    if not mission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mission not found"
        )
    
    update_data = mission_update.model_dump(exclude_unset=True)
    
    # Handle status changes with side effects
    if "status" in update_data:
        new_status = update_data["status"]
        if new_status == MissionStatus.COMPLETED and mission.status != MissionStatus.COMPLETED:
            mission.completed_at = datetime.utcnow()
        elif new_status != MissionStatus.COMPLETED:
            mission.completed_at = None
    
    for field, value in update_data.items():
        setattr(mission, field, value)
    
    session.commit()
    session.refresh(mission)
    return mission


@router.delete("/{mission_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_mission(
    mission_id: UUID,
    session: Session = Depends(get_session),
):
    """Delete a mission."""
    mission = session.get(Mission, mission_id)
    if not mission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mission not found"
        )
    
    session.delete(mission)
    session.commit()


@router.get("/{mission_id}/steps", response_model=List[StepSchema])
def list_mission_steps(
    mission_id: UUID,
    session: Session = Depends(get_session),
):
    """List all steps for a mission."""
    # Verify mission exists
    mission = session.get(Mission, mission_id)
    if not mission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mission not found"
        )
    
    result = session.exec(
        select(Step)
        .where(Step.mission_id == mission_id)
        .order_by(Step.order_index.asc())
    )
    return result.all()


@router.post("/{mission_id}/steps", response_model=StepSchema, status_code=status.HTTP_201_CREATED)
def create_mission_step(
    mission_id: UUID,
    step_data: StepCreate,
    session: Session = Depends(get_session),
):
    """Create a new step for a mission."""
    # Verify mission exists
    mission = session.get(Mission, mission_id)
    if not mission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mission not found"
        )
    
    # Ensure mission_id matches
    step_data.mission_id = mission_id
    
    # If order_index not provided, append to end
    if not hasattr(step_data, 'order_index') or step_data.order_index is None:
        result = session.exec(
            select(Step)
            .where(Step.mission_id == mission_id)
            .order_by(Step.order_index.desc())
            .limit(1)
        )
        last_step = result.first()
        step_data.order_index = (last_step.order_index + 1) if last_step else 0
    
    step = Step(**step_data.model_dump())
    session.add(step)
    session.commit()
    session.refresh(step)
    return step