"""Worker engine for executing agent work."""

import os
import yaml
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlmodel import Session
from sqlmodel import select

from ..config import settings
from ..models import Agent, Project, Step, StepStatus


class WorkerEngine:
    """Handles agent work execution and step processing."""
    
    def __init__(self):
        self.agents_dir = Path(settings.agents_dir)
        self.projects_dir = Path(settings.projects_dir)
    
    def find_and_execute_work(self, agent: Agent, session: Session) -> bool:
        """Find and execute available work for an agent."""
        try:
            # Find available steps for this agent
            available_steps = self._find_available_steps(agent, session)
            
            if not available_steps:
                return False
            
            # Take the first available step
            step = available_steps[0]
            
            # Load agent configuration
            agent_config = self._load_agent_config(agent)
            
            # Load project configuration
            project_config = self._load_project_config(agent.project_id, session)
            
            # Execute the step
            success = self._execute_step(step, agent, agent_config, project_config, session)
            
            return success
        
        except Exception as e:
            # Log error but don't crash
            return False
    
    def _find_available_steps(self, agent: Agent, session: Session) -> List[Step]:
        """Find steps that this agent can work on."""
        # Find unclaimed steps or steps already claimed by this agent
        query = (
            select(Step)
            .join(Step.mission)
            .where(
                (Step.claimed_by_agent_id.is_(None)) |
                (Step.claimed_by_agent_id == agent.id)
            )
            .where(Step.status.in_([StepStatus.PENDING, StepStatus.CLAIMED]))
            .where(Step.mission.has(project_id=agent.project_id))
            .order_by(Step.order_index.asc(), Step.created_at.asc())
        )
        
        result = session.exec(query)
        steps = result.all()
        
        # Filter steps based on agent capabilities
        suitable_steps = []
        for step in steps:
            if self._can_agent_handle_step(agent, step):
                suitable_steps.append(step)
        
        return suitable_steps
    
    def _can_agent_handle_step(self, agent: Agent, step: Step) -> bool:
        """Check if an agent can handle a specific step type."""
        # Load agent config to check capabilities
        try:
            agent_config = self._load_agent_config(agent)
            capabilities = agent_config.get("capabilities", [])
            
            # Map step types to required capabilities
            step_capability_map = {
                "code": "write_code",
                "test": "run_tests",
                "review": "review_code",
                "deploy": "deploy_code",
                "research": "research",
                "other": "general_work",
            }
            
            required_capability = step_capability_map.get(step.step_type.value, "general_work")
            
            # Check if agent has the required capability
            return required_capability in capabilities or "general_work" in capabilities
        
        except Exception:
            # If we can't load config, assume agent can handle it
            return True
    
    def _load_agent_config(self, agent: Agent) -> Dict[str, Any]:
        """Load agent configuration from YAML file."""
        try:
            agent_file = self.agents_dir / f"{agent.role}.yaml"
            if agent_file.exists():
                with open(agent_file, "r") as f:
                    config = yaml.safe_load(f)
                    # Merge with database config
                    config.update(agent.config)
                    return config
            
            # Fallback to database config only
            return agent.config
        
        except Exception:
            return agent.config
    
    def _load_project_config(self, project_id: UUID, session: Session) -> Dict[str, Any]:
        """Load project configuration."""
        try:
            project = session.get(Project, project_id)
            if not project:
                return {}
            
            # Try to load from YAML file
            project_file = self.projects_dir / f"{project.slug}.yaml"
            if project_file.exists():
                with open(project_file, "r") as f:
                    config = yaml.safe_load(f)
                    # Merge with database config
                    config.update(project.config)
                    return config
            
            # Fallback to database config
            return project.config
        
        except Exception:
            return {}
    
    def _execute_step(
        self,
        step: Step,
        agent: Agent,
        agent_config: Dict[str, Any],
        project_config: Dict[str, Any],
        session: Session
    ) -> bool:
        """Execute a step using the agent."""
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
            
            # Generate the work prompt for the agent
            work_prompt = self._generate_work_prompt(
                step, agent, agent_config, project_config, session
            )
            
            # For MVP, we'll simulate work execution
            # In a real implementation, this would:
            # 1. Spawn an OpenClaw sub-agent
            # 2. Pass the work prompt and context
            # 3. Wait for completion or handle async execution
            
            success = self._simulate_step_execution(step, work_prompt, session)
            
            return success
        
        except Exception as e:
            # Mark step as failed
            step.status = StepStatus.FAILED
            step.error = str(e)
            step.completed_at = datetime.utcnow()
            session.commit()
            return False
    
    def _generate_work_prompt(
        self,
        step: Step,
        agent: Agent,
        agent_config: Dict[str, Any],
        project_config: Dict[str, Any],
        session: Session
    ) -> str:
        """Generate a work prompt for the agent."""
        # Get the mission and project
        mission = session.get(step.mission)
        project = session.get(Project, agent.project_id)
        
        # Build context
        context = {
            "project_name": project.name if project else "Unknown",
            "project_description": project.description if project else "No description",
            "repo_path": project.repo_path if project else None,
            "mission_title": mission.title if mission else "Unknown",
            "mission_description": mission.description if mission else "No description",
            "step_title": step.title,
            "step_description": step.description,
            "step_type": step.step_type.value,
        }
        
        # Get the work prompt template from agent config
        work_prompt_template = agent_config.get("work_prompt", """
You are {agent_name} working on {project_name}.

Current task: {step_title}
Description: {step_description}
Step type: {step_type}

Mission: {mission_title}
{mission_description}

Project: {project_description}
Repository: {repo_path}

Please complete this task and report your results.
        """.strip())
        
        # Format the prompt
        try:
            work_prompt = work_prompt_template.format(
                agent_name=agent.name,
                **context
            )
        except KeyError as e:
            # If formatting fails, provide a basic prompt
            work_prompt = f"""
You are {agent.name} working on {context['project_name']}.

Please complete the following task:
{step.title}

Description: {step.description}
            """.strip()
        
        return work_prompt
    
    def _simulate_step_execution(self, step: Step, work_prompt: str, session: Session) -> bool:
        """Simulate step execution for MVP purposes."""
        import asyncio
        from datetime import datetime
        
        # Simulate some work time
        import time; time.sleep(1)
        
        # Generate simulated output based on step type
        outputs = {
            "research": f"Completed research for: {step.title}\n\nKey findings:\n- Analysis complete\n- Requirements identified\n- Next steps planned",
            "code": f"Implemented: {step.title}\n\nChanges made:\n- Code written and tested\n- Files updated\n- Ready for review",
            "test": f"Testing complete for: {step.title}\n\nTest results:\n- All tests passing\n- Coverage adequate\n- No issues found",
            "review": f"Code review complete for: {step.title}\n\nReview summary:\n- Code quality good\n- Best practices followed\n- Approved for deployment",
            "deploy": f"Deployment complete for: {step.title}\n\nDeployment summary:\n- Successfully deployed\n- Services running\n- Monitoring active",
            "other": f"Task complete: {step.title}\n\nWork summary:\n- Objectives achieved\n- Deliverables ready\n- Next steps identified",
        }
        
        step.output = outputs.get(step.step_type.value, f"Completed: {step.title}")
        step.status = StepStatus.COMPLETED
        step.completed_at = datetime.utcnow()
        
        session.commit()
        
        # Create step completed event
        from ..models import Event
        event = Event(
            event_type="step.completed",
            source_agent_id=step.claimed_by_agent_id,
            project_id=(session.get(step.mission)).project_id,
            payload={
                "step_id": str(step.id),
                "mission_id": str(step.mission_id),
                "step_type": step.step_type.value,
                "agent_id": str(step.claimed_by_agent_id),
            }
        )
        
        session.add(event)
        session.commit()
        
        return True