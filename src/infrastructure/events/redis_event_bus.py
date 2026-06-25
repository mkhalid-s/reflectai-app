"""
Redis Pub/Sub Event Bus for ReflectAI

Implements  Redis Pub/Sub Setup with hierarchical channel architecture.
Production-ready event streaming with <1000 events/hour capacity.
"""

import asyncio
import inspect
import json
import uuid
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from src.infrastructure.cache.redis_manager import RedisManager, get_redis_manager
from src.infrastructure.monitoring import get_metrics_collector, get_or_create_correlation_id
from src.shared import ErrorCategory, ErrorSeverity, ReflectAIError, get_logger

logger = get_logger(__name__)


@dataclass
class RedisEvent:
    """Redis pub/sub event structure."""

    event_id: str
    event_type: str
    correlation_id: str
    timestamp: datetime
    user_id: str | None
    data: dict[str, Any]
    metadata: dict[str, Any]

    def to_json(self) -> str:
        """Convert event to JSON for Redis pub/sub."""
        return json.dumps(
            {
                "event_id": self.event_id,
                "event_type": self.event_type,
                "correlation_id": self.correlation_id,
                "timestamp": self.timestamp.isoformat(),
                "user_id": self.user_id,
                "data": self.data,
                "metadata": self.metadata,
            }
        )

    @classmethod
    def from_json(cls, json_str: str) -> "RedisEvent":
        """Create event from JSON string."""
        data = json.loads(json_str)
        return cls(
            event_id=data["event_id"],
            event_type=data["event_type"],
            correlation_id=data["correlation_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            user_id=data.get("user_id"),
            data=data.get("data", {}),
            metadata=data.get("metadata", {}),
        )


class RedisEventHandler:
    """Enhanced event handler for Redis pub/sub events."""

    def __init__(
        self,
        handler: Callable,
        channels: list[str] = None,
        event_types: list[str] = None,
        filters: dict[str, Any] = None,
        priority: int = 0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        self.handler = handler
        self.channels = channels or []
        self.event_types = event_types or []
        self.filters = filters or {}
        self.priority = priority
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.is_async = inspect.iscoroutinefunction(handler)

        # Metrics
        self.events_processed = 0
        self.events_failed = 0
        self.total_processing_time = 0.0

    async def handle(self, event: RedisEvent) -> Any:
        """Execute the handler with retry logic."""
        start_time = datetime.now(UTC)

        for attempt in range(self.max_retries + 1):
            try:
                if self.is_async:
                    result = await self.handler(event)
                else:
                    result = self.handler(event)

                # Update metrics
                self.events_processed += 1
                processing_time = (datetime.now(UTC) - start_time).total_seconds()
                self.total_processing_time += processing_time

                return result

            except Exception as e:
                if attempt == self.max_retries:
                    self.events_failed += 1
                    logger.error(
                        f"Handler failed after {self.max_retries} retries",
                        extra={
                            "event_id": event.event_id,
                            "event_type": event.event_type,
                            "error": str(e),
                            "handler": self.handler.__name__,
                        },
                        exc_info=True,
                    )
                    raise

                logger.warning(
                    f"Handler attempt {attempt + 1} failed, retrying",
                    extra={
                        "event_id": event.event_id,
                        "error": str(e),
                        "retry_in": self.retry_delay,
                    },
                )
                await asyncio.sleep(self.retry_delay)

    def matches(self, event: RedisEvent, channel: str) -> bool:
        """Check if handler should process this event."""
        # Channel matching
        if self.channels and channel not in self.channels:
            # Check for pattern matching
            channel_matched = False
            for pattern in self.channels:
                if pattern.endswith(".*"):
                    prefix = pattern[:-2]
                    if channel.startswith(prefix):
                        channel_matched = True
                        break
                elif pattern == "*":
                    channel_matched = True
                    break

            if not channel_matched:
                return False

        # Event type matching
        if self.event_types and event.event_type not in self.event_types:
            return False

        # Filter matching
        for key, value in self.filters.items():
            event_value = None
            if hasattr(event, key):
                event_value = getattr(event, key)
            elif key in event.data:
                event_value = event.data[key]
            elif key in event.metadata:
                event_value = event.metadata[key]

            if event_value != value:
                return False

        return True


class RedisEventBus:
    """
    Production Redis pub/sub event bus implementing Task 8a requirements.

    Features:
    - Hierarchical channel naming: {domain}.{entity}.{action}
    - Separate Redis database (db=1) for pub/sub
    - Connection pooling and health monitoring
    - Event deduplication and retry logic
    - Performance metrics and monitoring
    """

    # Hierarchical channel names per Task 8a
    CORE_CHANNELS = {
        "USER_ACTIVITY_COMPLETED": "user.activity.completed",
        "USER_ANALYSIS_COMPLETED": "user.analysis.completed",
        "USER_REPORT_GENERATED": "user.report.generated",
    }

    CACHE_CHANNELS = {
        "CACHE_USER_UPDATED": "cache.user.updated",
        "CACHE_HOME_TAB_REFRESH": "cache.home_tab.refresh",
    }

    SYSTEM_CHANNELS = {
        "SLACK_EVENT_RECEIVED": "slack.event.received",
        "WORKFLOW_COMPLETED": "workflow.completed",
        "ERROR_OCCURRED": "error.occurred",
    }

    def __init__(self):
        """Initialize Redis pub/sub event bus."""
        self.redis_manager: RedisManager | None = None
        self.metrics_collector = get_metrics_collector()

        # Handler registry
        self.handlers: dict[str, list[RedisEventHandler]] = defaultdict(list)
        self.active_subscriptions: set[str] = set()
        self.subscription_tasks: dict[str, asyncio.Task] = {}

        # Connection state
        self.running = False
        self.health_check_task: asyncio.Task | None = None

        # Metrics
        self.events_published = 0
        self.events_received = 0
        self.events_processed = 0
        self.events_failed = 0
        self.connection_errors = 0

        logger.info("Redis event bus initialized")

    async def start(self) -> None:
        """Start the Redis event bus."""
        if self.running:
            return

        try:
            # Get Redis manager configured for pub/sub
            self.redis_manager = get_redis_manager()
            if not isinstance(self.redis_manager, RedisManager):
                raise ReflectAIError(
                    message="Redis manager required for pub/sub",
                    category=ErrorCategory.INFRASTRUCTURE,
                    severity=ErrorSeverity.HIGH,
                )

            # Test connection
            await self.redis_manager.ping()

            self.running = True

            # Start health check task
            self.health_check_task = asyncio.create_task(self._health_check_loop())

            logger.info("Redis event bus started successfully")

        except Exception as e:
            logger.error(f"Failed to start Redis event bus: {e}", exc_info=True)
            raise ReflectAIError(
                message=f"Redis event bus startup failed: {e}",
                category=ErrorCategory.INFRASTRUCTURE,
                severity=ErrorSeverity.HIGH,
            ) from e

    async def stop(self) -> None:
        """Stop the Redis event bus."""
        if not self.running:
            return

        self.running = False

        # Cancel all subscription tasks
        for task in self.subscription_tasks.values():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Cancel health check
        if self.health_check_task and not self.health_check_task.done():
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass

        # Clear state
        self.subscription_tasks.clear()
        self.active_subscriptions.clear()

        logger.info(
            f"Redis event bus stopped. Stats: published={self.events_published}, "
            f"received={self.events_received}, processed={self.events_processed}, "
            f"failed={self.events_failed}, connection_errors={self.connection_errors}"
        )

    async def publish(
        self,
        channel: str,
        event_type: str,
        data: dict[str, Any],
        user_id: str | None = None,
        correlation_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """
        Publish event to Redis pub/sub channel.

        Args:
            channel: Redis channel name (hierarchical naming)
            event_type: Event type identifier
            data: Event payload data
            user_id: Optional user ID
            correlation_id: Optional correlation ID
            metadata: Optional event metadata

        Returns:
            Number of subscribers that received the event
        """
        if not self.running:
            raise ReflectAIError(
                message="Event bus not running",
                category=ErrorCategory.INFRASTRUCTURE,
                severity=ErrorSeverity.MEDIUM,
            )

        try:
            # Create Redis event
            event = RedisEvent(
                event_id=str(uuid.uuid4()),
                event_type=event_type,
                correlation_id=correlation_id or get_or_create_correlation_id(),
                timestamp=datetime.now(UTC),
                user_id=user_id,
                data=data or {},
                metadata=metadata or {},
            )

            # Publish to Redis
            subscribers = await self.redis_manager.publish(channel, event.to_json())

            self.events_published += 1

            # Update metrics
            if self.metrics_collector:
                self.metrics_collector.increment_counter(
                    "redis_events_published_total",
                    tags={"channel": channel, "event_type": event_type},
                )

            logger.debug(
                "Published event to Redis channel",
                extra={
                    "channel": channel,
                    "event_type": event_type,
                    "event_id": event.event_id,
                    "subscribers": subscribers,
                },
            )

            return subscribers

        except Exception as e:
            self.events_failed += 1
            logger.error(
                "Failed to publish event to Redis",
                extra={"channel": channel, "event_type": event_type, "error": str(e)},
                exc_info=True,
            )
            raise ReflectAIError(
                message=f"Event publish failed: {e}",
                category=ErrorCategory.INFRASTRUCTURE,
                severity=ErrorSeverity.MEDIUM,
            ) from e

    def subscribe(
        self,
        handler: Callable,
        channels: list[str],
        event_types: list[str] = None,
        filters: dict[str, Any] = None,
        priority: int = 0,
    ) -> RedisEventHandler:
        """
        Subscribe handler to Redis pub/sub channels.

        Args:
            handler: Event handler function (sync or async)
            channels: List of Redis channels to subscribe to
            event_types: Optional list of event types to filter
            filters: Optional event filters
            priority: Handler priority (higher = executed first)

        Returns:
            RedisEventHandler instance
        """
        # Create handler wrapper
        event_handler = RedisEventHandler(
            handler=handler,
            channels=channels,
            event_types=event_types,
            filters=filters,
            priority=priority,
        )

        # Register handler for all specified channels
        for channel in channels:
            self.handlers[channel].append(event_handler)
            # Sort by priority (higher first)
            self.handlers[channel].sort(key=lambda h: -h.priority)

        logger.info(
            "Registered Redis event handler",
            extra={"channels": channels, "event_types": event_types, "handler": handler.__name__},
        )

        # Start subscription tasks for new channels
        asyncio.create_task(self._ensure_subscriptions(channels))

        return event_handler

    def unsubscribe(self, handler: RedisEventHandler) -> None:
        """Unsubscribe handler from all channels."""
        for channel_handlers in self.handlers.values():
            if handler in channel_handlers:
                channel_handlers.remove(handler)

        logger.info("Redis event handler unsubscribed")

    async def _ensure_subscriptions(self, channels: list[str]) -> None:
        """Ensure Redis subscriptions exist for channels."""
        if not self.running:
            return

        for channel in channels:
            if channel not in self.active_subscriptions:
                try:
                    # Start subscription task
                    task = asyncio.create_task(self._subscription_worker(channel))
                    self.subscription_tasks[channel] = task
                    self.active_subscriptions.add(channel)

                    logger.info(f"Started Redis subscription for channel: {channel}")

                except Exception as e:
                    logger.error(
                        f"Failed to subscribe to Redis channel: {channel}",
                        extra={"error": str(e)},
                        exc_info=True,
                    )

    async def _subscription_worker(self, channel: str) -> None:
        """Worker task for handling Redis channel subscription."""
        pubsub = None

        while self.running:
            try:
                # Create a persistent PubSub connection
                pubsub = await self.redis_manager.create_pubsub()
                await pubsub.subscribe(channel)
                logger.info(f"Redis subscription active for channel: {channel}")

                while self.running:
                    try:
                        # Get message with timeout
                        message = await asyncio.wait_for(
                            pubsub.get_message(ignore_subscribe_messages=True), timeout=5.0
                        )

                        if message is None:
                            continue

                        # Process message (handle both string and bytes)
                        message_data = message.get("data")
                        if isinstance(message_data, bytes):
                            message_data = message_data.decode("utf-8")

                        if message_data:
                            await self._handle_message(channel, message_data)

                    except asyncio.TimeoutError:
                        # Timeout is normal, continue listening
                        continue
                    except Exception as e:
                            logger.error(
                                "Error processing Redis message",
                                extra={"channel": channel, "error": str(e)},
                                exc_info=True,
                            )
                            await asyncio.sleep(1)  # Brief pause before retry

            except Exception as e:
                self.connection_errors += 1
                logger.error(
                    "Redis subscription connection error",
                    extra={"channel": channel, "error": str(e)},
                    exc_info=True,
                )

                if self.running:
                    # Exponential backoff before reconnecting
                    await asyncio.sleep(min(5.0, 1.0 * self.connection_errors))

            finally:
                # Always cleanup pubsub connection
                if pubsub:
                    try:
                        await pubsub.unsubscribe(channel)
                        await pubsub.close()
                        logger.debug(f"Closed Redis subscription for channel: {channel}")
                    except Exception as e:
                        logger.warning(f"Error closing pubsub connection: {e}")

    async def _handle_message(self, channel: str, message_data: str | bytes) -> None:
        """Handle incoming Redis pub/sub message."""
        try:
            self.events_received += 1

            # Parse event from JSON (handle both string and bytes)
            if isinstance(message_data, bytes):
                message_str = message_data.decode("utf-8")
            else:
                message_str = message_data

            event = RedisEvent.from_json(message_str)

            # Find matching handlers
            handlers = self.handlers.get(channel, [])
            matching_handlers = [h for h in handlers if h.matches(event, channel)]

            if not matching_handlers:
                logger.debug(
                    "No handlers found for event",
                    extra={
                        "channel": channel,
                        "event_type": event.event_type,
                        "event_id": event.event_id,
                    },
                )
                return

            # Process handlers concurrently
            tasks = []
            for handler in matching_handlers:
                task = asyncio.create_task(self._execute_handler(handler, event))
                tasks.append(task)

            # Wait for all handlers to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Count successful vs failed
            successful = sum(1 for r in results if not isinstance(r, Exception))
            failed = len(results) - successful

            self.events_processed += successful
            self.events_failed += failed

            if self.metrics_collector:
                self.metrics_collector.increment_counter(
                    "redis_events_processed_total",
                    tags={"channel": channel, "event_type": event.event_type},
                )

            logger.debug(
                "Processed Redis event",
                extra={
                    "channel": channel,
                    "event_type": event.event_type,
                    "event_id": event.event_id,
                    "handlers_successful": successful,
                    "handlers_failed": failed,
                },
            )

        except Exception as e:
            self.events_failed += 1
            logger.error(
                "Failed to handle Redis message",
                extra={"channel": channel, "error": str(e)},
                exc_info=True,
            )

    async def _execute_handler(self, handler: RedisEventHandler, event: RedisEvent) -> None:
        """Execute a single event handler."""
        try:
            await handler.handle(event)
        except Exception as e:
            logger.error(
                "Event handler execution failed",
                extra={
                    "handler": handler.handler.__name__,
                    "event_type": event.event_type,
                    "event_id": event.event_id,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

    async def _health_check_loop(self) -> None:
        """Background health check for Redis connectivity."""
        while self.running:
            try:
                await self.redis_manager.ping()
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                self.connection_errors += 1
                logger.error("Redis health check failed", extra={"error": str(e)}, exc_info=True)
                await asyncio.sleep(10)  # Retry more frequently on error

    def get_stats(self) -> dict[str, Any]:
        """Get event bus statistics."""
        handler_stats = {}
        for channel, handlers in self.handlers.items():
            handler_stats[channel] = {
                "handler_count": len(handlers),
                "total_processed": sum(h.events_processed for h in handlers),
                "total_failed": sum(h.events_failed for h in handlers),
                "avg_processing_time": sum(h.total_processing_time for h in handlers)
                / max(1, sum(h.events_processed for h in handlers)),
            }

        return {
            "running": self.running,
            "events_published": self.events_published,
            "events_received": self.events_received,
            "events_processed": self.events_processed,
            "events_failed": self.events_failed,
            "connection_errors": self.connection_errors,
            "active_subscriptions": len(self.active_subscriptions),
            "total_handlers": sum(len(h) for h in self.handlers.values()),
            "handler_stats": handler_stats,
        }


# Global Redis event bus instance
_redis_event_bus: RedisEventBus | None = None


def get_redis_event_bus() -> RedisEventBus:
    """Get or create the global Redis event bus instance."""
    global _redis_event_bus
    if _redis_event_bus is None:
        _redis_event_bus = RedisEventBus()
    return _redis_event_bus


# Convenience functions for common event patterns
async def publish_user_activity_completed(
    user_id: str,
    activity_id: str,
    competencies: list[str],
    metadata: dict[str, Any] | None = None,
) -> int:
    """Publish user activity completed event."""
    bus = get_redis_event_bus()
    return await bus.publish(
        channel=bus.CORE_CHANNELS["USER_ACTIVITY_COMPLETED"],
        event_type="user.activity.completed",
        data={"activity_id": activity_id, "competencies": competencies},
        user_id=user_id,
        metadata=metadata,
    )


async def publish_user_analysis_completed(
    user_id: str,
    analysis_id: str,
    competency_scores: dict[str, float],
    metadata: dict[str, Any] | None = None,
) -> int:
    """Publish user analysis completed event."""
    bus = get_redis_event_bus()
    return await bus.publish(
        channel=bus.CORE_CHANNELS["USER_ANALYSIS_COMPLETED"],
        event_type="user.analysis.completed",
        data={"analysis_id": analysis_id, "competency_scores": competency_scores},
        user_id=user_id,
        metadata=metadata,
    )


async def publish_cache_refresh(
    cache_type: str,
    cache_key: str,
    user_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> int:
    """Publish cache refresh event."""
    bus = get_redis_event_bus()

    if cache_type == "user":
        channel = bus.CACHE_CHANNELS["CACHE_USER_UPDATED"]
    elif cache_type == "home_tab":
        channel = bus.CACHE_CHANNELS["CACHE_HOME_TAB_REFRESH"]
    else:
        channel = "cache.updated"

    return await bus.publish(
        channel=channel,
        event_type=f"cache.{cache_type}.updated",
        data={"cache_key": cache_key, "cache_type": cache_type},
        user_id=user_id,
        metadata=metadata,
    )


# Decorator for Redis event handlers
def redis_event_handler(
    channels: list[str],
    event_types: list[str] = None,
    filters: dict[str, Any] = None,
    priority: int = 0,
):
    """
    Decorator to register a function as a Redis event handler.

    Usage:
        @redis_event_handler(
            channels=["user.activity.completed"],
            event_types=["user.activity.completed"]
        )
        async def handle_activity_completed(event: RedisEvent):
            # Process event
            pass
    """

    def decorator(func):
        # Register with global Redis event bus
        bus = get_redis_event_bus()
        bus.subscribe(func, channels, event_types, filters, priority)
        return func

    return decorator


if __name__ == "__main__":
    # Example usage and testing
    async def example_handler(event: RedisEvent):
        print(f"Received event: {event.event_type} - {event.data}")

    async def main():
        bus = get_redis_event_bus()

        # Start the bus
        await bus.start()

        # Subscribe to events
        bus.subscribe(
            handler=example_handler,
            channels=["user.activity.completed"],
            event_types=["user.activity.completed"],
        )

        # Publish an event
        await bus.publish(
            channel="user.activity.completed",
            event_type="user.activity.completed",
            data={"activity_id": "123", "competencies": ["leadership"]},
            user_id="user123",
        )

        # Wait a bit for processing
        await asyncio.sleep(2)

        # Get stats
        stats = bus.get_stats()
        print(f"Event bus stats: {stats}")

        # Stop the bus
        await bus.stop()

    asyncio.run(main())
