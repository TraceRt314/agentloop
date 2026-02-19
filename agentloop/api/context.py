"""Project context API endpoints for persistent agent memory."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from ..database import get_session
from ..models import Project, ProjectContext
from ..schemas import (
    ProjectContext as ProjectContextSchema,
    ProjectContextCreate,
)

router = APIRouter(prefix="/api/v1/context", tags=["context"])


@router.get("/{project_id}", response_model=List[ProjectContextSchema])
def list_context(
    project_id: UUID,
    category: Optional[str] = Query(None),
    session: Session = Depends(get_session),
):
    """List context entries for a project, optionally filtered by category."""
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    stmt = select(ProjectContext).where(ProjectContext.project_id == project_id)
    if category:
        stmt = stmt.where(ProjectContext.category == category)
    stmt = stmt.order_by(ProjectContext.created_at.desc())
    return session.exec(stmt).all()


@router.post(
    "/", response_model=ProjectContextSchema, status_code=status.HTTP_201_CREATED
)
def create_context(
    data: ProjectContextCreate,
    session: Session = Depends(get_session),
):
    """Create or upsert a context entry (unique by project+category+key)."""
    project = session.get(Project, data.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Upsert: if same project+category+key exists, update content
    existing = session.exec(
        select(ProjectContext)
        .where(ProjectContext.project_id == data.project_id)
        .where(ProjectContext.category == data.category)
        .where(ProjectContext.key == data.key)
    ).first()

    if existing:
        existing.content = data.content
        existing.source_agent_id = data.source_agent_id
        existing.source_step_id = data.source_step_id
        session.commit()
        session.refresh(existing)
        return existing

    entry = ProjectContext(**data.model_dump())
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_context(
    entry_id: UUID,
    session: Session = Depends(get_session),
):
    """Delete a context entry."""
    entry = session.get(ProjectContext, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Context entry not found")
    session.delete(entry)
    session.commit()
