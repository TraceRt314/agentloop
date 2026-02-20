"""Tests for the WorkerEngine."""

from unittest.mock import patch, MagicMock

from agentloop.engine.worker import WorkerEngine
from agentloop.models import StepStatus, StepType
from tests.conftest import (
    make_agent,
    make_mission,
    make_project,
    make_proposal,
    make_step,
)


def test_find_available_steps(session):
    """Worker should find pending steps matching the agent's project."""
    project = make_project(session)
    agent = make_agent(session, project)
    proposal = make_proposal(session, agent, project, status="approved")
    mission = make_mission(session, proposal, project, agent)
    step = make_step(session, mission, status=StepStatus.PENDING)

    worker = WorkerEngine()
    available = worker._find_available_steps(agent, session)
    assert len(available) == 1
    assert available[0].id == step.id


def test_no_steps_for_wrong_project(session):
    """Steps in a different project should not be returned."""
    project1 = make_project(session, slug="proj-1", name="Project 1")
    project2 = make_project(session, slug="proj-2", name="Project 2")
    agent1 = make_agent(session, project1, name="agent-1")
    agent2 = make_agent(session, project2, name="agent-2")
    proposal = make_proposal(session, agent2, project2, status="approved")
    mission = make_mission(session, proposal, project2, agent2)
    make_step(session, mission, status=StepStatus.PENDING)

    worker = WorkerEngine()
    available = worker._find_available_steps(agent1, session)
    assert len(available) == 0


def test_claimed_step_not_available_to_others(session):
    """A step claimed by one agent should not appear for another."""
    project = make_project(session)
    agent1 = make_agent(session, project, name="agent-1")
    agent2 = make_agent(session, project, name="agent-2")
    proposal = make_proposal(session, agent1, project, status="approved")
    mission = make_mission(session, proposal, project, agent1)
    make_step(
        session,
        mission,
        status=StepStatus.CLAIMED,
        claimed_by_agent_id=agent1.id,
    )

    worker = WorkerEngine()
    available = worker._find_available_steps(agent2, session)
    assert len(available) == 0


def test_capability_check(session):
    """Agent without the required capability should be excluded."""
    project = make_project(session)
    agent = make_agent(
        session,
        project,
        config={"capabilities": ["run_tests"]},
    )
    proposal = make_proposal(session, agent, project, status="approved")
    mission = make_mission(session, proposal, project, agent)
    make_step(session, mission, step_type=StepType.DEPLOY, status=StepStatus.PENDING)

    worker = WorkerEngine()
    available = worker._find_available_steps(agent, session)
    assert len(available) == 0


def test_general_work_capability_matches_all(session):
    """An agent with 'general_work' should handle any step type."""
    project = make_project(session)
    agent = make_agent(
        session,
        project,
        config={"capabilities": ["general_work"]},
    )
    proposal = make_proposal(session, agent, project, status="approved")
    mission = make_mission(session, proposal, project, agent)
    make_step(session, mission, step_type=StepType.DEPLOY, status=StepStatus.PENDING)

    worker = WorkerEngine()
    available = worker._find_available_steps(agent, session)
    assert len(available) == 1


@patch("agentloop.engine.worker.WorkerEngine._dispatch_to_backend", return_value=False)
def test_simulate_step_execution_fallback(mock_dispatch, session):
    """When gateway is unavailable, step should be simulated."""
    project = make_project(session)
    agent = make_agent(session, project)
    proposal = make_proposal(session, agent, project, status="approved")
    mission = make_mission(session, proposal, project, agent)
    step = make_step(session, mission, status=StepStatus.PENDING)

    worker = WorkerEngine()
    result = worker.find_and_execute_work(agent, session)

    assert result is True
    session.refresh(step)
    assert step.status == StepStatus.COMPLETED
    assert step.output is not None


def test_generate_work_prompt(session):
    """Work prompt should include mission and step context."""
    project = make_project(session)
    agent = make_agent(session, project, name="Coder")
    proposal = make_proposal(session, agent, project, status="approved")
    mission = make_mission(
        session, proposal, project, agent, title="Fix auth", description="Broken login"
    )
    step = make_step(
        session,
        mission,
        title="Write patch",
        description="Patch the auth module",
        step_type=StepType.CODE,
    )

    worker = WorkerEngine()
    prompt = worker._generate_work_prompt(step, agent, agent.config, {}, session)

    assert "Coder" in prompt
    assert "Write patch" in prompt
    assert "Fix auth" in prompt
