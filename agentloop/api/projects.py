"""Project management API endpoints."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session
from sqlmodel import select

from ..database import get_session
from ..models import Project, ProjectStatus
from ..schemas import (
    Project as ProjectSchema,
    ProjectCreate,
    ProjectUpdate,
)

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


@router.get("/", response_model=List[ProjectSchema])
def list_projects(
    session: Session = Depends(get_session),
    status_filter: Optional[ProjectStatus] = Query(None, alias="status"),
    include_decommissioned: bool = Query(False),
):
    """List projects. Excludes decommissioned by default."""
    stmt = select(Project)
    if status_filter:
        stmt = stmt.where(Project.status == status_filter)
    elif not include_decommissioned:
        stmt = stmt.where(Project.status != ProjectStatus.DECOMMISSIONED)
    return session.exec(stmt).all()


@router.post("/", response_model=ProjectSchema, status_code=status.HTTP_201_CREATED)
def create_project(
    project_data: ProjectCreate,
    session: Session = Depends(get_session),
):
    """Create a new project."""
    # Check if slug already exists
    existing = session.exec(
        select(Project).where(Project.slug == project_data.slug)
    )
    if existing.first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Project with this slug already exists"
        )
    
    project = Project(**project_data.model_dump())
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectSchema)
def get_project(
    project_id: UUID,
    session: Session = Depends(get_session),
):
    """Get a specific project by ID."""
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    return project


@router.get("/by-slug/{slug}", response_model=ProjectSchema)
def get_project_by_slug(
    slug: str,
    session: Session = Depends(get_session),
):
    """Get a specific project by slug."""
    result = session.exec(select(Project).where(Project.slug == slug))
    project = result.first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    return project


@router.patch("/{project_id}", response_model=ProjectSchema)
def update_project(
    project_id: UUID,
    project_update: ProjectUpdate,
    session: Session = Depends(get_session),
):
    """Update a project."""
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    update_data = project_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)
    
    session.commit()
    session.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: UUID,
    session: Session = Depends(get_session),
):
    """Delete a project."""
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    session.delete(project)
    session.commit()