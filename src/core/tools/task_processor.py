"""
Redis Task Processing System for ReflectAI

Implements task processing part of
- Redis lists as simple task queues for each agent type
- Task priority handling using separate Redis keys
- Task deduplication using task hashes
- Retry logic with exponential backoff for failed executions
- Integration with tool execution and monitoring

Provides reliable task queuing and processing for agent tools.
"""

import asyncio
import hashlib
import json
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

import redis.asyncio as redis

from src.shared import (
    CircuitBreaker,
    ErrorCategory,
    ErrorSeverity,
    ReflectAIError,
    get_logger,
    log_function_call,
    log_function_result,
)

from .base_tool import ToolRequest, ToolResponse


class TaskPriority(Enum):
    """Task priority levels"""

    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class TaskStatus(Enum):
    """Task processing status"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD_LETTER = "dead_letter"


@dataclass
class TaskRequest:
    """Task request for queue processing"""

    task_id: str
    agent_type: str  # 'analysis' or 'advisor'
    tool_request: ToolRequest
    priority: TaskPriority
    max_retries: int = 3
    retry_count: int = 0
    created_at: datetime = None
    scheduled_at: datetime = None
    expires_at: datetime | None = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(UTC)
        if self.scheduled_at is None:
            self.scheduled_at = datetime.now(UTC)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for Redis storage"""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat() if value else None
        # Convert enums to values
        data["priority"] = self.priority.value
        data["tool_request"] = self.tool_request.model_dump()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskRequest":
        """Create from dictionary loaded from Redis"""
        # Convert ISO strings back to datetime objects
        for key in ["created_at", "scheduled_at", "expires_at"]:
            if data.get(key):
                data[key] = datetime.fromisoformat(data[key])

        # Convert enums back from values
        data["priority"] = TaskPriority(data["priority"])
        data["tool_request"] = ToolRequest(**data["tool_request"])

        return cls(**data)

    def get_hash(self) -> str:
        """Generate hash for deduplication"""
        content = f"{self.agent_type}:{self.tool_request.get_request_hash()}"
        # Use SHA256 for deduplication hashing (more secure than MD5)
        return hashlib.sha256(content.encode()).hexdigest()


@dataclass
class ProcessingResult:
    """Result of task processing"""

    task_id: str
    status: TaskStatus
    tool_response: ToolResponse | None = None
    error: str | None = None
    processing_time: float = 0.0
    completed_at: datetime = None

    def __post_init__(self):
        if self.completed_at is None:
            self.completed_at = datetime.now(UTC)


class TaskProcessorError(ReflectAIError):
    """Specialized error for task processing failures"""

    def __init__(self, message: str, task_id: str | None = None, operation: str = "unknown"):
        super().__init__(
            message=message,
            category=ErrorCategory.TEMPORAL_WORKFLOW_ERROR,
            severity=ErrorSeverity.HIGH,
            context={"task_id": task_id or "unknown", "operation": operation},
        )


class TaskProcessor:
    """
    Redis-based task processor for agent tool execution

    Provides:
    - Priority queue management with Redis lists
    - Task deduplication and retry logic
    - Circuit breaker for Redis connection failures
    - Comprehensive monitoring and health checks
    """

    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        redis_password: str | None = None,
        queue_prefix: str = "reflectai:tasks",
        deduplication_ttl: int = 3600,  # 1 hour
        max_processing_time: int = 300,  # 5 minutes
        health_check_interval: int = 60,  # 1 minute
    ):
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_db = redis_db
        self.redis_password = redis_password
        self.queue_prefix = queue_prefix
        self.deduplication_ttl = deduplication_ttl
        self.max_processing_time = max_processing_time

        self.logger = get_logger("task.processor")

        # Redis connection with circuit breaker
        self._redis: redis.Redis | None = None
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=5, recovery_timeout=30, expected_exception=redis.RedisError
        )

        # Processing metrics
        self._processing_stats = {
            "tasks_processed": 0,
            "tasks_failed": 0,
            "tasks_retried": 0,
            "average_processing_time": 0.0,
            "last_processed": None,
        }

        # Background health check
        self._health_check_task: asyncio.Task | None = None
        self._shutdown_event = asyncio.Event()

    async def initialize(self) -> bool:
        """
        Initialize Redis connection and start background tasks

        Returns:
            True if initialization successful
        """
        try:
            # Create Redis connection
            self._redis = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                db=self.redis_db,
                password=self.redis_password,
                decode_responses=True,
            )

            # Test connection
            await self._redis.ping()
            self.logger.info("Redis connection established")

            # Start health check background task
            self._health_check_task = asyncio.create_task(self._health_check_loop())

            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize task processor: {str(e)}")
            return False

    async def shutdown(self) -> None:
        """Graceful shutdown of task processor"""
        self.logger.info("Shutting down task processor")

        # Signal shutdown
        self._shutdown_event.set()

        # Cancel health check task
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        # Close Redis connection
        if self._redis:
            await self._redis.close()

    async def enqueue_task(
        self,
        agent_type: str,
        tool_request: ToolRequest,
        priority: TaskPriority = TaskPriority.NORMAL,
        max_retries: int = 3,
        delay_seconds: int = 0,
        expires_in_seconds: int | None = None,
    ) -> str:
        """
        Enqueue a task for processing

        Args:
            agent_type: Agent type ('analysis' or 'advisor')
            tool_request: Tool execution request
            priority: Task priority level
            max_retries: Maximum retry attempts
            delay_seconds: Delay before task becomes available
            expires_in_seconds: Task expiration timeout

        Returns:
            Task ID

        Raises:
            TaskProcessorError: If task enqueuing fails
        """
        # Create task request
        task_id = f"{agent_type}_{int(time.time() * 1000000)}"
        scheduled_at = datetime.now(UTC) + timedelta(seconds=delay_seconds)
        expires_at = (
            datetime.now(UTC) + timedelta(seconds=expires_in_seconds)
            if expires_in_seconds
            else None
        )

        task_request = TaskRequest(
            task_id=task_id,
            agent_type=agent_type,
            tool_request=tool_request,
            priority=priority,
            max_retries=max_retries,
            scheduled_at=scheduled_at,
            expires_at=expires_at,
        )

        try:
            # Check for duplicates
            if await self._is_duplicate_task(task_request):
                self.logger.info(f"Skipping duplicate task: {task_id}")
                return task_id

            # Store task data
            await self._store_task_data(task_request)

            # Add to appropriate queue
            queue_name = self._get_queue_name(agent_type, priority)

            if delay_seconds > 0:
                # Use delayed queue for scheduled tasks
                delayed_queue = f"{queue_name}:delayed"
                score = int(scheduled_at.timestamp())
                await self._redis.zadd(delayed_queue, {task_id: score})
            else:
                # Add to immediate processing queue
                await self._redis.lpush(queue_name, task_id)

            # Set deduplication marker
            await self._set_deduplication_marker(task_request)

            log_function_call(
                function_name="enqueue_task",
                args={
                    "task_id": task_id,
                    "agent_type": agent_type,
                    "tool_name": tool_request.tool_name,
                    "priority": priority.value,
                },
                correlation_id=tool_request.correlation_id,
            )

            return task_id

        except Exception as e:
            raise TaskProcessorError(
                message=f"Failed to enqueue task: {str(e)}", task_id=task_id, operation="enqueue"
            ) from e

    async def dequeue_task(self, agent_type: str, timeout: int = 30) -> TaskRequest | None:
        """
        Dequeue a task for processing

        Args:
            agent_type: Agent type to process tasks for
            timeout: Blocking timeout in seconds

        Returns:
            Task request or None if timeout
        """
        try:
            # Process delayed tasks first
            await self._process_delayed_tasks(agent_type)

            # Get queues in priority order
            queues = [
                self._get_queue_name(agent_type, TaskPriority.HIGH),
                self._get_queue_name(agent_type, TaskPriority.NORMAL),
                self._get_queue_name(agent_type, TaskPriority.LOW),
            ]

            # Blocking pop from priority queues
            result = await self._circuit_breaker.call(self._redis.brpop, queues, timeout=timeout)

            if not result:
                return None

            queue_name, task_id = result

            # Load task data
            task_request = await self._load_task_data(task_id)
            if not task_request:
                self.logger.warning(f"Task data not found for ID: {task_id}")
                return None

            # Check if task has expired
            if task_request.expires_at and datetime.now(UTC) > task_request.expires_at:
                self.logger.info(f"Task expired: {task_id}")
                await self._cleanup_task_data(task_id)
                return await self.dequeue_task(agent_type, timeout)  # Try next task

            # Mark as processing
            await self._mark_task_processing(task_id)

            return task_request

        except Exception as e:
            self.logger.error(f"Failed to dequeue task: {str(e)}")
            return None

    async def complete_task(self, task_id: str, tool_response: ToolResponse) -> bool:
        """
        Mark a task as completed

        Args:
            task_id: Task identifier
            tool_response: Tool execution response

        Returns:
            True if successfully completed
        """
        try:
            # Create processing result
            result = ProcessingResult(
                task_id=task_id,
                status=TaskStatus.COMPLETED,
                tool_response=tool_response,
                processing_time=tool_response.execution_time,
            )

            # Store result
            await self._store_processing_result(result)

            # Update statistics
            self._update_processing_stats(result)

            # Cleanup task data
            await self._cleanup_task_data(task_id)

            log_function_result(
                function_name="complete_task",
                result={"task_id": task_id, "status": "completed"},
                correlation_id=tool_response.request_id,
            )

            return True

        except Exception as e:
            self.logger.error(f"Failed to complete task {task_id}: {str(e)}")
            return False

    async def fail_task(
        self, task_id: str, error: str, retry: bool = True, processing_time: float = 0.0
    ) -> bool:
        """
        Mark a task as failed and optionally retry

        Args:
            task_id: Task identifier
            error: Error message
            retry: Whether to retry the task
            processing_time: Time spent processing

        Returns:
            True if successfully handled
        """
        try:
            # Load task data
            task_request = await self._load_task_data(task_id)
            if not task_request:
                return False

            # Determine if we should retry
            should_retry = (
                retry
                and task_request.retry_count < task_request.max_retries
                and task_request.expires_at is None
                or datetime.now(UTC) < task_request.expires_at
            )

            if should_retry:
                # Increment retry count
                task_request.retry_count += 1

                # Calculate exponential backoff delay
                delay = min(2**task_request.retry_count, 300)  # Max 5 minutes

                # Re-enqueue with delay
                await self._requeue_task_with_delay(task_request, delay)

                # Create retry result
                result = ProcessingResult(
                    task_id=task_id,
                    status=TaskStatus.RETRYING,
                    error=error,
                    processing_time=processing_time,
                )

                self._processing_stats["tasks_retried"] += 1
                self.logger.info(
                    f"Retrying task {task_id} (attempt {task_request.retry_count}/{task_request.max_retries})"
                )

            else:
                # Create failure result
                result = ProcessingResult(
                    task_id=task_id,
                    status=TaskStatus.FAILED,
                    error=error,
                    processing_time=processing_time,
                )

                # Move to dead letter queue if max retries exceeded
                if task_request.retry_count >= task_request.max_retries:
                    await self._move_to_dead_letter_queue(task_id, task_request)

                self._processing_stats["tasks_failed"] += 1
                self.logger.error(f"Task {task_id} failed permanently: {error}")

            # Store result
            await self._store_processing_result(result)

            # Update statistics
            self._update_processing_stats(result)

            return True

        except Exception as e:
            self.logger.error(f"Failed to handle task failure {task_id}: {str(e)}")
            return False

    async def get_queue_stats(self, agent_type: str) -> dict[str, Any]:
        """
        Get queue statistics for an agent type

        Args:
            agent_type: Agent type to get stats for

        Returns:
            Queue statistics
        """
        try:
            stats = {}

            for priority in TaskPriority:
                queue_name = self._get_queue_name(agent_type, priority)
                delayed_queue = f"{queue_name}:delayed"
                processing_queue = f"{queue_name}:processing"

                # Get queue lengths
                pending_count = await self._redis.llen(queue_name)
                delayed_count = await self._redis.zcard(delayed_queue)
                processing_count = await self._redis.scard(processing_queue)

                stats[priority.value] = {
                    "pending": pending_count,
                    "delayed": delayed_count,
                    "processing": processing_count,
                }

            # Add processing statistics
            stats["processing_stats"] = self._processing_stats.copy()

            return stats

        except Exception as e:
            self.logger.error(f"Failed to get queue stats: {str(e)}")
            return {}

    async def get_health_status(self) -> dict[str, Any]:
        """Get processor health status"""
        try:
            # Test Redis connection
            await self._redis.ping()
            redis_healthy = True
        except Exception:
            redis_healthy = False

        # Calculate health metrics
        total_processed = self._processing_stats["tasks_processed"]
        total_failed = self._processing_stats["tasks_failed"]
        success_rate = 1.0 - (total_failed / max(total_processed, 1))

        if not redis_healthy:
            status = "unhealthy"
            reason = "redis_connection_failed"
        elif success_rate < 0.8:
            status = "degraded"
            reason = "high_failure_rate"
        else:
            status = "healthy"
            reason = "operational"

        return {
            "status": status,
            "reason": reason,
            "redis_healthy": redis_healthy,
            "success_rate": success_rate,
            "processing_stats": self._processing_stats.copy(),
            "last_health_check": datetime.now(UTC).isoformat(),
        }

    # Private helper methods

    def _get_queue_name(self, agent_type: str, priority: TaskPriority) -> str:
        """Get Redis queue name for agent type and priority"""
        return f"{self.queue_prefix}:{agent_type}:{priority.value}"

    async def _is_duplicate_task(self, task_request: TaskRequest) -> bool:
        """Check if task is a duplicate"""
        dedup_key = f"{self.queue_prefix}:dedup:{task_request.get_hash()}"
        return await self._redis.exists(dedup_key)

    async def _set_deduplication_marker(self, task_request: TaskRequest) -> None:
        """Set deduplication marker for task"""
        dedup_key = f"{self.queue_prefix}:dedup:{task_request.get_hash()}"
        await self._redis.setex(dedup_key, self.deduplication_ttl, task_request.task_id)

    async def _store_task_data(self, task_request: TaskRequest) -> None:
        """Store task data in Redis"""
        data_key = f"{self.queue_prefix}:data:{task_request.task_id}"
        data = json.dumps(task_request.to_dict())
        await self._redis.setex(data_key, self.max_processing_time + 300, data)

    async def _load_task_data(self, task_id: str) -> TaskRequest | None:
        """Load task data from Redis"""
        data_key = f"{self.queue_prefix}:data:{task_id}"
        data = await self._redis.get(data_key)
        if not data:
            return None
        return TaskRequest.from_dict(json.loads(data))

    async def _cleanup_task_data(self, task_id: str) -> None:
        """Cleanup task-related data"""
        keys_to_delete = [
            f"{self.queue_prefix}:data:{task_id}",
            f"{self.queue_prefix}:processing:{task_id}",
            f"{self.queue_prefix}:result:{task_id}",
        ]
        await self._redis.delete(*keys_to_delete)

    async def _mark_task_processing(self, task_id: str) -> None:
        """Mark task as currently processing"""
        processing_key = f"{self.queue_prefix}:processing:{task_id}"
        await self._redis.setex(
            processing_key, self.max_processing_time, datetime.now(UTC).isoformat()
        )

    async def _process_delayed_tasks(self, agent_type: str) -> None:
        """Move ready delayed tasks to immediate processing queues"""
        now_timestamp = int(datetime.now(UTC).timestamp())

        for priority in TaskPriority:
            queue_name = self._get_queue_name(agent_type, priority)
            delayed_queue = f"{queue_name}:delayed"

            # Get tasks ready for processing
            ready_tasks = await self._redis.zrangebyscore(
                delayed_queue, 0, now_timestamp, withscores=False
            )

            if ready_tasks:
                # Move to immediate processing queue
                pipe = self._redis.pipeline()
                pipe.lpush(queue_name, *ready_tasks)
                pipe.zrem(delayed_queue, *ready_tasks)
                await pipe.execute()

    async def _requeue_task_with_delay(self, task_request: TaskRequest, delay: int) -> None:
        """Re-queue task with delay for retry"""
        scheduled_at = datetime.now(UTC) + timedelta(seconds=delay)
        task_request.scheduled_at = scheduled_at

        # Update task data
        await self._store_task_data(task_request)

        # Add to delayed queue
        queue_name = self._get_queue_name(task_request.agent_type, task_request.priority)
        delayed_queue = f"{queue_name}:delayed"
        score = int(scheduled_at.timestamp())
        await self._redis.zadd(delayed_queue, {task_request.task_id: score})

    async def _move_to_dead_letter_queue(self, task_id: str, task_request: TaskRequest) -> None:
        """Move failed task to dead letter queue"""
        dead_letter_queue = f"{self.queue_prefix}:dead_letter"
        dead_letter_data = {
            "task_id": task_id,
            "agent_type": task_request.agent_type,
            "failed_at": datetime.now(UTC).isoformat(),
            "retry_count": task_request.retry_count,
        }
        await self._redis.lpush(dead_letter_queue, json.dumps(dead_letter_data))

    async def _store_processing_result(self, result: ProcessingResult) -> None:
        """Store processing result"""
        result_key = f"{self.queue_prefix}:result:{result.task_id}"
        result_data = {
            "task_id": result.task_id,
            "status": result.status.value,
            "error": result.error,
            "processing_time": result.processing_time,
            "completed_at": result.completed_at.isoformat(),
        }
        if result.tool_response:
            result_data["tool_response"] = result.tool_response.model_dump()

        # Store with TTL
        await self._redis.setex(result_key, 86400, json.dumps(result_data))  # 24 hours

    def _update_processing_stats(self, result: ProcessingResult) -> None:
        """Update processing statistics"""
        self._processing_stats["tasks_processed"] += 1

        if result.status == TaskStatus.FAILED:
            self._processing_stats["tasks_failed"] += 1

        # Update average processing time
        current_avg = self._processing_stats["average_processing_time"]
        current_count = self._processing_stats["tasks_processed"]
        new_avg = ((current_avg * (current_count - 1)) + result.processing_time) / current_count
        self._processing_stats["average_processing_time"] = new_avg
        self._processing_stats["last_processed"] = datetime.now(UTC).isoformat()

    async def _health_check_loop(self) -> None:
        """Background health check loop"""
        while not self._shutdown_event.is_set():
            try:
                # Clean up stale processing tasks
                await self._cleanup_stale_processing_tasks()

                # Wait for next check
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=60,  # 1 minute
                )
            except TimeoutError:
                continue  # Normal timeout, continue loop
            except Exception as e:
                self.logger.error(f"Health check error: {str(e)}")
                await asyncio.sleep(60)

    async def _cleanup_stale_processing_tasks(self) -> None:
        """Clean up tasks that have been processing too long"""
        processing_pattern = f"{self.queue_prefix}:processing:*"
        processing_keys = await self._redis.keys(processing_pattern)

        now = datetime.now(UTC)
        stale_tasks = []

        for key in processing_keys:
            started_at_str = await self._redis.get(key)
            if started_at_str:
                try:
                    started_at = datetime.fromisoformat(started_at_str)
                    if (now - started_at).seconds > self.max_processing_time:
                        task_id = key.split(":")[-1]
                        stale_tasks.append(task_id)
                except Exception:
                    continue

        # Handle stale tasks
        for task_id in stale_tasks:
            await self.fail_task(
                task_id,
                error=f"Task processing timeout after {self.max_processing_time} seconds",
                retry=True,
                processing_time=self.max_processing_time,
            )


# Global processor instance
_global_processor: TaskProcessor | None = None


async def get_task_processor() -> TaskProcessor:
    """Get the global task processor instance"""
    global _global_processor
    if _global_processor is None:
        _global_processor = TaskProcessor()
        await _global_processor.initialize()
    return _global_processor
