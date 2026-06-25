"""
Storage and Data Management System for ReflectAI

Implements Production
- TimescaleDB for time-series activity data with partitioning and compression
- Redis Stack for intelligent caching and session management
- User profile storage with optimistic locking and synchronization
- Competency data store with historical tracking and trend analysis
- Data validation and quality assurance pipelines
- Cache warming and optimization strategies

Provides comprehensive data layer for ReflectAI competency assessment platform.
"""

from src.infrastructure.cache.redis_manager import RedisManager, get_redis_manager

from .managers import (
    ActivityDataManager,
    CompetencyManager,
    UserProfileManager,
    get_activity_data_manager,
    get_competency_manager,
    get_user_profile_manager,
)
from .models import (
    ActivityData,
    ActivityDataModel,
    CompetencyScore,
    CompetencyScoreModel,
    SessionData,
    UserProfile,
    UserProfileModel,
)
from .storage_integration import (
    IntegratedActivityManager,
    StorageIntegrationManager,
    get_storage_integration_manager,
    initialize_storage_integration,
)
from .timescale_manager import TimescaleManager, get_timescale_manager

# from .validation import (
#     DataValidator, DataQualityChecker, get_data_validator
# )

__all__ = [
    # Data models
    "ActivityData",
    "UserProfile",
    "CompetencyScore",
    "SessionData",
    "ActivityDataModel",
    "UserProfileModel",
    "CompetencyScoreModel",
    # Data managers (legacy)
    "ActivityDataManager",
    "get_activity_data_manager",
    "UserProfileManager",
    "get_user_profile_manager",
    "CompetencyManager",
    "get_competency_manager",
    # Integrated storage managers (new)
    "IntegratedActivityManager",
    "StorageIntegrationManager",
    "get_storage_integration_manager",
    "initialize_storage_integration",
    # Infrastructure managers
    "TimescaleManager",
    "get_timescale_manager",
    "RedisManager",
    "get_redis_manager",
    # Validation - Not implemented yet
    # "DataValidator",
    # "DataQualityChecker",
    # "get_data_validator",
]
