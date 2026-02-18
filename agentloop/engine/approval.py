"""Auto-approval and human-in-the-loop approval engine."""

from datetime import datetime
from typing import List

from sqlmodel import Session
from sqlmodel import select

from ..models import Proposal, ProposalStatus


class ApprovalEngine:
    """Handles automatic approval and human-in-the-loop workflows."""
    
    def process_pending_approvals(self, session: Session) -> List[Proposal]:
        """Process all pending approvals, handling auto-approve logic."""
        processed_proposals = []
        
        try:
            # Find all pending proposals
            pending_proposals = session.exec(
                select(Proposal).where(Proposal.status == ProposalStatus.PENDING)
            )
            
            for proposal in pending_proposals.all():
                if self._should_auto_approve(proposal, session):
                    proposal.status = ProposalStatus.APPROVED
                    proposal.reviewed_by = "system"
                    proposal.reviewed_at = datetime.utcnow()
                    processed_proposals.append(proposal)
            
            session.commit()
        
        except Exception as e:
            # Log error but don't fail the whole process
            pass
        
        return processed_proposals
    
    def _should_auto_approve(self, proposal: Proposal, session: Session) -> bool:
        """Determine if a proposal should be automatically approved."""
        # Check the proposal's auto_approve flag
        if not proposal.auto_approve:
            return False
        
        # Additional rules can be added here:
        
        # 1. Low-risk proposals (certain priorities, certain agents, etc.)
        if proposal.priority.value in ["low", "medium"]:
            # Get the agent to check their auto-approval settings
            from ..models import Agent
            agent = session.get(Agent, proposal.agent_id)
            if agent and agent.config.get("auto_approve_proposals", False):
                return True
        
        # 2. Tactical fixes and small changes
        if any(keyword in proposal.title.lower() for keyword in ["fix", "patch", "hotfix", "typo"]):
            return True
        
        # 3. Documentation updates
        if any(keyword in proposal.title.lower() for keyword in ["docs", "documentation", "readme"]):
            return True
        
        # 4. Test improvements
        if any(keyword in proposal.title.lower() for keyword in ["test", "spec", "testing"]):
            return True
        
        return False
    
    def get_proposals_needing_human_review(self, session: Session) -> List[Proposal]:
        """Get proposals that need human review."""
        try:
            # Find pending proposals that haven't been auto-approved
            pending_proposals = session.exec(
                select(Proposal).where(
                    Proposal.status == ProposalStatus.PENDING,
                    Proposal.auto_approve == False
                )
            )
            
            return pending_proposals.all()
        
        except Exception as e:
            return []
    
    def approve_proposal(
        self, 
        proposal: Proposal, 
        reviewed_by: str,
        session: Session
    ) -> bool:
        """Manually approve a proposal."""
        try:
            if proposal.status != ProposalStatus.PENDING:
                return False
            
            proposal.status = ProposalStatus.APPROVED
            proposal.reviewed_by = reviewed_by
            proposal.reviewed_at = datetime.utcnow()
            
            session.commit()
            return True
        
        except Exception as e:
            return False
    
    def reject_proposal(
        self, 
        proposal: Proposal, 
        reviewed_by: str,
        rejection_reason: str,
        session: Session
    ) -> bool:
        """Manually reject a proposal."""
        try:
            if proposal.status != ProposalStatus.PENDING:
                return False
            
            proposal.status = ProposalStatus.REJECTED
            proposal.reviewed_by = reviewed_by
            proposal.reviewed_at = datetime.utcnow()
            
            # Store rejection reason in the proposal description or a separate field
            # For now, we'll append it to the rationale
            proposal.rationale += f"\n\nREJECTED: {rejection_reason}"
            
            session.commit()
            return True
        
        except Exception as e:
            return False