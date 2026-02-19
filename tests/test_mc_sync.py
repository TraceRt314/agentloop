"""Tests for Mission Control sync and integration."""

from unittest.mock import patch, MagicMock

import httpx

from agentloop.integrations.mission_control import (
    get_boards,
    get_board_tasks,
    update_task_status,
    create_task,
    mark_task_in_progress,
    mark_task_done,
    ask_user,
    sync_tasks_for_project,
)


def _mock_response(json_data, status_code=200):
    """Create a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp
        )
    return resp


# ─── MC API wrappers ───


@patch("agentloop.integrations.mission_control.httpx.get")
def test_get_boards(mock_get):
    """get_boards should parse items from response."""
    mock_get.return_value = _mock_response({"items": [{"id": "b1", "name": "Board"}]})
    boards = get_boards()
    assert len(boards) == 1
    assert boards[0]["id"] == "b1"


@patch("agentloop.integrations.mission_control.httpx.get")
def test_get_boards_failure_returns_empty(mock_get):
    """get_boards should return [] on failure."""
    mock_get.side_effect = Exception("connection refused")
    boards = get_boards()
    assert boards == []


@patch("agentloop.integrations.mission_control.httpx.get")
def test_get_board_tasks(mock_get):
    """get_board_tasks should return task list."""
    mock_get.return_value = _mock_response(
        {"items": [{"id": "t1", "status": "inbox"}]}
    )
    tasks = get_board_tasks("board-1")
    assert len(tasks) == 1


@patch("agentloop.integrations.mission_control.httpx.get")
def test_get_board_tasks_with_status_filter(mock_get):
    """get_board_tasks should pass status as query param."""
    mock_get.return_value = _mock_response({"items": []})
    get_board_tasks("board-1", status="inbox")
    url = mock_get.call_args[0][0]
    assert "?status=inbox" in url


@patch("agentloop.integrations.mission_control.httpx.patch")
def test_update_task_status(mock_patch):
    """update_task_status should PATCH the task."""
    mock_patch.return_value = _mock_response({"id": "t1", "status": "done"})
    result = update_task_status("b1", "t1", "done", "Completed by agent")
    assert result is not None
    assert result["status"] == "done"


@patch("agentloop.integrations.mission_control.httpx.post")
def test_create_task(mock_post):
    """create_task should POST to the board."""
    mock_post.return_value = _mock_response({"id": "t-new", "title": "New task"})
    result = create_task("b1", "New task", "desc", "high")
    assert result["id"] == "t-new"


# ─── Convenience wrappers ───


@patch("agentloop.integrations.mission_control.update_task_status")
def test_mark_task_in_progress(mock_update):
    """mark_task_in_progress should call update_task_status."""
    mock_update.return_value = {"id": "t1"}
    assert mark_task_in_progress("b1", "t1") is True
    mock_update.assert_called_once_with("b1", "t1", "in_progress")


@patch("agentloop.integrations.mission_control.update_task_status")
def test_mark_task_done(mock_update):
    """mark_task_done should call update_task_status with 'done'."""
    mock_update.return_value = {"id": "t1"}
    assert mark_task_done("b1", "t1") is True
    mock_update.assert_called_once_with("b1", "t1", "done")


@patch("agentloop.integrations.mission_control.update_task_status")
def test_mark_task_done_failure(mock_update):
    """mark_task_done should return False on failure."""
    mock_update.return_value = None
    assert mark_task_done("b1", "t1") is False


# ─── Ask-user (human-in-the-loop) ───


@patch("agentloop.integrations.mission_control.mc_post")
def test_ask_user(mock_post):
    """ask_user should POST to the gateway-main ask-user endpoint."""
    mock_post.return_value = {"id": "msg-1"}
    result = ask_user("board-1", "What should I do?", correlation_id="corr-1")
    assert result is not None

    call_path, call_data = mock_post.call_args[0]
    assert "/gateway/main/ask-user" in call_path
    assert call_data["content"] == "What should I do?"
    assert call_data["correlation_id"] == "corr-1"


@patch("agentloop.integrations.mission_control.mc_post")
def test_ask_user_without_correlation(mock_post):
    """ask_user should work without correlation_id."""
    mock_post.return_value = {"id": "msg-2"}
    result = ask_user("board-1", "Help!")
    call_data = mock_post.call_args[0][1]
    assert "correlation_id" not in call_data


# ─── Sync logic ───


@patch("agentloop.integrations.mission_control.get_board_tasks")
def test_sync_tasks_for_project(mock_tasks):
    """sync_tasks_for_project should return inbox/in_progress tasks only."""
    mock_tasks.return_value = [
        {"id": "t1", "status": "inbox"},
        {"id": "t2", "status": "in_progress"},
        {"id": "t3", "status": "done"},
        {"id": "t4", "status": "review"},
    ]
    result = sync_tasks_for_project("board-1")
    assert len(result) == 2
    ids = {t["id"] for t in result}
    assert ids == {"t1", "t2"}
