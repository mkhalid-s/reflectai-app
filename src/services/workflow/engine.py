"""
Workflow Engine for ReflectAI

Manages workflow execution and orchestration.
In development: Uses async tasks
In production: Will integrate with Temporal.io
"""

import asyncio
from collections import defaultdict
from datetime import UTC, datetime
from typing import Optional

from src.infrastructure.cache.redis_manager import get_redis_manager
from src.infrastructure.database.db_manager import get_database_manager
from src.infrastructure.events import get_event_bus
from src.shared.exceptions import ErrorCategory, ReflectAIError
from src.shared.logging import get_logger

from .models import WorkflowRequest, WorkflowResponse, WorkflowStatus, WorkflowType
from .workflows import (
    BatchProcessingWorkflow,
    ConversationWorkflow,
    ParallelAnalysisWorkflow,
    SequentialAnalysisWorkflow,
)

logger = get_logger(__name__)

# Singleton instance
_workflow_engine: Optional["WorkflowEngine"] = None


class WorkflowEngine:
    """
    Workflow execution engine.

    In development mode: Uses asyncio tasks for workflow execution.
    In production: Will integrate with Temporal.io for durable execution.
    """

    def __init__(self):
        self.event_bus = get_event_bus()
        self.redis_manager = get_redis_manager()
        self.db_manager = get_database_manager()

        # Track running workflows
        self.running_workflows: dict[str, asyncio.Task] = {}
        self.workflow_history: list[WorkflowResponse] = []

        # Workflow registry
        self.workflow_registry = {
            WorkflowType.SEQUENTIAL_ANALYSIS: SequentialAnalysisWorkflow,
            WorkflowType.PARALLEL_ANALYSIS: ParallelAnalysisWorkflow,
            WorkflowType.BATCH_PROCESSING: BatchProcessingWorkflow,
            WorkflowType.CONVERSATION: ConversationWorkflow,
        }

        # Metrics
        self.metrics = defaultdict(int)

    async def start_workflow(self, request: WorkflowRequest) -> WorkflowResponse:
        """
        Start a new workflow execution.

        Args:
            request: The workflow request

        Returns:
            WorkflowResponse with initial status
        """
        workflow_class = self.workflow_registry.get(request.workflow_type)

        if not workflow_class:
            raise ReflectAIError(
                message=f"Unknown workflow type: {request.workflow_type}",
                category=ErrorCategory.CONFIGURATION,
                details={"workflow_type": request.workflow_type.value},
            )

        # Create workflow instance
        workflow = workflow_class(request)
        workflow_id = workflow.workflow_id

        logger.info(f"Starting workflow {workflow_id} of type {request.workflow_type.value}")

        # Track metrics
        self.metrics[f"workflows_started_{request.workflow_type.value}"] += 1

        # Store workflow metadata in cache
        await self.redis_manager.set(
            "workflow",
            f"{workflow_id}:request",
            request.to_dict(),
            ttl_override=86400,  # 24 hours
        )

        # Create async task for workflow execution
        task = asyncio.create_task(self._execute_workflow(workflow))
        self.running_workflows[workflow_id] = task

        # Return initial response
        return WorkflowResponse(
            workflow_id=workflow_id,
            workflow_type=request.workflow_type,
            status=WorkflowStatus.RUNNING,
            user_id=request.user_id,
            team_id=request.team_id,
            correlation_id=request.correlation_id,
        )

    async def _execute_workflow(
        self,
        workflow: SequentialAnalysisWorkflow
        | ParallelAnalysisWorkflow
        | BatchProcessingWorkflow
        | ConversationWorkflow,
    ) -> WorkflowResponse:
        """
        Execute a workflow with timeout and error handling.

        Args:
            workflow: The workflow instance to execute

        Returns:
            WorkflowResponse with execution results
        """
        workflow_id = workflow.workflow_id

        try:
            # Apply timeout
            response = await asyncio.wait_for(
                workflow.run(), timeout=workflow.request.timeout_seconds
            )

            # Store response in cache
            await self.redis_manager.set(
                "workflow",
                f"{workflow_id}:response",
                response.to_dict(),
                ttl_override=86400,  # 24 hours
            )

            # Store in history
            self.workflow_history.append(response)
            if len(self.workflow_history) > 100:
                self.workflow_history = self.workflow_history[-100:]  # Keep last 100

            # Track metrics
            self.metrics[f"workflows_completed_{workflow.request.workflow_type.value}"] += 1

            # Store in database
            await self._store_workflow_result(response)

            return response

        except TimeoutError:
            response = WorkflowResponse(
                workflow_id=workflow_id,
                workflow_type=workflow.request.workflow_type,
                status=WorkflowStatus.TIMED_OUT,
                error=f"Workflow timed out after {workflow.request.timeout_seconds} seconds",
                user_id=workflow.request.user_id,
                team_id=workflow.request.team_id,
                correlation_id=workflow.request.correlation_id,
            )

            self.metrics[f"workflows_timedout_{workflow.request.workflow_type.value}"] += 1
            await self._store_workflow_result(response)
            return response

        except Exception as e:
            logger.error(f"Workflow {workflow_id} failed: {str(e)}")

            response = WorkflowResponse(
                workflow_id=workflow_id,
                workflow_type=workflow.request.workflow_type,
                status=WorkflowStatus.FAILED,
                error=str(e),
                user_id=workflow.request.user_id,
                team_id=workflow.request.team_id,
                correlation_id=workflow.request.correlation_id,
            )

            self.metrics[f"workflows_failed_{workflow.request.workflow_type.value}"] += 1
            await self._store_workflow_result(response)
            return response

        finally:
            # Clean up
            if workflow_id in self.running_workflows:
                del self.running_workflows[workflow_id]

    async def get_workflow_status(self, workflow_id: str) -> WorkflowResponse | None:
        """
        Get the status of a workflow.

        Args:
            workflow_id: The workflow ID to check

        Returns:
            WorkflowResponse if found, None otherwise
        """
        # Check cache first
        response_data = await self.redis_manager.get("workflow", f"{workflow_id}:response")
        if response_data:
            return WorkflowResponse(
                workflow_id=response_data["workflow_id"],
                workflow_type=WorkflowType(response_data["workflow_type"]),
                status=WorkflowStatus(response_data["status"]),
                result=response_data.get("result"),
                error=response_data.get("error"),
                user_id=response_data.get("user_id", ""),
                team_id=response_data.get("team_id", ""),
                correlation_id=response_data.get("correlation_id", ""),
            )

        # Check if running
        if workflow_id in self.running_workflows:
            return WorkflowResponse(
                workflow_id=workflow_id,
                workflow_type=WorkflowType.SEQUENTIAL_ANALYSIS,  # Default
                status=WorkflowStatus.RUNNING,
            )

        # Check history
        for response in self.workflow_history:
            if response.workflow_id == workflow_id:
                return response

        return None

    async def cancel_workflow(self, workflow_id: str) -> bool:
        """
        Cancel a running workflow.

        Args:
            workflow_id: The workflow ID to cancel

        Returns:
            True if cancelled, False if not found
        """
        if workflow_id in self.running_workflows:
            task = self.running_workflows[workflow_id]
            task.cancel()

            # Wait for cancellation
            try:
                await task
            except asyncio.CancelledError:
                # Expected exception when cancelling - safe to ignore
                pass

            # Store cancellation status
            response = WorkflowResponse(
                workflow_id=workflow_id,
                workflow_type=WorkflowType.SEQUENTIAL_ANALYSIS,  # Default
                status=WorkflowStatus.CANCELLED,
                completed_at=datetime.now(UTC),
            )

            await self.redis_manager.set(
                "workflow", f"{workflow_id}:response", response.to_dict(), ttl_override=86400
            )

            self.metrics["workflows_cancelled"] += 1
            return True

        return False

    async def list_workflows(
        self,
        user_id: str | None = None,
        workflow_type: WorkflowType | None = None,
        status: WorkflowStatus | None = None,
        limit: int = 20,
    ) -> list[WorkflowResponse]:
        """
        List workflows with optional filtering.

        Args:
            user_id: Filter by user ID
            workflow_type: Filter by workflow type
            status: Filter by status
            limit: Maximum number to return

        Returns:
            List of matching workflows
        """
        results = []

        for response in reversed(self.workflow_history):
            # Apply filters
            if user_id and response.user_id != user_id:
                continue
            if workflow_type and response.workflow_type != workflow_type:
                continue
            if status and response.status != status:
                continue

            results.append(response)

            if len(results) >= limit:
                break

        return results

    async def _store_workflow_result(self, response: WorkflowResponse):
        """Store workflow result in database."""
        try:
            await self.db_manager.store_workflow_execution(
                {
                    "workflow_id": response.workflow_id,
                    "workflow_type": response.workflow_type.value,
                    "status": response.status.value,
                    "user_id": response.user_id,
                    "team_id": response.team_id,
                    "correlation_id": response.correlation_id,
                    "result": response.result,
                    "error": response.error,
                    "started_at": response.started_at.isoformat(),
                    "completed_at": response.completed_at.isoformat()
                    if response.completed_at
                    else None,
                    "duration_ms": response.duration_ms,
                }
            )
        except Exception as e:
            logger.error(f"Failed to store workflow result: {str(e)}")

    def get_metrics(self) -> dict[str, int]:
        """Get workflow engine metrics."""
        return dict(self.metrics)

    async def cleanup(self):
        """Clean up resources."""
        # Cancel all running workflows
        for _workflow_id, task in list(self.running_workflows.items()):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                # Expected exception when cancelling - safe to ignore
                pass

        self.running_workflows.clear()
        self.workflow_history.clear()
        self.metrics.clear()


def get_workflow_engine() -> WorkflowEngine:
    """Get the workflow engine singleton."""
    global _workflow_engine

    if _workflow_engine is None:
        _workflow_engine = WorkflowEngine()

    return _workflow_engine
