"""
User Preferences model for ReflectAI user configuration

Implements user preference storage with support for:
- Categorized preference management
- JSONB storage for flexible preference values
- Active/inactive preference tracking
- Unique constraints per user/category/key
"""

import uuid
from typing import Any

from sqlalchemy import JSON, UUID, Boolean, CheckConstraint, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel


class UserPreference(BaseModel):
    """User preferences and configuration settings"""

    __tablename__ = "user_preferences"
    __table_args__ = (
        # Foreign key constraints
        # Check constraints from schema
        CheckConstraint(
            "LENGTH(preference_category) > 0", name="user_preferences_category_not_empty"
        ),
        CheckConstraint("LENGTH(preference_key) > 0", name="user_preferences_key_not_empty"),
        # Unique constraint
        CheckConstraint(
            "user_id IS NOT NULL AND preference_category IS NOT NULL AND preference_key IS NOT NULL",
            name="user_preferences_unique",
        ),
        # Indexes for performance
        Index("idx_user_preferences_user_id", "user_id"),
        Index("idx_user_preferences_category", "preference_category"),
        Index("idx_user_preferences_active", "is_active", postgresql_where="is_active = true"),
        {"comment": "User preferences and configuration settings"},
    )

    # Relationships
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, comment="Reference to user"
    )

    # Preference identification
    preference_category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Category of preference (notifications, reports, ui, etc.)",
    )

    preference_key: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="Specific preference key within category"
    )

    # Preference value
    preference_value: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, comment="Preference value stored as JSONB"
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        server_default="true",
        nullable=False,
        comment="Whether preference is currently active",
    )

    # Relationships
    user = relationship("User", back_populates="preferences")

    def __repr__(self) -> str:
        """String representation of user preference"""
        return (
            f"<UserPreference("
            f"id={self.id}, "
            f"user_id={self.user_id}, "
            f"category='{self.preference_category}', "
            f"key='{self.preference_key}', "
            f"active={self.is_active}"
            f")>"
        )

    def get_value(self, default: Any = None) -> Any:
        """Get the preference value with optional default"""
        return self.preference_value if self.preference_value is not None else default

    def set_value(self, value: Any) -> None:
        """Set the preference value"""
        self.preference_value = value

    def get_nested_value(self, *keys, default: Any = None) -> Any:
        """Get a nested value from the preference JSONB"""
        current = self.preference_value

        if not isinstance(current, dict):
            return default

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default

        return current

    def set_nested_value(self, *keys, value: Any) -> None:
        """Set a nested value in the preference JSONB"""
        if not isinstance(self.preference_value, dict):
            self.preference_value = {}

        current = self.preference_value

        # Navigate to the parent of the target key
        for key in keys[:-1]:
            if key not in current or not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]

        # Set the final value
        current[keys[-1]] = value

    def activate(self) -> None:
        """Activate this preference"""
        self.is_active = True

    def deactivate(self) -> None:
        """Deactivate this preference"""
        self.is_active = False

    def get_full_key(self) -> str:
        """Get the full preference key as category.key"""
        return f"{self.preference_category}.{self.preference_key}"

    @property
    def summary(self) -> dict[str, Any]:
        """Get preference summary for API responses"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "category": self.preference_category,
            "key": self.preference_key,
            "full_key": self.get_full_key(),
            "value": self.preference_value,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
