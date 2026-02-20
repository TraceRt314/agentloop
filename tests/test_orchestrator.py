"""Tests for the OrchestrationEngine tick cycle."""

from datetime import datetime, timedelta
from unittest.mock import patch

from agentloop.engine.orchestrator import OrchestrationEngine
from agentloop.models import (
    MissionStatus,
    ProposalStatus,
    StepStatus,
    StepType,
)
from tests.conftest import (
    make_agent,
    make_event,
    make_mission,
    make_project,
    make_proposal,
    make_step,
    make_trigger,
)


def test_tick_returns_result(session):
    """tick() should return an OrchestrationResult even with no data."""
    orch = OrchestrationEngine()
    result = orch.tick(session)
    assert result.duration_ms >= 0
    assert result.errors == []


def test_auto_approve_converts_to_mission(session):
    """Approved proposals should produce missions on the next tick."""
    project = make_project(session)
    agent = make_agent(session, project)
    proposal = make_proposal(session, agent, project, auto_approve=True)

    orch = OrchestrationEngine()
    orch.tick(session)  # approve
    orch.tick(session)  # create mission + steps

    session.refresh(proposal)
    assert proposal.status == ProposalStatus.APPROVED

    from sqlmodel import select
    from agentloop.models import Mission

    missions = session.exec(
        select(Mission).where(Mission.proposal_id == proposal.id)
    ).all()
    assert len(missions) == 1
    assert missions[0].status == MissionStatus.ACTIVE


def test_mission_gets_default_steps(session):
    """A newly-active mission should receive the 4 default steps."""
    project = make_project(session)
    agent = make_agent(session, project)
    proposal = make_proposal(session, agent, project, status=ProposalStatus.APPROVED)
    # Proposal already approved — first tick should create mission + steps

    orch = OrchestrationEngine()
    orch.tick(session)

    from sqlmodel import select
    from agentloop.models import Mission, Step

    mission = session.exec(
        select(Mission).where(Mission.proposal_id == proposal.id)
    ).first()
    assert mission is not None
    steps = session.exec(select(Step).where(Step.mission_id == mission.id)).all()
    assert len(steps) == 4
    types = {s.step_type for s in steps}
    assert types == {StepType.RESEARCH, StepType.CODE, StepType.TEST, StepType.REVIEW}


def test_mission_completion_on_all_steps_done(session):
    """Mission should transition to COMPLETED when all steps finish."""
    project = make_project(session)
    agent = make_agent(session, project)
    proposal = make_proposal(session, agent, project, status=ProposalStatus.APPROVED)
    mission = make_mission(session, proposal, project, agent)
    for i in range(3):
        make_step(
            session,
            mission,
            order_index=i,
            title=f"Step {i}",
            status=StepStatus.COMPLETED,
        )

    orch = OrchestrationEngine()
    orch.tick(session)

    session.refresh(mission)
    assert mission.status == MissionStatus.COMPLETED
    assert mission.completed_at is not None


def test_mission_not_completed_with_pending_steps(session):
    """Mission should stay ACTIVE if any step is still pending."""
    project = make_project(session)
    agent = make_agent(session, project)
    proposal = make_proposal(session, agent, project, status=ProposalStatus.APPROVED)
    mission = make_mission(session, proposal, project, agent)
    make_step(session, mission, order_index=0, status=StepStatus.COMPLETED)
    make_step(session, mission, order_index=1, status=StepStatus.PENDING)

    orch = OrchestrationEngine()
    orch.tick(session)

    session.refresh(mission)
    assert mission.status == MissionStatus.ACTIVE


@patch("agentloop.integrations.mission_control.ask_user", return_value={"id": "mock"})
def test_escalate_stuck_missions(mock_ask, session):
    """Stuck missions should be escalated via the on_stuck_check hook."""
    project = make_project(session)
    agent = make_agent(session, project)
    proposal = make_proposal(
        session,
        agent,
        project,
        status=ProposalStatus.APPROVED,
        mc_board_id="board-1",
        mc_task_id="task-1",
    )
    mission = make_mission(session, proposal, project, agent)
    make_step(session, mission, order_index=0, status=StepStatus.FAILED, error="timeout")

    # Import the MC plugin hook and wire it into a mock plugin manager
    from unittest.mock import MagicMock
    from agentloop.plugin import PluginManager

    pm = MagicMock(spec=PluginManager)

    # When on_stuck_check is dispatched, call the real MC hook
    import importlib
    import sys

    # Import the plugin hook module directly
    spec = importlib.util.spec_from_file_location(
        "mc_hooks", "plugins/mission-control/hooks.py"
    )
    mc_hooks = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mc_hooks)

    def _dispatch_hook(name, **kwargs):
        if name == "on_stuck_check":
            mc_hooks.on_stuck_check(**kwargs)
        return []

    pm.dispatch_hook.side_effect = _dispatch_hook

    orch = OrchestrationEngine(plugin_manager=pm)
    result = orch.tick(session)

    mock_ask.assert_called_once()
    call_args = mock_ask.call_args
    assert call_args[0][0] == "board-1"
    assert "stuck" in call_args[0][1].lower()

    # Should have created an escalation event
    from sqlmodel import select
    from agentloop.models import Event

    events = session.exec(
        select(Event).where(Event.event_type == "mission.escalated")
    ).all()
    assert len(events) == 1


def test_trigger_fires_on_matching_event(session):
    """A trigger should fire when a matching event appears."""
    project = make_project(session)
    agent = make_agent(session, project)
    proposal = make_proposal(session, agent, project, status=ProposalStatus.APPROVED)
    mission = make_mission(session, proposal, project, agent)
    make_step(session, mission, order_index=0, status=StepStatus.COMPLETED)

    make_trigger(
        session,
        project,
        event_pattern={"event_type": "step.completed"},
        action={
            "type": "create_step",
            "title": "Auto-deploy",
            "step_type": "deploy",
            "order_index": 99,
        },
    )
    make_event(
        session,
        project,
        event_type="step.completed",
        source_agent_id=agent.id,
        payload={"mission_id": str(mission.id), "step_id": "test"},
    )

    orch = OrchestrationEngine()
    result = orch.tick(session)
    assert result.triggers_fired >= 1


def test_cleanup_old_events(session):
    """Events older than 30 days should be cleaned up."""
    project = make_project(session)
    old_event = make_event(session, project)
    old_event.created_at = datetime.utcnow() - timedelta(days=31)
    session.commit()

    fresh_event = make_event(session, project, event_type="fresh.event")

    orch = OrchestrationEngine()
    orch.tick(session)

    from sqlmodel import select
    from agentloop.models import Event

    remaining = session.exec(select(Event)).all()
    event_types = {e.event_type for e in remaining}
    assert "fresh.event" in event_types


def test_expire_old_proposals(session):
    """Pending proposals older than 7 days should expire."""
    project = make_project(session)
    agent = make_agent(session, project)
    old_proposal = make_proposal(
        session, agent, project, auto_approve=False, title="Old proposal"
    )
    old_proposal.created_at = datetime.utcnow() - timedelta(days=8)
    session.commit()

    orch = OrchestrationEngine()
    orch.tick(session)

    session.refresh(old_proposal)
    assert old_proposal.status == ProposalStatus.EXPIRED
