"""Agent movement engine — controls where agents go in the virtual office."""

import random
from datetime import datetime
from typing import Dict, Optional, Tuple
from uuid import UUID

from sqlmodel import Session, select

from ..database import engine
from ..models import Agent, AgentAction

# Office locations (in office coordinates matching the PixiJS frontend)
LOCATIONS: Dict[str, Tuple[float, float]] = {
    # Desks (matching toIso grid positions * 60)
    "desk_pm": (120.0, 180.0),
    "desk_dev": (360.0, 180.0),
    "desk_qa": (120.0, 360.0),
    "desk_ops": (360.0, 360.0),
    # Shared spaces
    "meeting_table": (240.0, 240.0),
    "coffee_machine": (432.0, 48.0),
    "whiteboard": (90.0, 18.0),
    "server_rack": (450.0, 432.0),
    "bookshelf": (480.0, 120.0),
}

# Role → home desk mapping
ROLE_DESK: Dict[str, str] = {
    "product_manager": "desk_pm",
    "developer": "desk_dev",
    "quality_assurance": "desk_qa",
    "deployer": "desk_ops",
}

# Action → possible locations
ACTION_LOCATIONS: Dict[str, list] = {
    "idle": ["home_desk"],  # Go back to desk
    "working": ["home_desk"],  # Work at desk
    "thinking": ["coffee_machine", "whiteboard", "home_desk"],
    "talking": ["meeting_table"],
    "reviewing": ["home_desk", "whiteboard"],
    "walking": [],  # Intermediate state
}


def get_home_desk(role: str) -> Tuple[float, float]:
    """Get the home desk position for a role."""
    desk_key = ROLE_DESK.get(role, "desk_pm")
    return LOCATIONS[desk_key]


def pick_destination(agent: Agent, action: AgentAction) -> Tuple[float, float]:
    """Pick a destination based on what the agent is about to do."""
    possible = ACTION_LOCATIONS.get(action.value, ["home_desk"])
    if not possible:
        return get_home_desk(agent.role)
    
    choice = random.choice(possible)
    if choice == "home_desk":
        return get_home_desk(agent.role)
    
    base = LOCATIONS.get(choice, get_home_desk(agent.role))
    # Add small random offset so agents don't stack
    jitter_x = random.uniform(-15, 15)
    jitter_y = random.uniform(-15, 15)
    return (base[0] + jitter_x, base[1] + jitter_y)


def move_agent_to(agent_id: UUID, action: AgentAction, session: Optional[Session] = None) -> bool:
    """Move an agent to a location appropriate for their action.
    
    Updates position, target, and action in the database.
    Broadcasts via WebSocket if available.
    """
    def _do(s: Session):
        agent = s.get(Agent, agent_id)
        if not agent:
            return False
        
        dest = pick_destination(agent, action)
        
        # If agent needs to move, set walking first
        dist = ((agent.position_x - dest[0]) ** 2 + (agent.position_y - dest[1]) ** 2) ** 0.5
        if dist > 30:
            agent.current_action = AgentAction.WALKING
            agent.target_x = dest[0]
            agent.target_y = dest[1]
        else:
            agent.current_action = action
            agent.position_x = dest[0]
            agent.position_y = dest[1]
            agent.target_x = dest[0]
            agent.target_y = dest[1]
        
        agent.last_seen_at = datetime.utcnow()
        s.add(agent)
        s.commit()
        s.refresh(agent)
        return True
    
    if session:
        return _do(session)
    with Session(engine) as s:
        return _do(s)


def arrive_agent(agent_id: UUID, action: AgentAction, session: Optional[Session] = None) -> bool:
    """Snap agent to their target and set final action (after walking)."""
    def _do(s: Session):
        agent = s.get(Agent, agent_id)
        if not agent:
            return False
        agent.position_x = agent.target_x
        agent.position_y = agent.target_y
        agent.current_action = action
        s.add(agent)
        s.commit()
        return True
    
    if session:
        return _do(session)
    with Session(engine) as s:
        return _do(s)


def return_to_desk(agent_id: UUID, session: Optional[Session] = None) -> bool:
    """Send agent back to their desk and set idle."""
    return move_agent_to(agent_id, AgentAction.IDLE, session)


def send_to_meeting(agent_ids: list, session: Optional[Session] = None) -> bool:
    """Send multiple agents to the meeting table."""
    for aid in agent_ids:
        move_agent_to(aid, AgentAction.TALKING, session)
    return True


def send_to_coffee(agent_id: UUID, session: Optional[Session] = None) -> bool:
    """Send agent to get coffee (thinking break)."""
    return move_agent_to(agent_id, AgentAction.THINKING, session)
