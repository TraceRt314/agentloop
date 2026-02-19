"""Pydantic schemas for API requests and responses."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from .models import (
    AgentStatus,
    MissionStatus,
    ProjectStatus,
    ProposalPriority,
    ProposalStatus,
    StepStatus,
    StepType,
)


# Base schemas
class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    model_config = ConfigDict(from_attributes=True)


# Agent schemas
class AgentBase(BaseSchema):
    """Base agent schema."""
    name: str
    role: str
    description: str
    status: AgentStatus = AgentStatus.ACTIVE
    config: Dict[str, Any] = {}


class AgentCreate(AgentBase):
    """Schema for creating an agent."""
    project_id: UUID


class AgentUpdate(BaseSchema):
    """Schema for updating an agent."""
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[AgentStatus] = None
    config: Optional[Dict[str, Any]] = None


class Agent(AgentBase):
    """Agent response schema."""
    id: UUID
    project_id: UUID
    last_seen_at: Optional[datetime] = None
    created_at: datetime
    # UI state
    position_x: float = 0.0
    position_y: float = 0.0
    target_x: float = 0.0
    target_y: float = 0.0
    current_action: str = "idle"
    avatar: str = "default"


class AgentHeartbeat(BaseSchema):
    """Agent heartbeat schema."""
    status: AgentStatus = AgentStatus.ACTIVE
    metadata: Dict[str, Any] = {}


# Project schemas
class ProjectBase(BaseSchema):
    """Base project schema."""
    name: str
    slug: str
    description: str
    repo_path: Optional[str] = None
    status: ProjectStatus = ProjectStatus.ACTIVE
    config: Dict[str, Any] = {}


class ProjectCreate(ProjectBase):
    """Schema for creating a project."""
    pass


class ProjectUpdate(BaseSchema):
    """Schema for updating a project."""
    name: Optional[str] = None
    description: Optional[str] = None
    repo_path: Optional[str] = None
    status: Optional[ProjectStatus] = None
    config: Optional[Dict[str, Any]] = None


class Project(ProjectBase):
    """Project response schema."""
    id: UUID
    created_at: datetime


# Proposal schemas
class ProposalBase(BaseSchema):
    """Base proposal schema."""
    title: str
    description: str
    rationale: str
    priority: ProposalPriority = ProposalPriority.MEDIUM
    auto_approve: bool = False


class ProposalCreate(ProposalBase):
    """Schema for creating a proposal."""
    agent_id: UUID
    project_id: UUID


class ProposalUpdate(BaseSchema):
    """Schema for updating a proposal."""
    title: Optional[str] = None
    description: Optional[str] = None
    rationale: Optional[str] = None
    priority: Optional[ProposalPriority] = None
    status: Optional[ProposalStatus] = None
    auto_approve: Optional[bool] = None


class ProposalApproval(BaseSchema):
    """Schema for approving/rejecting proposals."""
    status: ProposalStatus  # approved or rejected
    reviewed_by: str
    review_notes: Optional[str] = None


class Proposal(ProposalBase):
    """Proposal response schema."""
    id: UUID
    agent_id: UUID
    project_id: UUID
    status: ProposalStatus
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime


# Mission schemas
class MissionBase(BaseSchema):
    """Base mission schema."""
    title: str
    description: str


class MissionCreate(MissionBase):
    """Schema for creating a mission."""
    proposal_id: UUID
    project_id: UUID
    assigned_agent_id: Optional[UUID] = None


class MissionUpdate(BaseSchema):
    """Schema for updating a mission."""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[MissionStatus] = None
    assigned_agent_id: Optional[UUID] = None


class Mission(MissionBase):
    """Mission response schema."""
    id: UUID
    proposal_id: UUID
    project_id: UUID
    status: MissionStatus
    assigned_agent_id: Optional[UUID] = None
    completed_at: Optional[datetime] = None
    created_at: datetime


# Step schemas
class StepBase(BaseSchema):
    """Base step schema."""
    title: str
    description: str
    step_type: StepType
    order_index: int


class StepCreate(StepBase):
    """Schema for creating a step."""
    mission_id: UUID


class StepUpdate(BaseSchema):
    """Schema for updating a step."""
    title: Optional[str] = None
    description: Optional[str] = None
    step_type: Optional[StepType] = None
    status: Optional[StepStatus] = None
    output: Optional[str] = None
    error: Optional[str] = None


class StepClaim(BaseSchema):
    """Schema for claiming a step."""
    agent_id: UUID


class StepComplete(BaseSchema):
    """Schema for completing a step."""
    output: str
    metadata: Optional[Dict[str, Any]] = None


class StepFail(BaseSchema):
    """Schema for failing a step."""
    error: str
    metadata: Optional[Dict[str, Any]] = None


class Step(StepBase):
    """Step response schema."""
    id: UUID
    mission_id: UUID
    status: StepStatus
    claimed_by_agent_id: Optional[UUID] = None
    output: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime


# Event schemas
class EventBase(BaseSchema):
    """Base event schema."""
    event_type: str
    payload: Dict[str, Any] = {}


class EventCreate(EventBase):
    """Schema for creating an event."""
    source_agent_id: Optional[UUID] = None
    project_id: UUID


class Event(EventBase):
    """Event response schema."""
    id: UUID
    source_agent_id: Optional[UUID] = None
    project_id: UUID
    created_at: datetime


# Trigger schemas
class TriggerBase(BaseSchema):
    """Base trigger schema."""
    name: str
    event_pattern: Dict[str, Any]
    action: Dict[str, Any]
    enabled: bool = True


class TriggerCreate(TriggerBase):
    """Schema for creating a trigger."""
    project_id: UUID


class TriggerUpdate(BaseSchema):
    """Schema for updating a trigger."""
    name: Optional[str] = None
    event_pattern: Optional[Dict[str, Any]] = None
    action: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None


class Trigger(TriggerBase):
    """Trigger response schema."""
    id: UUID
    project_id: UUID
    last_fired_at: Optional[datetime] = None
    created_at: datetime


# Orchestrator schemas
class OrchestrationResult(BaseSchema):
    """Schema for orchestration results."""
    triggers_evaluated: int
    triggers_fired: int
    events_processed: int
    actions_executed: int
    errors: List[str] = []
    duration_ms: float


class WorkCycleResult(BaseSchema):
    """Schema for agent work cycle results."""
    agent_id: UUID
    work_found: bool
    actions_taken: List[str] = []
    errors: List[str] = []
    duration_ms: float


class AgentWork(BaseSchema):
    """Schema for agent work assignment."""
    steps: List[Step] = []
    context: Dict[str, Any] = {}


# ProjectContext schemas
class ProjectContextCreate(BaseSchema):
    """Schema for creating a project context entry."""
    project_id: UUID
    category: str
    key: str
    content: str
    source_agent_id: Optional[UUID] = None
    source_step_id: Optional[UUID] = None


class ProjectContext(BaseSchema):
    """Project context response schema."""
    id: UUID
    project_id: UUID
    category: str
    key: str
    content: str
    source_agent_id: Optional[UUID] = None
    source_step_id: Optional[UUID] = None
    created_at: datetime


# Chat schemas
class ChatMessageCreate(BaseSchema):
    """Schema for sending a chat message."""
    content: str
    project_id: Optional[UUID] = None
    session_id: Optional[str] = None


class ChatMessageResponse(BaseSchema):
    """Chat message response schema."""
    id: UUID
    role: str
    content: str
    project_id: Optional[UUID] = None
    session_id: str
    created_at: datetime


class ChatResponse(BaseSchema):
    """Response from the chatbot."""
    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse
    session_id: str