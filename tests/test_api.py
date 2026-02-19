"""Tests for critical API endpoints."""

from agentloop.models import AgentStatus, MissionStatus, ProposalStatus, StepStatus
from tests.conftest import (
    make_agent,
    make_mission,
    make_project,
    make_proposal,
    make_step,
)


# ─── Health endpoints ───


def test_healthz(client):
    """GET /healthz should return healthy."""
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_deep_health(client, engine):
    """GET /api/v1/health should return status for each subsystem."""
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] in ("healthy", "warning", "degraded")
    assert "checks" in data
    assert "database" in data["checks"]


def test_root(client):
    """GET / should return app info."""
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["name"] == "AgentLoop"


# ─── Projects ───


def test_create_and_list_project(client):
    """POST /api/v1/projects and GET /api/v1/projects."""
    r = client.post(
        "/api/v1/projects",
        json={
            "name": "TestProj",
            "slug": "test-proj",
            "description": "desc",
            "config": {},
        },
    )
    assert r.status_code == 201
    project_id = r.json()["id"]

    r2 = client.get("/api/v1/projects")
    assert r2.status_code == 200
    slugs = [p["slug"] for p in r2.json()]
    assert "test-proj" in slugs


# ─── Agents ───


def test_create_and_get_agent(client):
    """Create a project, then an agent, then fetch it."""
    proj = client.post(
        "/api/v1/projects",
        json={
            "name": "AgentTest",
            "slug": "agent-test",
            "description": "d",
            "config": {},
        },
    ).json()

    r = client.post(
        "/api/v1/agents",
        json={
            "name": "bot-1",
            "role": "dev",
            "description": "A dev agent",
            "project_id": proj["id"],
            "config": {},
        },
    )
    assert r.status_code == 201
    agent_id = r.json()["id"]

    r2 = client.get(f"/api/v1/agents/{agent_id}")
    assert r2.status_code == 200
    assert r2.json()["name"] == "bot-1"


def test_list_agents_filters_by_project(client):
    """Agents should be filterable by project_id."""
    p1 = client.post(
        "/api/v1/projects",
        json={"name": "P1", "slug": "p1", "description": "d", "config": {}},
    ).json()
    p2 = client.post(
        "/api/v1/projects",
        json={"name": "P2", "slug": "p2", "description": "d", "config": {}},
    ).json()

    client.post(
        "/api/v1/agents",
        json={"name": "a1", "role": "dev", "description": "d", "project_id": p1["id"], "config": {}},
    )
    client.post(
        "/api/v1/agents",
        json={"name": "a2", "role": "dev", "description": "d", "project_id": p2["id"], "config": {}},
    )

    r = client.get(f"/api/v1/agents?project_id={p1['id']}")
    assert r.status_code == 200
    names = [a["name"] for a in r.json()]
    assert "a1" in names
    assert "a2" not in names


# ─── Proposals ───


def test_create_proposal(client):
    """Create a proposal via the API."""
    proj = client.post(
        "/api/v1/projects",
        json={"name": "PP", "slug": "pp", "description": "d", "config": {}},
    ).json()
    agent = client.post(
        "/api/v1/agents",
        json={"name": "a", "role": "d", "description": "d", "project_id": proj["id"], "config": {}},
    ).json()

    r = client.post(
        "/api/v1/proposals",
        json={
            "agent_id": agent["id"],
            "project_id": proj["id"],
            "title": "Test proposal",
            "description": "desc",
            "rationale": "reason",
        },
    )
    assert r.status_code == 201
    assert r.json()["status"] in ("draft", "pending")


# ─── Missions ───


def test_create_mission(client):
    """Create a mission via the API."""
    proj = client.post(
        "/api/v1/projects",
        json={"name": "MP", "slug": "mp", "description": "d", "config": {}},
    ).json()
    agent = client.post(
        "/api/v1/agents",
        json={"name": "a", "role": "d", "description": "d", "project_id": proj["id"], "config": {}},
    ).json()
    proposal = client.post(
        "/api/v1/proposals",
        json={
            "agent_id": agent["id"],
            "project_id": proj["id"],
            "title": "M-prop",
            "description": "d",
            "rationale": "r",
        },
    ).json()

    r = client.post(
        "/api/v1/missions",
        json={
            "proposal_id": proposal["id"],
            "project_id": proj["id"],
            "title": "Test mission",
            "description": "desc",
            "assigned_agent_id": agent["id"],
        },
    )
    assert r.status_code == 201
    assert r.json()["status"] == "planned"


# ─── Steps ───


def test_create_and_claim_step(client):
    """Create a step via mission endpoint and claim it for an agent."""
    proj = client.post(
        "/api/v1/projects",
        json={"name": "SP", "slug": "sp", "description": "d", "config": {}},
    ).json()
    agent = client.post(
        "/api/v1/agents",
        json={"name": "a", "role": "d", "description": "d", "project_id": proj["id"], "config": {}},
    ).json()
    proposal = client.post(
        "/api/v1/proposals",
        json={
            "agent_id": agent["id"],
            "project_id": proj["id"],
            "title": "SP-prop",
            "description": "d",
            "rationale": "r",
        },
    ).json()
    mission = client.post(
        "/api/v1/missions",
        json={
            "proposal_id": proposal["id"],
            "project_id": proj["id"],
            "title": "SM",
            "description": "d",
        },
    ).json()

    # Steps are created via /api/v1/missions/{id}/steps
    r_step = client.post(
        f"/api/v1/missions/{mission['id']}/steps",
        json={
            "mission_id": mission["id"],
            "title": "Do work",
            "description": "d",
            "step_type": "code",
            "order_index": 0,
        },
    )
    assert r_step.status_code == 201
    step = r_step.json()
    assert step["status"] == "pending"

    r = client.post(
        f"/api/v1/steps/{step['id']}/claim",
        json={"agent_id": agent["id"]},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "claimed"
    assert r.json()["claimed_by_agent_id"] == agent["id"]


# ─── Orchestrator ───


def test_orchestrator_tick_endpoint(client):
    """POST /api/v1/orchestrator/tick should succeed."""
    r = client.post("/api/v1/orchestrator/tick")
    assert r.status_code == 200
    assert "triggers_evaluated" in r.json()


def test_orchestrator_status(client):
    """GET /api/v1/orchestrator/status should return running."""
    r = client.get("/api/v1/orchestrator/status")
    assert r.status_code == 200
    assert r.json()["status"] == "running"
