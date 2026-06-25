"""
Event Bus Implementation for ReflectAI

Provides pub/sub messaging pattern for decoupled component communication.
Uses memory cache pub/sub for development, will use Redis for production.
"""

import asyncio
import inspect
import json
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from src.infrastructure.cache.redis_manager import get_redis_manager
from src.shared.logging import get_logger

from .event_types import BaseEvent

logger = get_logger(__name__)


@dataclass
class Event:
    """Generic event wrapper for non-typed events."""

    name: str
    data: dict[str, Any]
    correlation_id: str
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(UTC)

    def to_json(self) -> str:
        """Convert event to JSON string."""
        return json.dumps(
            {
                "name": self.name,
                "data": self.data,
                "correlation_id": self.correlation_id,
                "timestamp": self.timestamp.isoformat(),
            }
        )

    @classmethod
    def from_json(cls, json_str: str) -> "Event":
        """Create event from JSON string."""
        data = json.loads(json_str)
        return cls(
            name=data["name"],
            data=data["data"],
            correlation_id=data["correlation_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )


class EventHandler:
    """Wrapper for event handler functions with metadata."""

    def __init__(
        self,
        handler: Callable,
        event_types: list[str] = None,
        filters: dict[str, Any] = None,
        priority: int = 0,
    ):
        self.handler = handler
        self.event_types = event_types or []
        self.filters = filters or {}
        self.priority = priority
        self.is_async = inspect.iscoroutinefunction(handler)

    async def handle(self, event: Any) -> Any:
        """Execute the handler with the event."""
        if self.is_async:
            return await self.handler(event)
        else:
            return self.handler(event)

    def matches(self, event: Any) -> bool:
        """Check if this handler should process the event."""
        # Check event type match
        if isinstance(event, BaseEvent):
            event_type = event.event_type.value
        elif isinstance(event, Event):
            event_type = event.name
        else:
            return False

        if self.event_types and event_type not in self.event_types:
            return False

        # Check filters
        for key, value in self.filters.items():
            event_value = None
            if isinstance(event, BaseEvent):
                event_value = getattr(event, key, None)
            elif isinstance(event, Event):
                event_value = event.data.get(key)

            if event_value != value:
                return False

        return True


class EventBus:
    """
    Central event bus for pub/sub messaging.

    Supports both typed events (BaseEvent subclasses) and generic events.
    """

    def __init__(self):
        """Initialize event bus with Redis pub/sub support."""
        self.redis_manager = get_redis_manager()
        self.local_handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self.subscribed_channels: set[str] = set()
        self.running = False
        self._subscription_task = None

        # Metrics
        self.events_published = 0
        self.events_received = 0
        self.events_processed = 0
        self.events_failed = 0

        logger.info("Event bus initialized")

    async def start(self):
        """Start the event bus and begin processing events."""
        if self.running:
            return

        self.running = True
        logger.info("Event bus started")

        # Start subscription listener for Redis channels
        if self.subscribed_channels:
            self._subscription_task = asyncio.create_task(self._subscription_listener())

    async def stop(self):
        """Stop the event bus."""
        self.running = False

        if self._subscription_task:
            self._subscription_task.cancel()
            try:
                await self._subscription_task
            except asyncio.CancelledError:
                pass

        logger.info(
            f"Event bus stopped. Stats: published={self.events_published}, "
            f"received={self.events_received}, processed={self.events_processed}, "
            f"failed={self.events_failed}"
        )

    async def publish(self, event: Any, channel: str | None = None) -> int:
        """
        Publish an event to the bus.

        Args:
            event: Event to publish (BaseEvent, Event, or dict)
            channel: Optional channel name (defaults to event type)

        Returns:
            Number of subscribers notified
        """
        try:
            # Determine channel
            if channel is None:
                if isinstance(event, BaseEvent):
                    channel = event.event_type.value
                elif isinstance(event, Event):
                    channel = event.name
                else:
                    channel = "default"

            # Convert event to JSON for Redis
            if isinstance(event, BaseEvent):
                event_json = event.to_json()
            elif isinstance(event, Event):
                event_json = event.to_json()
            else:
                event_json = json.dumps(event)

            # Publish to Redis channel
            subscribers = await self.redis_manager.publish(channel, event_json)

            # Process local handlers immediately
            local_count = await self._process_local_handlers(event, channel)

            self.events_published += 1

            logger.debug(
                f"Published event to channel '{channel}': "
                f"{subscribers} Redis subscribers, {local_count} local handlers"
            )

            return subscribers + local_count

        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            self.events_failed += 1
            raise

    def subscribe(
        self,
        handler: Callable,
        event_types: list[str] = None,
        channels: list[str] = None,
        filters: dict[str, Any] = None,
        priority: int = 0,
    ) -> EventHandler:
        """
        Subscribe a handler to events.

        Args:
            handler: Async or sync function to handle events
            event_types: List of event type names to subscribe to
            channels: List of Redis channels to subscribe to
            filters: Additional filters for events
            priority: Handler priority (higher = earlier execution)

        Returns:
            EventHandler instance
        """
        # Create handler wrapper
        event_handler = EventHandler(handler, event_types, filters, priority)

        # Register for local handling
        all_types = (event_types or []) + (channels or [])
        if not all_types:
            all_types = ["*"]  # Subscribe to all if no types specified

        for event_type in all_types:
            self.local_handlers[event_type].append(event_handler)
            # Sort by priority
            self.local_handlers[event_type].sort(key=lambda h: -h.priority)

        # Note: For persistent Redis pub/sub subscriptions, use RedisEventBus instead.
        # Basic EventBus focuses on local handlers and ephemeral pub/sub
        if channels:
            for channel in channels:
                self.subscribed_channels.add(channel)

        logger.info(f"Registered handler for types: {all_types}")
        return event_handler

    def unsubscribe(self, handler: EventHandler):
        """Unsubscribe a handler from events."""
        for handlers in self.local_handlers.values():
            if handler in handlers:
                handlers.remove(handler)

        logger.info("Handler unsubscribed")

    async def _process_local_handlers(self, event: Any, channel: str) -> int:
        """Process local handlers for an event."""
        handlers_called = 0

        # Get handlers for this channel and wildcard
        handlers = self.local_handlers.get(channel, []) + self.local_handlers.get("*", [])

        for handler in handlers:
            if handler.matches(event):
                try:
                    await handler.handle(event)
                    handlers_called += 1
                    self.events_processed += 1
                except Exception as e:
                    logger.error(f"Handler error: {e}", exc_info=True)
                    self.events_failed += 1

        return handlers_called

    async def _handle_redis_message(self, channel: str, message: str):
        """Handle message received from Redis subscription."""
        try:
            self.events_received += 1

            # Parse message back to event
            try:
                data = json.loads(message)
                if "event_type" in data:
                    # It's a typed event
                    event = BaseEvent.from_json(message)
                else:
                    # It's a generic event
                    event = Event.from_json(message)
            except (json.JSONDecodeError, KeyError, ValueError, AttributeError):
                # Fallback to raw dict
                event = json.loads(message)

            # Process with local handlers
            await self._process_local_handlers(event, channel)

        except Exception as e:
            logger.error(f"Failed to handle Redis message: {e}")
            self.events_failed += 1

    async def _subscription_listener(self):
        """Background task to process subscription messages."""
        logger.info("Subscription listener started")

        while self.running:
            try:
                await asyncio.sleep(0.1)  # Small delay to prevent busy loop
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Subscription listener error: {e}")
                await asyncio.sleep(1)  # Back off on error

    def get_stats(self) -> dict[str, Any]:
        """Get event bus statistics."""
        return {
            "published": self.events_published,
            "received": self.events_received,
            "processed": self.events_processed,
            "failed": self.events_failed,
            "handlers": sum(len(h) for h in self.local_handlers.values()),
            "channels": len(self.subscribed_channels),
        }


# Global event bus instance
_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Get or create the global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


# Decorator for event handlers
def event_handler(
    event_types: list[str] = None,
    channels: list[str] = None,
    filters: dict[str, Any] = None,
    priority: int = 0,
):
    """
    Decorator to register a function as an event handler.

    Usage:
        @event_handler(event_types=[EventType.USER_ACTIVITY_CREATED.value])
        async def handle_activity(event: UserActivityEvent):
            # Process event
            pass
    """

    def decorator(func):
        # Register with global event bus on import
        bus = get_event_bus()
        bus.subscribe(func, event_types, channels, filters, priority)
        return func

    return decorator
