"""Event bus API endpoints."""

from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from sqlmodel import select

from ..database import get_session
from ..models import Event
from ..schemas import (
    Event as EventSchema,
    EventCreate,
)

router = APIRouter(prefix="/api/v1/events", tags=["events"])


@router.get("/", response_model=List[EventSchema])
def list_events(
    project_id: UUID = None,
    event_type: str = None,
    source_agent_id: UUID = None,
    limit: int = 100,
    offset: int = 0,
    session: Session = Depends(get_session),
):
    """List events with optional filtering."""
    query = select(Event).order_by(Event.created_at.desc())
    
    if project_id:
        query = query.where(Event.project_id == project_id)
    if event_type:
        query = query.where(Event.event_type == event_type)
    if source_agent_id:
        query = query.where(Event.source_agent_id == source_agent_id)
    
    query = query.offset(offset).limit(limit)
    result = session.exec(query)
    return result.all()


@router.post("/", response_model=EventSchema, status_code=status.HTTP_201_CREATED)
def create_event(
    event_data: EventCreate,
    session: Session = Depends(get_session),
):
    """Create a new event."""
    event = Event(**event_data.model_dump())
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


@router.get("/{event_id}", response_model=EventSchema)
def get_event(
    event_id: UUID,
    session: Session = Depends(get_session),
):
    """Get a specific event by ID."""
    event = session.get(Event, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    return event


@router.get("/types/", response_model=List[str])
def list_event_types(
    project_id: UUID = None,
    session: Session = Depends(get_session),
):
    """List all unique event types."""
    query = select(Event.event_type).distinct()
    
    if project_id:
        query = query.where(Event.project_id == project_id)
    
    result = session.exec(query)
    return result.all()


@router.post("/bulk", response_model=List[EventSchema], status_code=status.HTTP_201_CREATED)
def create_events_bulk(
    events_data: List[EventCreate],
    session: Session = Depends(get_session),
):
    """Create multiple events in bulk."""
    events = [Event(**event_data.model_dump()) for event_data in events_data]
    
    for event in events:
        session.add(event)
    
    session.commit()
    
    # Refresh all events to get their IDs
    for event in events:
        session.refresh(event)
    
    return events


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(
    event_id: UUID,
    session: Session = Depends(get_session),
):
    """Delete an event."""
    event = session.get(Event, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    
    session.delete(event)
    session.commit()