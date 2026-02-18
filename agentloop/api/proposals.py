"""Proposal management API endpoints."""

from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from sqlmodel import select

from ..database import get_session
from ..models import Proposal, ProposalStatus
from ..schemas import (
    Proposal as ProposalSchema,
    ProposalApproval,
    ProposalCreate,
    ProposalUpdate,
)

router = APIRouter(prefix="/api/v1/proposals", tags=["proposals"])


@router.get("/", response_model=List[ProposalSchema])
def list_proposals(
    project_id: UUID = None,
    status: ProposalStatus = None,
    agent_id: UUID = None,
    limit: int = 100,
    session: Session = Depends(get_session),
):
    """List proposals with optional filtering."""
    query = select(Proposal).order_by(Proposal.created_at.desc())
    
    if project_id:
        query = query.where(Proposal.project_id == project_id)
    if status:
        query = query.where(Proposal.status == status)
    if agent_id:
        query = query.where(Proposal.agent_id == agent_id)
    
    query = query.limit(limit)
    result = session.exec(query)
    return result.all()


@router.post("/", response_model=ProposalSchema, status_code=status.HTTP_201_CREATED)
def create_proposal(
    proposal_data: ProposalCreate,
    session: Session = Depends(get_session),
):
    """Create a new proposal."""
    proposal = Proposal(**proposal_data.model_dump())
    
    # If auto_approve is True, automatically approve the proposal
    if proposal.auto_approve:
        proposal.status = ProposalStatus.APPROVED
        proposal.reviewed_by = "system"
        proposal.reviewed_at = datetime.utcnow()
    else:
        proposal.status = ProposalStatus.PENDING
    
    session.add(proposal)
    session.commit()
    session.refresh(proposal)
    return proposal


@router.get("/{proposal_id}", response_model=ProposalSchema)
def get_proposal(
    proposal_id: UUID,
    session: Session = Depends(get_session),
):
    """Get a specific proposal by ID."""
    proposal = session.get(Proposal, proposal_id)
    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proposal not found"
        )
    return proposal


@router.patch("/{proposal_id}", response_model=ProposalSchema)
def update_proposal(
    proposal_id: UUID,
    proposal_update: ProposalUpdate,
    session: Session = Depends(get_session),
):
    """Update a proposal."""
    proposal = session.get(Proposal, proposal_id)
    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proposal not found"
        )
    
    # Don't allow status changes through this endpoint
    # Use the approval endpoint instead
    update_data = proposal_update.model_dump(exclude_unset=True)
    if "status" in update_data:
        del update_data["status"]
    
    for field, value in update_data.items():
        setattr(proposal, field, value)
    
    session.commit()
    session.refresh(proposal)
    return proposal


@router.post("/{proposal_id}/approve", response_model=ProposalSchema)
def approve_proposal(
    proposal_id: UUID,
    approval_data: ProposalApproval,
    session: Session = Depends(get_session),
):
    """Approve or reject a proposal."""
    proposal = session.get(Proposal, proposal_id)
    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proposal not found"
        )
    
    if proposal.status not in [ProposalStatus.DRAFT, ProposalStatus.PENDING]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot change status from {proposal.status}"
        )
    
    if approval_data.status not in [ProposalStatus.APPROVED, ProposalStatus.REJECTED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status must be 'approved' or 'rejected'"
        )
    
    proposal.status = approval_data.status
    proposal.reviewed_by = approval_data.reviewed_by
    proposal.reviewed_at = datetime.utcnow()
    
    session.commit()
    session.refresh(proposal)
    return proposal


@router.delete("/{proposal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_proposal(
    proposal_id: UUID,
    session: Session = Depends(get_session),
):
    """Delete a proposal."""
    proposal = session.get(Proposal, proposal_id)
    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proposal not found"
        )
    
    session.delete(proposal)
    session.commit()