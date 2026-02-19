"""Chat API — proxy to OpenClaw gateway with persistent history."""

import logging
from typing import List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from ..database import get_session
from ..integrations.openclaw import gateway_client, GatewayError
from ..models import ChatMessage, Project, ProjectContext
from ..schemas import (
    ChatMessageCreate,
    ChatMessageResponse,
    ChatResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/chat", tags=["chat"])

MAX_HISTORY = 20  # max messages to include in prompt context


def _build_system_prompt(project: Optional[Project], context_entries: list) -> str:
    """Build a system-level preamble with project context."""
    parts = ["You are a helpful assistant within the AgentLoop platform."]

    if project:
        parts.append(f"\nProject: {project.name} — {project.description}")
        if project.repo_path:
            parts.append(f"Repository: {project.repo_path}")
        techs = project.config.get("technologies", [])
        if techs:
            parts.append(f"Technologies: {', '.join(techs)}")

    if context_entries:
        parts.append("\n--- Project Knowledge ---")
        for entry in context_entries:
            parts.append(f"[{entry.category}/{entry.key}] {entry.content}")

    return "\n".join(parts)


def _build_chat_prompt(
    system_prompt: str,
    history: list[ChatMessage],
    user_message: str,
) -> str:
    """Build a full prompt string from system context + conversation history."""
    lines = [system_prompt, "\n--- Conversation ---"]
    for msg in history:
        role = "User" if msg.role == "user" else "Assistant"
        lines.append(f"{role}: {msg.content}")
    lines.append(f"User: {user_message}")
    lines.append("Assistant:")
    return "\n".join(lines)


@router.post("/", response_model=ChatResponse)
def send_message(
    data: ChatMessageCreate,
    session: Session = Depends(get_session),
):
    """Send a chat message and get a response from OpenClaw."""
    if not gateway_client.available:
        raise HTTPException(
            status_code=503, detail="OpenClaw gateway not available"
        )

    session_id = data.session_id or str(uuid4())
    project = None
    context_entries: list = []

    if data.project_id:
        project = session.get(Project, data.project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        context_entries = session.exec(
            select(ProjectContext)
            .where(ProjectContext.project_id == data.project_id)
            .order_by(ProjectContext.created_at.desc())
        ).all()[:30]

    # Fetch conversation history
    history = session.exec(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.desc())
    ).all()[:MAX_HISTORY]
    history.reverse()  # chronological order

    # Build prompt
    system_prompt = _build_system_prompt(project, context_entries)
    full_prompt = _build_chat_prompt(system_prompt, history, data.content)

    # Save user message
    user_msg = ChatMessage(
        role="user",
        content=data.content,
        session_id=session_id,
        project_id=data.project_id,
    )
    session.add(user_msg)
    session.flush()

    # Dispatch to OpenClaw
    try:
        result = gateway_client.run_agent(
            session_id=f"agentloop-chat-{session_id}",
            message=full_prompt,
            timeout=120,
        )
        response_text = gateway_client.extract_response_text(result)
        if not response_text:
            response_text = "(No response from agent)"
    except GatewayError as e:
        logger.error("Chat dispatch failed: %s", e)
        response_text = f"Error communicating with the agent: {e}"

    # Save assistant message
    assistant_msg = ChatMessage(
        role="assistant",
        content=response_text,
        session_id=session_id,
        project_id=data.project_id,
    )
    session.add(assistant_msg)
    session.commit()
    session.refresh(user_msg)
    session.refresh(assistant_msg)

    return ChatResponse(
        user_message=ChatMessageResponse.model_validate(user_msg),
        assistant_message=ChatMessageResponse.model_validate(assistant_msg),
        session_id=session_id,
    )


@router.get("/history/{session_id}", response_model=List[ChatMessageResponse])
def get_history(
    session_id: str,
    limit: int = Query(50, le=200),
    session: Session = Depends(get_session),
):
    """Get chat history for a session."""
    messages = session.exec(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .limit(limit)
    ).all()
    return messages


@router.get("/sessions", response_model=List[dict])
def list_sessions(
    project_id: Optional[UUID] = Query(None),
    session: Session = Depends(get_session),
):
    """List chat sessions, optionally filtered by project."""
    from sqlalchemy import func as sa_func, desc

    last_msg = sa_func.max(ChatMessage.created_at).label("last_message_at")
    stmt = (
        select(
            ChatMessage.session_id,
            ChatMessage.project_id,
            sa_func.count(ChatMessage.id).label("message_count"),
            last_msg,
        )
        .group_by(ChatMessage.session_id, ChatMessage.project_id)
        .order_by(desc("last_message_at"))
    )
    if project_id:
        stmt = stmt.where(ChatMessage.project_id == project_id)

    rows = session.exec(stmt).all()
    return [
        {
            "session_id": r[0],
            "project_id": str(r[1]) if r[1] else None,
            "message_count": r[2],
            "last_message_at": r[3].isoformat() if r[3] else None,
        }
        for r in rows
    ]
