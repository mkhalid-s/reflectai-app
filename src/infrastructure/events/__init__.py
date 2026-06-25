"""
Event System Infrastructure for ReflectAI

Redis Stack pub/sub event system for simplified, high-performance event streaming.
Implements 80% complexity reduction vs NATS with <1000 events/hour capacity.
Integrated with Doppler configuration management.

Falls back to basic event bus when Redis dependencies are not available.
"""

# Always available imports
from .event_bus import Event, EventBus, EventHandler, get_event_bus
from .event_types import (
    CacheInvalidationEvent,
    CompetencyAnalysisEvent,
    EventType,
    SlackEvent,
    SystemHealthEvent,
    UserActivityEvent,
    WorkflowEvent,
)

# Initialize basic exports
__all__ = [
    # Core event system
    "EventBus",
    "Event",
    "EventHandler",
    "get_event_bus",
    # Event types
    "EventType",
    "UserActivityEvent",
    "CompetencyAnalysisEvent",
    "WorkflowEvent",
    "CacheInvalidationEvent",
    "SystemHealthEvent",
    "SlackEvent",
]

# Try to import Redis-based components
try:
    from .redis_event_bus import (  # noqa: F401 - Re-exported in __all__
        RedisEvent,
        RedisEventBus,
        RedisEventHandler,
        get_redis_event_bus,
        publish_cache_refresh,
        publish_user_activity_completed,
        publish_user_analysis_completed,
        redis_event_handler,
    )

    __all__.extend(
        [
            # Redis event system
            "RedisEventBus",
            "RedisEvent",
            "RedisEventHandler",
            "get_redis_event_bus",
            "publish_user_activity_completed",
            "publish_user_analysis_completed",
            "publish_cache_refresh",
            "redis_event_handler",
        ]
    )

except ImportError as e:
    import warnings

    warnings.warn(f"Redis event bus not available: {e}. Using basic event bus.", ImportWarning, stacklevel=2)

# NOTE: redis_stack_manager.py was removed as duplicate code
# Use cache/redis_manager.py instead for Redis Stack functionality
