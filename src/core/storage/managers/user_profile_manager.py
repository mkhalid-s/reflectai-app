"""
User Profile Manager for ReflectAI

Implements user profile data management operations:
- User profile storage and retrieval with caching
- Profile update operations with validation
- Batch operations for team profile management
- Profile versioning and sync status tracking
- Data validation and integrity checks
- Performance monitoring and optimization

Provides high-level interface for all user profile operations.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from src.infrastructure.cache.redis_manager import RedisManager, get_redis_manager
from src.infrastructure.database.db_manager import get_database_manager
from src.infrastructure.database.models.user import User
from src.infrastructure.database.repositories import UserRepository
from src.shared import get_logger

from ..models.user_profile import (
    UserProfile,
    UserProfileModel,
)


class UserProfileInsertResult(BaseModel):
    """Result of user profile insertion operation"""

    success: bool = Field(..., description="Whether insertion succeeded")
    profile_id: str | None = Field(None, description="Inserted profile ID")
    errors: list[str] = Field(default_factory=list, description="Any errors encountered")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    cache_updated: bool = Field(default=False, description="Whether cache was updated")


class UserProfileBatchResult(BaseModel):
    """Result of batch user profile operations"""

    total_profiles: int = Field(..., description="Total profiles in batch")
    successful_inserts: int = Field(..., description="Number of successful insertions")
    failed_inserts: int = Field(default=0, description="Number of failed insertions")
    errors: list[str] = Field(default_factory=list, description="Batch processing errors")
    processing_time_ms: float = Field(..., description="Total processing time")
    batch_id: str | None = Field(None, description="Batch identifier")


class UserProfileUpdateResult(BaseModel):
    """Result of user profile update operation"""

    success: bool = Field(..., description="Whether update succeeded")
    profile_id: str = Field(..., description="Updated profile ID")
    updated_fields: list[str] = Field(default_factory=list, description="List of updated fields")
    errors: list[str] = Field(default_factory=list, description="Any errors encountered")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    version: int = Field(..., description="New profile version")


class UserProfileManager:
    """High-level user profile data management"""

    def __init__(self, database_manager=None, redis_manager: RedisManager | None = None):
        self.logger = get_logger("storage.user_profile_manager")
        self.db = database_manager or get_database_manager()
        self.redis = redis_manager or get_redis_manager()
        self.repository = UserRepository()

        # Performance tracking
        self.operation_stats = {
            "inserts": {"count": 0, "total_time": 0.0},
            "queries": {"count": 0, "total_time": 0.0},
            "updates": {"count": 0, "total_time": 0.0},
            "deletes": {"count": 0, "total_time": 0.0},
        }

    def _convert_to_db_model(self, profile: UserProfile) -> User:
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
            metadata=profile.metadata or {},
            created_at=profile.created_at,
            updated_at=profile.updated_at,
            version=profile.version,
        )

    async def insert_user_profile(
        self, profile: UserProfile, update_cache: bool = True, validate_duplicates: bool = True
    ) -> UserProfileInsertResult:
        """Insert a single user profile with validation and caching"""

        start_time = datetime.now(UTC)

        try:
            # Validate for duplicates if requested
            if validate_duplicates:
                duplicate = await self._check_duplicate_profile(profile)
                if duplicate:
                    return UserProfileInsertResult(
                        success=False,
                        errors=["Duplicate user profile detected"],
                        processing_time_ms=0.0,
                    )

            # Convert to database model and use repository
            db_user = self._convert_to_db_model(profile)
            created_user = await self.repository.create(db_user)

            # Update cache if requested
            cache_updated = False
            if update_cache:
                cache_updated = await self._update_profile_cache(profile)

            # Track performance
            processing_time = (datetime.now(UTC) - start_time).total_seconds() * 1000
            self.operation_stats["inserts"]["count"] += 1
            self.operation_stats["inserts"]["total_time"] += processing_time

            self.logger.info(f"Successfully inserted user profile {profile.profile_id}")

            return UserProfileInsertResult(
                success=True,
                profile_id=str(created_user.profile_id),
                processing_time_ms=processing_time,
                cache_updated=cache_updated,
            )

        except Exception as e:
            error_msg = f"Failed to insert user profile: {str(e)}"
            self.logger.error(error_msg)

            processing_time = (datetime.now(UTC) - start_time).total_seconds() * 1000

            return UserProfileInsertResult(
                success=False, errors=[error_msg], processing_time_ms=processing_time
            )

    async def update_user_profile(
        self, profile_id: str | uuid.UUID, updates: dict[str, Any], update_cache: bool = True
    ) -> UserProfileUpdateResult:
        """Update user profile fields"""

        start_time = datetime.now(UTC)

        try:
            # Define allowed fields for updates (whitelist approach for SQL injection prevention)
            allowed_fields = {
                "slack_user_id",
                "email",
                "full_name",
                "display_name",
                "avatar_url",
                "title",
                "department",
                "team_id",
                "manager_id",
                "location",
                "start_date",
                "employee_id",
                "employment_type",
                "primary_skills",
                "career_goals",
                "preferences",
                "metadata",
                "tags",
                "is_active",
                "last_activity_at",
                "onboarding_completed",
                "sync_status",
            }

            # Build update query dynamically with field validation
            update_fields = []
            params = []
            param_count = 1

            for field, value in updates.items():
                # Validate field name against whitelist (SQL injection protection)
                if field in allowed_fields:
                    update_fields.append(f"{field} = ${param_count}")
                    params.append(value)
                    param_count += 1

            if not update_fields:
                return UserProfileUpdateResult(
                    success=False,
                    profile_id=str(profile_id),
                    errors=["No valid fields to update"],
                    processing_time_ms=0.0,
                    version=0,
                )

            # Add version increment and updated_at
            update_fields.append("version = version + 1")
            update_fields.append("updated_at = NOW()")

            # nosec B608: SQL injection false positive - field names validated against whitelist
            # All values are parameterized with $ placeholders
            update_query = f"""
                UPDATE user_profiles
                SET {", ".join(update_fields)}
                WHERE profile_id = ${param_count}
                RETURNING version
            """
            params.append(str(profile_id))

            # Execute update
            postgres_manager = self.db.get_postgres_manager()
            result = await postgres_manager.execute_query(
                update_query, params, fetch="one", query_type="user_profile_update"
            )

            if not result:
                return UserProfileUpdateResult(
                    success=False,
                    profile_id=str(profile_id),
                    errors=["Profile not found"],
                    processing_time_ms=0.0,
                    version=0,
                )

            new_version = dict(result)["version"]

            # Update cache if requested
            if update_cache:
                await self._invalidate_profile_cache(profile_id)

            # Track performance
            processing_time = (datetime.now(UTC) - start_time).total_seconds() * 1000
            self.operation_stats["updates"]["count"] += 1
            self.operation_stats["updates"]["total_time"] += processing_time

            self.logger.info(f"Successfully updated user profile {profile_id}")

            return UserProfileUpdateResult(
                success=True,
                profile_id=str(profile_id),
                updated_fields=list(updates.keys()),
                processing_time_ms=processing_time,
                version=new_version,
            )

        except Exception as e:
            error_msg = f"Failed to update user profile: {str(e)}"
            self.logger.error(error_msg)

            processing_time = (datetime.now(UTC) - start_time).total_seconds() * 1000

            return UserProfileUpdateResult(
                success=False,
                profile_id=str(profile_id),
                errors=[error_msg],
                processing_time_ms=processing_time,
                version=0,
            )

    async def get_user_profile_by_id(self, profile_id: str | uuid.UUID) -> UserProfile | None:
        """Get a specific user profile by ID"""

        try:
            # Try cache first
            cache_key = f"profile:{str(profile_id)}"
            cached_profile = await self.redis.get("user_profile", cache_key)

            if cached_profile:
                return UserProfile(**cached_profile)

            # Query database
            query = """
                SELECT profile_id, user_id, team_id, full_name, email, slack_user_id,
                       role, department, manager_id, preferences, settings, sync_status,
                       metadata, created_at, updated_at, version
                FROM user_profiles
                WHERE profile_id = $1
            """

            postgres_manager = self.db.get_postgres_manager()
            row = await postgres_manager.execute_query(
                query, [str(profile_id)], fetch="one", query_type="user_profile_get_by_id"
            )

            if row:
                db_model = UserProfileModel(**dict(row))
                profile = db_model.to_user_profile()

                # Cache the result
                await self.redis.set("user_profile", cache_key, profile.dict(), ttl_seconds=3600)

                return profile

            return None

        except Exception as e:
            self.logger.error(f"Failed to get user profile {profile_id}: {str(e)}")
            return None

    async def get_user_profile_by_user_id(self, user_id: str | uuid.UUID) -> UserProfile | None:
        """Get user profile by user ID"""

        try:
            # Try cache first
            cache_key = f"user:{str(user_id)}"
            cached_profile = await self.redis.get("user_profile", cache_key)

            if cached_profile:
                return UserProfile(**cached_profile)

            # Query database
            query = """
                SELECT profile_id, user_id, team_id, full_name, email, slack_user_id,
                       role, department, manager_id, preferences, settings, sync_status,
                       metadata, created_at, updated_at, version
                FROM user_profiles
                WHERE user_id = $1
            """

            postgres_manager = self.db.get_postgres_manager()
            row = await postgres_manager.execute_query(
                query, [str(user_id)], fetch="one", query_type="user_profile_get_by_user_id"
            )

            if row:
                db_model = UserProfileModel(**dict(row))
                profile = db_model.to_user_profile()

                # Cache the result
                await self.redis.set("user_profile", cache_key, profile.dict(), ttl_seconds=3600)

                return profile

            return None

        except Exception as e:
            self.logger.error(f"Failed to get user profile by user_id {user_id}: {str(e)}")
            return None

    async def get_team_profiles(
        self, team_id: str | uuid.UUID, limit: int = 100, offset: int = 0
    ) -> list[UserProfile]:
        """Get all profiles for a team"""

        try:
            query = """
                SELECT profile_id, user_id, team_id, full_name, email, slack_user_id,
                       role, department, manager_id, preferences, settings, sync_status,
                       metadata, created_at, updated_at, version
                FROM user_profiles
                WHERE team_id = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
            """

            postgres_manager = self.db.get_postgres_manager()
            rows = await postgres_manager.execute_query(
                query,
                [str(team_id), limit, offset],
                fetch="all",
                query_type="user_profile_get_by_team",
            )

            profiles = []
            for row in rows:
                db_model = UserProfileModel(**dict(row))
                profile = db_model.to_user_profile()
                profiles.append(profile)

            return profiles

        except Exception as e:
            self.logger.error(f"Failed to get team profiles for team {team_id}: {str(e)}")
            return []

    async def delete_user_profile(self, profile_id: str | uuid.UUID) -> bool:
        """Delete a user profile"""

        try:
            query = "DELETE FROM user_profiles WHERE profile_id = $1"

            postgres_manager = self.db.get_postgres_manager()
            await postgres_manager.execute_query(
                query, [str(profile_id)], query_type="user_profile_delete"
            )

            # Invalidate cache
            await self._invalidate_profile_cache(profile_id)

            # Track performance
            self.operation_stats["deletes"]["count"] += 1

            self.logger.info(f"Successfully deleted user profile {profile_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to delete user profile {profile_id}: {str(e)}")
            return False

    async def _check_duplicate_profile(self, profile: UserProfile) -> bool:
        """Check if profile is a duplicate"""

        try:
            query = """
                SELECT COUNT(*) as count
                FROM user_profiles
                WHERE user_id = $1 OR email = $2
                LIMIT 1
            """

            postgres_manager = self.db.get_postgres_manager()
            result = await postgres_manager.execute_query(
                query,
                [str(profile.user_id), profile.email],
                fetch="val",
                query_type="duplicate_check",
            )

            return result > 0

        except Exception as e:
            self.logger.error(f"Duplicate check failed: {str(e)}")
            return False

    async def _update_profile_cache(self, profile: UserProfile) -> bool:
        """Update profile cache"""

        try:
            cache_key = str(profile.profile_id)
            user_cache_key = f"user:{str(profile.user_id)}"

            # Cache by both profile ID and user ID
            await self.redis.set("user_profile", cache_key, profile.dict(), ttl_seconds=3600)
            await self.redis.set("user_profile", user_cache_key, profile.dict(), ttl_seconds=3600)

            return True
        except Exception as e:
            self.logger.error(f"Cache update failed: {str(e)}")
            return False

    async def _invalidate_profile_cache(self, profile_id: str | uuid.UUID):
        """Invalidate profile cache entries"""

        try:
            cache_key = f"profile:{str(profile_id)}"
            await self.redis.delete("user_profile", cache_key)

            # Also invalidate user_id cache if we can get it
            profile = await self.get_user_profile_by_id(profile_id)
            if profile:
                user_cache_key = f"user:{str(profile.user_id)}"
                await self.redis.delete("user_profile", user_cache_key)

        except Exception as e:
            self.logger.error(f"Cache invalidation failed: {str(e)}")

    async def get_performance_stats(self) -> dict[str, Any]:
        """Get performance statistics"""

        stats = self.operation_stats.copy()

        # Calculate averages
        for _operation, data in stats.items():
            if data["count"] > 0:
                data["avg_time_ms"] = data["total_time"] / data["count"]
            else:
                data["avg_time_ms"] = 0.0

        return stats


# Global manager instance
_global_user_profile_manager: UserProfileManager | None = None


def get_user_profile_manager() -> UserProfileManager:
    """Get global user profile manager instance"""
    global _global_user_profile_manager
    if _global_user_profile_manager is None:
        _global_user_profile_manager = UserProfileManager()
    return _global_user_profile_manager
