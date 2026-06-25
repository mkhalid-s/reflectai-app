"""
User Profile Models for ReflectAI Storage

Implements user profile data structures with:
- User profile schema with validation and constraints
- User preferences and settings management
- Profile versioning and sync status tracking
- Integration with authentication and authorization

Provides comprehensive user profile modeling for the platform.
"""

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import UUID4, BaseModel, EmailStr, Field, validator


class ProfileSyncStatus(Enum):
    """Status of profile synchronization"""

    SYNCED = "synced"
    PENDING = "pending"
    FAILED = "failed"
    PARTIAL = "partial"


class UserPreferences(BaseModel):
    """User preferences and settings"""

    # Notification preferences
    email_notifications: bool = Field(default=True, description="Enable email notifications")
    slack_notifications: bool = Field(default=True, description="Enable Slack notifications")
    weekly_summary: bool = Field(default=True, description="Receive weekly summaries")
    monthly_report: bool = Field(default=True, description="Receive monthly reports")

    # Display preferences
    theme: str = Field(default="light", description="UI theme preference")
    timezone: str = Field(default="UTC", description="User timezone")
    language: str = Field(default="en", description="Preferred language")
    date_format: str = Field(default="YYYY-MM-DD", description="Preferred date format")

    # Privacy preferences
    profile_visibility: str = Field(default="team", description="Profile visibility level")
    activity_sharing: bool = Field(default=True, description="Share activity with team")
    anonymous_benchmarking: bool = Field(
        default=True, description="Participate in anonymous benchmarking"
    )

    # AI preferences
    ai_suggestions: bool = Field(default=True, description="Enable AI suggestions")
    auto_classification: bool = Field(default=True, description="Auto-classify activities")
    personalized_insights: bool = Field(default=True, description="Generate personalized insights")

    # Custom preferences
    custom_settings: dict[str, Any] = Field(default_factory=dict, description="Custom settings")

    @validator("theme")
    def validate_theme(cls, v):
        allowed_themes = ["light", "dark", "auto"]
        if v not in allowed_themes:
            raise ValueError(f"Theme must be one of {allowed_themes}")
        return v

    @validator("profile_visibility")
    def validate_visibility(cls, v):
        allowed_levels = ["private", "team", "organization", "public"]
        if v not in allowed_levels:
            raise ValueError(f"Visibility must be one of {allowed_levels}")
        return v


class ProfileUpdateResult(BaseModel):
    """Result of profile update operation"""

    success: bool = Field(..., description="Update success status")
    updated_fields: list[str] = Field(default_factory=list, description="Fields that were updated")
    version: int = Field(..., description="New profile version number")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Update timestamp")
    errors: list[str] = Field(default_factory=list, description="Any errors encountered")
    warnings: list[str] = Field(default_factory=list, description="Any warnings generated")


class UserProfile(BaseModel):
    """Core user profile model"""

    # Primary identifiers
    user_id: UUID4 = Field(..., description="Unique user identifier")
    slack_user_id: str = Field(..., description="Slack user ID")
    email: EmailStr = Field(..., description="User email address")

    # Basic information
    full_name: str = Field(..., description="User's full name")
    display_name: str | None = Field(None, description="Display name")
    avatar_url: str | None = Field(None, description="Avatar image URL")

    # Professional information
    title: str | None = Field(None, description="Job title")
    department: str | None = Field(None, description="Department")
    team_id: UUID4 | None = Field(None, description="Primary team identifier")
    manager_id: UUID4 | None = Field(None, description="Manager's user ID")
    location: str | None = Field(None, description="Work location")

    # Employment details
    start_date: datetime | None = Field(None, description="Employment start date")
    employee_id: str | None = Field(None, description="Employee ID")
    employment_type: str | None = Field(
        None, description="Employment type (full-time, contractor, etc)"
    )

    # Skills and competencies
    primary_skills: list[str] = Field(default_factory=list, description="Primary skills")
    secondary_skills: list[str] = Field(default_factory=list, description="Secondary skills")
    certifications: list[str] = Field(
        default_factory=list, description="Professional certifications"
    )
    expertise_areas: list[str] = Field(default_factory=list, description="Areas of expertise")

    # Preferences
    preferences: UserPreferences = Field(
        default_factory=UserPreferences, description="User preferences"
    )

    # Status and metadata
    is_active: bool = Field(default=True, description="Account active status")
    is_admin: bool = Field(default=False, description="Admin privileges")
    last_active: datetime | None = Field(None, description="Last activity timestamp")
    sync_status: ProfileSyncStatus = Field(
        default=ProfileSyncStatus.PENDING, description="Sync status"
    )

    # Versioning
    version: int = Field(default=1, description="Profile version number")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Profile creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )

    # Integration metadata
    slack_metadata: dict[str, Any] = Field(
        default_factory=dict, description="Slack-specific metadata"
    )
    external_ids: dict[str, str] = Field(default_factory=dict, description="External system IDs")

    @validator("employment_type")
    def validate_employment_type(cls, v):
        if v:
            allowed_types = ["full-time", "part-time", "contractor", "intern", "consultant"]
            if v.lower() not in allowed_types:
                raise ValueError(f"Employment type must be one of {allowed_types}")
            return v.lower()
        return v

    def update(self, **kwargs) -> ProfileUpdateResult:
        """Update profile fields"""
        updated_fields = []
        errors = []

        for field, value in kwargs.items():
            if hasattr(self, field):
                try:
                    setattr(self, field, value)
                    updated_fields.append(field)
                except Exception as e:
                    errors.append(f"Failed to update {field}: {str(e)}")

        if updated_fields:
            self.version += 1
            self.updated_at = datetime.now(UTC)

        return ProfileUpdateResult(
            success=len(errors) == 0,
            updated_fields=updated_fields,
            version=self.version,
            errors=errors,
        )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat(), UUID4: lambda v: str(v)}


class UserProfileModel(BaseModel):
    """Database model for user profiles"""

    id: UUID4 = Field(default_factory=uuid.uuid4, description="Database record ID")
    user_id: UUID4 = Field(..., description="User identifier")
    profile_data: UserProfile = Field(..., description="Profile data")

    # Audit fields
    created_by: UUID4 | None = Field(None, description="Created by user")
    updated_by: UUID4 | None = Field(None, description="Last updated by user")
    deleted_at: datetime | None = Field(None, description="Soft delete timestamp")

    # Search and indexing
    search_vector: str | None = Field(None, description="Full-text search vector")
    tags: list[str] = Field(default_factory=list, description="Profile tags for categorization")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat(), UUID4: lambda v: str(v)}
