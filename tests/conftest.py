"""Shared fixtures for AgentLoop tests."""

import os
import pytest
from typing import Generator
from uuid import UUID

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool
from uuid_extensions import uuid7

# Force test settings before any app import
os.environ["AGENTLOOP_DATABASE_URL"] = "sqlite://"
os.environ["AGENTLOOP_DEBUG"] = "false"
os.environ["AGENTLOOP_LOG_LEVEL"] = "WARNING"
os.environ["AGENTLOOP_MC_BASE_URL"] = "http://mc-test:9999"
os.environ["AGENTLOOP_BOARD_MAP"] = "{}"

from agentloop.models import (
    Agent,
    AgentAction,
    AgentStatus,
    Event,
    Mission,
    MissionStatus,
    Project,
    Proposal,
    ProposalPriority,
    ProposalStatus,
    Step,
    StepStatus,
    StepType,
    Trigger,
)
from agentloop.database import get_session
from agentloop.main import app


# ─── Database fixtures ───


@pytest.fixture(name="engine")
def fixture_engine():
    """In-memory SQLite engine for tests."""
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(eng)
    return eng


@pytest.fixture(name="session")
def fixture_session(engine) -> Generator[Session, None, None]:
    """DB session backed by the in-memory engine."""
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def fixture_client(engine) -> Generator[TestClient, None, None]:
    """FastAPI TestClient wired to the test database."""

    def _override_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = _override_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ─── Factory helpers ───


def make_project(session: Session, **overrides) -> Project:
    """Create and persist a Project."""
    data = {
        "name": "Test Project",
        "slug": "test-project",
        "description": "A test project",
        "config": {},
    }
    data.update(overrides)
    obj = Project(**data)
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


def make_agent(session: Session, project: Project, **overrides) -> Agent:
    """Create and persist an Agent."""
    data = {
        "name": "test-agent",
        "role": "developer",
        "description": "Test agent",
        "status": AgentStatus.ACTIVE,
        "project_id": project.id,
        "config": {"capabilities": ["write_code", "run_tests", "general_work"]},
        "position_x": 2.0,
        "position_y": 3.0,
        "target_x": 2.0,
        "target_y": 3.0,
    }
    data.update(overrides)
    obj = Agent(**data)
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


def make_proposal(
    session: Session, agent: Agent, project: Project, **overrides
) -> Proposal:
    """Create and persist a Proposal."""
    data = {
        "agent_id": agent.id,
        "project_id": project.id,
        "title": "Fix login bug",
        "description": "Fix the broken login flow",
        "rationale": "Users cannot log in",
        "priority": ProposalPriority.MEDIUM,
        "status": ProposalStatus.PENDING,
        "auto_approve": True,
    }
    data.update(overrides)
    obj = Proposal(**data)
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


def make_mission(
    session: Session, proposal: Proposal, project: Project, agent: Agent = None, **overrides
) -> Mission:
    """Create and persist a Mission."""
    data = {
        "proposal_id": proposal.id,
        "project_id": project.id,
        "title": proposal.title,
        "description": proposal.description,
        "status": MissionStatus.ACTIVE,
        "assigned_agent_id": agent.id if agent else None,
    }
    data.update(overrides)
    obj = Mission(**data)
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


def make_step(session: Session, mission: Mission, **overrides) -> Step:
    """Create and persist a Step."""
    data = {
        "mission_id": mission.id,
        "order_index": 0,
        "title": "Implement fix",
        "description": "Write the code fix",
        "step_type": StepType.CODE,
        "status": StepStatus.PENDING,
    }
    data.update(overrides)
    obj = Step(**data)
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


def make_event(session: Session, project: Project, **overrides) -> Event:
    """Create and persist an Event."""
    data = {
        "event_type": "test.event",
        "project_id": project.id,
        "payload": {"key": "value"},
    }
    data.update(overrides)
    obj = Event(**data)
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


def make_trigger(session: Session, project: Project, **overrides) -> Trigger:
    """Create and persist a Trigger."""
    data = {
        "project_id": project.id,
        "name": "test-trigger",
        "event_pattern": {"event_type": "step.completed"},
        "action": {"type": "create_step", "title": "Auto step"},
        "enabled": True,
    }
    data.update(overrides)
    obj = Trigger(**data)
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj
