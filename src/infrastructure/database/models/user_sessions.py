"""
User Sessions model for ReflectAI session management

Implements user session tracking with support for:
- Session data and context storage in JSONB
- Session expiration and lifecycle management
- Activity tracking and session cleanup
- Multiple session types (Slack conversations, etc.)
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, UUID, Boolean, CheckConstraint, DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel


class UserSession(BaseModel):
    """User session tracking and context management"""

    __tablename__ = "user_sessions"
    __table_args__ = (
        # Foreign key constraints
        # Check constraints from schema
        CheckConstraint("LENGTH(session_id) > 0", name="user_sessions_session_id_not_empty"),
        CheckConstraint(
            "expires_at IS NULL OR expires_at > created_at", name="user_sessions_expires_future"
        ),
        # Indexes for performance
        Index("idx_user_sessions_user_id", "user_id"),
        Index("idx_user_sessions_session_id", "session_id"),
        Index(
            "idx_user_sessions_active",
            "is_active",
            "last_activity_at",
            postgresql_where="is_active = true",
        ),
        Index(
            "idx_user_sessions_expires_at", "expires_at", postgresql_where="expires_at IS NOT NULL"
        ),
        {"comment": "User session tracking and context management"},
    )

    # Relationships
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, comment="Reference to user"
    )

    # Session identification
    session_id: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, comment="Unique session identifier"
    )

    session_type: Mapped[str] = mapped_column(
        String(50),
        server_default="slack_conversation",
        nullable=False,
        comment="Type of session (slack_conversation, api_session, etc.)",
    )

    # Session data
    session_data: Mapped[dict[str, Any]] = mapped_column(
        JSON, server_default="{}", nullable=False, comment="Session-specific data and state"
    )

    context_data: Mapped[dict[str, Any]] = mapped_column(
        JSON, server_default="{}", nullable=False, comment="Context information for session"
    )

    # Session status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        server_default="true",
        nullable=False,
        comment="Whether session is currently active",
    )

    # Activity tracking
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default="now()",
        nullable=False,
        comment="Last activity timestamp for session",
    )

    # Expiration
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Session expiration timestamp"
    )

    # Relationships
    user = relationship("User", back_populates="sessions")

    def __repr__(self) -> str:
        """String representation of user session"""
        return (
            f"<UserSession("
            f"id={self.id}, "
            f"user_id={self.user_id}, "
            f"session_id='{self.session_id}', "
            f"type='{self.session_type}', "
            f"active={self.is_active}"
            f")>"
        )

    def is_expired(self) -> bool:
        """Check if session has expired"""
        if not self.expires_at:
            return False
        return datetime.now(UTC) > self.expires_at.replace(tzinfo=None)

    def is_valid(self) -> bool:
        """Check if session is valid (active and not expired)"""
        return self.is_active and not self.is_expired()

    def get_age_seconds(self) -> float:
        """Get session age in seconds"""
        return (datetime.now(UTC) - self.created_at.replace(tzinfo=None)).total_seconds()

    def get_inactive_seconds(self) -> float:
        """Get seconds since last activity"""
        return (datetime.now(UTC) - self.last_activity_at.replace(tzinfo=None)).total_seconds()

    def update_activity(self) -> None:
        """Update last activity timestamp"""
        self.last_activity_at = datetime.now(UTC)

    def activate(self) -> None:
        """Activate session and update activity"""
        self.is_active = True
        self.update_activity()

    def deactivate(self) -> None:
        """Deactivate session"""
        self.is_active = False

    def extend_expiration(self, hours: int = 24) -> None:
        """Extend session expiration by specified hours"""
        from datetime import UTC, timedelta

        self.expires_at = datetime.now(UTC) + timedelta(hours=hours)

    def set_expiration(self, expires_at: datetime) -> None:
        """Set specific expiration time"""
        self.expires_at = expires_at

    def get_session_data_value(self, key: str, default: Any = None) -> Any:
        """Get a value from session_data"""
        if self.session_data and isinstance(self.session_data, dict):
            return self.session_data.get(key, default)
        return default

    def set_session_data_value(self, key: str, value: Any) -> None:
        """Set a value in session_data"""
        if not isinstance(self.session_data, dict):
            self.session_data = {}
        self.session_data[key] = value

    def get_context_data_value(self, key: str, default: Any = None) -> Any:
        """Get a value from context_data"""
        if self.context_data and isinstance(self.context_data, dict):
            return self.context_data.get(key, default)
        return default

    def set_context_data_value(self, key: str, value: Any) -> None:
        """Set a value in context_data"""
        if not isinstance(self.context_data, dict):
            self.context_data = {}
        self.context_data[key] = value

    def clear_session_data(self) -> None:
        """Clear all session data"""
        self.session_data = {}

    def clear_context_data(self) -> None:
        """Clear all context data"""
        self.context_data = {}

    def get_conversation_context(self) -> dict[str, Any] | None:
        """Get conversation context for Slack sessions"""
        if self.session_type == "slack_conversation":
            return {
                "channel_id": self.get_context_data_value("channel_id"),
                "thread_ts": self.get_context_data_value("thread_ts"),
                "last_message_ts": self.get_context_data_value("last_message_ts"),
                "conversation_state": self.get_session_data_value("conversation_state"),
                "topics": self.get_session_data_value("topics", []),
            }
        return None

    def update_conversation_context(self, **kwargs) -> None:
        """Update conversation context for Slack sessions"""
        if self.session_type == "slack_conversation":
            for key, value in kwargs.items():
                if key in ["channel_id", "thread_ts", "last_message_ts"]:
                    self.set_context_data_value(key, value)
                elif key in ["conversation_state", "topics"]:
                    self.set_session_data_value(key, value)

    def should_cleanup(self, inactive_hours: int = 48) -> bool:
        """Check if session should be cleaned up"""
        if not self.is_active or self.is_expired():
            return True

        # Check if inactive for too long
        inactive_seconds = self.get_inactive_seconds()
        return inactive_seconds > (inactive_hours * 3600)

    def get_duration_info(self) -> dict[str, Any]:
        """Get session duration and timing information"""
        return {
            "age_seconds": self.get_age_seconds(),
            "age_hours": self.get_age_seconds() / 3600,
            "inactive_seconds": self.get_inactive_seconds(),
            "inactive_minutes": self.get_inactive_seconds() / 60,
            "is_expired": self.is_expired(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "should_cleanup": self.should_cleanup(),
        }

    @property
    def summary(self) -> dict[str, Any]:
        """Get session summary for API responses"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "session_id": self.session_id,
            "session_type": self.session_type,
            "is_active": self.is_active,
            "is_valid": self.is_valid(),
            "last_activity_at": self.last_activity_at.isoformat(),
            "duration_info": self.get_duration_info(),
            "conversation_context": self.get_conversation_context(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
