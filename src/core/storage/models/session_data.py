"""
Session Data Models for ReflectAI Storage

Implements session and conversation data structures with:
- Session management with TTL support
- Conversation message tracking
- Thread mapping for Slack integration
- Context preservation across interactions

Provides comprehensive session modeling for conversational AI.
"""

import uuid
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from pydantic import UUID4, BaseModel, Field, validator


class MessageRole(Enum):
    """Role of message sender"""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"
    ERROR = "error"


class SessionStatus(Enum):
    """Session status"""

    ACTIVE = "active"
    IDLE = "idle"
    EXPIRED = "expired"
    COMPLETED = "completed"
    ERROR = "error"


class ConversationMessage(BaseModel):
    """Individual message in a conversation"""

    message_id: UUID4 = Field(default_factory=uuid.uuid4, description="Message identifier")
    role: MessageRole = Field(..., description="Message sender role")
    content: str = Field(..., description="Message content")

    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message timestamp")
    user_id: UUID4 | None = Field(None, description="User ID if from user")
    agent_id: str | None = Field(None, description="Agent ID if from assistant")

    # Slack integration
    slack_ts: str | None = Field(None, description="Slack timestamp")
    slack_channel: str | None = Field(None, description="Slack channel")
    slack_thread_ts: str | None = Field(None, description="Slack thread timestamp")

    # Processing metadata
    tokens_used: int | None = Field(None, description="Tokens consumed")
    processing_time_ms: int | None = Field(None, description="Processing time in milliseconds")
    model_used: str | None = Field(None, description="LLM model used")

    # Tool usage
    tool_calls: list[dict[str, Any]] = Field(default_factory=list, description="Tool calls made")
    tool_results: list[dict[str, Any]] = Field(default_factory=list, description="Tool results")

    # Error tracking
    error_type: str | None = Field(None, description="Error type if any")
    error_message: str | None = Field(None, description="Error message if any")
    retry_count: int = Field(default=0, description="Number of retries")

    # Additional context
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    attachments: list[str] = Field(default_factory=list, description="Attachment URLs")

    @validator("role")
    def validate_user_id_consistency(cls, v, values):
        """Ensure user_id is set for user messages"""
        if v == MessageRole.USER and not values.get("user_id"):
            raise ValueError("user_id required for USER role messages")
        return v


class SessionContext(BaseModel):
    """Context maintained across a session"""

    # User context
    user_profile: dict[str, Any] = Field(default_factory=dict, description="User profile snapshot")
    user_preferences: dict[str, Any] = Field(default_factory=dict, description="User preferences")

    # Conversation context
    current_topic: str | None = Field(None, description="Current conversation topic")
    topics_discussed: list[str] = Field(default_factory=list, description="Topics covered")
    entities_mentioned: dict[str, list[str]] = Field(
        default_factory=dict, description="Named entities"
    )

    # Analysis context
    detected_intents: list[str] = Field(default_factory=list, description="Detected user intents")
    sentiment_scores: list[float] = Field(default_factory=list, description="Sentiment scores")
    competencies_discussed: list[str] = Field(
        default_factory=list, description="Competencies mentioned"
    )

    # Agent state
    active_agents: list[str] = Field(default_factory=list, description="Active agent IDs")
    agent_memories: dict[str, Any] = Field(
        default_factory=dict, description="Agent-specific memory"
    )
    workflow_state: str | None = Field(None, description="Current workflow state")

    # Task tracking
    pending_tasks: list[dict[str, Any]] = Field(default_factory=list, description="Pending tasks")
    completed_tasks: list[dict[str, Any]] = Field(
        default_factory=list, description="Completed tasks"
    )

    # Custom context
    custom_data: dict[str, Any] = Field(default_factory=dict, description="Custom context data")

    def update_from_message(self, message: ConversationMessage) -> None:
        """Update context based on new message"""
        # This would contain logic to update context based on message content
        pass


class ThreadMapping(BaseModel):
    """Mapping between Slack threads and sessions"""

    thread_id: str = Field(..., description="Slack thread timestamp")
    channel_id: str = Field(..., description="Slack channel ID")
    session_id: UUID4 = Field(..., description="ReflectAI session ID")

    # Thread metadata
    parent_message_ts: str | None = Field(None, description="Parent message timestamp")
    thread_started: datetime = Field(
        default_factory=datetime.utcnow, description="Thread start time"
    )
    last_activity: datetime = Field(
        default_factory=datetime.utcnow, description="Last activity time"
    )

    # Participants
    participants: list[str] = Field(default_factory=list, description="Thread participants")
    message_count: int = Field(default=0, description="Number of messages")

    # Status
    is_active: bool = Field(default=True, description="Thread active status")
    closed_reason: str | None = Field(None, description="Reason for closing")


class SessionData(BaseModel):
    """Core session data model"""

    # Identifiers
    session_id: UUID4 = Field(default_factory=uuid.uuid4, description="Session identifier")
    user_id: UUID4 = Field(..., description="User identifier")
    workspace_id: str | None = Field(None, description="Slack workspace ID")

    # Session lifecycle
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Session creation time"
    )
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update time")
    expires_at: datetime | None = Field(None, description="Session expiration time")
    status: SessionStatus = Field(default=SessionStatus.ACTIVE, description="Session status")

    # Conversation data
    messages: list[ConversationMessage] = Field(
        default_factory=list, description="Conversation messages"
    )
    message_count: int = Field(default=0, description="Total message count")
    turn_count: int = Field(default=0, description="Conversation turns")

    # Context
    context: SessionContext = Field(default_factory=SessionContext, description="Session context")

    # Thread mappings
    thread_mappings: list[ThreadMapping] = Field(
        default_factory=list, description="Slack thread mappings"
    )
    primary_thread: str | None = Field(None, description="Primary Slack thread")

    # Analytics
    total_tokens: int = Field(default=0, description="Total tokens used")
    total_cost: float = Field(default=0.0, description="Total cost in USD")
    average_response_time: float | None = Field(
        None, description="Average response time in seconds"
    )

    # Quality metrics
    user_satisfaction: float | None = Field(
        None, ge=0.0, le=1.0, description="User satisfaction score"
    )
    resolution_status: str | None = Field(None, description="Issue resolution status")
    escalated: bool = Field(default=False, description="Whether session was escalated")

    # Metadata
    session_type: str = Field(default="chat", description="Type of session")
    channel_type: str = Field(default="slack", description="Communication channel")
    tags: list[str] = Field(default_factory=list, description="Session tags")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    def add_message(self, message: ConversationMessage) -> None:
        """Add a message to the session"""
        self.messages.append(message)
        self.message_count += 1
        self.updated_at = datetime.now(UTC)

        # Update turn count for user messages
        if message.role == MessageRole.USER:
            self.turn_count += 1

        # Update token count
        if message.tokens_used:
            self.total_tokens += message.tokens_used

        # Update context
        self.context.update_from_message(message)

    def calculate_ttl(self) -> timedelta:
        """Calculate time-to-live for session"""
        if self.status == SessionStatus.ACTIVE:
            return timedelta(hours=24)
        elif self.status == SessionStatus.IDLE:
            return timedelta(hours=4)
        else:
            return timedelta(days=7)

    def should_expire(self) -> bool:
        """Check if session should expire"""
        if self.expires_at and datetime.now(UTC) > self.expires_at:
            return True

        idle_threshold = timedelta(hours=1)
        if datetime.now(UTC) - self.updated_at > idle_threshold:
            self.status = SessionStatus.IDLE

        return False


class SessionDataModel(BaseModel):
    """Database model for sessions"""

    id: UUID4 = Field(default_factory=uuid.uuid4, description="Database record ID")
    session_id: UUID4 = Field(..., description="Session identifier")
    session_data: SessionData = Field(..., description="Session data")

    # Indexing and search
    search_vector: str | None = Field(None, description="Full-text search vector")
    indexed_at: datetime | None = Field(None, description="Last indexing timestamp")

    # Archival
    archived: bool = Field(default=False, description="Archive status")
    archived_at: datetime | None = Field(None, description="Archive timestamp")
    archive_reason: str | None = Field(None, description="Reason for archiving")

    # Data retention
    retention_policy: str = Field(default="standard", description="Retention policy")
    deletion_scheduled: datetime | None = Field(None, description="Scheduled deletion date")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat(), UUID4: lambda v: str(v)}
