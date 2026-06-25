"""
Activity Data Manager for ReflectAI

Implements  Activity Data Store and Management operations:
- Time-series optimized activity storage and retrieval
- Batch operations for high-throughput data ingestion
- Activity querying with filtering, pagination, and aggregation
- Data validation and integrity checks
- Performance monitoring and optimization

Provides high-level interface for all activity data operations.
"""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field

from src.infrastructure.cache.redis_manager import RedisManager, get_redis_manager
from src.infrastructure.database.db_manager import get_database_manager
from src.infrastructure.database.models.activity import Activity
from src.infrastructure.database.repositories import ActivityRepository
from src.shared import ErrorSeverity, ReflectAIError, get_logger

from ..models.activity_data import (
    ActivityData,
    ActivityDataModel,
    ActivityQuery,
    ActivitySummary,
)


class ActivityInsertResult(BaseModel):
    """Result of activity insertion operation"""

    success: bool = Field(..., description="Whether insertion succeeded")
    activity_id: str | None = Field(None, description="Inserted activity ID")
    errors: list[str] = Field(default_factory=list, description="Any errors encountered")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    cache_updated: bool = Field(default=False, description="Whether cache was updated")


class ActivityBatchResult(BaseModel):
    """Result of batch activity operations"""

    total_activities: int = Field(..., description="Total activities in batch")
    successful_inserts: int = Field(..., description="Number of successful insertions")
    failed_inserts: int = Field(default=0, description="Number of failed insertions")
    errors: list[str] = Field(default_factory=list, description="Batch processing errors")
    processing_time_ms: float = Field(..., description="Total processing time")
    batch_id: str | None = Field(None, description="Batch identifier")


class ActivityAggregation(BaseModel):
    """Activity aggregation results"""

    user_id: str = Field(..., description="User identifier")
    time_period: str = Field(..., description="Time period of aggregation")
    total_activities: int = Field(..., description="Total activities in period")
    by_type: dict[str, int] = Field(default_factory=dict, description="Activities by type")
    by_competency: dict[str, int] = Field(
        default_factory=dict, description="Activities by competency"
    )
    by_source: dict[str, int] = Field(default_factory=dict, description="Activities by source")
    avg_confidence: float = Field(default=0.0, description="Average confidence score")
    top_competencies: list[str] = Field(
        default_factory=list, description="Most active competencies"
    )


class ActivityDataManager:
    """High-level activity data management"""

    def __init__(self, database_manager=None, redis_manager: RedisManager | None = None):
        self.logger = get_logger("storage.activity_manager")
        self.db = database_manager or get_database_manager()
        self.redis = redis_manager or get_redis_manager()
        self.repository = ActivityRepository()

        # Performance tracking
        self.operation_stats = {
            "inserts": {"count": 0, "total_time": 0.0},
            "queries": {"count": 0, "total_time": 0.0},
            "updates": {"count": 0, "total_time": 0.0},
            "deletes": {"count": 0, "total_time": 0.0},
        }

        # TimescaleDB manager (lazy initialization)
        self._timescale = None

    async def _get_timescale(self):
        """Get TimescaleDB manager instance (lazy initialization)"""
        if not self._timescale:
            if not self.db.is_initialized:
                await self.db.initialize()
            self._timescale = self.db.get_timescale_manager()
        return self._timescale

    def _convert_to_db_model(self, activity: ActivityData) -> Activity:
        """Convert ActivityData to SQLAlchemy Activity model"""
        return Activity(
            id=activity.activity_id,
            user_id=activity.user_id,
            content=activity.description or activity.title,
            activity_type=activity.activity_type.value if activity.activity_type else None,
            source=activity.source.value if activity.source else "system",
            classification=activity.metadata or {},
            metrics=activity.competencies or {},
            processing_status="pending",
            correlation_id=getattr(activity, "correlation_id", None),
            thread_ts=getattr(activity, "thread_ts", None),
            confidence_score=activity.confidence_score,
            competency_areas=list(activity.competencies.keys()) if activity.competencies else [],
            timestamp=activity.timestamp or datetime.now(UTC),
        )

    async def insert_activity(
        self, activity: ActivityData, update_cache: bool = True, validate_duplicates: bool = True
    ) -> ActivityInsertResult:
        """Insert a single activity with validation and caching"""

        start_time = datetime.now(UTC)

        try:
            # Validate for duplicates if requested
            if validate_duplicates:
                duplicate = await self._check_duplicate_activity(activity)
                if duplicate:
                    return ActivityInsertResult(
                        success=False,
                        errors=["Duplicate activity detected"],
                        processing_time_ms=0.0,
                    )

            # Convert to SQLAlchemy model
            db_activity = self._convert_to_db_model(activity)

            # Insert using repository pattern
            created_activity = await self.repository.create(db_activity)

            # Update cache if requested
            cache_updated = False
            if update_cache:
                cache_updated = await self._update_activity_cache(activity)

            # Update user activity summary
            await self._update_activity_summary(activity)

            # Track performance
            processing_time = (datetime.now(UTC) - start_time).total_seconds() * 1000
            self.operation_stats["inserts"]["count"] += 1
            self.operation_stats["inserts"]["total_time"] += processing_time

            self.logger.info(f"Successfully inserted activity {created_activity.id}")

            return ActivityInsertResult(
                success=True,
                activity_id=str(created_activity.id),
                processing_time_ms=processing_time,
                cache_updated=cache_updated,
            )

        except Exception as e:
            error_msg = f"Failed to insert activity: {str(e)}"
            self.logger.error(error_msg)

            processing_time = (datetime.now(UTC) - start_time).total_seconds() * 1000

            return ActivityInsertResult(
                success=False, errors=[error_msg], processing_time_ms=processing_time
            )

    async def insert_activity_batch(
        self, activities: list[ActivityData], batch_size: int = 100, update_cache: bool = True
    ) -> ActivityBatchResult:
        """Insert activities in batches for performance"""

        start_time = datetime.now(UTC)
        total_activities = len(activities)
        successful_inserts = 0
        errors = []
        batch_id = str(uuid.uuid4())

        try:
            # Process in batches
            for i in range(0, total_activities, batch_size):
                batch = activities[i : i + batch_size]

                try:
                    # Convert to database models
                    db_models = [
                        ActivityDataModel.from_activity_data(activity) for activity in batch
                    ]

                    # Prepare batch insert query
                    insert_query = """
                        INSERT INTO activities (
                            activity_id, user_id, team_id, timestamp, activity_type,
                            title, description, source, confidence_score, metadata,
                            competencies, created_at, updated_at, version
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                    """

                    # Prepare parameters for batch
                    batch_params = []
                    for model in db_models:
                        batch_params.append(
                            [
                                model.activity_id,
                                model.user_id,
                                model.team_id,
                                model.timestamp,
                                model.activity_type,
                                model.title,
                                model.description,
                                model.source,
                                model.confidence_score,
                                model.metadata,
                                model.competencies,
                                model.created_at,
                                model.updated_at,
                                model.version,
                            ]
                        )

                    # Execute batch insert
                    timescale = await self._get_timescale()
                    result_count = await timescale.execute_batch(
                        insert_query, batch_params, query_type="activity_batch_insert"
                    )

                    successful_inserts += result_count

                    # Update cache for recent activities if requested
                    if update_cache:
                        recent_activities = [
                            a
                            for a in batch
                            if a.timestamp > datetime.now(UTC) - timedelta(hours=24)
                        ]
                        for activity in recent_activities[:10]:  # Limit cache updates
                            await self._update_activity_cache(activity)

                    self.logger.info(f"Successfully inserted batch of {result_count} activities")

                except Exception as e:
                    error_msg = f"Batch insert failed for activities {i}-{i + len(batch)}: {str(e)}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)

            # Update activity summaries in background
            asyncio.create_task(self._update_batch_summaries(activities))

            processing_time = (datetime.now(UTC) - start_time).total_seconds() * 1000

            return ActivityBatchResult(
                total_activities=total_activities,
                successful_inserts=successful_inserts,
                failed_inserts=total_activities - successful_inserts,
                errors=errors,
                processing_time_ms=processing_time,
                batch_id=batch_id,
            )

        except Exception as e:
            error_msg = f"Batch insert operation failed: {str(e)}"
            self.logger.error(error_msg)

            processing_time = (datetime.now(UTC) - start_time).total_seconds() * 1000

            return ActivityBatchResult(
                total_activities=total_activities,
                successful_inserts=successful_inserts,
                failed_inserts=total_activities - successful_inserts,
                errors=[error_msg],
                processing_time_ms=processing_time,
                batch_id=batch_id,
            )

    async def query_activities(self, query: ActivityQuery) -> list[ActivityData]:
        """Query activities with filtering and pagination"""

        start_time = datetime.now(UTC)

        try:
            # Build WHERE clause
            where_conditions = []
            params = []
            param_count = 1

            if query.user_id:
                where_conditions.append(f"user_id = ${param_count}")
                params.append(query.user_id)
                param_count += 1

            if query.team_id:
                where_conditions.append(f"team_id = ${param_count}")
                params.append(query.team_id)
                param_count += 1

            if query.activity_types:
                type_placeholders = ", ".join(
                    [f"${param_count + i}" for i in range(len(query.activity_types))]
                )
                where_conditions.append(f"activity_type IN ({type_placeholders})")
                params.extend([t.value for t in query.activity_types])
                param_count += len(query.activity_types)

            if query.competencies:
                where_conditions.append(f"competencies && ${param_count}")
                params.append(query.competencies)
                param_count += 1

            if query.start_date:
                where_conditions.append(f"timestamp >= ${param_count}")
                params.append(query.start_date)
                param_count += 1

            if query.end_date:
                where_conditions.append(f"timestamp <= ${param_count}")
                params.append(query.end_date)
                param_count += 1

            if query.days_back:
                cutoff_date = datetime.now(UTC) - timedelta(days=query.days_back)
                where_conditions.append(f"timestamp >= ${param_count}")
                params.append(cutoff_date)
                param_count += 1

            if query.min_confidence:
                where_conditions.append(f"confidence_score >= ${param_count}")
                params.append(query.min_confidence)
                param_count += 1

            if query.sources:
                source_placeholders = ", ".join(
                    [f"${param_count + i}" for i in range(len(query.sources))]
                )
                where_conditions.append(f"source IN ({source_placeholders})")
                params.extend([s.value for s in query.sources])
                param_count += len(query.sources)

            # Build final query
            base_query = """
                SELECT activity_id, user_id, team_id, timestamp, activity_type,
                       title, description, source, confidence_score, metadata,
                       competencies, created_at, updated_at, version
                FROM activities
            """

            if where_conditions:
                base_query += " WHERE " + " AND ".join(where_conditions)

            base_query += f" ORDER BY {query.order_by} {query.order_direction.upper()}"
            base_query += f" LIMIT ${param_count} OFFSET ${param_count + 1}"
            params.extend([query.limit, query.offset])

            # Execute query
            timescale = await self._get_timescale()
            rows = await timescale.execute_query(
                base_query, params, fetch="all", query_type="activity_query"
            )

            # Convert to ActivityData objects
            activities = []
            for row in rows:
                db_model = ActivityDataModel(**dict(row))
                activity = db_model.to_activity_data()
                activities.append(activity)

            # Track performance
            processing_time = (datetime.now(UTC) - start_time).total_seconds() * 1000
            self.operation_stats["queries"]["count"] += 1
            self.operation_stats["queries"]["total_time"] += processing_time

            self.logger.info(
                f"Query returned {len(activities)} activities in {processing_time:.2f}ms"
            )

            return activities

        except Exception as e:
            self.logger.error(f"Activity query failed: {str(e)}")
            raise ReflectAIError(
                f"Failed to query activities: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    async def get_activity_by_id(self, activity_id: str | uuid.UUID) -> ActivityData | None:
        """Get a specific activity by ID"""

        try:
            # Try cache first
            cache_key = f"activity:{str(activity_id)}"
            cached_activity = await self.redis.get("activity", cache_key)

            if cached_activity:
                return ActivityData(**cached_activity)

            # Query database
            query = """
                SELECT activity_id, user_id, team_id, timestamp, activity_type,
                       title, description, source, confidence_score, metadata,
                       competencies, created_at, updated_at, version
                FROM activities
                WHERE activity_id = $1
            """

            timescale = await self._get_timescale()
            row = await timescale.execute_query(
                query, [str(activity_id)], fetch="one", query_type="activity_get_by_id"
            )

            if row:
                db_model = ActivityDataModel(**dict(row))
                activity = db_model.to_activity_data()

                # Cache the result
                await self.redis.set("activity", cache_key, activity.dict())

                return activity

            return None

        except Exception as e:
            self.logger.error(f"Failed to get activity {activity_id}: {str(e)}")
            return None

    async def get_user_activity_summary(
        self,
        user_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[ActivitySummary]:
        """Get user activity summaries for date range"""

        try:
            # Default to last 30 days if no range specified
            if not end_date:
                end_date = datetime.now(UTC)
            if not start_date:
                start_date = end_date - timedelta(days=30)

            query = """
                SELECT user_id, date, total_activities, activity_types,
                       competency_activities, avg_confidence_score,
                       high_confidence_activities, activity_velocity, competency_breadth
                FROM user_activity_summary
                WHERE user_id = $1 AND date BETWEEN $2 AND $3
                ORDER BY date DESC
            """

            timescale = await self._get_timescale()
            rows = await timescale.execute_query(
                query,
                [user_id, start_date.date(), end_date.date()],
                fetch="all",
                query_type="activity_summary_query",
            )

            summaries = []
            for row in rows:
                summary = ActivitySummary(**dict(row))
                summaries.append(summary)

            return summaries

        except Exception as e:
            self.logger.error(f"Failed to get activity summary for user {user_id}: {str(e)}")
            return []

    async def aggregate_activities(
        self, user_id: str, time_period: str = "30_days", group_by: list[str] | None = None
    ) -> ActivityAggregation:
        """Aggregate activity data for analytics"""

        try:
            # Calculate time range
            if time_period == "7_days":
                start_date = datetime.now(UTC) - timedelta(days=7)
            elif time_period == "30_days":
                start_date = datetime.now(UTC) - timedelta(days=30)
            elif time_period == "90_days":
                start_date = datetime.now(UTC) - timedelta(days=90)
            else:
                start_date = datetime.now(UTC) - timedelta(days=30)  # Default

            # Base aggregation query
            base_query = """
                SELECT
                    COUNT(*) as total_activities,
                    AVG(confidence_score) as avg_confidence,
                    activity_type,
                    source,
                    unnest(competencies) as competency
                FROM activities
                WHERE user_id = $1 AND timestamp >= $2
                GROUP BY activity_type, source, competency
            """

            timescale = await self._get_timescale()
            rows = await timescale.execute_query(
                base_query, [user_id, start_date], fetch="all", query_type="activity_aggregation"
            )

            # Process aggregation results
            total_activities = 0
            by_type = {}
            by_source = {}
            by_competency = {}
            confidence_sum = 0.0
            confidence_count = 0

            for row in rows:
                row_dict = dict(row)
                count = row_dict.get("total_activities", 0)
                total_activities += count

                # Aggregate by type
                activity_type = row_dict.get("activity_type", "unknown")
                by_type[activity_type] = by_type.get(activity_type, 0) + count

                # Aggregate by source
                source = row_dict.get("source", "unknown")
                by_source[source] = by_source.get(source, 0) + count

                # Aggregate by competency
                competency = row_dict.get("competency")
                if competency:
                    by_competency[competency] = by_competency.get(competency, 0) + count

                # Aggregate confidence
                avg_conf = row_dict.get("avg_confidence", 0.0)
                if avg_conf:
                    confidence_sum += avg_conf * count
                    confidence_count += count

            avg_confidence = confidence_sum / confidence_count if confidence_count > 0 else 0.0

            # Get top competencies
            top_competencies = sorted(
                by_competency.keys(), key=lambda k: by_competency[k], reverse=True
            )[:5]

            return ActivityAggregation(
                user_id=user_id,
                time_period=time_period,
                total_activities=total_activities,
                by_type=by_type,
                by_competency=by_competency,
                by_source=by_source,
                avg_confidence=avg_confidence,
                top_competencies=top_competencies,
            )

        except Exception as e:
            self.logger.error(f"Activity aggregation failed for user {user_id}: {str(e)}")
            return ActivityAggregation(user_id=user_id, time_period=time_period, total_activities=0)

    async def _check_duplicate_activity(self, activity: ActivityData) -> bool:
        """Check if activity is a duplicate"""

        try:
            # Check for activities with same user, timestamp (±5 min), and description
            time_buffer = timedelta(minutes=5)
            start_time = activity.timestamp - time_buffer
            end_time = activity.timestamp + time_buffer

            query = """
                SELECT COUNT(*) as count
                FROM activities
                WHERE user_id = $1
                AND timestamp BETWEEN $2 AND $3
                AND description = $4
                LIMIT 1
            """

            timescale = await self._get_timescale()
            result = await timescale.execute_query(
                query,
                [str(activity.user_id), start_time, end_time, activity.description],
                fetch="val",
                query_type="duplicate_check",
            )

            return result > 0

        except Exception as e:
            self.logger.error(f"Duplicate check failed: {str(e)}")
            return False

    async def _update_activity_cache(self, activity: ActivityData) -> bool:
        """Update activity cache"""

        try:
            cache_key = str(activity.activity_id)
            return await self.redis.set("activity", cache_key, activity.dict())
        except Exception as e:
            self.logger.error(f"Cache update failed: {str(e)}")
            return False

    async def _update_activity_summary(self, activity: ActivityData):
        """Update user activity summary for the day"""

        try:
            activity_date = activity.timestamp.date()

            # Upsert daily summary
            upsert_query = """
                INSERT INTO user_activity_summary
                (user_id, date, total_activities, activity_types, competency_activities,
                 avg_confidence_score, high_confidence_activities, competency_breadth, updated_at)
                VALUES ($1, $2, 1, $3, $4, $5, $6, $7, NOW())
                ON CONFLICT (user_id, date) DO UPDATE SET
                    total_activities = user_activity_summary.total_activities + 1,
                    activity_types = user_activity_summary.activity_types || EXCLUDED.activity_types,
                    competency_activities = user_activity_summary.competency_activities || EXCLUDED.competency_activities,
                    avg_confidence_score = (user_activity_summary.avg_confidence_score * user_activity_summary.total_activities + EXCLUDED.avg_confidence_score) / (user_activity_summary.total_activities + 1),
                    high_confidence_activities = CASE WHEN EXCLUDED.avg_confidence_score > 0.8 THEN user_activity_summary.high_confidence_activities + 1 ELSE user_activity_summary.high_confidence_activities END,
                    competency_breadth = GREATEST(user_activity_summary.competency_breadth, EXCLUDED.competency_breadth),
                    updated_at = NOW()
            """

            # Build activity type JSON
            activity_types_json = {activity.activity_type.value: 1}

            # Build competency JSON
            competency_json = {}
            for comp in activity.competencies:
                competency_json[comp] = 1

            params = [
                str(activity.user_id),
                activity_date,
                activity_types_json,
                competency_json,
                activity.confidence_score,
                1 if activity.confidence_score > 0.8 else 0,
                len(activity.competencies),
            ]

            timescale = await self._get_timescale()
            await timescale.execute_query(
                upsert_query, params, query_type="activity_summary_update"
            )

        except Exception as e:
            self.logger.error(f"Activity summary update failed: {str(e)}")

    async def _update_batch_summaries(self, activities: list[ActivityData]):
        """Update activity summaries for batch of activities (background task)"""

        try:
            # Group activities by user and date
            user_date_activities = {}
            for activity in activities:
                key = (str(activity.user_id), activity.timestamp.date())
                if key not in user_date_activities:
                    user_date_activities[key] = []
                user_date_activities[key].append(activity)

            # Update each user-date combination
            for (user_id, date), day_activities in user_date_activities.items():
                await self._update_user_date_summary(user_id, date, day_activities)

        except Exception as e:
            self.logger.error(f"Batch summary update failed: {str(e)}")

    async def _update_user_date_summary(
        self, user_id: str, date: datetime, activities: list[ActivityData]
    ):
        """Update summary for specific user and date"""

        try:
            # Calculate aggregates
            total_count = len(activities)
            activity_types = {}
            competency_activities = {}
            confidence_sum = 0.0
            high_confidence_count = 0
            competencies_set = set()

            for activity in activities:
                # Activity types
                activity_type = activity.activity_type.value
                activity_types[activity_type] = activity_types.get(activity_type, 0) + 1

                # Competencies
                for comp in activity.competencies:
                    competency_activities[comp] = competency_activities.get(comp, 0) + 1
                    competencies_set.add(comp)

                # Confidence
                confidence_sum += activity.confidence_score
                if activity.confidence_score > 0.8:
                    high_confidence_count += 1

            avg_confidence = confidence_sum / total_count if total_count > 0 else 0.0

            # Upsert summary
            upsert_query = """
                INSERT INTO user_activity_summary
                (user_id, date, total_activities, activity_types, competency_activities,
                 avg_confidence_score, high_confidence_activities, competency_breadth, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
                ON CONFLICT (user_id, date) DO UPDATE SET
                    total_activities = EXCLUDED.total_activities,
                    activity_types = EXCLUDED.activity_types,
                    competency_activities = EXCLUDED.competency_activities,
                    avg_confidence_score = EXCLUDED.avg_confidence_score,
                    high_confidence_activities = EXCLUDED.high_confidence_activities,
                    competency_breadth = EXCLUDED.competency_breadth,
                    updated_at = NOW()
            """

            params = [
                user_id,
                date,
                total_count,
                activity_types,
                competency_activities,
                avg_confidence,
                high_confidence_count,
                len(competencies_set),
            ]

            timescale = await self._get_timescale()
            await timescale.execute_query(
                upsert_query, params, query_type="user_date_summary_update"
            )

        except Exception as e:
            self.logger.error(f"User date summary update failed: {str(e)}")

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
_global_activity_manager: ActivityDataManager | None = None


def get_activity_data_manager() -> ActivityDataManager:
    """Get global activity data manager instance"""
    global _global_activity_manager
    if _global_activity_manager is None:
        _global_activity_manager = ActivityDataManager()
    return _global_activity_manager
