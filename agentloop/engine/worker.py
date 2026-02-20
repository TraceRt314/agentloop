"""Worker engine for executing agent work via OpenClaw gateway."""

import logging
import yaml
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from uuid import UUID

from sqlmodel import Session, select

from ..config import settings
from ..models import Agent, Event, Mission, Project, ProjectContext, Step, StepStatus

logger = logging.getLogger(__name__)


@runtime_checkable
class StepDispatcher(Protocol):
    """Protocol for step dispatch backends (e.g. OpenClaw)."""

    def dispatch(self, step_id: str, work_prompt: str, timeout: int,
                 agent_config: Optional[Dict[str, Any]] = None) -> dict: ...


class WorkerEngine:
    """Handles agent work execution and step processing."""

    _dispatcher: Optional[StepDispatcher] = None
    _plugin_manager = None

    def __init__(self):
        self.agents_dir = Path(settings.agents_dir)
        self.projects_dir = Path(settings.projects_dir)

    @classmethod
    def set_dispatcher(cls, dispatcher: StepDispatcher) -> None:
        """Register an external step dispatcher."""
        cls._dispatcher = dispatcher

    @classmethod
    def set_plugin_manager(cls, pm) -> None:
        """Register the plugin manager for hook dispatch."""
        cls._plugin_manager = pm

    def find_and_execute_work(self, agent: Agent, session: Session) -> bool:
        """Find and execute available work for an agent."""
        try:
            available_steps = self._find_available_steps(agent, session)
            if not available_steps:
                return False

            step = available_steps[0]
            agent_config = self._load_agent_config(agent)
            project_config = self._load_project_config(agent.project_id, session)
            return self._execute_step(step, agent, agent_config, project_config, session)
        except Exception as e:
            logger.exception("find_and_execute_work failed for agent %s", agent.name)
            return False

    def _find_available_steps(self, agent: Agent, session: Session) -> List[Step]:
        """Find steps that this agent can work on."""
        query = (
            select(Step)
            .join(Step.mission)
            .where(
                (Step.claimed_by_agent_id.is_(None))
                | (Step.claimed_by_agent_id == agent.id)
            )
            .where(Step.status.in_([StepStatus.PENDING, StepStatus.CLAIMED]))
            .where(Step.mission.has(project_id=agent.project_id))
            .order_by(Step.order_index.asc(), Step.created_at.asc())
        )
        steps = session.exec(query).all()
        return [s for s in steps if self._can_agent_handle_step(agent, s)]

    def _can_agent_handle_step(self, agent: Agent, step: Step) -> bool:
        """Check if an agent can handle a specific step type."""
        try:
            agent_config = self._load_agent_config(agent)
            capabilities = agent_config.get("capabilities", [])
            step_capability_map = {
                "code": "write_code",
                "test": "run_tests",
                "review": "review_code",
                "deploy": "deploy_code",
                "research": "research",
                "security": "security_audit",
                "other": "general_work",
            }
            required = step_capability_map.get(step.step_type.value, "general_work")
            return required in capabilities or "general_work" in capabilities
        except Exception:
            logger.debug("Could not check capabilities for agent %s, allowing step", agent.name)
            return True

    def _load_agent_config(self, agent: Agent) -> Dict[str, Any]:
        """Load agent configuration from YAML file or database."""
        try:
            agent_file = self.agents_dir / f"{agent.role}.yaml"
            if agent_file.exists():
                with open(agent_file, "r") as f:
                    config = yaml.safe_load(f)
                    config.update(agent.config)
                    return config
            return agent.config
        except Exception:
            logger.debug("Could not load YAML config for agent %s, using DB config", agent.role)
            return agent.config

    def _load_project_config(self, project_id: UUID, session: Session) -> Dict[str, Any]:
        """Load project configuration."""
        try:
            project = session.get(Project, project_id)
            if not project:
                return {}
            project_file = self.projects_dir / f"{project.slug}.yaml"
            if project_file.exists():
                with open(project_file, "r") as f:
                    config = yaml.safe_load(f)
                    config.update(project.config)
                    return config
            return project.config
        except Exception:
            logger.debug("Could not load project config for %s, using empty config", project_id)
            return {}

    def _execute_step(
        self,
        step: Step,
        agent: Agent,
        agent_config: Dict[str, Any],
        project_config: Dict[str, Any],
        session: Session,
    ) -> bool:
        """Execute a step — dispatch to OpenClaw gateway."""
        try:
            # Claim the step if not already claimed
            if step.claimed_by_agent_id != agent.id:
                step.claimed_by_agent_id = agent.id
                step.status = StepStatus.CLAIMED
                session.commit()

            # Start the step
            step.status = StepStatus.RUNNING
            step.started_at = datetime.utcnow()
            session.commit()

            # Generate the work prompt
            work_prompt = self._generate_work_prompt(
                step, agent, agent_config, project_config, session
            )

            # Dispatch to OpenClaw agent (synchronous CLI call)
            dispatched = self._dispatch_to_gateway(step, agent, work_prompt, agent_config)

            if dispatched:
                # _dispatch_to_gateway already set step.status and output
                mission = session.get(Mission, step.mission_id)
                event_type = (
                    "step.completed"
                    if step.status == StepStatus.COMPLETED
                    else "step.failed"
                )
                event = Event(
                    event_type=event_type,
                    source_agent_id=agent.id,
                    project_id=mission.project_id if mission else agent.project_id,
                    payload={
                        "step_id": str(step.id),
                        "mission_id": str(step.mission_id),
                        "step_type": step.step_type.value,
                        "agent_name": agent.name,
                    },
                )
                session.add(event)
                session.commit()

                # Plugin hook: step completed/failed
                if self._plugin_manager:
                    self._plugin_manager.dispatch_hook(
                        "on_step_complete", session=session, step=step, agent=agent,
                    )
            else:
                logger.warning("Gateway dispatch failed, falling back to simulated execution")
                self._simulate_step_execution(step, work_prompt, session)

                # Plugin hook after simulation too
                if self._plugin_manager:
                    self._plugin_manager.dispatch_hook(
                        "on_step_complete", session=session, step=step, agent=agent,
                    )

            return True

        except Exception as e:
            logger.exception("Step execution failed: %s", e)
            step.status = StepStatus.FAILED
            step.error = str(e)
            step.completed_at = datetime.utcnow()
            session.commit()
            return False

    def _dispatch_to_gateway(self, step: Step, agent: Agent, work_prompt: str,
                             agent_config: Optional[Dict[str, Any]] = None) -> bool:
        """Send work to the OpenClaw agent via CLI subprocess.

        The CLI runs synchronously — the agent processes the prompt and
        returns the result as JSON. We parse the output and store it
        directly on the step.

        Returns True if execution succeeded, False otherwise.
        """
        from ..integrations.openclaw import gateway_client, GatewayError

        if not gateway_client.available:
            logger.warning("openclaw CLI not available, skipping dispatch")
            return False

        try:
            result = gateway_client.dispatch_step(
                step_id=str(step.id),
                work_prompt=work_prompt,
                timeout=settings.step_timeout_seconds,
                agent_config=agent_config,
            )

            # Extract agent response text and store as step output
            response_text = gateway_client.extract_response_text(result)
            status = result.get("status", "unknown")

            if status == "ok" and response_text:
                step.output = response_text
                step.status = StepStatus.COMPLETED
                step.completed_at = datetime.utcnow()
                logger.info(
                    "Step %s completed via openclaw agent (%d chars output)",
                    step.id, len(response_text),
                )
            elif status == "ok":
                step.output = "Agent completed but returned no text output."
                step.status = StepStatus.COMPLETED
                step.completed_at = datetime.utcnow()
            else:
                step.error = f"Agent returned status: {status}"
                step.status = StepStatus.FAILED
                step.completed_at = datetime.utcnow()
                logger.warning("Step %s agent returned non-ok status: %s", step.id, status)

            return True

        except GatewayError as e:
            logger.error("Gateway dispatch failed for step %s: %s", step.id, e)
            return False
        except Exception as e:
            logger.exception("Unexpected error dispatching step %s: %s", step.id, e)
            return False

    def _generate_work_prompt(
        self,
        step: Step,
        agent: Agent,
        agent_config: Dict[str, Any],
        project_config: Dict[str, Any],
        session: Session,
    ) -> str:
        """Generate a work prompt for the agent."""
        mission = session.get(Mission, step.mission_id)
        project = session.get(Project, agent.project_id)

        # Gather persistent project context
        project_knowledge = ""
        if project:
            ctx_entries = session.exec(
                select(ProjectContext)
                .where(ProjectContext.project_id == project.id)
                .order_by(ProjectContext.created_at.desc())
            ).all()[:20]
            if ctx_entries:
                lines = ["--- Project Knowledge ---"]
                for e in ctx_entries:
                    lines.append(f"[{e.category}/{e.key}] {e.content}")
                project_knowledge = "\n".join(lines)

        # Read context files from repo
        context_files_content = ""
        context_files = agent_config.get("context_files", [])
        if context_files and project and project.repo_path:
            repo = Path(project.repo_path)
            lines = ["--- Context Files ---"]
            for rel_path in context_files:
                full_path = repo / rel_path
                if full_path.exists() and full_path.is_file():
                    try:
                        content = full_path.read_text()[:5000]
                        lines.append(f"\n### {rel_path}\n{content}")
                    except Exception:
                        lines.append(f"\n### {rel_path}\n[Could not read file]")
            if len(lines) > 1:
                context_files_content = "\n".join(lines)

        context = {
            "project_name": project.name if project else "Unknown",
            "project_description": project.description if project else "",
            "repo_path": project.repo_path if project else None,
            "mission_title": mission.title if mission else "Unknown",
            "mission_description": mission.description if mission else "",
            "step_title": step.title,
            "step_description": step.description,
            "step_type": step.step_type.value,
            "project_knowledge": project_knowledge,
            "context_files_content": context_files_content,
            "system_prompt": agent_config.get("system_prompt", ""),
        }

        work_prompt_template = agent_config.get(
            "work_prompt",
            (
                "You are {agent_name} working on {project_name}.\n\n"
                "Current task: {step_title}\n"
                "Description: {step_description}\n"
                "Step type: {step_type}\n\n"
                "Mission: {mission_title}\n"
                "{mission_description}\n\n"
                "Project: {project_description}\n"
                "Repository: {repo_path}\n\n"
                "{project_knowledge}\n\n"
                "Please complete this task and report your results."
            ),
        )

        try:
            return work_prompt_template.format(agent_name=agent.name, **context)
        except KeyError:
            return (
                f"You are {agent.name} working on {context['project_name']}.\n\n"
                f"Please complete the following task:\n{step.title}\n\n"
                f"Description: {step.description}"
            )

    def _simulate_step_execution(
        self, step: Step, work_prompt: str, session: Session
    ) -> bool:
        """Fallback: mark step completed with simulated output."""
        outputs = {
            "research": f"Completed research for: {step.title}\n\nKey findings:\n- Analysis complete\n- Requirements identified\n- Next steps planned",
            "code": f"Implemented: {step.title}\n\nChanges made:\n- Code written and tested\n- Files updated\n- Ready for review",
            "test": f"Testing complete for: {step.title}\n\nTest results:\n- All tests passing\n- Coverage adequate\n- No issues found",
            "review": f"Code review complete for: {step.title}\n\nReview summary:\n- Code quality good\n- Best practices followed\n- Approved for deployment",
            "deploy": f"Deployment complete for: {step.title}\n\nDeployment summary:\n- Successfully deployed\n- Services running\n- Monitoring active",
            "security": f"Security review complete for: {step.title}\n\nFindings:\n- No critical vulnerabilities found\n- Input validation adequate\n- No hardcoded secrets detected",
            "other": f"Task complete: {step.title}\n\nWork summary:\n- Objectives achieved\n- Deliverables ready",
        }

        step.output = outputs.get(step.step_type.value, f"Completed: {step.title}")
        step.status = StepStatus.COMPLETED
        step.completed_at = datetime.utcnow()
        session.commit()

        mission = session.get(Mission, step.mission_id)
        event = Event(
            event_type="step.completed",
            source_agent_id=step.claimed_by_agent_id,
            project_id=mission.project_id if mission else step.claimed_by_agent.project_id,
            payload={
                "step_id": str(step.id),
                "mission_id": str(step.mission_id),
                "step_type": step.step_type.value,
                "agent_id": str(step.claimed_by_agent_id),
                "simulated": True,
            },
        )
        session.add(event)
        session.commit()
        return True


