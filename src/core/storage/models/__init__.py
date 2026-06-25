"""
Data Models for ReflectAI Storage System

Provides Pydantic models and database schemas for:
- Activity data with validation and constraints
- User profiles with versioning support
- Competency scores with historical tracking
- Session data with TTL management
- Data integrity and validation models

Ensures type safety and validation across the storage layer.
"""

from .activity_data import (
    ActivityData,
    ActivityDataModel,
    ActivityMetadata,
    ActivitySource,
    ActivityType,
)
from .competency_data import (
    CompetencyMilestone,
    CompetencyScore,
    CompetencyScoreModel,
    CompetencySnapshot,
    CompetencyTrend,
)
from .session_data import (
    ConversationMessage,
    SessionContext,
    SessionData,
    SessionDataModel,
    ThreadMapping,
)
from .user_profile import (
    ProfileSyncStatus,
    ProfileUpdateResult,
    UserPreferences,
    UserProfile,
    UserProfileModel,
)

__all__ = [
    # Activity models
    "ActivityData",
    "ActivityDataModel",
    "ActivityMetadata",
    "ActivityType",
    "ActivitySource",
    # User profile models
    "UserProfile",
    "UserProfileModel",
    "UserPreferences",
    "ProfileUpdateResult",
    "ProfileSyncStatus",
    # Competency models
    "CompetencyScore",
    "CompetencyScoreModel",
    "CompetencySnapshot",
    "CompetencyTrend",
    "CompetencyMilestone",
    # Session models
    "SessionData",
    "SessionDataModel",
    "ConversationMessage",
    "SessionContext",
    "ThreadMapping",
]
