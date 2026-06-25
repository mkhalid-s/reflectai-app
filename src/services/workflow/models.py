"""
Workflow Data Models for ReflectAI

Defines workflow requests, responses, and state management structures.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class WorkflowType(Enum):
    """Types of workflows available."""

    SEQUENTIAL_ANALYSIS = "sequential_analysis"
    PARALLEL_ANALYSIS = "parallel_analysis"
    BATCH_PROCESSING = "batch_processing"
    CONVERSATION = "conversation"
    REPORT_GENERATION = "report_generation"
    COMPETENCY_ASSESSMENT = "competency_assessment"
    INLINE_ANALYSIS = "inline_analysis"
    QUICK_SUMMARY = "quick_summary"


class WorkflowStatus(Enum):
    """Workflow execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


class ActivityType(Enum):
    """Types of activities in workflows (updated for combined agent architecture)."""

    # Combined Agent Activities
    COMBINED_ANALYSIS = "combined_analysis"
    COMBINED_ADVISORY = "combined_advisory"
    CHAT_RESPONSE = "chat_response"

    # Inline Analysis Activities
    ANALYZE_INLINE_CONTENT = "analyze_inline_content"
    ASSESS_CONTENT_COMPETENCIES = "assess_content_competencies"
    FORMAT_INLINE_REPORT = "format_inline_report"
    DELIVER_REPORT = "deliver_report"

    # Quick Summary Activities
    FETCH_SUMMARY_DATA = "fetch_summary_data"
    FORMAT_SLACK_SUMMARY = "format_slack_summary"
    POST_SLACK_MESSAGE = "post_slack_message"

    # Legacy activities (deprecated but kept for backward compatibility)
    ANALYZE_ACTIVITY = "analyze_activity"
    ASSESS_COMPETENCY = "assess_competency"
    GENERATE_ADVICE = "generate_advice"
    SYNTHESIZE_INSIGHTS = "synthesize_insights"
    GENERATE_REPORT = "generate_report"
    CLASSIFY_INTENT = "classify_intent"
    FETCH_CONTEXT = "fetch_context"


@dataclass
class WorkflowContext:
    """Context carried through workflow execution."""

    workflow_id: str
    workflow_type: WorkflowType
    user_id: str
    team_id: str
    correlation_id: str
    conversation_id: str | None = None
    thread_ts: str | None = None
    batch_id: str | None = None
    priority: int = 0  # 0=normal, 1=high

    # Execution context
    started_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)
    search_attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "workflow_id": self.workflow_id,
            "workflow_type": self.workflow_type.value,
            "user_id": self.user_id,
            "team_id": self.team_id,
            "correlation_id": self.correlation_id,
            "conversation_id": self.conversation_id,
            "thread_ts": self.thread_ts,
            "batch_id": self.batch_id,
            "priority": self.priority,
            "started_at": self.started_at.isoformat(),
            "metadata": self.metadata,
            "search_attributes": self.search_attributes,
        }


@dataclass
class WorkflowRequest:
    """Request to start a workflow."""

    workflow_type: WorkflowType
    user_id: str
    team_id: str
    correlation_id: str

    # Input data
    input_data: dict[str, Any] = field(default_factory=dict)

    # Optional context
    conversation_id: str | None = None
    thread_ts: str | None = None
    batch_items: list[dict[str, Any]] | None = None
    priority: int = 0

    # Execution options
    timeout_seconds: int = 300  # 5 minutes default
    retry_policy: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "workflow_type": self.workflow_type.value,
            "user_id": self.user_id,
            "team_id": self.team_id,
            "correlation_id": self.correlation_id,
            "input_data": self.input_data,
            "conversation_id": self.conversation_id,
            "thread_ts": self.thread_ts,
            "batch_items": self.batch_items,
            "priority": self.priority,
            "timeout_seconds": self.timeout_seconds,
            "retry_policy": self.retry_policy,
        }


@dataclass
class WorkflowResponse:
    """Response from workflow execution."""

    workflow_id: str
    workflow_type: WorkflowType
    status: WorkflowStatus

    # Results
    result: dict[str, Any] | None = None
    error: str | None = None

    # Execution details
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    duration_ms: int | None = None

    # Context
    user_id: str = ""
    team_id: str = ""
    correlation_id: str = ""

    # Activity results
    activities_completed: list[str] = field(default_factory=list)
    activities_failed: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "workflow_id": self.workflow_id,
            "workflow_type": self.workflow_type.value,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "user_id": self.user_id,
            "team_id": self.team_id,
            "correlation_id": self.correlation_id,
            "activities_completed": self.activities_completed,
            "activities_failed": self.activities_failed,
        }


@dataclass
class ActivityRequest:
    """Request for an activity within a workflow."""

    activity_type: ActivityType
    input_data: dict[str, Any]
    context: WorkflowContext
    timeout_seconds: int = 60
    retry_attempts: int = 3

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "activity_type": self.activity_type.value,
            "input_data": self.input_data,
            "context": self.context.to_dict(),
            "timeout_seconds": self.timeout_seconds,
            "retry_attempts": self.retry_attempts,
        }


@dataclass
class ActivityResponse:
    """Response from activity execution."""

    activity_type: ActivityType
    success: bool
    result: dict[str, Any] | None = None
    error: str | None = None
    duration_ms: int = 0
    retry_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "activity_type": self.activity_type.value,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "retry_count": self.retry_count,
        }


@dataclass
class BatchItem:
    """Item in a batch processing workflow."""

    item_id: str
    data: dict[str, Any]
    status: WorkflowStatus = WorkflowStatus.PENDING
    result: dict[str, Any] | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "item_id": self.item_id,
            "data": self.data,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
        }
