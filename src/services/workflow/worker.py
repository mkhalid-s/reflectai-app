"""
Temporal Worker for ReflectAI

The worker connects to Temporal server and executes workflows and activities.
This replaces the custom asyncio-based task execution engine.
"""

import asyncio
import logging

from temporalio.client import Client
from temporalio.runtime import Runtime, TelemetryConfig, TelemetryFilter
from temporalio.worker import Worker

from src.shared import get_config, get_logger
from src.shared.exceptions import ErrorCategory, ReflectAIError

from .activities import (
    aggregate_report_data,
    analyze_activity,
    # Inline analysis activities
    analyze_inline_content,
    assess_competency,
    assess_content_competencies,
    chat_response,
    combined_advisory,
    combined_analysis,
    deliver_report,
    fetch_context,
    # Quick summary activities
    fetch_summary_data,
    format_inline_report,
    format_slack_summary,
    generate_advice,
    generate_pdf_report,
    post_slack_message,
    process_batch_item,
    save_report_to_database,
    send_report_notification,
    synthesize_insights,
    upload_report_to_slack,
)
from .workflows import (
    BatchProcessingWorkflow,
    ConversationWorkflow,
    InlineAnalysisReportWorkflow,
    OptimizedAnalysisWorkflow,
    ParallelAnalysisWorkflow,
    QuickSummaryWorkflow,
    ReportGenerationWorkflow,
    SequentialAnalysisWorkflow,
)

logger = get_logger(__name__)


class TemporalWorker:
    """
    Temporal worker that executes workflows and activities.

    Manages connection to Temporal server and provides lifecycle management
    for workflow and activity execution.
    """

    def __init__(
        self,
        max_concurrent_activities: int = 10,
        max_concurrent_workflows: int = 5,
        max_concurrent_local_activities: int = 10,
    ):
        self.config = get_config()
        self.client: Client | None = None
        self.worker: Worker | None = None

        # Worker configuration
        self.temporal_host = self.config.temporal.host
        self.temporal_port = self.config.temporal.port
        self.temporal_namespace = self.config.temporal.namespace
        self.task_queue = self.config.temporal.task_queue

        # Concurrency limits
        self.max_concurrent_activities = max_concurrent_activities
        self.max_concurrent_workflows = max_concurrent_workflows
        self.max_concurrent_local_activities = max_concurrent_local_activities

        # Tracking
        self.is_running = False

    async def initialize(self):
        """Initialize connection to Temporal server."""
        try:
            # Configure Temporal runtime with default telemetry
            runtime = Runtime(telemetry=TelemetryConfig())

            temporal_address = f"{self.temporal_host}:{self.temporal_port}"
            logger.info(f"Connecting worker to Temporal server at {temporal_address}")

            # Connect to Temporal server
            self.client = await Client.connect(
                target_host=temporal_address, namespace=self.temporal_namespace, runtime=runtime
            )

            # Import workflow sandbox config
            from temporalio.worker.workflow_sandbox import SandboxedWorkflowRunner, SandboxRestrictions

            # Create worker with workflows and activities
            sandbox_restrictions = SandboxRestrictions.default.with_passthrough_modules(
                "src.version", "src.shared", "src.infrastructure", "src.core"
            )

            self.worker = Worker(
                client=self.client,
                task_queue=self.task_queue,
                workflows=[
                    SequentialAnalysisWorkflow,
                    ParallelAnalysisWorkflow,
                    BatchProcessingWorkflow,
                    ConversationWorkflow,
                    OptimizedAnalysisWorkflow,
                    ReportGenerationWorkflow,
                    InlineAnalysisReportWorkflow,
                    QuickSummaryWorkflow,
                ],
                workflow_runner=SandboxedWorkflowRunner(restrictions=sandbox_restrictions),
                activities=[
                    analyze_activity,
                    assess_competency,
                    generate_advice,
                    synthesize_insights,
                    fetch_context,
                    process_batch_item,
                    combined_analysis,
                    combined_advisory,
                    chat_response,
                    aggregate_report_data,
                    generate_pdf_report,
                    save_report_to_database,
                    upload_report_to_slack,
                    send_report_notification,
                    # Inline analysis activities
                    analyze_inline_content,
                    assess_content_competencies,
                    format_inline_report,
                    deliver_report,
                    # Quick summary activities
                    fetch_summary_data,
                    format_slack_summary,
                    post_slack_message,
                ],
                max_concurrent_activities=self.max_concurrent_activities,
                max_concurrent_workflow_tasks=self.max_concurrent_workflows,
                max_concurrent_local_activities=self.max_concurrent_local_activities,
            )

            logger.info(
                "Temporal worker initialized successfully",
                extra={
                    "task_queue": self.task_queue,
                    "temporal_host": self.temporal_host,
                    "temporal_port": self.temporal_port,
                    "max_concurrent_activities": self.max_concurrent_activities,
                    "max_concurrent_workflows": self.max_concurrent_workflows,
                },
            )

        except Exception as e:
            logger.error(f"Failed to initialize Temporal worker: {e}")
            raise ReflectAIError(
                message=f"Temporal worker initialization failed: {str(e)}",
                error_code="TEMPORAL_WORKER_INIT_FAILED",
                category=ErrorCategory.INFRASTRUCTURE_ERROR,
                context={
                    "temporal_host": self.temporal_host,
                    "temporal_port": self.temporal_port,
                    "task_queue": self.task_queue,
                },
            ) from e

    async def start(self):
        """Start the Temporal worker."""
        if not self.worker:
            raise ReflectAIError(
                message="Worker not initialized. Call initialize() first.",
                category=ErrorCategory.INFRASTRUCTURE_ERROR,
            )

        if self.is_running:
            logger.warning("Worker is already running")
            return

        try:
            logger.info(f"Starting Temporal worker on task queue: {self.task_queue}")
            self.is_running = True

            # Start the worker (this blocks)
            await self.worker.run()

        except Exception as e:
            self.is_running = False
            logger.error(f"Temporal worker failed: {e}")
            raise ReflectAIError(
                message=f"Temporal worker execution failed: {str(e)}",
                category=ErrorCategory.INFRASTRUCTURE_ERROR,
            ) from e

    async def shutdown(self):
        """Gracefully shutdown the worker."""
        try:
            if self.worker and self.is_running:
                logger.info("Shutting down Temporal worker...")

                # Signal shutdown (worker.run() should exit)
                self.is_running = False

                # Note: Temporal Python worker doesn't have an explicit shutdown method
                # The worker.run() method should be cancelled via asyncio task cancellation
                logger.info("Worker shutdown signal sent")

        except Exception as e:
            logger.error(f"Error during worker shutdown: {e}")

    async def health_check(self) -> bool:
        """Check if worker is healthy and connected to Temporal."""
        try:
            if not self.client:
                return False

            # Try to get system info from Temporal server
            await self.client.workflow_service.get_system_info()
            return True

        except Exception as e:
            logger.warning(f"Worker health check failed: {e}")
            return False

    def get_status(self) -> dict:
        """Get worker status information."""
        return {
            "is_running": self.is_running,
            "task_queue": self.task_queue,
            "temporal_address": f"{self.temporal_host}:{self.temporal_port}",
            "namespace": self.temporal_namespace,
            "max_concurrent_activities": self.max_concurrent_activities,
            "max_concurrent_workflows": self.max_concurrent_workflows,
            "workflows_registered": len(self.worker.workflows) if self.worker else 0,
            "activities_registered": len(self.worker.activities) if self.worker else 0,
        }


# Singleton instance
_temporal_worker: TemporalWorker | None = None


async def get_temporal_worker() -> TemporalWorker:
    """Get the Temporal worker singleton."""
    global _temporal_worker

    if _temporal_worker is None:
        worker = TemporalWorker()
        await worker.initialize()  # Only set global AFTER successful init
        _temporal_worker = worker

    return _temporal_worker


async def start_temporal_worker():
    """Start the Temporal worker as a background task."""
    worker = await get_temporal_worker()

    # Create background task for worker
    worker_task = asyncio.create_task(worker.start())

    logger.info("Temporal worker started as background task")
    return worker_task


async def stop_temporal_worker():
    """Stop the Temporal worker."""
    global _temporal_worker

    if _temporal_worker:
        await _temporal_worker.shutdown()
        _temporal_worker = None
        logger.info("Temporal worker stopped")


# Context manager for worker lifecycle
class TemporalWorkerContext:
    """Context manager for Temporal worker lifecycle."""

    def __init__(self):
        self.worker_task = None

    async def __aenter__(self):
        """Start worker on context entry."""
        self.worker_task = await start_temporal_worker()
        return self.worker_task

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Stop worker on context exit."""
        if self.worker_task and not self.worker_task.done():
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass

        await stop_temporal_worker()


# Main entry point when run as module
if __name__ == "__main__":
    import random
    import signal
    import sys
    from typing import Optional

    logger.info("Starting Temporal worker process...")

    # Shutdown event for signal handling
    shutdown_event = asyncio.Event()
    worker_task: Optional[asyncio.Task] = None

    def handle_shutdown_signal(signum, frame):
        """Handle shutdown signals (SIGTERM, SIGINT)."""
        sig_name = signal.Signals(signum).name
        logger.info(f"Received shutdown signal: {sig_name}")
        shutdown_event.set()

        # Cancel worker task if running
        if worker_task and not worker_task.done():
            logger.info("Cancelling worker task...")
            worker_task.cancel()

    async def main():
        """Main entry point for worker process."""
        global worker_task
        worker = None
        retry_count = 0
        max_retries = 5
        base_delay = 2.0  # seconds

        try:
            while retry_count < max_retries:
                try:
                    # Initialize worker with retry logic
                    logger.info(f"Initializing worker (attempt {retry_count + 1}/{max_retries})...")
                    worker = await get_temporal_worker()
                    logger.info("Worker initialized successfully, starting...")

                    # Run worker in a task so we can cancel it
                    worker_task = asyncio.create_task(worker.start())

                    # Wait for either worker completion or shutdown signal
                    done, pending = await asyncio.wait(
                        [worker_task, asyncio.create_task(shutdown_event.wait())],
                        return_when=asyncio.FIRST_COMPLETED,
                    )

                    # Cancel pending tasks
                    for task in pending:
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass

                    # Check if worker task had an exception
                    if worker_task in done and not worker_task.cancelled():
                        exc = worker_task.exception()
                        if exc:
                            raise exc

                    # Clean shutdown - worker ran successfully and then stopped
                    logger.info("Worker stopped cleanly")
                    break

                except asyncio.CancelledError:
                    logger.info("Worker task cancelled")
                    break

                except Exception as e:
                    retry_count += 1
                    if retry_count >= max_retries:
                        logger.error(
                            f"Worker failed after {max_retries} retries: {e}",
                            exc_info=True,
                        )
                        sys.exit(1)

                    # Exponential backoff with jitter
                    delay = base_delay * (2 ** (retry_count - 1))
                    jitter = delay * 0.1  # 10% jitter
                    wait_time = delay + random.uniform(-jitter, jitter)
                    logger.warning(
                        f"Worker initialization failed, retrying in {wait_time:.1f}s...",
                        extra={"error": str(e), "retry": retry_count, "max_retries": max_retries},
                    )

                    # Clean up failed worker before retry
                    if worker:
                        try:
                            await worker.shutdown()
                        except Exception as shutdown_err:
                            logger.debug(f"Error shutting down failed worker: {shutdown_err}")

                        # Reset singleton so next attempt creates fresh instance
                        global _temporal_worker
                        _temporal_worker = None
                        worker = None

                    await asyncio.sleep(wait_time)

        finally:
            # Only runs when exiting main() completely (not on retries)
            if worker and worker.is_running:
                logger.info("Shutting down worker...")
                try:
                    # The actual cancellation happens in signal handler
                    # This is just cleanup
                    if worker_task and not worker_task.done():
                        worker_task.cancel()
                        try:
                            await worker_task
                        except asyncio.CancelledError:
                            pass

                    await worker.shutdown()
                    logger.info("Worker shutdown complete")
                except Exception as e:
                    logger.error(f"Error during worker shutdown: {e}")

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, handle_shutdown_signal)
    signal.signal(signal.SIGINT, handle_shutdown_signal)

    # Run the worker
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker stopped by keyboard interrupt")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)
