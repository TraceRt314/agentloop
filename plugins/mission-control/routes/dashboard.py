"""Dashboard routes — MC board/task proxy and sync endpoints.

These routes are contributed by the mission-control plugin and provide
proxy access to Mission Control boards and tasks.
"""

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from agentloop.database import get_session
from agentloop.integrations.mission_control import (
    get_boards, get_board_tasks, BOARD_PROJECT_MAP,
    sync_tasks_for_project, report_agent_activity, update_task_status,
)
from agentloop.models import (
    Agent, AgentStatus, Mission, MissionStatus, Project,
    Proposal, ProposalPriority, ProposalStatus,
)

router = APIRouter(prefix="/api/v1/mc", tags=["mission-control"])


@router.get("/boards")
def mc_boards():
    """Proxy — get all Mission Control boards with task counts."""
    boards = get_boards()
    result = []
    for b in boards:
        board_id = b.get("id", "")
        tasks = get_board_tasks(board_id)
        project_slug = BOARD_PROJECT_MAP.get(board_id, "unknown")

        status_counts = {}
        for t in tasks:
            s = t.get("status", "unknown")
            status_counts[s] = status_counts.get(s, 0) + 1

        result.append({
            "id": board_id,
            "name": b.get("name", ""),
            "description": b.get("description", ""),
            "project_slug": project_slug,
            "task_count": len(tasks),
            "status_counts": status_counts,
        })
    return {"boards": result}


@router.get("/boards/{board_id}/tasks")
def mc_board_tasks(board_id: str):
    """Proxy — get tasks for a specific MC board."""
    tasks = get_board_tasks(board_id)
    return {"board_id": board_id, "tasks": tasks, "total": len(tasks)}


@router.post("/sync")
def sync_mission_control(session: Session = Depends(get_session)):
    """Bidirectional sync with Mission Control.

    Inbound:  Fetches open tasks from MC boards and creates proposals.
    Outbound: Reports completed missions back to MC as task status updates.
    """
    created = []
    skipped = 0
    reported = []

    for board_id, project_slug in BOARD_PROJECT_MAP.items():
        project = session.exec(
            select(Project).where(Project.slug == project_slug)
        ).first()
        if not project:
            continue

        default_agent = session.exec(
            select(Agent)
            .where(Agent.project_id == project.id)
            .where(Agent.status == AgentStatus.ACTIVE)
        ).first()
        if not default_agent:
            continue

        tasks = sync_tasks_for_project(board_id)
        for task in tasks:
            mc_task_id = task.get("id", "")
            if not mc_task_id:
                continue

            existing = session.exec(
                select(Proposal).where(Proposal.mc_task_id == mc_task_id)
            ).first()
            if existing:
                skipped += 1
                continue

            mc_priority = task.get("priority", "medium").lower()
            priority_map = {
                "critical": ProposalPriority.CRITICAL,
                "high": ProposalPriority.HIGH,
                "medium": ProposalPriority.MEDIUM,
                "low": ProposalPriority.LOW,
            }
            priority = priority_map.get(mc_priority, ProposalPriority.MEDIUM)

            proposal = Proposal(
                agent_id=default_agent.id,
                project_id=project.id,
                title=task.get("title", "Untitled MC Task"),
                description=task.get("description", ""),
                rationale=f"Synced from Mission Control task {mc_task_id}",
                priority=priority,
                status=ProposalStatus.PENDING,
                auto_approve=priority in (ProposalPriority.CRITICAL, ProposalPriority.HIGH),
                mc_task_id=mc_task_id,
                mc_board_id=board_id,
            )
            session.add(proposal)
            created.append({
                "board": board_id,
                "project": project_slug,
                "mc_task_id": mc_task_id,
                "title": proposal.title,
                "priority": priority.value,
                "auto_approve": proposal.auto_approve,
            })

        # Outbound: completed missions → MC task status
        completed_missions = session.exec(
            select(Mission)
            .join(Proposal)
            .where(Mission.project_id == project.id)
            .where(Mission.status == MissionStatus.COMPLETED)
            .where(Proposal.mc_task_id.isnot(None))
            .where(Proposal.mc_board_id == board_id)
        ).all()

        for mission in completed_missions:
            proposal = session.get(Proposal, mission.proposal_id)
            if not proposal or not proposal.mc_task_id:
                continue

            agent_name = "AgentLoop"
            if mission.assigned_agent_id:
                agent = session.get(Agent, mission.assigned_agent_id)
                if agent:
                    agent_name = agent.name

            report_agent_activity(
                board_id, proposal.mc_task_id, agent_name,
                f"Mission completed: {mission.title}",
            )
            update_task_status(board_id, proposal.mc_task_id, "review")
            reported.append({
                "mc_task_id": proposal.mc_task_id,
                "mission": mission.title,
                "agent": agent_name,
            })

    session.commit()

    return {
        "status": "ok",
        "proposals_created": len(created),
        "proposals_skipped": skipped,
        "missions_reported": len(reported),
        "created": created,
        "reported": reported,
    }
