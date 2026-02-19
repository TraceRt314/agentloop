"""Simulation API — drives agent behavior, movement, and MC sync."""

import random
import time
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..database import get_session
from ..models import Agent, AgentAction, AgentStatus, Event, Project, Step, StepStatus, Mission, MissionStatus
from ..engine.movement import (
    move_agent_to, arrive_agent, return_to_desk, send_to_meeting,
    send_to_coffee, get_home_desk,
)
from ..integrations.mission_control import (
    sync_tasks_for_project, mark_task_in_progress, mark_task_done,
    get_boards, BOARD_PROJECT_MAP,
)

router = APIRouter(prefix="/api/v1/simulation", tags=["simulation"])


@router.post("/tick")
def simulation_tick(session: Session = Depends(get_session)):
    """Run one simulation tick — updates agent positions and states.
    
    This should be called periodically (e.g. every 10-30 seconds) to
    animate the office. It:
    1. Checks active missions/steps
    2. Updates agent actions based on what they're doing
    3. Moves agents to appropriate locations
    4. Syncs with Mission Control
    """
    agents = session.exec(select(Agent).where(Agent.status == AgentStatus.ACTIVE)).all()
    updates = []
    
    for agent in agents:
        # Check if agent is walking — if close to target, arrive
        if agent.current_action == AgentAction.WALKING:
            dist = ((agent.position_x - agent.target_x) ** 2 + 
                    (agent.position_y - agent.target_y) ** 2) ** 0.5
            if dist < 20:
                # Determine what action they were walking toward
                # For now, check if they have active work
                active_step = session.exec(
                    select(Step)
                    .where(Step.claimed_by_agent_id == agent.id)
                    .where(Step.status == StepStatus.RUNNING)
                ).first()
                if active_step:
                    arrive_agent(agent.id, AgentAction.WORKING, session)
                    updates.append({"agent": agent.name, "action": "arrived_working"})
                else:
                    arrive_agent(agent.id, AgentAction.IDLE, session)
                    updates.append({"agent": agent.name, "action": "arrived_idle"})
            else:
                # Interpolate position toward target
                speed = 8.0
                dx = agent.target_x - agent.position_x
                dy = agent.target_y - agent.position_y
                mag = max(dist, 0.01)
                agent.position_x += (dx / mag) * min(speed, dist)
                agent.position_y += (dy / mag) * min(speed, dist)
                session.add(agent)
                updates.append({"agent": agent.name, "action": "walking", 
                              "pos": [round(agent.position_x, 1), round(agent.position_y, 1)]})
            continue
        
        # Check for active work
        active_step = session.exec(
            select(Step)
            .where(Step.claimed_by_agent_id == agent.id)
            .where(Step.status == StepStatus.RUNNING)
        ).first()
        
        if active_step:
            if agent.current_action != AgentAction.WORKING:
                move_agent_to(agent.id, AgentAction.WORKING, session)
                updates.append({"agent": agent.name, "action": "start_working"})
        else:
            # No active work — idle behaviors
            if agent.current_action == AgentAction.WORKING:
                return_to_desk(agent.id, session)
                updates.append({"agent": agent.name, "action": "finished_work"})
            elif agent.current_action == AgentAction.IDLE:
                # Random idle behaviors (small chance each tick)
                roll = random.random()
                if roll < 0.03:  # 3% chance to go get coffee
                    send_to_coffee(agent.id, session)
                    updates.append({"agent": agent.name, "action": "coffee_break"})
                elif roll < 0.05:  # 2% chance to check whiteboard
                    move_agent_to(agent.id, AgentAction.THINKING, session)
                    updates.append({"agent": agent.name, "action": "thinking"})
            elif agent.current_action in (AgentAction.THINKING, AgentAction.REVIEWING):
                # Return to desk after a bit
                if random.random() < 0.15:
                    return_to_desk(agent.id, session)
                    updates.append({"agent": agent.name, "action": "back_to_desk"})
    
    session.commit()
    
    return {
        "status": "ok",
        "timestamp": time.time(),
        "agent_count": len(agents),
        "updates": updates,
    }


@router.post("/sync-mc")
def sync_mission_control(session: Session = Depends(get_session)):
    """Sync tasks from Mission Control into AgentLoop.
    
    Fetches open tasks from MC boards and creates proposals/context
    that agents can work on.
    """
    synced = []
    
    for board_id, project_slug in BOARD_PROJECT_MAP.items():
        project = session.exec(
            select(Project).where(Project.slug == project_slug)
        ).first()
        
        if not project:
            continue
        
        tasks = sync_tasks_for_project(board_id)
        for task in tasks:
            # Store MC task reference in project config for agents to pick up
            synced.append({
                "board": board_id,
                "project": project_slug,
                "task_id": task.get("id"),
                "title": task.get("title"),
                "priority": task.get("priority"),
                "status": task.get("status"),
            })
    
    return {
        "status": "ok",
        "synced_tasks": len(synced),
        "tasks": synced,
    }


@router.post("/demo")
def demo_activity(session: Session = Depends(get_session)):
    """Trigger demo activity — makes agents move around and do things.
    
    Useful for showing off the UI without real work happening.
    """
    agents = session.exec(select(Agent).where(Agent.status == AgentStatus.ACTIVE)).all()
    if not agents:
        return {"status": "no agents"}
    
    actions_taken = []
    
    # Pick 1-2 random agents to do something
    active_agents = random.sample(agents, min(2, len(agents)))
    
    for agent in active_agents:
        action = random.choice([
            AgentAction.WORKING, AgentAction.THINKING,
            AgentAction.TALKING, AgentAction.REVIEWING,
        ])
        move_agent_to(agent.id, action, session)
        actions_taken.append({"agent": agent.name, "action": action.value})
    
    # Small chance of a meeting (all agents go to table)
    if random.random() < 0.2:
        send_to_meeting([a.id for a in agents], session)
        actions_taken = [{"agent": a.name, "action": "meeting"} for a in agents]
    
    session.commit()
    
    return {
        "status": "ok",
        "actions": actions_taken,
    }
