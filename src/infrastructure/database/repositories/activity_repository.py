"""
Activity Repository Implementation for ReflectAI

⚠️ **ARCHITECTURAL NOTE** ⚠️
This repository uses SQLAlchemy ORM patterns via BaseRepository, but db_manager.py uses asyncpg.
Current status: Implementation exists but may have compatibility issues.
Recommendation: Test thoroughly or rewrite to use asyncpg directly.

Provides comprehensive activity management with specialized TimescaleDB operations:
- Time-series queries and aggregations optimized for TimescaleDB hypertables
- Activity processing workflow management
- Competency mapping and analysis
- Performance metrics and analytics
- Correlation tracking and threading
- Bulk operations for high-volume data processing
- Advanced filtering by content, classification, and metrics
"""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from src.shared import ErrorSeverity, ReflectAIError, get_logger

from ..models.activity import Activity
from .base_repository import (
    BaseRepository,
    FilterCriteria,
    PaginationParams,
    SortCriteria,
)


class ActivityRepository(BaseRepository[Activity]):
    """
    Activity-specific repository optimized for TimescaleDB time-series operations

    Features:
    - TimescaleDB hypertable optimizations
    - Time-bucketed aggregations and analytics
    - Activity processing workflow management
    - Competency area analysis and reporting
    - Performance metrics tracking
    - Content classification and search
    - Correlation tracking for related activities
    """

    def __init__(self):
        super().__init__(Activity)
        self.logger = get_logger("repository.activity")

        # Activity-specific caching - shorter TTL due to high volume
        self.cache_ttl_seconds = 180  # 3 minutes for activities
        self.enable_query_cache = True

    # =====================
    # Activity-Specific Queries
    # =====================

    async def get_user_activities(
        self,
        user_id: uuid.UUID,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        activity_types: list[str] | None = None,
        processing_status: list[str] | None = None,
        pagination: PaginationParams | None = None,
    ) -> list[Activity]:
        """Get activities for a specific user with optional filtering"""
        try:
            filters = [FilterCriteria("user_id", "eq", user_id)]

            if start_time:
                filters.append(FilterCriteria("timestamp", "gte", start_time))

            if end_time:
                filters.append(FilterCriteria("timestamp", "lte", end_time))

            if activity_types:
                filters.append(FilterCriteria("activity_type", "in", activity_types))

            if processing_status:
                filters.append(FilterCriteria("processing_status", "in", processing_status))

            # Default sort by timestamp descending
            sorts = [SortCriteria("timestamp", "desc")]

            if pagination:
                result = await self.find_with_pagination(pagination, filters, sorts)
                return result.items
            else:
                return await self.find_all(filters, sorts)

        except Exception as e:
            self.logger.error(f"Error getting user activities for user {user_id}: {str(e)}")
            raise ReflectAIError(
                f"Failed to get user activities: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    async def get_recent_activities(
        self,
        hours: int = 24,
        limit: int = 100,
        activity_types: list[str] | None = None,
        processing_status: str = "complete",
    ) -> list[Activity]:
        """Get recent activities across all users"""
        try:
            since_time = datetime.now(UTC) - timedelta(hours=hours)

            filters = [
                FilterCriteria("timestamp", "gte", since_time),
                FilterCriteria("processing_status", "eq", processing_status),
            ]

            if activity_types:
                filters.append(FilterCriteria("activity_type", "in", activity_types))

            sorts = [SortCriteria("timestamp", "desc")]

            # Use pagination to limit results
            pagination = PaginationParams(page=1, page_size=limit)
            result = await self.find_with_pagination(pagination, filters, sorts)

            return result.items

        except Exception as e:
            self.logger.error(f"Error getting recent activities: {str(e)}")
            raise ReflectAIError(
                f"Failed to get recent activities: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    async def get_pending_activities(
        self, older_than_minutes: int = 0, limit: int = 50
    ) -> list[Activity]:
        """Get activities pending processing"""
        try:
            filters = [FilterCriteria("processing_status", "eq", "pending")]

            if older_than_minutes > 0:
                cutoff_time = datetime.now(UTC) - timedelta(minutes=older_than_minutes)
                filters.append(FilterCriteria("timestamp", "lte", cutoff_time))

            # Sort by timestamp ascending (oldest first for processing)
            sorts = [SortCriteria("timestamp", "asc")]

            pagination = PaginationParams(page=1, page_size=limit)
            result = await self.find_with_pagination(pagination, filters, sorts)

            return result.items

        except Exception as e:
            self.logger.error(f"Error getting pending activities: {str(e)}")
            raise ReflectAIError(
                f"Failed to get pending activities: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    async def update_processing_status(
        self,
        activity_id: uuid.UUID,
        status: str,
        confidence_score: float | None = None,
        classification_data: dict[str, Any] | None = None,
        metrics_data: dict[str, Any] | None = None,
    ) -> Activity | None:
        """Update activity processing status and analysis results"""
        try:
            update_data = {"processing_status": status}

            if confidence_score is not None:
                update_data["confidence_score"] = Decimal(str(confidence_score))

            if classification_data:
                update_data["classification"] = classification_data

            if metrics_data:
                update_data["metrics"] = metrics_data

            return await self.update(activity_id, update_data)

        except Exception as e:
            self.logger.error(
                f"Error updating processing status for activity {activity_id}: {str(e)}"
            )
            raise ReflectAIError(
                f"Failed to update processing status: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    async def add_competency_areas(
        self, activity_id: uuid.UUID, competency_areas: list[str]
    ) -> Activity | None:
        """Add competency areas to an activity"""
        try:
            # Get current activity to merge competency areas
            activity = await self.get_by_id(activity_id)
            if not activity:
                return None

            current_areas = activity.competency_areas or []
            updated_areas = list(set(current_areas + competency_areas))

            return await self.update(activity_id, {"competency_areas": updated_areas})

        except Exception as e:
            self.logger.error(f"Error adding competency areas to activity {activity_id}: {str(e)}")
            raise ReflectAIError(
                f"Failed to add competency areas: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    # =====================
    # TimescaleDB Time-Series Operations
    # =====================

    async def get_activity_time_series(
        self,
        start_time: datetime,
        end_time: datetime,
        bucket_interval: str = "1 hour",
        user_id: uuid.UUID | None = None,
        activity_types: list[str] | None = None,
        group_by_type: bool = False,
    ) -> list[dict[str, Any]]:
        """Get time-bucketed activity counts using TimescaleDB time_bucket"""
        try:
            # Build base query
            if group_by_type:
                base_query = """
                    SELECT
                        time_bucket($1, timestamp) as time_bucket,
                        activity_type,
                        COUNT(*) as activity_count
                    FROM activities
                    WHERE timestamp >= $2 AND timestamp <= $3
                """
                params = [bucket_interval, start_time, end_time]
                param_index = 4
            else:
                base_query = """
                    SELECT
                        time_bucket($1, timestamp) as time_bucket,
                        COUNT(*) as activity_count
                    FROM activities
                    WHERE timestamp >= $2 AND timestamp <= $3
                """
                params = [bucket_interval, start_time, end_time]
                param_index = 4

            # Add user filter
            if user_id:
                base_query += f" AND user_id = ${param_index}"
                params.append(user_id)
                param_index += 1

            # Add activity type filter
            if activity_types:
                placeholders = ",".join(
                    [f"${i}" for i in range(param_index, param_index + len(activity_types))]
                )
                base_query += f" AND activity_type IN ({placeholders})"
                params.extend(activity_types)
                param_index += len(activity_types)

            # Add grouping and ordering
            if group_by_type:
                base_query += (
                    " GROUP BY time_bucket, activity_type ORDER BY time_bucket, activity_type"
                )
            else:
                base_query += " GROUP BY time_bucket ORDER BY time_bucket"

            result = await self.execute_raw_query(base_query, params, "all")

            if group_by_type:
                return (
                    [
                        {"time_bucket": row[0], "activity_type": row[1], "activity_count": row[2]}
                        for row in result
                    ]
                    if result
                    else []
                )
            else:
                return (
                    [{"time_bucket": row[0], "activity_count": row[1]} for row in result]
                    if result
                    else []
                )

        except Exception as e:
            self.logger.error(f"Error getting activity time series: {str(e)}")
            raise ReflectAIError(
                f"Failed to get activity time series: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    async def get_activity_stats_by_period(
        self, start_time: datetime, end_time: datetime, user_id: uuid.UUID | None = None
    ) -> dict[str, Any]:
        """Get comprehensive activity statistics for a time period"""
        try:
            params = [start_time, end_time]
            user_filter = ""

            if user_id:
                user_filter = "AND user_id = $3"
                params.append(user_id)

            query = f"""
                SELECT
                    COUNT(*) as total_activities,
                    COUNT(DISTINCT user_id) as unique_users,
                    COUNT(DISTINCT activity_type) as unique_types,
                    COUNT(*) FILTER (WHERE processing_status = 'complete') as processed_activities,
                    COUNT(*) FILTER (WHERE processing_status = 'pending') as pending_activities,
                    COUNT(*) FILTER (WHERE processing_status = 'failed') as failed_activities,
                    AVG(confidence_score) as avg_confidence,
                    COUNT(*) FILTER (WHERE competency_areas IS NOT NULL AND array_length(competency_areas, 1) > 0) as activities_with_competencies,
                    AVG(array_length(competency_areas, 1)) FILTER (WHERE competency_areas IS NOT NULL) as avg_competencies_per_activity
                FROM activities
                WHERE timestamp >= $1 AND timestamp <= $2 {user_filter}
            """

            result = await self.execute_raw_query(query, params, "one")

            if result:
                return {
                    "total_activities": result[0] or 0,
                    "unique_users": result[1] or 0,
                    "unique_types": result[2] or 0,
                    "processed_activities": result[3] or 0,
                    "pending_activities": result[4] or 0,
                    "failed_activities": result[5] or 0,
                    "avg_confidence": float(result[6]) if result[6] else 0.0,
                    "activities_with_competencies": result[7] or 0,
                    "avg_competencies_per_activity": float(result[8]) if result[8] else 0.0,
                    "processing_rate": (result[3] / result[0] * 100) if result[0] else 0,
                    "period_start": start_time.isoformat(),
                    "period_end": end_time.isoformat(),
                }
            else:
                return {}

        except Exception as e:
            self.logger.error(f"Error getting activity stats by period: {str(e)}")
            raise ReflectAIError(
                f"Failed to get activity statistics: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    async def get_top_users_by_activity(
        self,
        start_time: datetime,
        end_time: datetime,
        limit: int = 10,
        activity_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get top users by activity count in a time period"""
        try:
            params = [start_time, end_time, limit]
            type_filter = ""

            if activity_type:
                type_filter = "AND activity_type = $4"
                params.insert(-1, activity_type)  # Insert before limit

            query = f"""
                SELECT
                    a.user_id,
                    u.display_name,
                    u.slack_user_id,
                    COUNT(*) as activity_count,
                    COUNT(DISTINCT a.activity_type) as unique_activity_types,
                    AVG(a.confidence_score) as avg_confidence,
                    COUNT(*) FILTER (WHERE a.competency_areas IS NOT NULL AND array_length(a.competency_areas, 1) > 0) as competency_activities
                FROM activities a
                LEFT JOIN users u ON a.user_id = u.id
                WHERE a.timestamp >= $1 AND a.timestamp <= $2 {type_filter}
                GROUP BY a.user_id, u.display_name, u.slack_user_id
                ORDER BY activity_count DESC
                LIMIT ${len(params)}
            """

            result = await self.execute_raw_query(query, params, "all")

            return (
                [
                    {
                        "user_id": str(row[0]),
                        "display_name": row[1],
                        "slack_user_id": row[2],
                        "activity_count": row[3],
                        "unique_activity_types": row[4],
                        "avg_confidence": float(row[5]) if row[5] else 0.0,
                        "competency_activities": row[6],
                    }
                    for row in result
                ]
                if result
                else []
            )

        except Exception as e:
            self.logger.error(f"Error getting top users by activity: {str(e)}")
            raise ReflectAIError(f"Failed to get top users: {str(e)}", ErrorSeverity.MEDIUM) from e

    # =====================
    # Competency Analysis
    # =====================

    async def get_competency_distribution(
        self, start_time: datetime, end_time: datetime, user_id: uuid.UUID | None = None
    ) -> list[dict[str, Any]]:
        """Get distribution of competency areas demonstrated in activities"""
        try:
            params = [start_time, end_time]
            user_filter = ""

            if user_id:
                user_filter = "AND user_id = $3"
                params.append(user_id)

            # Use PostgreSQL array functions to unnest competency areas
            query = f"""
                SELECT
                    competency_area,
                    COUNT(*) as activity_count,
                    COUNT(DISTINCT user_id) as user_count,
                    AVG(confidence_score) as avg_confidence
                FROM (
                    SELECT
                        unnest(competency_areas) as competency_area,
                        user_id,
                        confidence_score
                    FROM activities
                    WHERE timestamp >= $1 AND timestamp <= $2
                    AND competency_areas IS NOT NULL
                    AND array_length(competency_areas, 1) > 0 {user_filter}
                ) competency_activities
                GROUP BY competency_area
                ORDER BY activity_count DESC
            """

            result = await self.execute_raw_query(query, params, "all")

            return (
                [
                    {
                        "competency_area": row[0],
                        "activity_count": row[1],
                        "user_count": row[2],
                        "avg_confidence": float(row[3]) if row[3] else 0.0,
                    }
                    for row in result
                ]
                if result
                else []
            )

        except Exception as e:
            self.logger.error(f"Error getting competency distribution: {str(e)}")
            raise ReflectAIError(
                f"Failed to get competency distribution: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    async def get_activities_by_competency(
        self,
        competency_area: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        user_id: uuid.UUID | None = None,
        pagination: PaginationParams | None = None,
    ) -> list[Activity]:
        """Get activities that demonstrate a specific competency area"""
        try:
            # Use raw query for array contains operation
            params = [competency_area]
            param_index = 2

            base_query = """
                SELECT * FROM activities
                WHERE competency_areas @> ARRAY[$1]::text[]
                AND processing_status = 'complete'
            """

            if start_time:
                base_query += f" AND timestamp >= ${param_index}"
                params.append(start_time)
                param_index += 1

            if end_time:
                base_query += f" AND timestamp <= ${param_index}"
                params.append(end_time)
                param_index += 1

            if user_id:
                base_query += f" AND user_id = ${param_index}"
                params.append(user_id)
                param_index += 1

            base_query += " ORDER BY timestamp DESC"

            if pagination:
                base_query += f" LIMIT {pagination.page_size} OFFSET {pagination.offset}"

            result = await self.execute_raw_query(base_query, params, "all")

            return [Activity(**dict(row)) for row in result] if result else []

        except Exception as e:
            self.logger.error(f"Error getting activities by competency {competency_area}: {str(e)}")
            raise ReflectAIError(
                f"Failed to get activities by competency: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    # =====================
    # Content Search and Analysis
    # =====================

    async def search_activities_by_content(
        self,
        search_term: str,
        user_id: uuid.UUID | None = None,
        activity_types: list[str] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        pagination: PaginationParams | None = None,
    ) -> list[Activity]:
        """Search activities by content using full-text search"""
        try:
            params = [f"%{search_term}%"]
            param_index = 2

            base_query = """
                SELECT * FROM activities
                WHERE content ILIKE $1
                AND processing_status = 'complete'
            """

            if user_id:
                base_query += f" AND user_id = ${param_index}"
                params.append(user_id)
                param_index += 1

            if activity_types:
                placeholders = ",".join(
                    [f"${i}" for i in range(param_index, param_index + len(activity_types))]
                )
                base_query += f" AND activity_type IN ({placeholders})"
                params.extend(activity_types)
                param_index += len(activity_types)

            if start_time:
                base_query += f" AND timestamp >= ${param_index}"
                params.append(start_time)
                param_index += 1

            if end_time:
                base_query += f" AND timestamp <= ${param_index}"
                params.append(end_time)
                param_index += 1

            base_query += " ORDER BY timestamp DESC"

            if pagination:
                base_query += f" LIMIT {pagination.page_size} OFFSET {pagination.offset}"

            result = await self.execute_raw_query(base_query, params, "all")

            return [Activity(**dict(row)) for row in result] if result else []

        except Exception as e:
            self.logger.error(f"Error searching activities by content: {str(e)}")
            raise ReflectAIError(
                f"Failed to search activities: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    async def get_activities_by_classification(
        self,
        classification_key: str,
        classification_value: Any,
        user_id: uuid.UUID | None = None,
        pagination: PaginationParams | None = None,
    ) -> list[Activity]:
        """Get activities by classification data (JSONB field)"""
        try:
            params = [classification_key, str(classification_value)]
            param_index = 3

            base_query = """
                SELECT * FROM activities
                WHERE classification->>$1 = $2
                AND processing_status = 'complete'
            """

            if user_id:
                base_query += f" AND user_id = ${param_index}"
                params.append(user_id)
                param_index += 1

            base_query += " ORDER BY timestamp DESC"

            if pagination:
                base_query += f" LIMIT {pagination.page_size} OFFSET {pagination.offset}"

            result = await self.execute_raw_query(base_query, params, "all")

            return [Activity(**dict(row)) for row in result] if result else []

        except Exception as e:
            self.logger.error(f"Error getting activities by classification: {str(e)}")
            raise ReflectAIError(
                f"Failed to get activities by classification: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    # =====================
    # Correlation and Threading
    # =====================

    async def get_correlated_activities(
        self, correlation_id: str, exclude_activity_id: uuid.UUID | None = None
    ) -> list[Activity]:
        """Get activities with the same correlation ID"""
        try:
            filters = [FilterCriteria("correlation_id", "eq", correlation_id)]

            if exclude_activity_id:
                filters.append(FilterCriteria("id", "ne", exclude_activity_id))

            sorts = [SortCriteria("timestamp", "asc")]

            return await self.find_all(filters, sorts)

        except Exception as e:
            self.logger.error(f"Error getting correlated activities: {str(e)}")
            raise ReflectAIError(
                f"Failed to get correlated activities: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    async def get_thread_activities(
        self, thread_ts: str, channel_id: str | None = None
    ) -> list[Activity]:
        """Get activities in a Slack thread"""
        try:
            filters = [FilterCriteria("thread_ts", "eq", thread_ts)]

            if channel_id:
                filters.append(FilterCriteria("channel_id", "eq", channel_id))

            sorts = [SortCriteria("timestamp", "asc")]

            return await self.find_all(filters, sorts)

        except Exception as e:
            self.logger.error(f"Error getting thread activities: {str(e)}")
            raise ReflectAIError(
                f"Failed to get thread activities: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    # =====================
    # Bulk Operations for High Volume
    # =====================

    async def bulk_mark_processed(
        self,
        activity_ids: list[uuid.UUID],
        processing_status: str = "complete",
        confidence_score: float | None = None,
    ) -> int:
        """Bulk update processing status for multiple activities"""
        try:
            update_data = {"processing_status": processing_status}

            if confidence_score is not None:
                update_data["confidence_score"] = Decimal(str(confidence_score))

            filters = [FilterCriteria("id", "in", activity_ids)]

            updated_count = await self.update_many(filters, update_data)
            self.logger.info(f"Bulk updated processing status for {updated_count} activities")

            return updated_count

        except Exception as e:
            self.logger.error(f"Error bulk updating processing status: {str(e)}")
            raise ReflectAIError(
                f"Failed to bulk update processing status: {str(e)}", ErrorSeverity.HIGH
            ) from e

    async def bulk_add_competencies(
        self, activity_competency_map: dict[uuid.UUID, list[str]]
    ) -> int:
        """Bulk add competency areas to multiple activities"""
        try:
            update_count = 0

            # Process in batches to avoid overwhelming the database
            batch_size = 100
            activity_ids = list(activity_competency_map.keys())

            for i in range(0, len(activity_ids), batch_size):
                batch_ids = activity_ids[i : i + batch_size]

                # Get current activities to merge competency areas
                current_activities = await self.find_all([FilterCriteria("id", "in", batch_ids)])

                for activity in current_activities:
                    new_competencies = activity_competency_map[activity.id]
                    current_areas = activity.competency_areas or []
                    merged_areas = list(set(current_areas + new_competencies))

                    await self.update(activity.id, {"competency_areas": merged_areas})
                    update_count += 1

            self.logger.info(f"Bulk added competencies to {update_count} activities")
            return update_count

        except Exception as e:
            self.logger.error(f"Error bulk adding competencies: {str(e)}")
            raise ReflectAIError(
                f"Failed to bulk add competencies: {str(e)}", ErrorSeverity.HIGH
            ) from e

    async def archive_old_activities(
        self, older_than_days: int = 90, batch_size: int = 1000, dry_run: bool = False
    ) -> dict[str, int]:
        """Archive old activities by updating processing_status"""
        try:
            cutoff_date = datetime.now(UTC) - timedelta(days=older_than_days)

            # Count activities to archive
            count_query = """
                SELECT COUNT(*) FROM activities
                WHERE timestamp < $1 AND processing_status != 'archived'
            """

            total_count = await self.execute_raw_query(count_query, [cutoff_date], "val")

            if dry_run:
                return {"total_to_archive": total_count or 0, "archived": 0, "dry_run": True}

            # Archive in batches
            archived_count = 0

            while True:
                # Update a batch
                update_query = """
                    UPDATE activities
                    SET processing_status = 'archived', updated_at = now()
                    WHERE id IN (
                        SELECT id FROM activities
                        WHERE timestamp < $1 AND processing_status != 'archived'
                        LIMIT $2
                    )
                """

                result = await self.execute_raw_query(
                    update_query, [cutoff_date, batch_size], "rowcount"
                )

                batch_archived = result if result else 0
                archived_count += batch_archived

                if batch_archived == 0:
                    break

                self.logger.info(f"Archived {archived_count}/{total_count} activities")

            return {
                "total_to_archive": total_count or 0,
                "archived": archived_count,
                "dry_run": False,
            }

        except Exception as e:
            self.logger.error(f"Error archiving old activities: {str(e)}")
            raise ReflectAIError(
                f"Failed to archive activities: {str(e)}", ErrorSeverity.HIGH
            ) from e
