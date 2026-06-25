"""
Model Conversion Utilities for ReflectAI

Provides centralized conversion utilities between business logic models (Pydantic)
and database models (SQLAlchemy) for consistent data transformation across the system.

Features:
- ActivityData <-> Activity conversions
- UserProfile <-> User conversions
- CompetencyScore <-> Competency conversions
- Standardized conversion patterns
- Error handling and validation
"""

from datetime import UTC, datetime

from src.infrastructure.database.models.activity import Activity
from src.infrastructure.database.models.competency import Competency
from src.infrastructure.database.models.user import User
from src.shared import get_logger

from ..models.activity_data import ActivityData, ActivityStatus, ActivityType
from ..models.competency_data import CompetencyScore
from ..models.user_profile import ProfileSyncStatus, UserProfile

logger = get_logger("storage.model_converters")


class ModelConverter:
    """Centralized model conversion utilities"""

    @staticmethod
    def activity_to_db_model(activity: ActivityData) -> Activity:
        """Convert ActivityData to Activity database model"""
        return Activity(
            id=activity.activity_id,
            user_id=activity.user_id,
            content=activity.description or activity.title,
            activity_type=activity.activity_type.value if activity.activity_type else None,
            activity_status=activity.activity_status.value if activity.activity_status else None,
            occurred_at=activity.occurred_at,
            metadata_=activity.metadata or {},
            created_at=activity.created_at or datetime.now(UTC),
            updated_at=activity.updated_at or datetime.now(UTC),
            version=activity.version or 1,
        )

    @staticmethod
    def db_model_to_activity(db_activity: Activity) -> ActivityData:
        """Convert Activity database model to ActivityData"""
        return ActivityData(
            activity_id=db_activity.id,
            user_id=db_activity.user_id,
            title=db_activity.content[:100] if db_activity.content else "",
            description=db_activity.content,
            activity_type=ActivityType(db_activity.activity_type)
            if db_activity.activity_type
            else None,
            activity_status=ActivityStatus(db_activity.activity_status)
            if db_activity.activity_status
            else None,
            occurred_at=db_activity.occurred_at,
            metadata=db_activity.metadata_ or {},
            created_at=db_activity.created_at,
            updated_at=db_activity.updated_at,
            version=db_activity.version,
        )

    @staticmethod
    def user_profile_to_db_model(profile: UserProfile) -> User:
        """Convert UserProfile to User database model"""
        return User(
            id=profile.user_id,
            profile_id=profile.profile_id,
            team_id=profile.team_id,
            full_name=profile.full_name,
            email=profile.email,
            slack_user_id=profile.slack_user_id,
            role=profile.role,
            department=profile.department,
            manager_id=profile.manager_id,
            preferences=profile.preferences.dict() if profile.preferences else {},
            settings=profile.settings or {},
            sync_status=profile.sync_status.value if profile.sync_status else None,
            metadata_=profile.metadata or {},
            created_at=profile.created_at,
            updated_at=profile.updated_at,
            version=profile.version,
        )

    @staticmethod
    def db_model_to_user_profile(db_user: User) -> UserProfile:
        """Convert User database model to UserProfile"""
        from ..models.user_profile import UserPreferences

        preferences = None
        if db_user.preferences:
            try:
                preferences = UserPreferences(**db_user.preferences)
            except Exception as e:
                logger.warning(f"Failed to convert preferences: {e}")

        sync_status = None
        if db_user.sync_status:
            try:
                sync_status = ProfileSyncStatus(db_user.sync_status)
            except Exception as e:
                logger.warning(f"Failed to convert sync_status: {e}")

        return UserProfile(
            profile_id=db_user.profile_id,
            user_id=db_user.id,
            team_id=db_user.team_id,
            full_name=db_user.full_name,
            email=db_user.email,
            slack_user_id=db_user.slack_user_id,
            role=db_user.role,
            department=db_user.department,
            manager_id=db_user.manager_id,
            preferences=preferences,
            settings=db_user.settings or {},
            sync_status=sync_status,
            metadata=db_user.metadata_ or {},
            created_at=db_user.created_at,
            updated_at=db_user.updated_at,
            version=db_user.version,
        )

    @staticmethod
    def competency_score_to_db_model(score: CompetencyScore) -> Competency:
        """Convert CompetencyScore to Competency database model"""
        return Competency(
            id=score.score_id,
            user_id=score.user_id,
            competency_id=score.competency_name,  # Using competency_name as competency_id
            competency_name=score.competency_name,
            current_level=score.score_value,
            evidence_count=len(score.evidence_sources) if score.evidence_sources else 0,
            confidence_interval=score.confidence_level,
            last_calculated_at=score.assessed_at,
            assessment_method=score.assessment_method,
            metadata_=score.metadata or {},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            version=1,
        )

    @staticmethod
    def db_model_to_competency_score(db_competency: Competency) -> CompetencyScore:
        """Convert Competency database model to CompetencyScore"""
        return CompetencyScore(
            score_id=db_competency.id,
            user_id=db_competency.user_id,
            competency_name=db_competency.competency_name,
            score_value=float(db_competency.current_level),
            confidence_level=float(db_competency.confidence_interval)
            if db_competency.confidence_interval
            else 0.0,
            assessment_method=db_competency.assessment_method or "manual",
            evidence_sources=[],  # Would need to be populated from related tables
            metadata=db_competency.metadata_ or {},
            assessed_at=db_competency.last_calculated_at or db_competency.updated_at,
            created_at=db_competency.created_at,
            updated_at=db_competency.updated_at,
            version=db_competency.version,
        )


# Convenience functions for direct access
def convert_activity_to_db(activity: ActivityData) -> Activity:
    """Convert ActivityData to database model"""
    return ModelConverter.activity_to_db_model(activity)


def convert_db_to_activity(db_activity: Activity) -> ActivityData:
    """Convert database model to ActivityData"""
    return ModelConverter.db_model_to_activity(db_activity)


def convert_user_profile_to_db(profile: UserProfile) -> User:
    """Convert UserProfile to database model"""
    return ModelConverter.user_profile_to_db_model(profile)


def convert_db_to_user_profile(db_user: User) -> UserProfile:
    """Convert database model to UserProfile"""
    return ModelConverter.db_model_to_user_profile(db_user)


def convert_competency_score_to_db(score: CompetencyScore) -> Competency:
    """Convert CompetencyScore to database model"""
    return ModelConverter.competency_score_to_db_model(score)


def convert_db_to_competency_score(db_competency: Competency) -> CompetencyScore:
    """Convert database model to CompetencyScore"""
    return ModelConverter.db_model_to_competency_score(db_competency)
