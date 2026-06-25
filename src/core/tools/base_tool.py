"""
Base Tool Framework for ReflectAI

Implements the foundation of  Simple agent tools including:
- Base Tool class with execute() method and error handling
- Tool permission system and security validation
- Performance metrics collection and monitoring
- Integration with production agent system and shared utilities

All agent-specific tools inherit from this base framework.
"""

import hashlib
import time
import uuid
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.shared import (
    ErrorCategory,
    ErrorContext,
    ErrorSeverity,
    ReflectAIError,
    get_logger,
    log_error_with_context,
    log_function_call,
    log_function_result,
    track_error,
    with_error_context,
)


class ToolPermission(Enum):
    """Tool permission levels for security validation"""

    READ_ONLY = "read_only"
    READ_WRITE = "read_write"
    ADMIN = "admin"


class ToolStatus(Enum):
    """Tool execution status tracking"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class ToolError(ReflectAIError):
    """Specialized error for tool execution failures"""

    def __init__(
        self,
        message: str,
        tool_name: str,
        operation: str | None = None,
        details: dict[str, Any] | None = None,
        original_error: Exception | None = None,
    ):
        super().__init__(
            message=message,
            category=ErrorCategory.VALIDATION_ERROR,
            severity=ErrorSeverity.HIGH,
            context={
                "tool_name": tool_name,
                "operation": operation or "unknown",
                **(details or {}),
            },
            original_error=original_error,
        )
        self.tool_name = tool_name
        self.operation = operation


class ToolRequest(BaseModel):
    """Request model for tool execution"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    tool_name: str = Field(..., description="Name of the tool to execute")
    operation: str = Field(default="execute", description="Operation to perform")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Tool parameters")
    user_context: dict[str, Any] | None = Field(
        None, description="User context for security and personalization"
    )
    user_id: str | None = Field(None, description="User ID from context (backward compatibility)")
    agent_id: str | None = Field(None, description="Agent making the request")
    request_id: str | None = Field(None, description="Request identifier")
    correlation_id: str | None = Field(None, description="Request correlation ID")
    timeout: int | None = Field(30, description="Execution timeout in seconds")

    def __init__(self, **data):
        # Handle backward compatibility and user context extraction
        if "user_context" in data and data["user_context"]:
            if not data.get("user_id") and "user_id" in data["user_context"]:
                data["user_id"] = data["user_context"]["user_id"]

        # Generate request ID if not provided
        if not data.get("request_id"):
            data["request_id"] = self._generate_request_id(data)

        super().__init__(**data)

    @staticmethod
    def _generate_request_id(data: dict[str, Any]) -> str:
        """Generate request ID based on tool and parameters"""
        tool_name = data.get("tool_name", "unknown")
        timestamp = int(time.time() * 1000)
        return f"{tool_name}_{timestamp}_{str(uuid.uuid4())[:8]}"

    def get_request_hash(self) -> str:
        """Generate unique hash for request deduplication"""
        # Include user context in hash for proper deduplication
        user_part = ""
        if self.user_context:
            user_part = f":{self.user_context.get('user_id', '')}"
        elif self.user_id:
            user_part = f":{self.user_id}"

        content = (
            f"{self.tool_name}:{self.operation}:{str(sorted(self.parameters.items()))}{user_part}"
        )
        # Use SHA256 for deduplication hashing (more secure than MD5)
        return hashlib.sha256(content.encode()).hexdigest()


class ToolResponse(BaseModel):
    """Response model for tool execution"""

    request_id: str = Field(..., description="Original request identifier")
    tool_name: str = Field(..., description="Tool that executed")
    status: ToolStatus = Field(..., description="Execution status")
    result: Any | None = Field(None, description="Tool execution result")
    error: str | None = Field(None, description="Error message if failed")
    execution_time: float = Field(..., description="Execution time in seconds")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metrics: dict[str, Any] = Field(default_factory=dict, description="Performance metrics")


@dataclass
class ToolMetrics:
    """Tool performance metrics collection"""

    tool_name: str
    operation: str
    execution_count: int = 0
    total_execution_time: float = 0.0
    success_count: int = 0
    failure_count: int = 0
    average_execution_time: float = 0.0
    last_execution: datetime | None = None
    error_types: dict[str, int] = field(default_factory=dict)

    def update(self, execution_time: float, success: bool, error_type: str | None = None):
        """Update metrics with new execution data"""
        self.execution_count += 1
        self.total_execution_time += execution_time
        self.average_execution_time = self.total_execution_time / self.execution_count
        self.last_execution = datetime.now(UTC)

        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
            if error_type:
                self.error_types[error_type] = self.error_types.get(error_type, 0) + 1


class Tool(ABC):
    """
    Base class for all ReflectAI tools

    Provides:
    - Standard execution interface with error handling
    - Permission-based security validation
    - Performance metrics collection
    - Integration with shared logging and error handling
    """

    def __init__(
        self,
        name: str,
        description: str,
        required_permissions: list[ToolPermission],
        timeout: int = 30,
    ):
        self.name = name
        self.description = description
        self.required_permissions = required_permissions
        self.timeout = timeout
        self.logger = get_logger(f"tool.{name}")
        self.metrics = ToolMetrics(tool_name=name, operation="default")
        self._metrics_by_operation: dict[str, ToolMetrics] = {}

    async def execute(self, request: ToolRequest, agent_context: Any | None = None) -> ToolResponse:
        """
        Execute tool with comprehensive error handling and metrics

        Args:
            request: Tool execution request
            agent_context: Optional agent context for advanced integrations

        Returns:
            ToolResponse with execution results and metrics
        """
        start_time = time.time()
        request_id = request.get_request_hash()

        # Initialize response
        response = ToolResponse(
            request_id=request_id,
            tool_name=self.name,
            status=ToolStatus.PENDING,
            execution_time=0.0,
        )

        try:
            # Validate permissions
            await self._validate_permissions(request)

            # Log execution start
            log_function_call(
                function_name=f"{self.name}.execute",
                args={"operation": request.operation, "user_id": request.user_id},
                correlation_id=request.correlation_id,
            )

            response.status = ToolStatus.RUNNING

            # Execute tool with timeout handling
            async with self._execution_context(request):
                result = await self._execute_operation(request, agent_context)

            response.result = result
            response.status = ToolStatus.COMPLETED

            # Update success metrics
            execution_time = time.time() - start_time
            self._update_metrics(request.operation, execution_time, success=True)

            log_function_result(
                function_name=f"{self.name}.execute",
                result={"status": "success", "execution_time": execution_time},
                correlation_id=request.correlation_id,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            error_type = type(e).__name__

            # Update failure metrics
            self._update_metrics(
                request.operation, execution_time, success=False, error_type=error_type
            )

            # Handle different error types
            if isinstance(e, ToolError):
                response.error = str(e)
                response.status = ToolStatus.FAILED
            elif isinstance(e, TimeoutError):
                response.error = f"Tool execution timeout after {self.timeout} seconds"
                response.status = ToolStatus.TIMEOUT
            else:
                # Wrap unexpected errors
                tool_error = ToolError(
                    message=f"Unexpected error in {self.name}: {str(e)}",
                    tool_name=self.name,
                    operation=request.operation,
                    original_error=e,
                )
                response.error = str(tool_error)
                response.status = ToolStatus.FAILED

            # Log error with context
            log_error_with_context(
                error=e,
                context={
                    "tool_name": self.name,
                    "operation": request.operation,
                    "user_id": request.user_id,
                    "execution_time": execution_time,
                },
                correlation_id=request.correlation_id,
            )

            # Track error for monitoring
            track_error(e, context={"tool_name": self.name, "operation": request.operation})

        finally:
            response.execution_time = time.time() - start_time
            response.metrics = self.get_metrics_summary()

        return response

    @abstractmethod
    async def _execute_operation(
        self, request: ToolRequest, agent_context: Any | None = None
    ) -> Any:
        """
        Implement tool-specific execution logic

        Args:
            request: Tool execution request
            agent_context: Optional agent context

        Returns:
            Tool execution result

        Raises:
            ToolError: For tool-specific failures
        """
        pass

    async def _validate_permissions(self, request: ToolRequest) -> None:
        """
        Validate tool permissions for the request

        Args:
            request: Tool execution request

        Raises:
            ToolError: If permission validation fails
        """
        # Basic permission validation - can be extended for more sophisticated checks
        if request.user_id is None and ToolPermission.READ_ONLY not in self.required_permissions:
            raise ToolError(
                message="User context required for this tool",
                tool_name=self.name,
                operation=request.operation,
            )

    @asynccontextmanager
    async def _execution_context(self, request: ToolRequest):
        """Async context manager for tool execution with timeout handling"""
        try:
            with with_error_context(
                ErrorContext(
                    operation=f"{self.name}.{request.operation}",
                    user_id=request.user_id,
                    correlation_id=request.correlation_id,
                )
            ):
                yield
        except Exception as e:
            raise e

    def _update_metrics(
        self, operation: str, execution_time: float, success: bool, error_type: str | None = None
    ):
        """Update tool metrics for the operation"""
        if operation not in self._metrics_by_operation:
            self._metrics_by_operation[operation] = ToolMetrics(
                tool_name=self.name, operation=operation
            )

        metrics = self._metrics_by_operation[operation]
        metrics.update(execution_time, success, error_type)

        # Update overall metrics
        self.metrics.update(execution_time, success, error_type)

    def get_metrics_summary(self) -> dict[str, Any]:
        """Get comprehensive metrics summary for monitoring"""
        return {
            "overall": {
                "execution_count": self.metrics.execution_count,
                "success_rate": self.metrics.success_count / max(self.metrics.execution_count, 1),
                "average_execution_time": self.metrics.average_execution_time,
                "last_execution": self.metrics.last_execution.isoformat()
                if self.metrics.last_execution
                else None,
            },
            "by_operation": {
                op: {
                    "execution_count": metrics.execution_count,
                    "success_rate": metrics.success_count / max(metrics.execution_count, 1),
                    "average_execution_time": metrics.average_execution_time,
                }
                for op, metrics in self._metrics_by_operation.items()
            },
            "error_types": dict(self.metrics.error_types),
        }

    def get_health_status(self) -> dict[str, Any]:
        """Get tool health status for monitoring"""
        if self.metrics.execution_count == 0:
            return {"status": "healthy", "reason": "no_executions"}

        success_rate = self.metrics.success_count / self.metrics.execution_count
        avg_time = self.metrics.average_execution_time

        if success_rate < 0.8:
            return {
                "status": "unhealthy",
                "reason": "high_failure_rate",
                "success_rate": success_rate,
            }
        elif avg_time > self.timeout * 0.8:
            return {
                "status": "degraded",
                "reason": "slow_performance",
                "avg_execution_time": avg_time,
            }
        else:
            return {
                "status": "healthy",
                "success_rate": success_rate,
                "avg_execution_time": avg_time,
            }


# Global tool registry instance
_tool_instances: dict[str, Tool] = {}


def get_tool_base_class() -> type:
    """Get the base Tool class for inheritance"""
    return Tool


def register_tool_instance(tool: Tool) -> None:
    """Register a tool instance globally"""
    _tool_instances[tool.name] = tool


def get_tool_instance(name: str) -> Tool | None:
    """Get a registered tool instance by name"""
    return _tool_instances.get(name)


def get_all_tool_instances() -> dict[str, Tool]:
    """Get all registered tool instances"""
    return _tool_instances.copy()
