"""Trigger management API endpoints."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from sqlmodel import select

from ..database import get_session
from ..models import Trigger
from ..schemas import (
    Trigger as TriggerSchema,
    TriggerCreate,
    TriggerUpdate,
)

router = APIRouter(prefix="/api/v1/triggers", tags=["triggers"])


@router.get("/", response_model=List[TriggerSchema])
def list_triggers(
    project_id: UUID = None,
    enabled: bool = None,
    session: Session = Depends(get_session),
):
    """List triggers with optional filtering."""
    query = select(Trigger).order_by(Trigger.created_at.desc())
    
    if project_id:
        query = query.where(Trigger.project_id == project_id)
    if enabled is not None:
        query = query.where(Trigger.enabled == enabled)
    
    result = session.exec(query)
    return result.all()


@router.post("/", response_model=TriggerSchema, status_code=status.HTTP_201_CREATED)
def create_trigger(
    trigger_data: TriggerCreate,
    session: Session = Depends(get_session),
):
    """Create a new trigger."""
    # Check if trigger name already exists for this project
    existing = session.exec(
        select(Trigger).where(
            Trigger.project_id == trigger_data.project_id,
            Trigger.name == trigger_data.name
        )
    )
    if existing.first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Trigger with this name already exists for this project"
        )
    
    trigger = Trigger(**trigger_data.model_dump())
    session.add(trigger)
    session.commit()
    session.refresh(trigger)
    return trigger


@router.get("/{trigger_id}", response_model=TriggerSchema)
def get_trigger(
    trigger_id: UUID,
    session: Session = Depends(get_session),
):
    """Get a specific trigger by ID."""
    trigger = session.get(Trigger, trigger_id)
    if not trigger:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trigger not found"
        )
    return trigger


@router.patch("/{trigger_id}", response_model=TriggerSchema)
def update_trigger(
    trigger_id: UUID,
    trigger_update: TriggerUpdate,
    session: Session = Depends(get_session),
):
    """Update a trigger."""
    trigger = session.get(Trigger, trigger_id)
    if not trigger:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trigger not found"
        )
    
    update_data = trigger_update.model_dump(exclude_unset=True)
    
    # Check name uniqueness if name is being updated
    if "name" in update_data and update_data["name"] != trigger.name:
        existing = session.exec(
            select(Trigger).where(
                Trigger.project_id == trigger.project_id,
                Trigger.name == update_data["name"],
                Trigger.id != trigger_id
            )
        )
        if existing.first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Trigger with this name already exists for this project"
            )
    
    for field, value in update_data.items():
        setattr(trigger, field, value)
    
    session.commit()
    session.refresh(trigger)
    return trigger


@router.delete("/{trigger_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trigger(
    trigger_id: UUID,
    session: Session = Depends(get_session),
):
    """Delete a trigger."""
    trigger = session.get(Trigger, trigger_id)
    if not trigger:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trigger not found"
        )
    
    session.delete(trigger)
    session.commit()


@router.post("/{trigger_id}/enable", response_model=TriggerSchema)
def enable_trigger(
    trigger_id: UUID,
    session: Session = Depends(get_session),
):
    """Enable a trigger."""
    trigger = session.get(Trigger, trigger_id)
    if not trigger:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trigger not found"
        )
    
    trigger.enabled = True
    session.commit()
    session.refresh(trigger)
    return trigger


@router.post("/{trigger_id}/disable", response_model=TriggerSchema)
def disable_trigger(
    trigger_id: UUID,
    session: Session = Depends(get_session),
):
    """Disable a trigger."""
    trigger = session.get(Trigger, trigger_id)
    if not trigger:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trigger not found"
        )
    
    trigger.enabled = False
    session.commit()
    session.refresh(trigger)
    return trigger