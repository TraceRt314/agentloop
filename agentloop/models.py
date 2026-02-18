"""SQLModel database models for AgentLoop."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from uuid_extensions import uuid7
from sqlmodel import Column, Field, JSON, Relationship, SQLModel


class AgentStatus(str, Enum):
    """Agent status values."""
    ACTIVE = "active"
    PAUSED = "paused"


class ProposalStatus(str, Enum):
    """Proposal status values."""
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ProposalPriority(str, Enum):
    """Proposal priority values."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class MissionStatus(str, Enum):
    """Mission status values."""
    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    """Step status values."""
    PENDING = "pending"
    CLAIMED = "claimed"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class StepType(str, Enum):
    """Step type values."""
    CODE = "code"
    TEST = "test"
    REVIEW = "review"
    DEPLOY = "deploy"
    RESEARCH = "research"
    OTHER = "other"


# Base models with common fields
class BaseModel(SQLModel):
    """Base model with common fields."""
    id: UUID = Field(default_factory=uuid7, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TimestampedModel(BaseModel):
    """Base model with created_at and updated_at."""
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# Database models
class AgentAction(str, Enum):
    """Current agent action for UI."""
    IDLE = "idle"
    WALKING = "walking"
    WORKING = "working"
    TALKING = "talking"
    REVIEWING = "reviewing"
    THINKING = "thinking"


class Agent(BaseModel, table=True):
    """Agent registry table."""
    name: str = Field(index=True)
    role: str = Field(index=True)
    description: str
    status: AgentStatus = Field(default=AgentStatus.ACTIVE, index=True)
    project_id: UUID = Field(foreign_key="project.id", index=True)
    config: Dict[str, Any] = Field(sa_column=Column(JSON))
    last_seen_at: Optional[datetime] = None
    # UI state
    position_x: float = Field(default=0.0)
    position_y: float = Field(default=0.0)
    target_x: float = Field(default=0.0)
    target_y: float = Field(default=0.0)
    current_action: AgentAction = Field(default=AgentAction.IDLE)
    avatar: str = Field(default="default")
    
    # Relationships
    project: "Project" = Relationship(back_populates="agents")
    proposals: List["Proposal"] = Relationship(back_populates="agent")
    missions: List["Mission"] = Relationship(back_populates="assigned_agent")
    steps: List["Step"] = Relationship(back_populates="claimed_by_agent")
    events: List["Event"] = Relationship(back_populates="source_agent")


class Project(BaseModel, table=True):
    """Project configuration table."""
    name: str = Field(index=True)
    slug: str = Field(unique=True, index=True)
    description: str
    repo_path: Optional[str] = None
    config: Dict[str, Any] = Field(sa_column=Column(JSON))
    
    # Relationships
    agents: List["Agent"] = Relationship(back_populates="project")
    proposals: List["Proposal"] = Relationship(back_populates="project")
    missions: List["Mission"] = Relationship(back_populates="project")
    events: List["Event"] = Relationship(back_populates="project")
    triggers: List["Trigger"] = Relationship(back_populates="project")


class Proposal(BaseModel, table=True):
    """Proposal table."""
    agent_id: UUID = Field(foreign_key="agent.id", index=True)
    project_id: UUID = Field(foreign_key="project.id", index=True)
    title: str = Field(index=True)
    description: str
    rationale: str
    priority: ProposalPriority = Field(default=ProposalPriority.MEDIUM, index=True)
    status: ProposalStatus = Field(default=ProposalStatus.DRAFT, index=True)
    auto_approve: bool = Field(default=False)
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    
    # Relationships
    agent: Agent = Relationship(back_populates="proposals")
    project: Project = Relationship(back_populates="proposals")
    missions: List["Mission"] = Relationship(back_populates="proposal")


class Mission(BaseModel, table=True):
    """Mission table."""
    proposal_id: UUID = Field(foreign_key="proposal.id", index=True)
    project_id: UUID = Field(foreign_key="project.id", index=True)
    title: str = Field(index=True)
    description: str
    status: MissionStatus = Field(default=MissionStatus.PLANNED, index=True)
    assigned_agent_id: Optional[UUID] = Field(foreign_key="agent.id", index=True)
    completed_at: Optional[datetime] = None
    
    # Relationships
    proposal: Proposal = Relationship(back_populates="missions")
    project: Project = Relationship(back_populates="missions")
    assigned_agent: Optional[Agent] = Relationship(back_populates="missions")
    steps: List["Step"] = Relationship(back_populates="mission")


class Step(BaseModel, table=True):
    """Step table."""
    mission_id: UUID = Field(foreign_key="mission.id", index=True)
    order_index: int = Field(index=True)
    title: str = Field(index=True)
    description: str
    step_type: StepType = Field(index=True)
    status: StepStatus = Field(default=StepStatus.PENDING, index=True)
    claimed_by_agent_id: Optional[UUID] = Field(foreign_key="agent.id", index=True)
    output: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Relationships
    mission: Mission = Relationship(back_populates="steps")
    claimed_by_agent: Optional[Agent] = Relationship(back_populates="steps")


class Event(BaseModel, table=True):
    """Event bus table."""
    event_type: str = Field(index=True)
    source_agent_id: Optional[UUID] = Field(foreign_key="agent.id", index=True)
    project_id: UUID = Field(foreign_key="project.id", index=True)
    payload: Dict[str, Any] = Field(sa_column=Column(JSON))
    
    # Relationships
    source_agent: Optional[Agent] = Relationship(back_populates="events")
    project: Project = Relationship(back_populates="events")


class Trigger(BaseModel, table=True):
    """Trigger definitions table."""
    project_id: UUID = Field(foreign_key="project.id", index=True)
    name: str = Field(index=True)
    event_pattern: Dict[str, Any] = Field(sa_column=Column(JSON))
    action: Dict[str, Any] = Field(sa_column=Column(JSON))
    enabled: bool = Field(default=True, index=True)
    last_fired_at: Optional[datetime] = None
    
    # Relationships
    project: Project = Relationship(back_populates="triggers")