"""Mission Control plugin hooks.

Handles MC sync, mission reporting, stuck escalation, and SSE streams.
All MC-specific logic that was previously hardcoded in the core.
"""

import asyncio
import logging

from sqlmodel import select

logger = logging.getLogger(__name__)


def on_startup(**kwargs):
    """Start SSE streams for MC boards."""
    from agentloop.integrations.mc_streams import set_sync_callback, start_all_board_streams

    app = kwargs.get("app")

    def _sync_board(board_id: str) -> None:
        """Trigger inbound sync when SSE detects a new task."""
        from agentloop.database import engine as db_engine
        from sqlmodel import Session
        try:
            with Session(db_engine) as session:
                on_tick_sync(session=session)
        except Exception:
            logger.warning("SSE-triggered sync failed for board %s", board_id)

    set_sync_callback(_sync_board)

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(start_all_board_streams())
    except RuntimeError:
        logger.debug("No running loop — SSE streams will start later")
    except Exception:
        logger.warning("Could not start MC SSE streams (will fall back to polling)")

    logger.info("mission-control plugin: started")


def on_shutdown(**kwargs):
    """Stop SSE streams."""
    from agentloop.integrations.mc_streams import stop_all_streams

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(stop_all_streams())
    except RuntimeError:
        pass

    logger.info("mission-control plugin: stopped")


def on_tick_sync(**kwargs):
    """Sync tasks from Mission Control into proposals (inbound).

    Runs each orchestrator tick to pull new tasks.
    """
    session = kwargs.get("session")
    if session is None:
        return

    from agentloop.integrations.mission_control import (
        BOARD_PROJECT_MAP, sync_tasks_for_project,
    )
    from agentloop.models import (
        Agent, AgentStatus, Project, ProjectStatus, Proposal,
        ProposalPriority, ProposalStatus,
    )

    if not BOARD_PROJECT_MAP:
        return

    for board_id, project_slug in BOARD_PROJECT_MAP.items():
        try:
            project = session.exec(
                select(Project).where(Project.slug == project_slug)
            ).first()
            if not project or project.status == ProjectStatus.DECOMMISSIONED:
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

            session.commit()
        except Exception as e:
            logger.warning("MC sync for board %s failed: %s", board_id, e)


def on_mission_complete(**kwargs):
    """Report a completed mission back to Mission Control."""
    session = kwargs.get("session")
    mission = kwargs.get("mission")
    if not session or not mission:
        return

    from agentloop.integrations.mission_control import (
        report_agent_activity, update_task_status,
    )
    from agentloop.models import Agent, Proposal

    proposal = session.get(Proposal, mission.proposal_id)
    if not proposal or not proposal.mc_task_id or not proposal.mc_board_id:
        return

    agent_name = "AgentLoop"
    if mission.assigned_agent_id:
        agent = session.get(Agent, mission.assigned_agent_id)
        if agent:
            agent_name = agent.name

    try:
        report_agent_activity(
            proposal.mc_board_id,
            proposal.mc_task_id,
            agent_name,
            f"Mission completed: {mission.title}",
        )
        update_task_status(
            proposal.mc_board_id,
            proposal.mc_task_id,
            "review",
            comment=f"Completed by {agent_name} via AgentLoop.",
        )
    except Exception as e:
        logger.warning("MC outbound report failed for mission %s: %s", mission.id, e)


def on_stuck_check(**kwargs):
    """Detect missions with failed steps and escalate to human via MC."""
    session = kwargs.get("session")
    if not session:
        return

    from agentloop.integrations.mission_control import ask_user
    from agentloop.models import (
        Event, Mission, MissionStatus, Proposal, Step, StepStatus,
    )

    try:
        active_missions = session.exec(
            select(Mission).where(Mission.status == MissionStatus.ACTIVE)
        ).all()

        escalated = 0
        for mission in active_missions:
            steps = session.exec(
                select(Step).where(Step.mission_id == mission.id)
            ).all()
            if not steps:
                continue

            has_failed = any(s.status == StepStatus.FAILED for s in steps)
            has_pending = any(
                s.status in (StepStatus.PENDING, StepStatus.RUNNING, StepStatus.CLAIMED)
                for s in steps
            )

            if has_failed and not has_pending:
                proposal = session.get(Proposal, mission.proposal_id)
                if not proposal or not proposal.mc_board_id:
                    continue

                failed_step = next(s for s in steps if s.status == StepStatus.FAILED)
                msg = (
                    f"Mission '{mission.title}' is stuck.\n"
                    f"Failed step: {failed_step.title} ({failed_step.step_type.value})\n"
                    f"Error: {failed_step.error or 'unknown'}\n\n"
                    f"Please advise: retry, skip, or cancel?"
                )
                result = ask_user(
                    proposal.mc_board_id,
                    msg,
                    correlation_id=f"stuck-mission-{mission.id}",
                )
                if result:
                    logger.info(
                        "Escalated stuck mission %s to human via MC", mission.id
                    )
                    event = Event(
                        event_type="mission.escalated",
                        project_id=mission.project_id,
                        source_agent_id=mission.assigned_agent_id,
                        payload={
                            "mission_id": str(mission.id),
                            "failed_step_id": str(failed_step.id),
                            "reason": "stuck_failed_steps",
                        },
                    )
                    session.add(event)
                    escalated += 1

        if escalated:
            session.commit()
    except Exception:
        logger.exception("Failed to escalate stuck missions")


HOOKS = {
    "on_startup": on_startup,
    "on_shutdown": on_shutdown,
    "on_tick_sync": on_tick_sync,
    "on_mission_complete": on_mission_complete,
    "on_stuck_check": on_stuck_check,
}
