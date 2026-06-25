"""
Storage Integration Layer for ReflectAI

Implements complete integration between storage managers and new database infrastructure.
Bridges existing storage tools with production database schema and TimescaleDB optimizations.

Implements  Storage and data management tools integration:
- Integration with new database schema (15 tables)
- TimescaleDB integration for time-series data
- Redis integration for caching and sessions
- Storage manager coordination and lifecycle
- Data validation and quality assurance
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field

from src.infrastructure.cache.redis_manager import RedisManager, get_redis_manager
from src.infrastructure.database.db_manager import DatabaseManager, get_database_manager
from src.shared import ErrorSeverity, ReflectAIError, get_logger

from .models.activity_data import ActivityData


class StorageIntegrationConfig(BaseModel):
    """Configuration for storage integration"""

    # Database settings
    enable_timescale_features: bool = Field(default=True, description="Enable TimescaleDB features")
    enable_caching: bool = Field(default=True, description="Enable Redis caching")

    # Performance settings
    batch_size: int = Field(default=100, description="Default batch size for operations")
    cache_ttl_seconds: int = Field(default=3600, description="Default cache TTL")
    max_query_timeout: int = Field(default=30, description="Max query timeout (seconds)")

    # Data retention
    activity_retention_days: int = Field(default=730, description="Activity data retention (days)")
    cache_retention_hours: int = Field(default=24, description="Cache data retention (hours)")


class StorageHealthStatus(BaseModel):
    """Storage system health status"""

    status: str = Field(..., description="Overall status")
    database_status: dict[str, Any] = Field(..., description="Database health")
    redis_status: dict[str, Any] = Field(..., description="Redis health")
    integration_status: dict[str, Any] = Field(..., description="Integration health")
    performance_metrics: dict[str, Any] = Field(..., description="Performance metrics")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class IntegratedActivityManager:
    """
    Activity manager integrated with new database infrastructure

    Replaces the existing ActivityDataManager with full database schema integration
    """

    def __init__(
        self,
        database_manager: DatabaseManager | None = None,
        redis_manager: RedisManager | None = None,
    ):
        self.logger = get_logger("storage.integrated_activity")
        self.db_manager = database_manager or get_database_manager()
        self.redis_manager = redis_manager or get_redis_manager()

        # Get TimescaleDB manager from database infrastructure
        self._timescale = None

        # Performance tracking
        self.stats = {
            "operations": {"insert": 0, "query": 0, "update": 0, "delete": 0},
            "performance": {"avg_insert_ms": 0.0, "avg_query_ms": 0.0},
            "errors": {"total": 0, "by_type": {}},
        }

    async def _get_timescale(self):
        """Get TimescaleDB manager instance"""
        if not self._timescale:
            if not self.db_manager.is_initialized:
                await self.db_manager.initialize()
            self._timescale = self.db_manager.get_timescale_manager()
        return self._timescale

    async def insert_activity(self, activity: ActivityData) -> dict[str, Any]:
        """Insert activity using new database schema"""
        start_time = datetime.now(UTC)

        try:
            timescale = await self._get_timescale()

            # Use the new activities table schema
            insert_query = """
                INSERT INTO activities (
                    activity_id, user_id, activity_type, title, description,
                    source, confidence_score, metadata, competencies, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                RETURNING activity_id
            """

            params = [
                str(activity.activity_id),
                str(activity.user_id),
                activity.activity_type.value
                if hasattr(activity.activity_type, "value")
                else str(activity.activity_type),
                activity.title,
                activity.description,
                activity.source.value
                if hasattr(activity.source, "value")
                else str(activity.source),
                float(activity.confidence_score),
                activity.metadata if activity.metadata else {},
                list(activity.competencies) if activity.competencies else [],
                activity.timestamp,
            ]

            result = await timescale.execute_query(
                insert_query, params, fetch="val", query_type="activity_insert"
            )

            # Update performance stats
            processing_time = (datetime.now(UTC) - start_time).total_seconds() * 1000
            self.stats["operations"]["insert"] += 1
            self._update_performance_stats("insert", processing_time)

            # Update cache if enabled
            if hasattr(self.redis_manager, "set"):
                cache_key = f"activity:{result}"
                await self.redis_manager.set("activities", cache_key, activity.dict(), ttl=3600)

            self.logger.info(f"Successfully inserted activity {result}")

            return {"success": True, "activity_id": result, "processing_time_ms": processing_time}

        except Exception as e:
            processing_time = (datetime.now(UTC) - start_time).total_seconds() * 1000
            self.stats["errors"]["total"] += 1

            error_msg = f"Failed to insert activity: {str(e)}"
            self.logger.error(error_msg)

            return {"success": False, "error": error_msg, "processing_time_ms": processing_time}

    async def query_activities(
        self,
        user_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        activity_types: list[str] | None = None,
        competencies: list[str] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Query activities using new database schema"""
        start_time = datetime.now(UTC)

        try:
            timescale = await self._get_timescale()

            # Build dynamic query
            where_conditions = []
            params = []
            param_count = 1

            if user_id:
                where_conditions.append(f"user_id = ${param_count}")
                params.append(user_id)
                param_count += 1

            if start_date:
                where_conditions.append(f"created_at >= ${param_count}")
                params.append(start_date)
                param_count += 1

            if end_date:
                where_conditions.append(f"created_at <= ${param_count}")
                params.append(end_date)
                param_count += 1

            if activity_types:
                type_placeholders = ", ".join(
                    [f"${param_count + i}" for i in range(len(activity_types))]
                )
                where_conditions.append(f"activity_type IN ({type_placeholders})")
                params.extend(activity_types)
                param_count += len(activity_types)

            if competencies:
                where_conditions.append(f"competencies && ${param_count}")
                params.append(competencies)
                param_count += 1

            # Base query using new schema
            base_query = """
                SELECT activity_id, user_id, activity_type, title, description,
                       source, confidence_score, metadata, competencies, created_at
                FROM activities
            """

            if where_conditions:
                base_query += " WHERE " + " AND ".join(where_conditions)

            base_query += (
                f" ORDER BY created_at DESC LIMIT ${param_count} OFFSET ${param_count + 1}"
            )
            params.extend([limit, offset])

            # Execute query
            rows = await timescale.execute_query(
                base_query, params, fetch="all", query_type="activity_query"
            )

            # Convert to activity objects
            activities = []
            for row in rows:
                row_dict = dict(row)
                # Convert to ActivityData format
                activity = ActivityData(
                    activity_id=row_dict["activity_id"],
                    user_id=row_dict["user_id"],
                    activity_type=row_dict["activity_type"],
                    title=row_dict["title"],
                    description=row_dict["description"],
                    source=row_dict["source"],
                    confidence_score=row_dict["confidence_score"],
                    metadata=row_dict.get("metadata", {}),
                    competencies=row_dict.get("competencies", []),
                    timestamp=row_dict["created_at"],
                )
                activities.append(activity.dict())

            # Update performance stats
            processing_time = (datetime.now(UTC) - start_time).total_seconds() * 1000
            self.stats["operations"]["query"] += 1
            self._update_performance_stats("query", processing_time)

            self.logger.info(
                f"Query returned {len(activities)} activities in {processing_time:.2f}ms"
            )

            return {
                "success": True,
                "activities": activities,
                "count": len(activities),
                "processing_time_ms": processing_time,
            }

        except Exception as e:
            processing_time = (datetime.now(UTC) - start_time).total_seconds() * 1000
            self.stats["errors"]["total"] += 1

            error_msg = f"Failed to query activities: {str(e)}"
            self.logger.error(error_msg)

            return {
                "success": False,
                "error": error_msg,
                "activities": [],
                "count": 0,
                "processing_time_ms": processing_time,
            }

    async def get_activity_by_id(self, activity_id: str) -> dict[str, Any] | None:
        """Get specific activity by ID"""
        try:
            timescale = await self._get_timescale()

            query = """
                SELECT activity_id, user_id, activity_type, title, description,
                       source, confidence_score, metadata, competencies, created_at
                FROM activities
                WHERE activity_id = $1
            """

            row = await timescale.execute_query(
                query, [activity_id], fetch="one", query_type="activity_get_by_id"
            )

            if row:
                return dict(row)
            return None

        except Exception as e:
            self.logger.error(f"Failed to get activity {activity_id}: {str(e)}")
            return None

    def _update_performance_stats(self, operation: str, processing_time: float):
        """Update performance statistics"""
        current_avg = self.stats["performance"].get(f"avg_{operation}_ms", 0.0)
        count = self.stats["operations"][operation]

        # Calculate rolling average
        new_avg = ((current_avg * (count - 1)) + processing_time) / count
        self.stats["performance"][f"avg_{operation}_ms"] = new_avg

    async def get_stats(self) -> dict[str, Any]:
        """Get manager statistics"""
        return self.stats.copy()


class IntegratedUserProfileManager:
    """User profile manager integrated with new database schema"""

    def __init__(self, database_manager: DatabaseManager | None = None):
        self.logger = get_logger("storage.integrated_user_profile")
        self.db_manager = database_manager or get_database_manager()
        self._timescale = None

    async def _get_timescale(self):
        """Get TimescaleDB manager instance"""
        if not self._timescale:
            if not self.db_manager.is_initialized:
                await self.db_manager.initialize()
            self._timescale = self.db_manager.get_timescale_manager()
        return self._timescale

    async def create_user_profile(self, user_data: dict[str, Any]) -> dict[str, Any]:
        """Create user profile using new schema"""
        try:
            timescale = await self._get_timescale()

            insert_query = """
                INSERT INTO users (
                    user_id, email, full_name, role, team_id,
                    slack_user_id, preferences, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING user_id
            """

            params = [
                user_data["user_id"],
                user_data["email"],
                user_data.get("full_name"),
                user_data.get("role", "user"),
                user_data.get("team_id"),
                user_data.get("slack_user_id"),
                user_data.get("preferences", {}),
                datetime.now(UTC),
            ]

            result = await timescale.execute_query(
                insert_query, params, fetch="val", query_type="user_create"
            )

            return {"success": True, "user_id": result}

        except Exception as e:
            self.logger.error(f"Failed to create user profile: {str(e)}")
            return {"success": False, "error": str(e)}

    async def get_user_profile(self, user_id: str) -> dict[str, Any] | None:
        """Get user profile by ID"""
        try:
            timescale = await self._get_timescale()

            query = """
                SELECT user_id, email, full_name, role, team_id,
                       slack_user_id, preferences, created_at, updated_at, last_active
                FROM users
                WHERE user_id = $1
            """

            row = await timescale.execute_query(
                query, [user_id], fetch="one", query_type="user_get"
            )

            if row:
                return dict(row)
            return None

        except Exception as e:
            self.logger.error(f"Failed to get user profile {user_id}: {str(e)}")
            return None


class IntegratedCompetencyManager:
    """Competency management integrated with new database schema"""

    def __init__(self, database_manager: DatabaseManager | None = None):
        self.logger = get_logger("storage.integrated_competency")
        self.db_manager = database_manager or get_database_manager()
        self._timescale = None

    async def _get_timescale(self):
        """Get TimescaleDB manager instance"""
        if not self._timescale:
            if not self.db_manager.is_initialized:
                await self.db_manager.initialize()
            self._timescale = self.db_manager.get_timescale_manager()
        return self._timescale

    async def record_competency_score(self, competency_data: dict[str, Any]) -> dict[str, Any]:
        """Record competency score using new schema"""
        try:
            timescale = await self._get_timescale()

            # Insert into competency_history table (time-series optimized)
            insert_query = """
                INSERT INTO competency_history (
                    user_id, competency_id, score, level, evidence_level,
                    confidence, source, metadata, timestamp
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING id
            """

            params = [
                competency_data["user_id"],
                competency_data["competency_id"],
                competency_data["score"],
                competency_data.get("level"),
                competency_data.get("evidence_level"),
                competency_data.get("confidence", 0.8),
                competency_data.get("source", "system"),
                competency_data.get("metadata", {}),
                competency_data.get("timestamp", datetime.now(UTC)),
            ]

            result = await timescale.execute_query(
                insert_query, params, fetch="val", query_type="competency_score_record"
            )

            return {"success": True, "record_id": result}

        except Exception as e:
            self.logger.error(f"Failed to record competency score: {str(e)}")
            return {"success": False, "error": str(e)}

    async def get_user_competency_history(
        self, user_id: str, competency_id: str | None = None, days_back: int = 90
    ) -> list[dict[str, Any]]:
        """Get user competency history"""
        try:
            timescale = await self._get_timescale()

            where_conditions = ["user_id = $1", "timestamp >= $2"]
            params = [user_id, datetime.now(UTC) - timedelta(days=days_back)]
            param_count = 3

            if competency_id:
                where_conditions.append(f"competency_id = ${param_count}")
                params.append(competency_id)

            # nosec B608: SQL injection false positive - all user input is parameterized
            # where_conditions contains only hardcoded SQL fragments with $ placeholders
            query = f"""
                SELECT user_id, competency_id, score, level, evidence_level,
                       confidence, source, metadata, timestamp
                FROM competency_history
                WHERE {" AND ".join(where_conditions)}
                ORDER BY timestamp DESC
            """

            rows = await timescale.execute_query(
                query, params, fetch="all", query_type="competency_history_query"
            )

            return [dict(row) for row in rows] if rows else []

        except Exception as e:
            self.logger.error(f"Failed to get competency history: {str(e)}")
            return []


class StorageIntegrationManager:
    """
    Master storage integration manager

    Coordinates all storage managers and provides unified interface
    """

    def __init__(self, config: StorageIntegrationConfig | None = None):
        self.logger = get_logger("storage.integration_manager")
        self.config = config or StorageIntegrationConfig()

        # Initialize managers
        self.db_manager: DatabaseManager | None = None
        self.redis_manager: RedisManager | None = None

        # Integrated managers
        self.activity_manager: IntegratedActivityManager | None = None
        self.user_profile_manager: IntegratedUserProfileManager | None = None
        self.competency_manager: IntegratedCompetencyManager | None = None

        self.is_initialized = False

    async def initialize(self) -> bool:
        """Initialize all storage components"""
        try:
            self.logger.info("Initializing storage integration layer")

            # Initialize database infrastructure
            self.db_manager = get_database_manager()
            if not self.db_manager.is_initialized:
                await self.db_manager.initialize()

            # Initialize Redis
            self.redis_manager = get_redis_manager()

            # Initialize integrated managers
            self.activity_manager = IntegratedActivityManager(self.db_manager, self.redis_manager)
            self.user_profile_manager = IntegratedUserProfileManager(self.db_manager)
            self.competency_manager = IntegratedCompetencyManager(self.db_manager)

            # Verify integration health
            health_status = await self.health_check()
            if health_status.status != "healthy":
                raise ReflectAIError(
                    f"Storage integration health check failed: {health_status}",
                    ErrorSeverity.CRITICAL,
                )

            self.is_initialized = True
            self.logger.info("Storage integration layer initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Storage integration initialization failed: {str(e)}")
            raise ReflectAIError(
                f"Storage integration failed: {str(e)}", ErrorSeverity.CRITICAL
            ) from e

    async def health_check(self) -> StorageHealthStatus:
        """Comprehensive storage system health check"""
        try:
            # Check database health
            db_health = (
                await self.db_manager.health_check()
                if self.db_manager
                else {"status": "not_initialized"}
            )

            # Check Redis health (if available)
            redis_health = (
                {"status": "available"} if self.redis_manager else {"status": "not_available"}
            )

            # Check integration components
            integration_status = {
                "activity_manager": self.activity_manager is not None,
                "user_profile_manager": self.user_profile_manager is not None,
                "competency_manager": self.competency_manager is not None,
            }

            # Get performance metrics
            performance_metrics = {}
            if self.activity_manager:
                performance_metrics["activity_manager"] = await self.activity_manager.get_stats()

            # Determine overall status
            overall_status = "healthy"
            if db_health.get("status") != "healthy":
                overall_status = "unhealthy"
            elif not all(integration_status.values()):
                overall_status = "degraded"

            return StorageHealthStatus(
                status=overall_status,
                database_status=db_health,
                redis_status=redis_health,
                integration_status=integration_status,
                performance_metrics=performance_metrics,
            )

        except Exception as e:
            self.logger.error(f"Storage health check failed: {str(e)}")
            return StorageHealthStatus(
                status="unhealthy",
                database_status={"error": str(e)},
                redis_status={"status": "unknown"},
                integration_status={"error": str(e)},
                performance_metrics={},
            )

    def get_activity_manager(self) -> IntegratedActivityManager:
        """Get integrated activity manager"""
        if not self.activity_manager:
            raise ReflectAIError("Storage integration not initialized", ErrorSeverity.CRITICAL)
        return self.activity_manager

    def get_user_profile_manager(self) -> IntegratedUserProfileManager:
        """Get integrated user profile manager"""
        if not self.user_profile_manager:
            raise ReflectAIError("Storage integration not initialized", ErrorSeverity.CRITICAL)
        return self.user_profile_manager

    def get_competency_manager(self) -> IntegratedCompetencyManager:
        """Get integrated competency manager"""
        if not self.competency_manager:
            raise ReflectAIError("Storage integration not initialized", ErrorSeverity.CRITICAL)
        return self.competency_manager

    async def close(self):
        """Close all storage connections"""
        try:
            if self.db_manager:
                await self.db_manager.close()

            self.logger.info("Storage integration layer closed")
        except Exception as e:
            self.logger.error(f"Error closing storage integration: {str(e)}")


# Global storage integration manager
_global_storage_integration: StorageIntegrationManager | None = None


def get_storage_integration_manager(
    config: StorageIntegrationConfig | None = None,
) -> StorageIntegrationManager:
    """Get global storage integration manager"""
    global _global_storage_integration
    if _global_storage_integration is None:
        _global_storage_integration = StorageIntegrationManager(config)
    return _global_storage_integration


async def initialize_storage_integration() -> StorageIntegrationManager:
    """Initialize storage integration (call on startup)"""
    manager = get_storage_integration_manager()
    await manager.initialize()
    return manager


async def close_storage_integration():
    """Close storage integration (call on shutdown)"""
    global _global_storage_integration
    if _global_storage_integration:
        await _global_storage_integration.close()
        _global_storage_integration = None
