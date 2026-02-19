"""Seed all 7 projects with agents and triggers.

Usage: python scripts/seed_all_projects.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agentloop.database import create_db_and_tables, engine
from agentloop.models import (
    Agent, AgentAction, AgentStatus, Project, ProjectStatus, Trigger,
)
from sqlmodel import Session, select
from uuid_extensions import uuid7


PROJECTS = [
    {
        "name": "Playdel",
        "slug": "playdel",
        "description": "Flutter app for sports challenges, matchmaking, and leagues",
        "repo_path": "/Users/tracert/github/orgs/Playdel",
        "board_id": "f961ea63-1619-47e1-9925-c54bcae17a08",
        "status": ProjectStatus.ACTIVE,
        "config": {
            "technologies": ["Flutter", "Dart", "Firebase"],
            "environments": ["development", "staging", "production"],
        },
    },
    {
        "name": "Blackcat",
        "slug": "blackcat",
        "description": "Monitoring platform with SABA connectors and data services",
        "repo_path": "/Users/tracert/github/personal/blackcat",
        "board_id": "2d7eb924-ae02-428c-beee-e148830b0cae",
        "status": ProjectStatus.ACTIVE,
        "config": {
            "technologies": ["Node.js", "Docker", "SABA API"],
            "environments": ["development", "production"],
        },
    },
    {
        "name": "Mitheithel",
        "slug": "mitheithel",
        "description": "Open data platform, Next.js apps, and brand ecosystem",
        "repo_path": "/Users/tracert/github/orgs/Mitheithel",
        "board_id": "3221facb-38eb-4539-9159-7d55df200e21",
        "status": ProjectStatus.ACTIVE,
        "config": {
            "technologies": ["Next.js", "TypeScript", "Python"],
            "environments": ["development", "production"],
        },
    },
    {
        "name": "Problyx",
        "slug": "problyx",
        "description": "Prediction market platform with AMM and JWT auth",
        "repo_path": "/Users/tracert/github/personal/prob-monorepo",
        "board_id": "5c2d5641-ce08-42ba-81f1-2e5c49d950ad",
        "status": ProjectStatus.ACTIVE,
        "config": {
            "technologies": ["TypeScript", "Next.js", "Node.js", "Railway"],
            "environments": ["development", "production"],
        },
    },
    {
        "name": "GPTStonks",
        "slug": "gptstonks",
        "description": "Financial chatbot platform (decommissioned)",
        "repo_path": "/Users/tracert/github/orgs/GPTStonks",
        "board_id": "c8ad0829-e973-4e74-9903-cf9361cd0d85",
        "status": ProjectStatus.DECOMMISSIONED,
        "config": {
            "technologies": ["Python", "OpenBB"],
            "decommissioned_reason": "Project sunset — no active development",
        },
    },
    {
        "name": "Polymarket Bot",
        "slug": "polymarket-bot",
        "description": "Automated trading bot for Polymarket prediction markets",
        "repo_path": "/Users/tracert/github/personal/polymarket_bot",
        "board_id": "c5c5dc10-e54b-4cce-92cc-2d3c07a3bf24",
        "status": ProjectStatus.ACTIVE,
        "config": {
            "technologies": ["Python", "Polymarket API", "BetBurger"],
            "environments": ["development", "production"],
        },
    },
    {
        "name": "AgentLoop Platform",
        "slug": "agentloop-platform",
        "description": "Multi-agent closed-loop orchestration system",
        "repo_path": "/Users/tracert/github/personal/agentloop",
        "board_id": "4a59d0b8-ac1b-4a7b-82bc-ec64d7e0878d",
        "status": ProjectStatus.ACTIVE,
        "config": {
            "technologies": ["Python", "FastAPI", "Next.js", "PixiJS"],
            "environments": ["development"],
        },
    },
]

AGENTS = [
    {
        "name": "Luna",
        "role": "product_manager",
        "description": "Reviews the board, identifies priorities, creates proposals.",
        "position_x": 100.0, "position_y": 200.0,
        "target_x": 100.0, "target_y": 200.0,
        "avatar": "pm",
        "config": {"auto_approve": False, "work_interval_minutes": 60},
    },
    {
        "name": "Spark",
        "role": "developer",
        "description": "Claims coding tasks, implements features, fixes bugs.",
        "position_x": 360.0, "position_y": 200.0,
        "target_x": 360.0, "target_y": 200.0,
        "avatar": "dev",
        "config": {
            "auto_approve": True,
            "auto_approve_proposals": True,
            "work_interval_minutes": 30,
        },
    },
    {
        "name": "Sage",
        "role": "quality_assurance",
        "description": "Reviews completed work, runs tests, validates quality.",
        "position_x": 100.0, "position_y": 400.0,
        "target_x": 100.0, "target_y": 400.0,
        "avatar": "qa",
        "config": {"auto_approve": True, "work_interval_minutes": 45},
    },
    {
        "name": "Bolt",
        "role": "deployer",
        "description": "Handles deployment, CI/CD, infrastructure.",
        "position_x": 360.0, "position_y": 400.0,
        "target_x": 360.0, "target_y": 400.0,
        "avatar": "deploy",
        "config": {"auto_approve": False, "work_interval_minutes": 120},
    },
]

TRIGGERS = [
    {
        "name": "qa_on_dev_complete",
        "event_pattern": {"event_type": "step.completed", "conditions": {"step_type": "code"}},
        "action": {
            "type": "create_step",
            "step_type": "review",
            "assign_role": "quality_assurance",
            "title_template": "Review: {step_title}",
        },
    },
    {
        "name": "mission_complete_check",
        "event_pattern": {"event_type": "step.completed"},
        "action": {"type": "evaluate_mission_completion"},
    },
]


def seed_all():
    with Session(engine) as session:
        for proj_data in PROJECTS:
            slug = proj_data["slug"]
            existing = session.exec(
                select(Project).where(Project.slug == slug)
            ).first()

            if existing:
                # Update status if changed (e.g., decommission GPTStonks)
                if existing.status != proj_data["status"]:
                    existing.status = proj_data["status"]
                    session.commit()
                    print(f"  Updated {slug} status → {proj_data['status'].value}")
                else:
                    print(f"  {slug} already exists, skipping")
                continue

            board_id = proj_data.pop("board_id")
            project = Project(id=uuid7(), **proj_data)
            project.config["mission_control_board_id"] = board_id
            session.add(project)
            session.flush()

            # Skip agents for decommissioned projects
            if proj_data["status"] == ProjectStatus.DECOMMISSIONED:
                session.commit()
                print(f"  {slug} (decommissioned) — no agents")
                continue

            for agent_data in AGENTS:
                agent = Agent(
                    id=uuid7(),
                    project_id=project.id,
                    status=AgentStatus.ACTIVE,
                    current_action=AgentAction.IDLE,
                    **agent_data,
                )
                session.add(agent)

            for trigger_data in TRIGGERS:
                trigger = Trigger(
                    id=uuid7(),
                    project_id=project.id,
                    enabled=True,
                    **trigger_data,
                )
                session.add(trigger)

            session.commit()
            print(f"  {slug} + 4 agents + 2 triggers")

    print("\nDone. All projects seeded.")


if __name__ == "__main__":
    seed_all()
