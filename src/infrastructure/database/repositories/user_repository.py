"""
⚠️ **ARCHITECTURAL NOTE**: This repository uses SQLAlchemy ORM patterns via BaseRepository,
but db_manager.py uses asyncpg. Current status: Implementation exists but may have compatibility issues.
Recommendation: Test thoroughly or rewrite to use asyncpg directly.

User Repository Implementation for ReflectAI

Provides comprehensive user management operations including:
- User profile management and team queries
- Slack integration support
- Activity tracking and status management
- Team-based operations and bulk user operations
- Advanced querying with profile data search
- Caching strategies for frequently accessed users
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from src.shared import ErrorSeverity, ReflectAIError, get_logger

from ..models.user import User
from .base_repository import (
    BaseRepository,
    FilterCriteria,
    PaginationParams,
    SortCriteria,
)


class UserRepository(BaseRepository[User]):
    """
    User-specific repository with advanced team and profile management capabilities

    Features:
    - Team-based user queries and management
    - Slack user integration operations
    - Profile data search and management
    - Activity status tracking
    - User preference management
    - Bulk team operations
    """

    def __init__(self):
        super().__init__(User)
        self.logger = get_logger("repository.user")

        # User-specific caching configuration
        self.cache_ttl_seconds = 600  # 10 minutes for users (longer than base)
        self.enable_query_cache = True

    # =====================
    # User-Specific Queries
    # =====================

    async def get_by_slack_user_id(self, slack_user_id: str) -> User | None:
        """Get user by Slack user ID"""
        try:
            filters = [FilterCriteria("slack_user_id", "eq", slack_user_id)]
            return await self.find_one(filters)
        except Exception as e:
            self.logger.error(f"Error getting user by Slack ID {slack_user_id}: {str(e)}")
            raise ReflectAIError(
                f"Failed to get user by Slack ID: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email address"""
        try:
            filters = [FilterCriteria("email", "eq", email)]
            return await self.find_one(filters)
        except Exception as e:
            self.logger.error(f"Error getting user by email {email}: {str(e)}")
            raise ReflectAIError(
                f"Failed to get user by email: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    async def create_or_update_from_slack(
        self, slack_user_id: str, team_id: str, user_data: dict[str, Any]
    ) -> User:
        """Create or update user from Slack user data"""
        try:
            # Try to find existing user
            existing_user = await self.get_by_slack_user_id(slack_user_id)

            # Prepare user data
            user_record_data = {
                "slack_user_id": slack_user_id,
                "team_id": team_id,
                "email": user_data.get("profile", {}).get("email"),
                "display_name": user_data.get("profile", {}).get("display_name"),
                "real_name": user_data.get("profile", {}).get("real_name"),
                "timezone": user_data.get("tz", "UTC"),
                "is_active": not user_data.get("deleted", False),
                "profile_data": {
                    "slack_profile": user_data,
                    "updated_from_slack_at": datetime.now(UTC).isoformat(),
                },
            }

            if existing_user:
                # Update existing user
                updated_user = await self.update(existing_user.id, user_record_data)
                self.logger.info(f"Updated user from Slack: {slack_user_id}")
                return updated_user
            else:
                # Create new user
                new_user = await self.create(user_record_data)
                self.logger.info(f"Created new user from Slack: {slack_user_id}")
                return new_user

        except Exception as e:
            self.logger.error(f"Error creating/updating user from Slack data: {str(e)}")
            raise ReflectAIError(
                f"Failed to sync user from Slack: {str(e)}", ErrorSeverity.HIGH
            ) from e

    async def update_last_activity(self, user_id: uuid.UUID) -> bool:
        """Update user's last activity timestamp"""
        try:
            update_data = {"last_activity_at": datetime.now(UTC)}
            updated_user = await self.update(user_id, update_data)
            return updated_user is not None
        except Exception as e:
            self.logger.error(f"Error updating last activity for user {user_id}: {str(e)}")
            raise ReflectAIError(
                f"Failed to update user activity: {str(e)}", ErrorSeverity.LOW
            ) from e

    async def update_profile_data(
        self, user_id: uuid.UUID, profile_updates: dict[str, Any], merge: bool = True
    ) -> User | None:
        """Update user profile data (JSONB field)"""
        try:
            # Get current user to merge profile data
            current_user = await self.get_by_id(user_id)
            if not current_user:
                return None

            if merge:
                # Merge with existing profile data
                current_profile = current_user.profile_data or {}
                updated_profile = {**current_profile, **profile_updates}
            else:
                # Replace profile data entirely
                updated_profile = profile_updates

            return await self.update(user_id, {"profile_data": updated_profile})

        except Exception as e:
            self.logger.error(f"Error updating profile data for user {user_id}: {str(e)}")
            raise ReflectAIError(
                f"Failed to update profile data: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    # =====================
    # Team-Based Operations
    # =====================

    async def get_team_users(
        self, team_id: str, active_only: bool = True, pagination: PaginationParams | None = None
    ) -> list[User]:
        """Get all users for a specific team"""
        try:
            filters = [FilterCriteria("team_id", "eq", team_id)]

            if active_only:
                filters.append(FilterCriteria("is_active", "eq", True))

            if pagination:
                result = await self.find_with_pagination(pagination, filters)
                return result.items
            else:
                return await self.find_all(filters)

        except Exception as e:
            self.logger.error(f"Error getting team users for team {team_id}: {str(e)}")
            raise ReflectAIError(f"Failed to get team users: {str(e)}", ErrorSeverity.MEDIUM) from e

    async def get_team_user_count(self, team_id: str, active_only: bool = True) -> int:
        """Get count of users in a team"""
        try:
            filters = [FilterCriteria("team_id", "eq", team_id)]

            if active_only:
                filters.append(FilterCriteria("is_active", "eq", True))

            return await self.count(filters)

        except Exception as e:
            self.logger.error(f"Error counting team users for team {team_id}: {str(e)}")
            raise ReflectAIError(
                f"Failed to count team users: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    async def get_team_admins(self, team_id: str) -> list[User]:
        """Get admin users for a team (based on profile data)"""
        try:
            # Use raw query for JSON field searching
            query = """
                SELECT * FROM users
                WHERE team_id = $1
                AND is_active = true
                AND (profile_data->>'is_admin' = 'true' OR profile_data->>'role' = 'admin')
                ORDER BY display_name
            """

            result = await self.execute_raw_query(query, [team_id], "all")

            return [User(**dict(row)) for row in result] if result else []

        except Exception as e:
            self.logger.error(f"Error getting team admins for team {team_id}: {str(e)}")
            raise ReflectAIError(
                f"Failed to get team admins: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    async def deactivate_team_users(
        self, team_id: str, exclude_user_ids: list[uuid.UUID] = None
    ) -> int:
        """Deactivate all users in a team (except specified exclusions)"""
        try:
            filters = [FilterCriteria("team_id", "eq", team_id)]

            if exclude_user_ids:
                filters.append(FilterCriteria("id", "not_in", exclude_user_ids))

            update_data = {"is_active": False}
            return await self.update_many(filters, update_data)

        except Exception as e:
            self.logger.error(f"Error deactivating team users for team {team_id}: {str(e)}")
            raise ReflectAIError(
                f"Failed to deactivate team users: {str(e)}", ErrorSeverity.HIGH
            ) from e

    async def get_teams_by_user_count(self, min_users: int = 1) -> list[dict[str, Any]]:
        """Get teams with their user counts"""
        try:
            query = """
                SELECT
                    team_id,
                    COUNT(*) as total_users,
                    COUNT(*) FILTER (WHERE is_active = true) as active_users,
                    MIN(created_at) as earliest_user_created,
                    MAX(last_activity_at) as latest_activity
                FROM users
                GROUP BY team_id
                HAVING COUNT(*) >= $1
                ORDER BY active_users DESC, total_users DESC
            """

            result = await self.execute_raw_query(query, [min_users], "all")

            return (
                [
                    {
                        "team_id": row[0],
                        "total_users": row[1],
                        "active_users": row[2],
                        "earliest_user_created": row[3],
                        "latest_activity": row[4],
                    }
                    for row in result
                ]
                if result
                else []
            )

        except Exception as e:
            self.logger.error(f"Error getting teams by user count: {str(e)}")
            raise ReflectAIError(
                f"Failed to get team statistics: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    # =====================
    # Activity and Status Queries
    # =====================

    async def get_recently_active_users(
        self, team_id: str | None = None, since_hours: int = 24, limit: int = 50
    ) -> list[User]:
        """Get users who have been active recently"""
        try:
            cutoff_time = datetime.now(UTC) - timedelta(hours=since_hours)

            filters = [
                FilterCriteria("last_activity_at", "gte", cutoff_time),
                FilterCriteria("is_active", "eq", True),
            ]

            if team_id:
                filters.append(FilterCriteria("team_id", "eq", team_id))

            sorts = [SortCriteria("last_activity_at", "desc")]

            # Use pagination to limit results
            pagination = PaginationParams(page=1, page_size=limit)
            result = await self.find_with_pagination(pagination, filters, sorts)

            return result.items

        except Exception as e:
            self.logger.error(f"Error getting recently active users: {str(e)}")
            raise ReflectAIError(
                f"Failed to get active users: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    async def get_inactive_users(
        self,
        team_id: str | None = None,
        inactive_days: int = 30,
        pagination: PaginationParams | None = None,
    ) -> list[User]:
        """Get users who have been inactive for specified period"""
        try:
            cutoff_time = datetime.now(UTC) - timedelta(days=inactive_days)

            filters = [FilterCriteria("is_active", "eq", True)]

            # Users with no activity or old activity
            filters.extend([FilterCriteria("last_activity_at", "lt", cutoff_time)])

            if team_id:
                filters.append(FilterCriteria("team_id", "eq", team_id))

            sorts = [SortCriteria("last_activity_at", "asc")]

            if pagination:
                result = await self.find_with_pagination(pagination, filters, sorts)
                return result.items
            else:
                return await self.find_all(filters, sorts)

        except Exception as e:
            self.logger.error(f"Error getting inactive users: {str(e)}")
            raise ReflectAIError(
                f"Failed to get inactive users: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    async def get_user_activity_summary(self, user_id: uuid.UUID, days: int = 30) -> dict[str, Any]:
        """Get comprehensive activity summary for a user"""
        try:
            user = await self.get_by_id(user_id)
            if not user:
                return {}

            # Get activity data from related tables using raw queries
            since_date = datetime.now(UTC) - timedelta(days=days)

            # Activity count
            activity_query = """
                SELECT COUNT(*) FROM activities
                WHERE user_id = $1 AND created_at >= $2
            """
            activity_count = await self.execute_raw_query(
                activity_query, [user_id, since_date], "val"
            )

            # Competency updates count
            competency_query = """
                SELECT COUNT(*) FROM competency_history
                WHERE user_id = $1 AND timestamp >= $2
            """
            competency_count = await self.execute_raw_query(
                competency_query, [user_id, since_date], "val"
            )

            # Workflow interactions
            workflow_query = """
                SELECT COUNT(*) FROM workflows
                WHERE user_id = $1 AND created_at >= $2
            """
            workflow_count = await self.execute_raw_query(
                workflow_query, [user_id, since_date], "val"
            )

            return {
                "user_id": str(user_id),
                "period_days": days,
                "last_activity_at": user.last_activity_at.isoformat()
                if user.last_activity_at
                else None,
                "activity_count": activity_count or 0,
                "competency_updates": competency_count or 0,
                "workflow_interactions": workflow_count or 0,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Error getting activity summary for user {user_id}: {str(e)}")
            raise ReflectAIError(
                f"Failed to get user activity summary: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    # =====================
    # Search and Advanced Queries
    # =====================

    async def search_users(
        self,
        search_term: str,
        team_id: str | None = None,
        active_only: bool = True,
        pagination: PaginationParams | None = None,
    ) -> list[User]:
        """Search users by name, email, or Slack ID"""
        try:
            # Build search filters
            search_pattern = f"%{search_term}%"

            # Search in multiple fields using OR logic via raw query
            where_conditions = [
                "display_name ILIKE $1",
                "real_name ILIKE $1",
                "email ILIKE $1",
                "slack_user_id ILIKE $1",
            ]

            params = [search_pattern]
            param_index = 2

            # Add team filter
            if team_id:
                where_conditions.append(f"team_id = ${param_index}")
                params.append(team_id)
                param_index += 1

            # Add active filter
            if active_only:
                where_conditions.append(f"is_active = ${param_index}")
                params.append(True)
                param_index += 1

            # Build base query
            base_query = f"""
                SELECT * FROM users
                WHERE ({" OR ".join(where_conditions[:4])})
            """

            # Add additional where conditions
            if len(where_conditions) > 4:
                base_query += f" AND {' AND '.join(where_conditions[4:])}"

            base_query += " ORDER BY display_name, real_name"

            # Add pagination
            if pagination:
                base_query += f" LIMIT {pagination.page_size} OFFSET {pagination.offset}"

            result = await self.execute_raw_query(base_query, params, "all")

            return [User(**dict(row)) for row in result] if result else []

        except Exception as e:
            self.logger.error(f"Error searching users with term '{search_term}': {str(e)}")
            raise ReflectAIError(f"Failed to search users: {str(e)}", ErrorSeverity.MEDIUM) from e

    async def search_profile_data(
        self, profile_key: str, profile_value: Any, team_id: str | None = None
    ) -> list[User]:
        """Search users by profile data content"""
        try:
            params = [profile_key, str(profile_value)]
            param_index = 3

            # Base query for profile data search
            base_query = """
                SELECT * FROM users
                WHERE profile_data->>$1 = $2
                AND is_active = true
            """

            if team_id:
                base_query += f" AND team_id = ${param_index}"
                params.append(team_id)
                param_index += 1

            base_query += " ORDER BY display_name"

            result = await self.execute_raw_query(base_query, params, "all")

            return [User(**dict(row)) for row in result] if result else []

        except Exception as e:
            self.logger.error(
                f"Error searching profile data {profile_key}={profile_value}: {str(e)}"
            )
            raise ReflectAIError(
                f"Failed to search profile data: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    # =====================
    # Bulk Operations
    # =====================

    async def bulk_update_timezone(self, user_ids: list[uuid.UUID], timezone: str) -> int:
        """Bulk update timezone for multiple users"""
        try:
            filters = [FilterCriteria("id", "in", user_ids)]
            update_data = {"timezone": timezone}

            updated_count = await self.update_many(filters, update_data)
            self.logger.info(f"Bulk updated timezone for {updated_count} users")

            return updated_count

        except Exception as e:
            self.logger.error(f"Error bulk updating timezone: {str(e)}")
            raise ReflectAIError(
                f"Failed to bulk update timezone: {str(e)}", ErrorSeverity.HIGH
            ) from e

    async def bulk_deactivate_users(self, user_ids: list[uuid.UUID]) -> int:
        """Bulk deactivate multiple users"""
        try:
            filters = [FilterCriteria("id", "in", user_ids)]
            update_data = {"is_active": False}

            deactivated_count = await self.update_many(filters, update_data)
            self.logger.info(f"Bulk deactivated {deactivated_count} users")

            return deactivated_count

        except Exception as e:
            self.logger.error(f"Error bulk deactivating users: {str(e)}")
            raise ReflectAIError(
                f"Failed to bulk deactivate users: {str(e)}", ErrorSeverity.HIGH
            ) from e

    async def sync_team_from_slack(
        self, team_id: str, slack_users: list[dict[str, Any]]
    ) -> dict[str, int]:
        """Sync entire team from Slack user data"""
        try:
            sync_stats = {"created": 0, "updated": 0, "errors": 0}

            for slack_user_data in slack_users:
                try:
                    slack_user_id = slack_user_data.get("id")
                    if not slack_user_id:
                        continue

                    existing_user = await self.get_by_slack_user_id(slack_user_id)

                    if existing_user:
                        # Update existing
                        await self.create_or_update_from_slack(
                            slack_user_id, team_id, slack_user_data
                        )
                        sync_stats["updated"] += 1
                    else:
                        # Create new
                        await self.create_or_update_from_slack(
                            slack_user_id, team_id, slack_user_data
                        )
                        sync_stats["created"] += 1

                except Exception as e:
                    self.logger.warning(
                        f"Error syncing user {slack_user_data.get('id', 'unknown')}: {str(e)}"
                    )
                    sync_stats["errors"] += 1

            self.logger.info(f"Team sync completed for {team_id}: {sync_stats}")
            return sync_stats

        except Exception as e:
            self.logger.error(f"Error syncing team from Slack: {str(e)}")
            raise ReflectAIError(
                f"Failed to sync team from Slack: {str(e)}", ErrorSeverity.HIGH
            ) from e

    # =====================
    # Analytics and Reporting
    # =====================

    async def get_user_growth_stats(
        self, team_id: str | None = None, days: int = 30
    ) -> dict[str, Any]:
        """Get user growth statistics over time period"""
        try:
            since_date = datetime.now(UTC) - timedelta(days=days)

            params = [since_date]
            team_filter = ""
            if team_id:
                team_filter = "AND team_id = $2"
                params.append(team_id)

            query = f"""
                SELECT
                    DATE_TRUNC('day', created_at) as day,
                    COUNT(*) as new_users,
                    COUNT(*) FILTER (WHERE is_active = true) as active_new_users
                FROM users
                WHERE created_at >= $1 {team_filter}
                GROUP BY DATE_TRUNC('day', created_at)
                ORDER BY day
            """

            result = await self.execute_raw_query(query, params, "all")

            growth_data = (
                [
                    {
                        "date": row[0].date().isoformat(),
                        "new_users": row[1],
                        "active_new_users": row[2],
                    }
                    for row in result
                ]
                if result
                else []
            )

            # Calculate totals
            total_new = sum(item["new_users"] for item in growth_data)
            total_active_new = sum(item["active_new_users"] for item in growth_data)

            return {
                "period_days": days,
                "team_id": team_id,
                "total_new_users": total_new,
                "total_active_new_users": total_active_new,
                "daily_growth": growth_data,
            }

        except Exception as e:
            self.logger.error(f"Error getting user growth stats: {str(e)}")
            raise ReflectAIError(
                f"Failed to get user growth statistics: {str(e)}", ErrorSeverity.MEDIUM
            ) from e
