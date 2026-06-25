"""
Agent Registry for ReflectAI

Manages all available agents and their coordination.
"""

from typing import Any, Optional

from src.shared.exceptions import ErrorCategory, ReflectAIError
from src.shared.logging import get_logger

from .base import AgentRequest, AgentResponse, AgentRole, BaseAgent

logger = get_logger(__name__)

# Singleton instance
_agent_registry: Optional["AgentRegistry"] = None


class AgentRegistry:
    """
    Central registry for all agents.

    Manages:
    - Agent lifecycle
    - Agent selection
    - Agent coordination
    - Performance tracking
    """

    def __init__(self):
        self.agents: dict[AgentRole, BaseAgent] = {}
        self.agent_metrics: dict[AgentRole, dict[str, Any]] = {}

        # Initialize agents
        self._initialize_agents()

    def _initialize_agents(self):
        """Initialize all available agents (Phase 1 simplified architecture)."""
        logger.info("Initializing simplified agent registry (Phase 1)")

        # Lazy import to avoid circular dependencies
        from .advisor_agent import AdvisorAgent
        from .analysis_agent import AnalysisAgent
        from .chat_responder import ChatResponderAgent

        # Create combined agent instances (Phase 1 simplification)
        self.agents[AgentRole.ANALYSIS_AGENT] = (
            AnalysisAgent()
        )  # Data analysis + competency assessment
        self.agents[AgentRole.ADVISOR_AGENT] = AdvisorAgent()  # Career strategy + insight synthesis
        self.agents[AgentRole.CHAT_RESPONDER] = ChatResponderAgent()  # Conversational interface

        # Initialize metrics
        for role in AgentRole:
            self.agent_metrics[role] = {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "total_duration_ms": 0,
                "total_llm_cost": 0.0,
            }

        logger.info(f"Initialized {len(self.agents)} agents")

    def get_agent(self, role: AgentRole) -> BaseAgent:
        """
        Get an agent by role.

        Args:
            role: The agent role

        Returns:
            The agent instance
        """
        if role not in self.agents:
            raise ReflectAIError(
                message=f"Agent not found: {role.value}", category=ErrorCategory.CONFIGURATION
            )

        return self.agents[role]

    async def execute_task(self, role: AgentRole, request: AgentRequest) -> AgentResponse:
        """
        Execute a task with a specific agent.

        Args:
            role: The agent role
            request: The task request

        Returns:
            Agent response
        """
        agent = self.get_agent(role)

        logger.info(f"Executing task with {agent.name}: {request.task[:50]}...")

        # Update request metrics
        self.agent_metrics[role]["total_requests"] += 1

        # Execute task
        response = await agent.execute(request)

        # Update metrics
        if response.success:
            self.agent_metrics[role]["successful_requests"] += 1
        else:
            self.agent_metrics[role]["failed_requests"] += 1

        self.agent_metrics[role]["total_duration_ms"] += response.duration_ms
        self.agent_metrics[role]["total_llm_cost"] += response.llm_cost

        return response

    async def select_best_agent(self, task: str, context: dict[str, Any]) -> AgentRole:
        """
        Select the best agent for a task (Phase 1 simplified architecture).

        Args:
            task: The task description
            context: Task context

        Returns:
            Best agent role for the task
        """
        # Simple rule-based selection for Phase 1 agents
        task_lower = task.lower()

        # Analysis-related tasks (data analysis, competency assessment, classification)
        if any(
            word in task_lower
            for word in ["analyze", "classify", "pattern", "competency", "skill", "assess"]
        ):
            return AgentRole.ANALYSIS_AGENT
        # Advisory tasks (career strategy, insight synthesis, recommendations)
        elif any(
            word in task_lower
            for word in ["career", "advice", "plan", "goal", "synthesize", "summary", "insight"]
        ):
            return AgentRole.ADVISOR_AGENT
        # Conversational tasks
        elif any(word in task_lower for word in ["chat", "hello", "help", "question"]):
            return AgentRole.CHAT_RESPONDER
        else:
            # Default to chat responder for general queries
            return AgentRole.CHAT_RESPONDER

    async def coordinate_agents(
        self, task: str, roles: list[AgentRole], context: dict[str, Any]
    ) -> dict[str, AgentResponse]:
        """
        Coordinate multiple agents for a complex task.

        Args:
            task: The overall task
            roles: List of agent roles to coordinate
            context: Shared context

        Returns:
            Dictionary of responses by role
        """
        responses = {}
        accumulated_context = context.copy()

        for role in roles:
            # Create request with accumulated context
            request = AgentRequest(
                task=task,
                context=accumulated_context,
                previous_results=[r.to_dict() for r in responses.values()],
            )

            # Execute with agent
            response = await self.execute_task(role, request)
            responses[role] = response

            # Add results to context for next agent
            if response.success and response.result:
                accumulated_context[f"{role.value}_results"] = response.result

        return responses

    def get_agent_info(self, role: AgentRole) -> dict[str, Any]:
        """Get information about an agent."""
        agent = self.get_agent(role)
        metrics = self.agent_metrics.get(role, {})

        return {
            **agent.get_info(),
            "metrics": metrics,
            "avg_duration_ms": (
                metrics["total_duration_ms"] / metrics["total_requests"]
                if metrics["total_requests"] > 0
                else 0
            ),
            "success_rate": (
                metrics["successful_requests"] / metrics["total_requests"]
                if metrics["total_requests"] > 0
                else 0
            ),
        }

    def list_agents(self) -> list[dict[str, Any]]:
        """List all available agents."""
        return [self.get_agent_info(role) for role in AgentRole]

    def get_metrics(self) -> dict[str, Any]:
        """Get overall registry metrics."""
        total_requests = sum(m["total_requests"] for m in self.agent_metrics.values())
        total_successful = sum(m["successful_requests"] for m in self.agent_metrics.values())
        total_cost = sum(m["total_llm_cost"] for m in self.agent_metrics.values())

        return {
            "total_agents": len(self.agents),
            "total_requests": total_requests,
            "total_successful": total_successful,
            "overall_success_rate": (
                total_successful / total_requests if total_requests > 0 else 0
            ),
            "total_llm_cost": round(total_cost, 4),
            "agent_metrics": self.agent_metrics,
        }

    def reset_metrics(self):
        """Reset all metrics."""
        for role in AgentRole:
            self.agent_metrics[role] = {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "total_duration_ms": 0,
                "total_llm_cost": 0.0,
            }

        logger.info("Agent registry metrics reset")


def get_agent_registry() -> AgentRegistry:
    """Get the agent registry singleton."""
    global _agent_registry

    if _agent_registry is None:
        _agent_registry = AgentRegistry()

    return _agent_registry
