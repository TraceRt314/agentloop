"""Tests for the ApprovalEngine."""

from agentloop.engine.approval import ApprovalEngine
from agentloop.models import ProposalPriority, ProposalStatus
from tests.conftest import make_agent, make_project, make_proposal


def test_auto_approve_with_flag(session):
    """Proposals with auto_approve=True and matching keywords get approved."""
    project = make_project(session)
    agent = make_agent(session, project)
    proposal = make_proposal(
        session, agent, project, auto_approve=True, title="Fix typo in README"
    )

    engine = ApprovalEngine()
    processed = engine.process_pending_approvals(session)

    assert len(processed) == 1
    session.refresh(proposal)
    assert proposal.status == ProposalStatus.APPROVED
    assert proposal.reviewed_by == "system"


def test_no_auto_approve_without_flag(session):
    """Proposals with auto_approve=False should NOT be auto-approved."""
    project = make_project(session)
    agent = make_agent(session, project)
    proposal = make_proposal(
        session,
        agent,
        project,
        auto_approve=False,
        title="Big refactor",
        priority=ProposalPriority.HIGH,
    )

    engine = ApprovalEngine()
    processed = engine.process_pending_approvals(session)

    assert len(processed) == 0
    session.refresh(proposal)
    assert proposal.status == ProposalStatus.PENDING


def test_auto_approve_docs_keyword(session):
    """Proposals about docs get auto-approved when auto_approve=True."""
    project = make_project(session)
    agent = make_agent(session, project)
    proposal = make_proposal(
        session, agent, project, auto_approve=True, title="Update documentation"
    )

    engine = ApprovalEngine()
    processed = engine.process_pending_approvals(session)
    assert len(processed) == 1


def test_auto_approve_test_keyword(session):
    """Proposals about tests get auto-approved when auto_approve=True."""
    project = make_project(session)
    agent = make_agent(session, project)
    proposal = make_proposal(
        session, agent, project, auto_approve=True, title="Add test coverage"
    )

    engine = ApprovalEngine()
    processed = engine.process_pending_approvals(session)
    assert len(processed) == 1


def test_manual_approve(session):
    """approve_proposal should transition a pending proposal to APPROVED."""
    project = make_project(session)
    agent = make_agent(session, project)
    proposal = make_proposal(
        session, agent, project, auto_approve=False, title="Refactor auth"
    )

    engine = ApprovalEngine()
    result = engine.approve_proposal(proposal, "human-reviewer", session)

    assert result is True
    session.refresh(proposal)
    assert proposal.status == ProposalStatus.APPROVED
    assert proposal.reviewed_by == "human-reviewer"


def test_manual_reject(session):
    """reject_proposal should transition a pending proposal to REJECTED."""
    project = make_project(session)
    agent = make_agent(session, project)
    proposal = make_proposal(
        session, agent, project, auto_approve=False, title="Bad idea"
    )

    engine = ApprovalEngine()
    result = engine.reject_proposal(proposal, "human-reviewer", "Too risky", session)

    assert result is True
    session.refresh(proposal)
    assert proposal.status == ProposalStatus.REJECTED
    assert "REJECTED: Too risky" in proposal.rationale


def test_cannot_approve_non_pending(session):
    """Approving an already-approved proposal should return False."""
    project = make_project(session)
    agent = make_agent(session, project)
    proposal = make_proposal(
        session, agent, project, status=ProposalStatus.APPROVED
    )

    engine = ApprovalEngine()
    result = engine.approve_proposal(proposal, "reviewer", session)
    assert result is False


def test_proposals_needing_human_review(session):
    """Only non-auto-approve pending proposals need human review."""
    project = make_project(session)
    agent = make_agent(session, project)
    make_proposal(session, agent, project, auto_approve=True, title="Auto one")
    manual = make_proposal(
        session,
        agent,
        project,
        auto_approve=False,
        title="Manual review needed",
    )

    engine = ApprovalEngine()
    needing = engine.get_proposals_needing_human_review(session)

    titles = [p.title for p in needing]
    assert "Manual review needed" in titles
    assert "Auto one" not in titles
