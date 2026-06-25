"""
Event Type Definitions for ReflectAI Event System

Defines all event types used throughout the application for
inter-component communication via pub/sub pattern.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class EventType(Enum):
    """Enumeration of all event types in the system."""

    # User activity events
    USER_ACTIVITY_CREATED = "user.activity.created"
    USER_ACTIVITY_UPDATED = "user.activity.updated"
    USER_ACTIVITY_ANALYZED = "user.activity.analyzed"

    # Competency events
    COMPETENCY_CALCULATED = "competency.calculated"
    COMPETENCY_UPDATED = "competency.updated"
    COMPETENCY_MILESTONE_REACHED = "competency.milestone"

    # Workflow events
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_FAILED = "workflow.failed"
    WORKFLOW_STEP_COMPLETED = "workflow.step.completed"

    # Cache events
    CACHE_INVALIDATED = "cache.invalidated"
    CACHE_WARMED = "cache.warmed"
    HOME_TAB_UPDATE_REQUIRED = "cache.home_tab.update"

    # System health events
    SYSTEM_HEALTH_CHECK = "system.health.check"
    SYSTEM_ERROR = "system.error"
    SYSTEM_WARNING = "system.warning"
    SYSTEM_METRIC = "system.metric"

    # Slack events
    SLACK_MESSAGE_RECEIVED = "slack.message.received"
    SLACK_APP_MENTION = "slack.app.mention"
    SLACK_COMMAND_EXECUTED = "slack.command.executed"
    SLACK_HOME_OPENED = "slack.home.opened"
    SLACK_INTERACTION = "slack.interaction"

    # Agent events
    AGENT_STARTED = "agent.started"
    AGENT_COMPLETED = "agent.completed"
    AGENT_FAILED = "agent.failed"

    # LLM events
    LLM_REQUEST_STARTED = "llm.request.started"
    LLM_REQUEST_COMPLETED = "llm.request.completed"
    LLM_REQUEST_FAILED = "llm.request.failed"


@dataclass
class BaseEvent:
    """Base class for all events."""

    event_type: EventType
    correlation_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source: str = "system"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        """Serialize event to JSON string."""
        data = {
            "event_type": self.event_type.value,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "metadata": self.metadata,
            "payload": self.get_payload(),
        }
        return json.dumps(data)

    def get_payload(self) -> dict[str, Any]:
        """Get event-specific payload. Override in subclasses."""
        return {}

    @classmethod
    def from_json(cls, json_str: str) -> "BaseEvent":
        """Deserialize event from JSON string."""
        data = json.loads(json_str)
        return cls(
            event_type=EventType(data["event_type"]),
            correlation_id=data["correlation_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            source=data.get("source", "system"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class UserActivityEvent(BaseEvent):
    """Event for user activity actions."""

    user_id: str = ""
    team_id: str = ""
    activity_id: str = ""
    activity_type: str = ""
    activity_data: dict[str, Any] = field(default_factory=dict)

    def get_payload(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "team_id": self.team_id,
            "activity_id": self.activity_id,
            "activity_type": self.activity_type,
            "activity_data": self.activity_data,
        }


@dataclass
class CompetencyAnalysisEvent(BaseEvent):
    """Event for competency analysis results."""

    user_id: str = ""
    competency_id: str = ""
    competency_name: str = ""
    score: float = 0.0
    confidence: float = 0.0
    evidence: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def get_payload(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "competency_id": self.competency_id,
            "competency_name": self.competency_name,
            "score": self.score,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "recommendations": self.recommendations,
        }


@dataclass
class WorkflowEvent(BaseEvent):
    """Event for workflow state changes."""

    workflow_id: str = ""
    workflow_type: str = ""
    step_name: str = ""
    status: str = ""
    result: dict[str, Any] | None = None
    error: str | None = None
    execution_time_ms: int = 0

    def get_payload(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "workflow_type": self.workflow_type,
            "step_name": self.step_name,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
        }


@dataclass
class CacheInvalidationEvent(BaseEvent):
    """Event for cache invalidation notifications."""

    cache_keys: list[str] = field(default_factory=list)
    cache_patterns: list[str] = field(default_factory=list)
    reason: str = ""
    invalidate_all: bool = False

    def get_payload(self) -> dict[str, Any]:
        return {
            "cache_keys": self.cache_keys,
            "cache_patterns": self.cache_patterns,
            "reason": self.reason,
            "invalidate_all": self.invalidate_all,
        }


@dataclass
class SystemHealthEvent(BaseEvent):
    """Event for system health and monitoring."""

    component: str = ""
    status: str = "healthy"  # healthy, degraded, unhealthy
    metrics: dict[str, float] = field(default_factory=dict)
    checks: dict[str, bool] = field(default_factory=dict)
    message: str = ""

    def get_payload(self) -> dict[str, Any]:
        return {
            "component": self.component,
            "status": self.status,
            "metrics": self.metrics,
            "checks": self.checks,
            "message": self.message,
        }


@dataclass
class SlackEvent(BaseEvent):
    """Event for Slack interactions."""

    team_id: str = ""
    user_id: str = ""
    channel_id: str = ""
    thread_ts: str | None = None
    event_ts: str = ""
    slack_event_type: str = ""  # message, app_mention, command, etc.
    text: str = ""
    slack_metadata: dict[str, Any] = field(default_factory=dict)

    def get_payload(self) -> dict[str, Any]:
        return {
            "team_id": self.team_id,
            "user_id": self.user_id,
            "channel_id": self.channel_id,
            "thread_ts": self.thread_ts,
            "event_ts": self.event_ts,
            "slack_event_type": self.slack_event_type,
            "text": self.text,
            "slack_metadata": self.slack_metadata,
        }


# Event creation helpers
def create_activity_event(
    user_id: str,
    team_id: str,
    activity_type: str,
    activity_data: dict[str, Any],
    correlation_id: str,
) -> UserActivityEvent:
    """Helper to create user activity event."""
    return UserActivityEvent(
        event_type=EventType.USER_ACTIVITY_CREATED,
        correlation_id=correlation_id,
        user_id=user_id,
        team_id=team_id,
        activity_type=activity_type,
        activity_data=activity_data,
        source="activity_tracker",
    )


def create_workflow_event(
    workflow_id: str, workflow_type: str, status: str, correlation_id: str, **kwargs
) -> WorkflowEvent:
    """Helper to create workflow event."""
    event_type_map = {
        "started": EventType.WORKFLOW_STARTED,
        "completed": EventType.WORKFLOW_COMPLETED,
        "failed": EventType.WORKFLOW_FAILED,
        "step_completed": EventType.WORKFLOW_STEP_COMPLETED,
    }

    return WorkflowEvent(
        event_type=event_type_map.get(status, EventType.WORKFLOW_STARTED),
        correlation_id=correlation_id,
        workflow_id=workflow_id,
        workflow_type=workflow_type,
        status=status,
        source="temporal_worker",
        **kwargs,
    )


def create_cache_invalidation_event(
    keys: list[str] | None = None,
    patterns: list[str] | None = None,
    reason: str = "",
    correlation_id: str = "",
) -> CacheInvalidationEvent:
    """Helper to create cache invalidation event."""
    return CacheInvalidationEvent(
        event_type=EventType.CACHE_INVALIDATED,
        correlation_id=correlation_id,
        cache_keys=keys or [],
        cache_patterns=patterns or [],
        reason=reason,
        source="cache_manager",
    )
