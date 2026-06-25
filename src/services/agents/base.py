"""
Base Agent Implementation for ReflectAI

Provides the foundation for all AI agents in the system.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from src.core.llm import LLMRequest, get_llm_gateway
from src.core.llm.optimizer import get_batch_processor, get_model_selector
from src.infrastructure.cache.redis_manager import get_redis_manager
from src.infrastructure.database.db_manager import get_database_manager
from src.shared import ErrorCategory, ReflectAIError, get_logger

logger = get_logger(__name__)


class AgentRole(Enum):
    """Agent roles in the system (simplified architecture)."""

    ANALYSIS_AGENT = "analysis_agent"  # Combined data analysis + competency assessment
    ADVISOR_AGENT = "advisor_agent"  # Combined career strategy + insight synthesis
    CHAT_RESPONDER = "chat_responder"  # Conversational interface


class AgentCapability(Enum):
    """Capabilities that agents can have."""

    ANALYSIS = "analysis"
    ASSESSMENT = "assessment"
    ADVICE = "advice"
    SYNTHESIS = "synthesis"
    CONVERSATION = "conversation"
    RESEARCH = "research"
    PLANNING = "planning"
    EXECUTION = "execution"


class AgentState(Enum):
    """Agent execution states."""

    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING = "executing"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentRequest:
    """Request to an agent."""

    task: str
    context: dict[str, Any] = field(default_factory=dict)
    user_id: str | None = None
    team_id: str | None = None
    correlation_id: str | None = None

    # Execution options
    max_iterations: int = 5
    timeout_seconds: int = 120
    require_confirmation: bool = False

    # Memory and history
    conversation_history: list[dict[str, str]] = field(default_factory=list)
    previous_results: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task": self.task,
            "context": self.context,
            "user_id": self.user_id,
            "team_id": self.team_id,
            "correlation_id": self.correlation_id,
            "max_iterations": self.max_iterations,
            "timeout_seconds": self.timeout_seconds,
            "require_confirmation": self.require_confirmation,
            "conversation_history": self.conversation_history,
            "previous_results": self.previous_results,
        }


@dataclass
class AgentResponse:
    """Response from an agent."""

    success: bool
    result: dict[str, Any] | None = None
    error: str | None = None

    # Execution details
    agent_name: str = ""
    state: AgentState = AgentState.IDLE
    iterations_used: int = 0
    duration_ms: int = 0

    # LLM details
    llm_calls: int = 0
    llm_cost: float = 0.0
    tokens_used: int = 0

    # Additional metadata
    confidence: float = 0.0
    evidence: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "agent_name": self.agent_name,
            "state": self.state.value,
            "iterations_used": self.iterations_used,
            "duration_ms": self.duration_ms,
            "llm_calls": self.llm_calls,
            "llm_cost": self.llm_cost,
            "tokens_used": self.tokens_used,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "recommendations": self.recommendations,
        }


class BaseAgent(ABC):
    """
    Base class for all AI agents.

    Provides common functionality for:
    - LLM interaction
    - Tool execution
    - Memory management
    - State tracking
    """

    def __init__(
        self,
        name: str,
        description: str,
        capabilities: list[AgentCapability],
        agent_type: str | None = None,
    ):
        self.name = name
        self.description = description
        self.capabilities = capabilities
        self.agent_type = agent_type or name.lower().replace(" ", "_")

        # Services
        self.llm_gateway = get_llm_gateway()
        self.redis_manager = get_redis_manager()
        self.db_manager = get_database_manager()
        self.batch_processor = get_batch_processor()
        self.model_selector = get_model_selector()

        # State
        self.state = AgentState.IDLE
        self.current_task = None

        # Tools registry
        self.tools: dict[str, Callable] = {}

        # Metrics
        self.total_executions = 0
        self.total_llm_calls = 0
        self.total_llm_cost = 0.0

    async def execute(self, request: AgentRequest) -> AgentResponse:
        """
        Execute the agent's task.

        Args:
            request: The agent request

        Returns:
            AgentResponse with results
        """
        start_time = time.time()
        self.state = AgentState.THINKING
        self.current_task = request.task

        try:
            # Apply timeout
            result = await asyncio.wait_for(self._run(request), timeout=request.timeout_seconds)

            duration_ms = int((time.time() - start_time) * 1000)

            self.state = AgentState.COMPLETED
            self.total_executions += 1

            return AgentResponse(
                success=True,
                result=result,
                agent_name=self.name,
                state=self.state,
                duration_ms=duration_ms,
                **self._get_metrics(),
            )

        except TimeoutError:
            self.state = AgentState.FAILED
            return AgentResponse(
                success=False,
                error=f"Agent timed out after {request.timeout_seconds} seconds",
                agent_name=self.name,
                state=self.state,
            )

        except Exception as e:
            logger.error(f"Agent {self.name} failed: {str(e)}")
            self.state = AgentState.FAILED

            return AgentResponse(
                success=False, error=str(e), agent_name=self.name, state=self.state
            )

        finally:
            self.current_task = None

    @abstractmethod
    async def _run(self, request: AgentRequest) -> dict[str, Any]:
        """
        Override in subclasses to implement agent logic.

        Args:
            request: The agent request

        Returns:
            Result dictionary
        """
        pass

    async def think(
        self,
        prompt: str,
        context: dict[str, Any] = None,
        require_json: bool = False,
        user_id: str | None = None,
        enable_batching: bool = True,
    ) -> str:
        """
        Use LLM to think about a problem with optimization.

        Args:
            prompt: The prompt to send to LLM
            context: Additional context
            require_json: Whether to require JSON response
            user_id: User ID for optimization
            enable_batching: Whether to enable batch processing

        Returns:
            LLM response
        """
        # Select optimal model tier based on complexity
        model_tier, confidence, reasoning = self.model_selector.select_optimal_model(
            content=prompt, context=context, user_id=user_id
        )

        # Create optimized LLM request
        messages = [{"role": "user", "content": prompt}]
        if require_json:
            messages.append(
                {"role": "system", "content": "Please respond with valid JSON format only."}
            )

        llm_request = LLMRequest(
            messages=messages,
            model_tier=model_tier,
            user_id=user_id or self.current_task or "agent",
            correlation_id=f"agent-{self.name}-{datetime.now(UTC).timestamp()}",
            system_prompt=self._get_system_prompt(),
            context={
                **(context or {}),
                "agent": self.name,
                "complexity_confidence": confidence,
                "selection_reasoning": reasoning,
            },
        )

        # Try batch processing for cost optimization
        if enable_batching and user_id:
            batch_id = self.batch_processor.add_to_batch(
                user_id=user_id,
                request_data={
                    "agent": self.name,
                    "prompt": prompt,
                    "context": context,
                    "model_tier": model_tier.value,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
            )

            if batch_id:
                logger.debug(f"Request batched for user {user_id}, batch_id: {batch_id}")
                # In a full implementation, we'd wait for batch processing
                # For now, proceed with individual request but log the batching

        response = await self.llm_gateway.process_request(llm_request)

        # Track metrics
        self.total_llm_calls += 1
        self.total_llm_cost += response.cost_usd

        # Note: LLMResponse doesn't have a success field, so we check for content
        if not response.content:
            raise ReflectAIError(
                message="LLM generation failed: No content in response",
                error_code="AGENT_LLM_FAILURE",
                category=ErrorCategory.LLM_PROVIDER_ERROR,
            )

        logger.debug(
            f"Agent {self.name} LLM call completed",
            extra={
                "model_tier": model_tier.value,
                "cost": response.cost_usd,
                "reasoning": reasoning,
            },
        )

        return response.content

    def register_tool(self, name: str, func: Callable):
        """
        Register a tool for the agent to use.

        Args:
            name: Tool name
            func: Tool function
        """
        self.tools[name] = func
        logger.info(f"Registered tool {name} for agent {self.name}")

    async def use_tool(self, name: str, **kwargs) -> Any:
        """
        Use a registered tool.

        Args:
            name: Tool name
            **kwargs: Tool arguments

        Returns:
            Tool result
        """
        if name not in self.tools:
            raise ReflectAIError(
                message=f"Tool {name} not found",
                error_code="TOOL_NOT_FOUND",
                category=ErrorCategory.CONFIGURATION_ERROR,
            )

        tool = self.tools[name]

        # Execute tool
        self.state = AgentState.EXECUTING

        if asyncio.iscoroutinefunction(tool):
            result = await tool(**kwargs)
        else:
            result = tool(**kwargs)

        self.state = AgentState.THINKING

        return result

    async def remember(self, key: str, value: Any, ttl: int = 3600):
        """
        Store information in memory.

        Args:
            key: Memory key
            value: Value to store
            ttl: Time to live in seconds
        """
        await self.redis_manager.set("agent", f"{self.name}:{key}", value, ttl_override=ttl)

    async def recall(self, key: str) -> Any | None:
        """
        Recall information from memory.

        Args:
            key: Memory key

        Returns:
            Recalled value or None
        """
        return await self.redis_manager.get("agent", f"{self.name}:{key}")

    def _get_system_prompt(self) -> str:
        """Get the system prompt for this agent."""
        capabilities_str = ", ".join([c.value for c in self.capabilities])

        return f"""You are {self.name}, an AI agent with the following capabilities: {capabilities_str}.

{self.description}

Your responses should be:
1. Accurate and based on available data
2. Actionable when providing recommendations
3. Clear and well-structured
4. Honest about uncertainties or limitations

Current task: {self.current_task or "None"}"""

    def _get_metrics(self) -> dict[str, Any]:
        """Get current metrics."""
        return {
            "llm_calls": self.total_llm_calls,
            "llm_cost": self.total_llm_cost,
            "tokens_used": 0,  # Would need token counting
        }

    def get_info(self) -> dict[str, Any]:
        """Get agent information."""
        return {
            "name": self.name,
            "description": self.description,
            "capabilities": [c.value for c in self.capabilities],
            "agent_type": self.agent_type,
            "state": self.state.value,
            "current_task": self.current_task,
            "tools": list(self.tools.keys()),
            "metrics": self._get_metrics(),
        }
