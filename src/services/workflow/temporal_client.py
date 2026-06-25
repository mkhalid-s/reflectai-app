"""
Temporal Workflow Client for ReflectAI

Replaces the custom async workflow engine with Temporal.io client.
Provides workflow execution, status monitoring, and management.
"""

from datetime import UTC, datetime, timedelta
from typing import Optional

from temporalio.client import Client, WorkflowHandle
from temporalio.common import RetryPolicy
from temporalio.exceptions import WorkflowAlreadyStartedError

from src.infrastructure.events import get_event_bus
from src.infrastructure.events.event_types import create_workflow_event
from src.shared import get_config
from src.shared.exceptions import ErrorCategory, ReflectAIError
from src.shared.logging import get_logger

from .models import WorkflowContext, WorkflowRequest, WorkflowResponse, WorkflowStatus, WorkflowType

logger = get_logger(__name__)

# Singleton instance
_temporal_client: Optional["TemporalWorkflowClient"] = None


class TemporalWorkflowClient:
    """
    Temporal workflow client for ReflectAI.

    Provides a clean interface to Temporal.io for workflow execution,
    replacing the custom asyncio-based workflow engine.
    """

    def __init__(self):
        self.config = get_config()
        self.event_bus = get_event_bus()
        self.client: Client | None = None

        # Temporal configuration
        self.temporal_host = self.config.temporal.host
        self.temporal_port = self.config.temporal.port
        self.temporal_namespace = self.config.temporal.namespace
        self.task_queue = self.config.temporal.task_queue

        # Running workflows tracking
        self.workflow_handles: dict[str, WorkflowHandle] = {}

    async def initialize(self):
        """Initialize Temporal client connection."""
        try:
            temporal_address = f"{self.temporal_host}:{self.temporal_port}"
            logger.info(f"Connecting to Temporal server at {temporal_address}")

            self.client = await Client.connect(
                target_host=temporal_address, namespace=self.temporal_namespace
            )

            logger.info("Successfully connected to Temporal server")

        except Exception as e:
            logger.error(f"Failed to connect to Temporal server: {e}")
            raise ReflectAIError(
                message=f"Temporal client initialization failed: {str(e)}",
                error_code="TEMPORAL_CLIENT_INIT_FAILED",
                category=ErrorCategory.INFRASTRUCTURE_ERROR,
                context={"temporal_host": self.temporal_host, "temporal_port": self.temporal_port},
            ) from e

    async def start_workflow(
        self, workflow_class: type, request: WorkflowRequest, workflow_id: str | None = None
    ) -> WorkflowResponse:
        """
        Start a new Temporal workflow.

        Args:
            workflow_class: The Temporal workflow class
            request: The workflow request
            workflow_id: Optional custom workflow ID

        Returns:
            WorkflowResponse with initial status
        """
        if not self.client:
            raise ReflectAIError(
                message="Temporal client not initialized",
                error_code="TEMPORAL_CLIENT_NOT_INITIALIZED",
                category=ErrorCategory.INFRASTRUCTURE_ERROR
            )

        # Use correlation_id as workflow_id for traceability
        workflow_id = workflow_id or request.correlation_id

        try:
            # Create workflow context for search attributes
            context = WorkflowContext(
                workflow_id=workflow_id,
                workflow_type=request.workflow_type,
                user_id=request.user_id,
                team_id=request.team_id,
                correlation_id=request.correlation_id,
                conversation_id=request.conversation_id,
                thread_ts=request.thread_ts,
                priority=request.priority,
            )

            # Start workflow with Temporal
            handle = await self.client.start_workflow(
                workflow_class.run,
                request,
                id=workflow_id,
                task_queue=self.task_queue,
                execution_timeout=timedelta(seconds=request.timeout_seconds),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    backoff_coefficient=2.0,
                    maximum_interval=timedelta(seconds=60),
                    maximum_attempts=3,
                ),
                search_attributes=context.search_attributes,
            )

            # Store handle for tracking
            self.workflow_handles[workflow_id] = handle

            logger.info(
                f"Started Temporal workflow {workflow_id}",
                extra={
                    "workflow_type": request.workflow_type.value,
                    "user_id": request.user_id,
                    "correlation_id": request.correlation_id,
                },
            )

            # Publish workflow started event
            event = create_workflow_event(
                workflow_id=workflow_id,
                workflow_type=request.workflow_type.value,
                status="started",
                correlation_id=request.correlation_id,
                user_id=request.user_id,
                team_id=request.team_id,
            )
            await self.event_bus.publish(event)

            return WorkflowResponse(
                workflow_id=workflow_id,
                workflow_type=request.workflow_type,
                status=WorkflowStatus.RUNNING,
                user_id=request.user_id,
                team_id=request.team_id,
                correlation_id=request.correlation_id,
                started_at=datetime.now(UTC),
            )

        except WorkflowAlreadyStartedError:
            logger.warning(f"Workflow {workflow_id} already started, returning existing handle")

            handle = self.client.get_workflow_handle(workflow_id)
            self.workflow_handles[workflow_id] = handle

            return WorkflowResponse(
                workflow_id=workflow_id,
                workflow_type=request.workflow_type,
                status=WorkflowStatus.RUNNING,
                user_id=request.user_id,
                team_id=request.team_id,
                correlation_id=request.correlation_id,
            )

        except Exception as e:
            logger.error(f"Failed to start workflow {workflow_id}: {e}")

            # Publish workflow failed event
            event = create_workflow_event(
                workflow_id=workflow_id,
                workflow_type=request.workflow_type.value,
                status="failed",
                correlation_id=request.correlation_id,
                error=str(e),
            )
            await self.event_bus.publish(event)

            raise ReflectAIError(
                message=f"Failed to start workflow: {str(e)}",
                category=ErrorCategory.WORKFLOW,
                details={"workflow_id": workflow_id, "workflow_type": request.workflow_type.value},
            ) from e

    async def get_workflow_status(self, workflow_id: str) -> WorkflowResponse | None:
        """
        Get the status of a running workflow.

        Args:
            workflow_id: The workflow ID to check

        Returns:
            WorkflowResponse with current status, or None if not found
        """
        if not self.client:
            raise ReflectAIError(
                message="Temporal client not initialized",
                error_code="TEMPORAL_CLIENT_NOT_INITIALIZED",
                category=ErrorCategory.INFRASTRUCTURE_ERROR
            )

        try:
            # Get workflow handle
            handle = self.workflow_handles.get(workflow_id)
            if not handle:
                handle = self.client.get_workflow_handle(workflow_id)

            # Get workflow description
            description = await handle.describe()

            # Convert Temporal status to our status
            status_mapping = {
                "WORKFLOW_EXECUTION_STATUS_RUNNING": WorkflowStatus.RUNNING,
                "WORKFLOW_EXECUTION_STATUS_COMPLETED": WorkflowStatus.COMPLETED,
                "WORKFLOW_EXECUTION_STATUS_FAILED": WorkflowStatus.FAILED,
                "WORKFLOW_EXECUTION_STATUS_CANCELED": WorkflowStatus.CANCELLED,
                "WORKFLOW_EXECUTION_STATUS_TERMINATED": WorkflowStatus.FAILED,
                "WORKFLOW_EXECUTION_STATUS_TIMED_OUT": WorkflowStatus.TIMED_OUT,
            }

            status = status_mapping.get(description.status.name, WorkflowStatus.RUNNING)

            # Get result if completed
            result = None
            error = None

            if status == WorkflowStatus.COMPLETED:
                try:
                    result = await handle.result()
                except Exception as e:
                    error = str(e)
                    status = WorkflowStatus.FAILED

            return WorkflowResponse(
                workflow_id=workflow_id,
                workflow_type=WorkflowType.SEQUENTIAL_ANALYSIS,  # Default, could be extracted from search attributes
                status=status,
                result=result,
                error=error,
                started_at=description.start_time,
                completed_at=description.close_time,
                correlation_id=workflow_id,  # Using workflow_id as correlation_id
            )

        except Exception as e:
            logger.error(f"Failed to get workflow status for {workflow_id}: {e}")
            return None

    async def cancel_workflow(self, workflow_id: str) -> bool:
        """
        Cancel a running workflow.

        Args:
            workflow_id: The workflow ID to cancel

        Returns:
            True if cancelled successfully, False otherwise
        """
        if not self.client:
            return False

        try:
            handle = self.workflow_handles.get(workflow_id)
            if not handle:
                handle = self.client.get_workflow_handle(workflow_id)

            await handle.cancel()

            # Remove from tracking
            if workflow_id in self.workflow_handles:
                del self.workflow_handles[workflow_id]

            logger.info(f"Successfully cancelled workflow {workflow_id}")

            # Publish cancellation event
            event = create_workflow_event(
                workflow_id=workflow_id,
                workflow_type="unknown",
                status="cancelled",
                correlation_id=workflow_id,
            )
            await self.event_bus.publish(event)

            return True

        except Exception as e:
            logger.error(f"Failed to cancel workflow {workflow_id}: {e}")
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
        if not self.client:
            return []

        try:
            # Build query filter
            query_parts = []

            if user_id:
                query_parts.append(f'UserId = "{user_id}"')

            if workflow_type:
                query_parts.append(f'WorkflowType = "{workflow_type.value}"')

            " AND ".join(query_parts) if query_parts else None

            # List workflows using Temporal's list API
            # Note: This is a simplified implementation
            # In practice, you'd use Temporal's visibility API
            workflows = []

            for workflow_id, _handle in list(self.workflow_handles.items()):
                try:
                    workflow_status = await self.get_workflow_status(workflow_id)
                    if workflow_status:
                        # Apply filters
                        if status and workflow_status.status != status:
                            continue

                        workflows.append(workflow_status)

                        if len(workflows) >= limit:
                            break

                except Exception as e:
                    logger.warning(f"Failed to get status for workflow {workflow_id}: {e}")
                    continue

            return workflows

        except Exception as e:
            logger.error(f"Failed to list workflows: {e}")
            return []

    async def cleanup(self):
        """Clean up resources."""
        try:
            # Clear workflow handles
            self.workflow_handles.clear()

            # Close client connection
            if self.client:
                # Note: temporalio.Client doesn't have an explicit close method
                # The connection will be cleaned up when the client is garbage collected
                self.client = None

            logger.info("Temporal client cleanup completed")

        except Exception as e:
            logger.error(f"Error during Temporal client cleanup: {e}")


async def get_temporal_client() -> TemporalWorkflowClient:
    """Get the Temporal workflow client singleton."""
    global _temporal_client

    if _temporal_client is None:
        _temporal_client = TemporalWorkflowClient()
        await _temporal_client.initialize()

    return _temporal_client
