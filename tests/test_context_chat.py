"""Tests for ProjectContext and Chat API endpoints."""

from unittest.mock import patch, MagicMock

from tests.conftest import make_project

from agentloop.models import ProjectStatus


# ─── Project status filtering ───


def test_decommissioned_excluded_by_default(client, session):
    """GET /api/v1/projects excludes decommissioned projects."""
    make_project(session, slug="active-proj", status=ProjectStatus.ACTIVE)
    make_project(session, slug="dead-proj", status=ProjectStatus.DECOMMISSIONED)

    r = client.get("/api/v1/projects")
    assert r.status_code == 200
    slugs = [p["slug"] for p in r.json()]
    assert "active-proj" in slugs
    assert "dead-proj" not in slugs


def test_decommissioned_shown_with_flag(client, session):
    """GET /api/v1/projects?include_decommissioned=true shows all."""
    make_project(session, slug="active2", status=ProjectStatus.ACTIVE)
    make_project(session, slug="dead2", status=ProjectStatus.DECOMMISSIONED)

    r = client.get("/api/v1/projects?include_decommissioned=true")
    assert r.status_code == 200
    slugs = [p["slug"] for p in r.json()]
    assert "active2" in slugs
    assert "dead2" in slugs


def test_filter_by_status(client, session):
    """GET /api/v1/projects?status=paused filters correctly."""
    make_project(session, slug="paused-proj", status=ProjectStatus.PAUSED)
    make_project(session, slug="active3", status=ProjectStatus.ACTIVE)

    r = client.get("/api/v1/projects?status=paused")
    assert r.status_code == 200
    slugs = [p["slug"] for p in r.json()]
    assert "paused-proj" in slugs
    assert "active3" not in slugs


# ─── ProjectContext CRUD ───


def test_create_context_entry(client, session):
    """POST /api/v1/context creates a context entry."""
    proj = make_project(session, slug="ctx-proj")

    r = client.post(
        "/api/v1/context",
        json={
            "project_id": str(proj.id),
            "category": "architecture",
            "key": "db_choice",
            "content": "Using PostgreSQL with SQLAlchemy",
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["category"] == "architecture"
    assert data["key"] == "db_choice"


def test_upsert_context_entry(client, session):
    """POST /api/v1/context upserts on same project+category+key."""
    proj = make_project(session, slug="upsert-proj")

    # Create
    r1 = client.post(
        "/api/v1/context",
        json={
            "project_id": str(proj.id),
            "category": "decisions",
            "key": "auth",
            "content": "JWT tokens",
        },
    )
    assert r1.status_code == 201
    entry_id = r1.json()["id"]

    # Upsert (same project+category+key)
    r2 = client.post(
        "/api/v1/context",
        json={
            "project_id": str(proj.id),
            "category": "decisions",
            "key": "auth",
            "content": "Switched to session cookies",
        },
    )
    assert r2.status_code == 201
    assert r2.json()["id"] == entry_id
    assert r2.json()["content"] == "Switched to session cookies"


def test_list_context_entries(client, session):
    """GET /api/v1/context/{project_id} lists entries."""
    proj = make_project(session, slug="list-ctx")

    client.post(
        "/api/v1/context",
        json={
            "project_id": str(proj.id),
            "category": "patterns",
            "key": "api_style",
            "content": "RESTful with JSON",
        },
    )
    client.post(
        "/api/v1/context",
        json={
            "project_id": str(proj.id),
            "category": "bugs",
            "key": "mem_leak",
            "content": "Fixed memory leak in worker",
        },
    )

    r = client.get(f"/api/v1/context/{proj.id}")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_list_context_by_category(client, session):
    """GET /api/v1/context/{id}?category=bugs filters."""
    proj = make_project(session, slug="cat-ctx")

    client.post(
        "/api/v1/context",
        json={"project_id": str(proj.id), "category": "bugs", "key": "b1", "content": "bug 1"},
    )
    client.post(
        "/api/v1/context",
        json={"project_id": str(proj.id), "category": "notes", "key": "n1", "content": "note 1"},
    )

    r = client.get(f"/api/v1/context/{proj.id}?category=bugs")
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["key"] == "b1"


def test_delete_context_entry(client, session):
    """DELETE /api/v1/context/{entry_id} removes an entry."""
    proj = make_project(session, slug="del-ctx")

    r1 = client.post(
        "/api/v1/context",
        json={"project_id": str(proj.id), "category": "notes", "key": "tmp", "content": "temp"},
    )
    entry_id = r1.json()["id"]

    r2 = client.delete(f"/api/v1/context/{entry_id}")
    assert r2.status_code == 204

    r3 = client.get(f"/api/v1/context/{proj.id}")
    assert len(r3.json()) == 0


# ─── Chat API ───


def _install_mock_chat_dispatcher():
    """Install a mock ChatDispatcher on WorkerEngine and return it."""
    from agentloop.engine.worker import WorkerEngine

    mock_dispatcher = MagicMock()
    mock_dispatcher.available = True
    mock_dispatcher.send.return_value = {"status": "ok"}
    mock_dispatcher.extract_text.return_value = "Hello from agent!"
    WorkerEngine._chat_dispatcher = mock_dispatcher
    return mock_dispatcher


def _clear_chat_dispatcher():
    from agentloop.engine.worker import WorkerEngine
    WorkerEngine._chat_dispatcher = None


def test_chat_send_message(client, session):
    """POST /api/v1/chat sends message and returns response."""
    mock_disp = _install_mock_chat_dispatcher()

    proj = make_project(session, slug="chat-proj")

    r = client.post(
        "/api/v1/chat/",
        json={"content": "Hello", "project_id": str(proj.id)},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["user_message"]["content"] == "Hello"
    assert data["assistant_message"]["content"] == "Hello from agent!"
    assert data["session_id"]

    _clear_chat_dispatcher()


def test_chat_gateway_unavailable(client):
    """POST /api/v1/chat returns 503 when no chat dispatcher configured."""
    _clear_chat_dispatcher()

    r = client.post("/api/v1/chat/", json={"content": "Hello"})
    assert r.status_code == 503


def test_chat_history(client, session):
    """GET /api/v1/chat/history/{session_id} returns messages."""
    mock_disp = _install_mock_chat_dispatcher()
    mock_disp.extract_text.return_value = "Reply"

    r = client.post("/api/v1/chat/", json={"content": "First message"})
    sid = r.json()["session_id"]

    r2 = client.get(f"/api/v1/chat/history/{sid}")
    assert r2.status_code == 200
    assert len(r2.json()) == 2  # user + assistant
    assert r2.json()[0]["role"] == "user"
    assert r2.json()[1]["role"] == "assistant"

    _clear_chat_dispatcher()


def test_chat_sessions_list(client, session):
    """GET /api/v1/chat/sessions lists active sessions."""
    mock_disp = _install_mock_chat_dispatcher()
    mock_disp.extract_text.return_value = "ok"

    client.post("/api/v1/chat/", json={"content": "msg1"})

    r = client.get("/api/v1/chat/sessions")
    assert r.status_code == 200
    assert len(r.json()) >= 1
    assert r.json()[0]["message_count"] == 2

    _clear_chat_dispatcher()
