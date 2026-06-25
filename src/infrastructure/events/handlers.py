"""
Built-in Event Handlers for ReflectAI System Events

Provides default handlers for system events like cache invalidation,
health monitoring, and activity tracking.
"""

import json
from datetime import UTC, datetime

from src.infrastructure.cache.redis_manager import get_redis_manager
from src.infrastructure.database.db_manager import get_database_manager
from src.shared.logging import get_logger

from .event_bus import event_handler, get_event_bus
from .event_types import (
    BaseEvent,
    CacheInvalidationEvent,
    CompetencyAnalysisEvent,
    EventType,
    SlackEvent,
    SystemHealthEvent,
    UserActivityEvent,
    WorkflowEvent,
)

logger = get_logger(__name__)


# Cache invalidation handlers
@event_handler(event_types=[EventType.CACHE_INVALIDATED.value], priority=10)
async def handle_cache_invalidation(event: CacheInvalidationEvent):
    """Handle cache invalidation events."""
    try:
        redis_manager = get_redis_manager()
        invalidated_count = 0

        # Invalidate specific keys (keys should include namespace prefix)
        for full_key in event.cache_keys:
            # Parse namespace from key (format: namespace:key)
            if ":" in full_key:
                namespace, key = full_key.split(":", 1)
                if await redis_manager.delete(namespace, key):
                    invalidated_count += 1
            else:
                logger.warning(f"Invalid cache key format (missing namespace): {full_key}")

        # Invalidate by pattern
        for pattern in event.cache_patterns:
            # Pattern format: namespace:pattern
            if ":" in pattern:
                namespace, key_pattern = pattern.split(":", 1)
                deleted = await redis_manager.delete_pattern(namespace, key_pattern)
                invalidated_count += deleted
            else:
                logger.warning(f"Invalid cache pattern format (missing namespace): {pattern}")

        # Flush all if requested
        if event.invalidate_all:
            await redis_manager.clear_all()
            logger.info(f"Cache flushed completely. Reason: {event.reason}")
        else:
            logger.info(f"Cache invalidated {invalidated_count} keys. Reason: {event.reason}")

    except Exception as e:
        logger.error(f"Cache invalidation failed: {e}")


@event_handler(event_types=[EventType.HOME_TAB_UPDATE_REQUIRED.value], priority=5)
async def handle_home_tab_update(event: CacheInvalidationEvent):
    """Handle home tab cache updates."""
    try:
        redis_manager = get_redis_manager()

        # Extract user and team from cache keys
        for full_key in event.cache_keys:
            # Key format: home_tab:team_id:user_id or home_tab:key
            if full_key.startswith("home_tab:"):
                # Remove namespace prefix
                key_without_ns = full_key[9:]  # Remove "home_tab:"

                # Invalidate the home tab cache
                await redis_manager.delete("home_tab", key_without_ns)

                # Parse team_id and user_id for logging
                parts = key_without_ns.split(":")
                if len(parts) >= 2:
                    team_id = parts[0]
                    user_id = parts[1]
                    logger.info(f"Home tab cache invalidated for user {user_id} in team {team_id}")
                else:
                    logger.info(f"Home tab cache invalidated: {key_without_ns}")

    except Exception as e:
        logger.error(f"Home tab update failed: {e}")


# Activity tracking handlers
@event_handler(event_types=[EventType.USER_ACTIVITY_CREATED.value])
async def handle_activity_created(event: UserActivityEvent):
    """Handle new user activity events."""
    try:
        # Store activity in database
        db = get_database_manager()
        activity_data = {
            "user_id": event.user_id,
            "team_id": event.team_id,
            "activity_type": event.activity_type,
            "data": event.activity_data,
            "created_at": event.timestamp.isoformat(),
        }

        activity_id = await db.insert_activity(activity_data)
        logger.info(f"Activity stored: {activity_id} for user {event.user_id}")

        # Invalidate user's cached data
        redis_manager = get_redis_manager()
        await redis_manager.delete("user", f"profile:{event.user_id}")

        # Publish analysis request
        bus = get_event_bus()
        analysis_event = UserActivityEvent(
            event_type=EventType.USER_ACTIVITY_ANALYZED,
            correlation_id=event.correlation_id,
            user_id=event.user_id,
            team_id=event.team_id,
            activity_id=activity_id,
            activity_type=event.activity_type,
            activity_data=event.activity_data,
        )
        await bus.publish(analysis_event)

    except Exception as e:
        logger.error(f"Failed to handle activity creation: {e}")


@event_handler(event_types=[EventType.USER_ACTIVITY_ANALYZED.value])
async def trigger_competency_calculation(event: UserActivityEvent):
    """Trigger competency calculation after activity analysis."""
    try:
        # This would normally trigger the competency engine
        logger.info(f"Triggering competency calculation for activity {event.activity_id}")

        # For now, just log the trigger
        # In production, this will call the actual competency engine

    except Exception as e:
        logger.error(f"Failed to trigger competency calculation: {e}")


# Workflow tracking handlers
@event_handler(
    event_types=[
        EventType.WORKFLOW_STARTED.value,
        EventType.WORKFLOW_COMPLETED.value,
        EventType.WORKFLOW_FAILED.value,
    ]
)
async def handle_workflow_events(event: WorkflowEvent):
    """Track workflow execution events."""
    try:
        db = get_database_manager()

        # Store workflow event
        event_data = {
            "event_type": event.event_type.value,
            "workflow_id": event.workflow_id,
            "workflow_type": event.workflow_type,
            "status": event.status,
            "data": {
                "step_name": event.step_name,
                "result": event.result,
                "error": event.error,
                "execution_time_ms": event.execution_time_ms,
            },
            "correlation_id": event.correlation_id,
            "created_at": event.timestamp.isoformat(),
        }

        await db.insert_event(event_data)

        # Update metrics
        if event.event_type == EventType.WORKFLOW_COMPLETED:
            logger.info(f"Workflow {event.workflow_id} completed in {event.execution_time_ms}ms")
        elif event.event_type == EventType.WORKFLOW_FAILED:
            logger.error(f"Workflow {event.workflow_id} failed: {event.error}")

    except Exception as e:
        logger.error(f"Failed to handle workflow event: {e}")


# System health monitoring
@event_handler(event_types=[EventType.SYSTEM_HEALTH_CHECK.value])
async def monitor_system_health(event: SystemHealthEvent):
    """Monitor system health events."""
    try:
        # Log health status
        if event.status == "unhealthy":
            logger.error(f"Component {event.component} is unhealthy: {event.message}")
        elif event.status == "degraded":
            logger.warning(f"Component {event.component} is degraded: {event.message}")
        else:
            logger.debug(f"Component {event.component} is healthy")

        # Store critical health events
        if event.status in ["unhealthy", "degraded"]:
            db = get_database_manager()
            health_data = {
                "event_type": "system.health",
                "data": {
                    "component": event.component,
                    "status": event.status,
                    "metrics": event.metrics,
                    "checks": event.checks,
                    "message": event.message,
                },
                "correlation_id": event.correlation_id,
                "created_at": event.timestamp.isoformat(),
            }
            await db.insert_event(health_data)

    except Exception as e:
        logger.error(f"Failed to monitor health: {e}")


# Slack event handlers
@event_handler(event_types=[EventType.SLACK_MESSAGE_RECEIVED.value])
async def handle_slack_message(event: SlackEvent):
    """Process incoming Slack messages."""
    try:
        logger.info(f"Slack message from {event.user_id}: {event.text[:50]}...")

        # Check for duplicate processing (deduplication)
        redis_manager = get_redis_manager()
        dedup_key = f"dedup:{event.event_ts}"

        existing_dedup = await redis_manager.get("slack", dedup_key)
        if existing_dedup:
            logger.debug(f"Duplicate Slack event {event.event_ts}, skipping")
            return

        # Mark as processed (with 5 minute TTL)
        await redis_manager.set("slack", dedup_key, "1", ttl_override=300)

        # Store message for context
        thread_key = f"thread:{event.team_id}:{event.channel_id}:{event.thread_ts or event.event_ts}"
        thread_data = {"user_id": event.user_id, "text": event.text, "timestamp": event.event_ts}

        # Append to thread context
        existing = await redis_manager.get("slack", thread_key)
        if existing:
            thread_context = json.loads(str(existing))
            thread_context["messages"].append(thread_data)
        else:
            thread_context = {"messages": [thread_data]}

        await redis_manager.set("slack", thread_key, thread_context, ttl_override=3600)  # 1 hour TTL

        # This would trigger intent classification and workflow routing
        # For now, just log it
        logger.info(f"Slack message stored in thread context: slack:{thread_key}")

    except Exception as e:
        logger.error(f"Failed to handle Slack message: {e}")


# Competency milestone notifications
@event_handler(event_types=[EventType.COMPETENCY_MILESTONE_REACHED.value])
async def notify_competency_milestone(event: CompetencyAnalysisEvent):
    """Notify users of competency milestones."""
    try:
        logger.info(
            f"User {event.user_id} reached milestone in {event.competency_name}: {event.score}"
        )

        # Invalidate home tab cache to show update
        bus = get_event_bus()

        # Get team_id from user data (would normally query database)
        team_id = event.metadata.get("team_id", "unknown")

        # Build home tab cache key (format: home_tab:team_id:user_id)
        home_tab_key = f"home_tab:{team_id}:{event.user_id}"

        invalidation_event = CacheInvalidationEvent(
            event_type=EventType.HOME_TAB_UPDATE_REQUIRED,
            correlation_id=event.correlation_id,
            cache_keys=[home_tab_key],
            reason=f"Competency milestone reached: {event.competency_name}",
        )

        await bus.publish(invalidation_event)

    except Exception as e:
        logger.error(f"Failed to notify milestone: {e}")


# Performance monitoring
@event_handler(event_types=[EventType.LLM_REQUEST_COMPLETED.value])
async def track_llm_usage(event: BaseEvent):
    """Track LLM usage for cost monitoring."""
    try:
        # Extract metrics from event
        tokens = event.metadata.get("tokens_used", 0)
        cost = event.metadata.get("cost_usd", 0.0)
        model = event.metadata.get("model", "unknown")
        duration_ms = event.metadata.get("duration_ms", 0)

        # Update daily usage metrics in cache
        redis_manager = get_redis_manager()
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        metrics_key = f"metrics:{today}"

        # Get existing metrics (using regular get/set since RedisManager doesn't expose hgetall/hset)
        existing_data = await redis_manager.get("llm", metrics_key)
        if existing_data:
            existing = existing_data if isinstance(existing_data, dict) else {}
        else:
            existing = {}

        # Update metrics
        total_tokens = int(existing.get("tokens", 0)) + tokens
        total_cost = float(existing.get("cost", 0.0)) + cost
        total_requests = int(existing.get("requests", 0)) + 1

        # Build updated metrics dict
        updated_metrics = {
            "tokens": total_tokens,
            "cost": total_cost,
            "requests": total_requests,
            f"model_{model}": int(existing.get(f"model_{model}", 0)) + 1,
        }

        # Store updated metrics with 30-day TTL
        await redis_manager.set("llm", metrics_key, updated_metrics, ttl_override=2592000)

        logger.debug(f"LLM usage tracked: {tokens} tokens, ${cost:.4f}, {duration_ms}ms")

    except Exception as e:
        logger.error(f"Failed to track LLM usage: {e}")


async def initialize_event_handlers():
    """Initialize all event handlers and start the event bus."""
    bus = get_event_bus()
    await bus.start()

    logger.info(f"Event handlers initialized. Active handlers: {bus.get_stats()['handlers']}")

    # Publish initial health check
    health_event = SystemHealthEvent(
        event_type=EventType.SYSTEM_HEALTH_CHECK,
        correlation_id=f"startup-{datetime.now(UTC).isoformat()}",
        component="event_system",
        status="healthy",
        message="Event system initialized",
    )

    await bus.publish(health_event)
