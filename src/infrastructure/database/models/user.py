"""
User model for ReflectAI with Slack integration

Implements user management and profile data storage with support for:
- Slack user integration and metadata
- Profile data storage in JSONB format
- Timezone and activity tracking
- Proper indexing for performance
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, CheckConstraint, DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel


class User(BaseModel):
    """User model with Slack integration and profile management"""

    __tablename__ = "users"
    __table_args__ = (
        # Check constraints from schema
        CheckConstraint("LENGTH(slack_user_id) > 0", name="users_slack_user_id_not_empty"),
        CheckConstraint("LENGTH(team_id) > 0", name="users_team_id_not_empty"),
        # Indexes for performance
        Index("idx_users_slack_user_id", "slack_user_id"),
        Index("idx_users_team_id", "team_id"),
        Index("idx_users_email", "email", postgresql_where="email IS NOT NULL"),
        Index("idx_users_active_last_activity", "is_active", "last_activity_at"),
        Index("idx_users_profile_data_gin", "profile_data", postgresql_using="gin"),
        {"comment": "User accounts with Slack integration and profile data"},
    )

    # Core identification
    slack_user_id: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, comment="Slack user ID for integration"
    )

    email: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True, comment="User email address"
    )

    # Profile information
    display_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Display name for UI"
    )

    real_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="User's real name"
    )

    # Team and workspace
    team_id: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="Slack team/workspace ID"
    )

    # Extended profile data
    profile_data: Mapped[dict[str, Any]] = mapped_column(
        JSON, server_default="{}", nullable=False, comment="Extended profile data in JSONB format"
    )

    # User preferences and settings
    timezone: Mapped[str] = mapped_column(
        String(50), server_default="UTC", nullable=False, comment="User timezone"
    )

    # Status tracking
    is_active: Mapped[bool] = mapped_column(
        Boolean, server_default="true", nullable=False, comment="Whether user account is active"
    )

    last_activity_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Last recorded user activity timestamp"
    )

    # Relationships
    activities = relationship("Activity", back_populates="user", cascade="all, delete-orphan")
    competencies = relationship("Competency", back_populates="user", cascade="all, delete-orphan")
    workflows = relationship("Workflow", back_populates="user", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="user", cascade="all, delete-orphan")
    preferences = relationship(
        "UserPreference", back_populates="user", cascade="all, delete-orphan"
    )
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        """String representation of user"""
        return (
            f"<User("
            f"id={self.id}, "
            f"slack_user_id='{self.slack_user_id}', "
            f"display_name='{self.display_name}', "
            f"team_id='{self.team_id}', "
            f"is_active={self.is_active}"
            f")>"
        )

    def get_display_name_or_fallback(self) -> str:
        """Get display name with fallback to real name or Slack ID"""
        return self.display_name or self.real_name or f"User {self.slack_user_id}"

    def update_last_activity(self) -> None:
        """Update the last activity timestamp to now"""
        self.last_activity_at = datetime.now(UTC)

    def get_profile_value(self, key: str, default: Any = None) -> Any:
        """Get a value from profile_data with fallback"""
        if self.profile_data and isinstance(self.profile_data, dict):
            return self.profile_data.get(key, default)
        return default

    def set_profile_value(self, key: str, value: Any) -> None:
        """Set a value in profile_data"""
        if not isinstance(self.profile_data, dict):
            self.profile_data = {}
        self.profile_data[key] = value

    def is_team_member(self, team_id: str) -> bool:
        """Check if user belongs to specified team"""
        return self.team_id == team_id

    @property
    def profile_summary(self) -> dict[str, Any]:
        """Get summary of user profile for API responses"""
        return {
            "id": str(self.id),
            "slack_user_id": self.slack_user_id,
            "display_name": self.get_display_name_or_fallback(),
            "email": self.email,
            "team_id": self.team_id,
            "timezone": self.timezone,
            "is_active": self.is_active,
            "last_activity_at": self.last_activity_at.isoformat()
            if self.last_activity_at
            else None,
            "created_at": self.created_at.isoformat(),
        }
