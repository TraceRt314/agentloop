"""Core orchestration engine for the closed-loop system."""
from sqlmodel import Session
from ..database import engine

import asyncio
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlmodel import Session
from sqlmodel import select

from ..database import engine
from ..models import (
    Agent,
    Event,
    Mission,
    MissionStatus,
    Proposal,
    ProposalStatus,
    Step,
    StepStatus,
    Trigger,
)
from ..schemas import OrchestrationResult, WorkCycleResult
from .approval import ApprovalEngine
from .worker import WorkerEngine

import logging
logger = logging.getLogger(__name__)


class OrchestrationEngine:
    """Main orchestration engine that runs the closed-loop system."""
    
    def __init__(self):
        self.approval_engine = ApprovalEngine()
        self.worker_engine = WorkerEngine()
    
    def tick(self, session: Optional[Session] = None) -> OrchestrationResult:
        """Run one orchestration cycle."""
        start_time = time.time()
        errors = []
        triggers_evaluated = 0
        triggers_fired = 0
        events_processed = 0
        actions_executed = 0
        
        if session is None:
            with Session(engine) as session:
                return self._run_tick(session)
        else:
            return self._run_tick(session)
    
    def _run_tick(self, session: Session) -> OrchestrationResult:
        """Internal tick implementation."""
        start_time = time.time()
        errors = []
        triggers_evaluated = 0
        triggers_fired = 0
        events_processed = 0
        actions_executed = 0
        
        try:
            # 0. Sync tasks from Mission Control → proposals
            self._sync_mission_control(session)

            # 1. Process pending approvals
            approval_results = self.approval_engine.process_pending_approvals(session)
            actions_executed += len(approval_results)
            
            # 2. Evaluate triggers against recent events
            trigger_results = self._evaluate_triggers(session)
            triggers_evaluated = trigger_results["evaluated"]
            triggers_fired = trigger_results["fired"]
            actions_executed += trigger_results["actions_executed"]
            errors.extend(trigger_results["errors"])
            
            # 3. Convert approved proposals to missions
            mission_results = self._create_missions_from_proposals(session)
            actions_executed += len(mission_results)
            
            # 4. Break down missions into steps
            step_results = self._create_steps_from_missions(session)
            actions_executed += len(step_results)
            
            # 5. Check for completed missions
            completion_results = self._check_mission_completions(session)
            actions_executed += len(completion_results)

            # 6. Escalate stuck missions to human
            escalated = self._escalate_stuck_missions(session)
            actions_executed += escalated

            # 7. Cleanup old events and expired proposals
            cleanup_results = self._cleanup_old_data(session)
            actions_executed += cleanup_results
            
        except Exception as e:
            errors.append(f"Orchestration tick failed: {str(e)}")
        
        duration_ms = (time.time() - start_time) * 1000
        
        return OrchestrationResult(
            triggers_evaluated=triggers_evaluated,
            triggers_fired=triggers_fired,
            events_processed=events_processed,
            actions_executed=actions_executed,
            errors=errors,
            duration_ms=duration_ms,
        )
    
    def work_cycle(self, agent_id: UUID, session: Optional[Session] = None) -> WorkCycleResult:
        """Run a full work cycle for a specific agent."""
        start_time = time.time()
        
        if session is None:
            with Session(engine) as session:
                return self._run_work_cycle(agent_id, session)
        else:
            return self._run_work_cycle(agent_id, session)
    
    def _run_work_cycle(self, agent_id: UUID, session: Session) -> WorkCycleResult:
        """Internal work cycle implementation."""
        start_time = time.time()
        actions_taken = []
        errors = []
        
        try:
            # Get the agent
            agent = session.get(Agent, agent_id)
            if not agent:
                errors.append(f"Agent {agent_id} not found")
                return WorkCycleResult(
                    agent_id=agent_id,
                    work_found=False,
                    errors=errors,
                    duration_ms=(time.time() - start_time) * 1000,
                )
            
            # Update agent heartbeat
            agent.last_seen_at = datetime.utcnow()
            session.commit()
            
            # Find work for this agent
            work_found = self.worker_engine.find_and_execute_work(agent, session)
            
            if work_found:
                actions_taken.append("Executed available work")
            
        except Exception as e:
            errors.append(f"Work cycle failed for agent {agent_id}: {str(e)}")
        
        duration_ms = (time.time() - start_time) * 1000
        
        return WorkCycleResult(
            agent_id=agent_id,
            work_found=len(actions_taken) > 0,
            actions_taken=actions_taken,
            errors=errors,
            duration_ms=duration_ms,
        )
    
    def _evaluate_triggers(self, session: Session) -> Dict[str, Any]:
        """Evaluate all active triggers against recent events."""
        result = {
            "evaluated": 0,
            "fired": 0,
            "actions_executed": 0,
            "errors": [],
        }
        
        try:
            # Get all enabled triggers
            triggers_result = session.exec(
                select(Trigger).where(Trigger.enabled == True)
            )
            triggers = triggers_result.all()
            
            # Get recent events (last 5 minutes)
            since = datetime.utcnow() - timedelta(minutes=5)
            events_result = session.exec(
                select(Event).where(Event.created_at >= since)
            )
            recent_events = events_result.all()
            
            for trigger in triggers:
                result["evaluated"] += 1
                
                # Check if trigger matches any recent events
                matching_events = self._match_events_to_trigger(recent_events, trigger)
                
                if matching_events:
                    # Execute trigger action
                    try:
                        action_result = self._execute_trigger_action(
                            trigger, matching_events, session
                        )
                        if action_result:
                            result["fired"] += 1
                            result["actions_executed"] += 1
                            
                            # Update last_fired_at
                            trigger.last_fired_at = datetime.utcnow()
                            session.commit()
                            
                    except Exception as e:
                        result["errors"].append(
                            f"Failed to execute trigger '{trigger.name}': {str(e)}"
                        )
        
        except Exception as e:
            result["errors"].append(f"Failed to evaluate triggers: {str(e)}")
        
        return result
    
    def _match_events_to_trigger(self, events: List[Event], trigger: Trigger) -> List[Event]:
        """Check if any events match the trigger pattern."""
        matching_events = []
        pattern = trigger.event_pattern
        
        for event in events:
            # Skip if project doesn't match
            if event.project_id != trigger.project_id:
                continue
            
            # Check event type
            if "event_type" in pattern and event.event_type != pattern["event_type"]:
                continue
            
            # Check conditions
            if "conditions" in pattern:
                conditions = pattern["conditions"]
                if not self._check_event_conditions(event, conditions):
                    continue
            
            matching_events.append(event)
        
        return matching_events
    
    def _check_event_conditions(self, event: Event, conditions: Dict[str, Any]) -> bool:
        """Check if an event meets the specified conditions."""
        for key, expected_value in conditions.items():
            if key not in event.payload:
                return False
            
            actual_value = event.payload[key]
            if actual_value != expected_value:
                return False
        
        return True
    
    def _execute_trigger_action(
        self, trigger: Trigger, events: List[Event], session: Session
    ) -> bool:
        """Execute the action specified by a trigger."""
        action = trigger.action
        action_type = action.get("type")
        
        if action_type == "create_step":
            return self._create_step_from_trigger(trigger, events, action, session)
        elif action_type == "evaluate_mission_completion":
            return self._evaluate_mission_completion_from_trigger(
                trigger, events, action, session
            )
        else:
            raise ValueError(f"Unknown trigger action type: {action_type}")
    
    def _create_step_from_trigger(
        self, trigger: Trigger, events: List[Event], action: Dict[str, Any], session: Session
    ) -> bool:
        """Create a step based on trigger action."""
        try:
            # Find the mission from the event
            for event in events:
                if "mission_id" in event.payload:
                    mission_id = UUID(event.payload["mission_id"])
                    mission = session.get(Mission, mission_id)
                    
                    if mission:
                        # Create the step
                        step = Step(
                            mission_id=mission.id,
                            order_index=action.get("order_index", 999),
                            title=action.get("title", "Auto-generated step"),
                            description=action.get("description", "Generated by trigger"),
                            step_type=action.get("step_type", "other"),
                        )
                        
                        session.add(step)
                        session.commit()
                        return True
            
            return False
        except Exception as e:
            raise RuntimeError(f"Failed to create step from trigger: {str(e)}")
    
    def _evaluate_mission_completion_from_trigger(
        self, trigger: Trigger, events: List[Event], action: Dict[str, Any], session: Session
    ) -> bool:
        """Evaluate mission completion based on trigger."""
        try:
            for event in events:
                if "mission_id" in event.payload:
                    mission_id = UUID(event.payload["mission_id"])
                    mission = session.get(Mission, mission_id)
                    
                    if mission and mission.status == MissionStatus.ACTIVE:
                        # Check if all steps are completed
                        steps_result = session.exec(
                            select(Step).where(Step.mission_id == mission.id)
                        )
                        steps = steps_result.all()
                        
                        if steps and all(step.status == StepStatus.COMPLETED for step in steps):
                            mission.status = MissionStatus.COMPLETED
                            mission.completed_at = datetime.utcnow()
                            session.commit()
                            
                            # Create mission completed event
                            event = Event(
                                event_type="mission.completed",
                                project_id=mission.project_id,
                                source_agent_id=mission.assigned_agent_id,
                                payload={
                                    "mission_id": str(mission.id),
                                    "proposal_id": str(mission.proposal_id),
                                }
                            )
                            session.add(event)
                            session.commit()
                            return True
            
            return False
        except Exception as e:
            raise RuntimeError(f"Failed to evaluate mission completion: {str(e)}")
    
    def _create_missions_from_proposals(self, session: Session) -> List[Mission]:
        """Convert approved proposals to missions."""
        missions = []
        
        try:
            # Find approved proposals without missions
            proposals_result = session.exec(
                select(Proposal).where(Proposal.status == ProposalStatus.APPROVED)
            )
            
            for proposal in proposals_result.all():
                # Check if mission already exists
                existing_mission = session.exec(
                    select(Mission).where(Mission.proposal_id == proposal.id)
                )
                
                if not existing_mission.first():
                    # Create mission
                    mission = Mission(
                        proposal_id=proposal.id,
                        project_id=proposal.project_id,
                        title=proposal.title,
                        description=proposal.description,
                        status=MissionStatus.PLANNED,
                        assigned_agent_id=proposal.agent_id,
                    )
                    
                    session.add(mission)
                    missions.append(mission)
            
            session.commit()

        except Exception:
            logger.exception("Failed to create missions from proposals")

        return missions
    
    def _create_steps_from_missions(self, session: Session) -> List[Step]:
        """Create default steps for new missions."""
        steps = []
        
        try:
            # Find planned missions without steps
            missions_result = session.exec(
                select(Mission).where(Mission.status == MissionStatus.PLANNED)
            )
            
            for mission in missions_result.all():
                # Check if steps already exist
                existing_steps = session.exec(
                    select(Step).where(Step.mission_id == mission.id)
                )
                
                if not existing_steps.first():
                    # Create default steps based on mission
                    default_steps = [
                        {
                            "title": "Research and Planning",
                            "description": f"Research and plan the implementation of: {mission.title}",
                            "step_type": "research",
                            "order_index": 0,
                        },
                        {
                            "title": "Implementation",
                            "description": f"Implement the solution for: {mission.title}",
                            "step_type": "code",
                            "order_index": 1,
                        },
                        {
                            "title": "Testing",
                            "description": f"Test the implementation of: {mission.title}",
                            "step_type": "test",
                            "order_index": 2,
                        },
                        {
                            "title": "Review",
                            "description": f"Review and validate: {mission.title}",
                            "step_type": "review",
                            "order_index": 3,
                        },
                    ]
                    
                    for step_data in default_steps:
                        step = Step(
                            mission_id=mission.id,
                            **step_data
                        )
                        session.add(step)
                        steps.append(step)
                    
                    # Update mission status to active
                    mission.status = MissionStatus.ACTIVE
            
            session.commit()

        except Exception:
            logger.exception("Failed to create steps from missions")

        return steps
    
    def _check_mission_completions(self, session: Session) -> List[Mission]:
        """Check for missions that should be marked as completed."""
        completed_missions = []
        
        try:
            # Find active missions
            missions_result = session.exec(
                select(Mission).where(Mission.status == MissionStatus.ACTIVE)
            )
            
            for mission in missions_result.all():
                # Check if all steps are completed
                steps_result = session.exec(
                    select(Step).where(Step.mission_id == mission.id)
                )
                steps = steps_result.all()
                
                if steps and all(step.status == StepStatus.COMPLETED for step in steps):
                    mission.status = MissionStatus.COMPLETED
                    mission.completed_at = datetime.utcnow()
                    completed_missions.append(mission)

                    # Create mission completed event
                    event = Event(
                        event_type="mission.completed",
                        project_id=mission.project_id,
                        source_agent_id=mission.assigned_agent_id,
                        payload={
                            "mission_id": str(mission.id),
                            "proposal_id": str(mission.proposal_id),
                        }
                    )
                    session.add(event)

                    # Report completion back to MC
                    self._report_mission_to_mc(mission, session)
            
            session.commit()

        except Exception:
            logger.exception("Failed to check mission completions")

        return completed_missions
    
    def _report_mission_to_mc(self, mission: Mission, session: Session) -> None:
        """Report a completed mission back to Mission Control."""
        from ..integrations.mission_control import (
            report_agent_activity, update_task_status,
        )

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

    def _sync_mission_control(self, session: Session) -> None:
        """Sync tasks from Mission Control into proposals (inbound only).

        The full bidirectional endpoint lives at ``/api/v1/simulation/sync-mc``.
        This light version runs each orchestrator tick to pull new tasks.
        """
        from ..integrations.mission_control import (
            BOARD_PROJECT_MAP, sync_tasks_for_project,
        )
        from ..models import AgentStatus, ProposalPriority, ProposalStatus, Project

        if not BOARD_PROJECT_MAP:
            return

        for board_id, project_slug in BOARD_PROJECT_MAP.items():
            try:
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

    def _escalate_stuck_missions(self, session: Session) -> int:
        """Detect missions with failed steps and escalate to human via MC.

        A mission is considered stuck when at least one step is FAILED
        and no steps are currently RUNNING or PENDING.
        """
        from ..integrations.mission_control import ask_user

        escalated = 0
        try:
            active_missions = session.exec(
                select(Mission).where(Mission.status == MissionStatus.ACTIVE)
            ).all()

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
                    # Find the MC board for this mission
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
                        # Record escalation event
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
        return escalated

    def _cleanup_old_data(self, session: Session) -> int:
        """Clean up old events and expired proposals."""
        actions = 0
        
        try:
            # Delete events older than 30 days
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            old_events = session.exec(
                select(Event).where(Event.created_at < cutoff_date)
            )
            
            for event in old_events.all():
                session.delete(event)
                actions += 1
            
            # Mark old pending proposals as expired
            expired_cutoff = datetime.utcnow() - timedelta(days=7)
            old_proposals = session.exec(
                select(Proposal).where(
                    Proposal.status == ProposalStatus.PENDING,
                    Proposal.created_at < expired_cutoff
                )
            )
            
            for proposal in old_proposals.all():
                proposal.status = ProposalStatus.EXPIRED
                actions += 1
            
            session.commit()

        except Exception:
            logger.exception("Failed to cleanup old data")

        return actions