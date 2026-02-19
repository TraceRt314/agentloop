"""Seed the database with an example project and agents.

Usage:
    python scripts/seed.py                           # defaults
    python scripts/seed.py --name MyProject --slug myproject --repo /path/to/repo
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agentloop.database import create_db_and_tables, engine
from agentloop.models import Agent, Project, AgentStatus, AgentAction, Trigger
from sqlmodel import Session
from uuid_extensions import uuid7


def seed(name: str, slug: str, description: str, repo_path: str, board_id: str):
    create_db_and_tables()

    with Session(engine) as session:
        from sqlmodel import select
        existing = session.exec(select(Project).where(Project.slug == slug)).first()
        if existing:
            print(f"Project '{slug}' already seeded. Skipping.")
            return

        project = Project(
            id=uuid7(),
            name=name,
            slug=slug,
            description=description,
            repo_path=repo_path,
            config={
                "mission_control_board_id": board_id,
            },
        )
        session.add(project)
        session.flush()

        # Create agents with office positions
        agents_data = [
            {
                "name": "Luna",
                "role": "product_manager",
                "description": "Reviews the board, identifies priorities, creates proposals.",
                "position_x": 100.0,
                "position_y": 200.0,
                "target_x": 100.0,
                "target_y": 200.0,
                "avatar": "pm",
                "config": {"auto_approve": False, "work_interval_minutes": 60},
            },
            {
                "name": "Spark",
                "role": "developer",
                "description": "Claims coding tasks, implements features, fixes bugs.",
                "position_x": 360.0,
                "position_y": 200.0,
                "target_x": 360.0,
                "target_y": 200.0,
                "avatar": "dev",
                "config": {"auto_approve": True, "work_interval_minutes": 30},
            },
            {
                "name": "Sage",
                "role": "quality_assurance",
                "description": "Reviews completed work, runs tests, validates quality.",
                "position_x": 100.0,
                "position_y": 400.0,
                "target_x": 100.0,
                "target_y": 400.0,
                "avatar": "qa",
                "config": {"auto_approve": True, "work_interval_minutes": 45},
            },
            {
                "name": "Bolt",
                "role": "deployer",
                "description": "Handles deployment, CI/CD, infrastructure.",
                "position_x": 360.0,
                "position_y": 400.0,
                "target_x": 360.0,
                "target_y": 400.0,
                "avatar": "deploy",
                "config": {"auto_approve": False, "work_interval_minutes": 120},
            },
        ]

        for data in agents_data:
            agent = Agent(
                id=uuid7(),
                project_id=project.id,
                status=AgentStatus.ACTIVE,
                current_action=AgentAction.IDLE,
                **data,
            )
            session.add(agent)

        # Create triggers
        triggers_data = [
            {
                "name": "qa_on_dev_complete",
                "event_pattern": {"event_type": "step.completed", "conditions": {"step_type": "code"}},
                "action": {"type": "create_step", "step_type": "review", "assign_role": "quality_assurance", "title_template": "Review: {step_title}"},
            },
            {
                "name": "mission_complete_check",
                "event_pattern": {"event_type": "step.completed"},
                "action": {"type": "evaluate_mission_completion"},
            },
        ]

        for data in triggers_data:
            trigger = Trigger(
                id=uuid7(),
                project_id=project.id,
                enabled=True,
                **data,
            )
            session.add(trigger)

        session.commit()
        print(f"Seeded: {name} project + 4 agents (Luna, Spark, Sage, Bolt) + 2 triggers")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed AgentLoop database")
    parser.add_argument("--name", default="Example Project", help="Project name")
    parser.add_argument("--slug", default="example", help="Project slug")
    parser.add_argument("--description", default="Example project for AgentLoop", help="Project description")
    parser.add_argument("--repo", default="", help="Path to the project repository")
    parser.add_argument("--board-id", default="", help="Mission Control board UUID")
    args = parser.parse_args()
    seed(args.name, args.slug, args.description, args.repo, args.board_id)
