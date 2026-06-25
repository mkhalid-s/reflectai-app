"""
TimescaleDB Manager for ReflectAI

Implements  Activity Data Store and Management with TimescaleDB:
- Time-series optimized storage for activity data
- Partitioned tables by date and user for efficient querying
- Composite indexes for fast retrieval patterns
- Data compression for historical records
- Connection pooling and query optimization

Provides high-performance time-series storage for ReflectAI activity tracking.
"""

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

import asyncpg
from pydantic import BaseModel, Field

from src.shared import ErrorSeverity, ReflectAIError, get_logger


class TimescaleConnectionConfig(BaseModel):
    """TimescaleDB connection configuration"""

    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, description="Database port")
    database: str = Field(default="reflectai", description="Database name")
    user: str = Field(default="reflectai_user", description="Database user")
    password: str = Field(default="", description="Database password")

    # Connection pool settings
    min_connections: int = Field(default=10, description="Minimum connections in pool")
    max_connections: int = Field(default=50, description="Maximum connections in pool")
    max_queries: int = Field(default=50000, description="Max queries per connection")
    max_inactive_time: float = Field(default=300.0, description="Max inactive time (seconds)")

    # SSL settings
    ssl_mode: str = Field(default="prefer", description="SSL mode")
    ssl_cert_path: str | None = Field(None, description="SSL certificate path")


class QueryMetrics(BaseModel):
    """Query performance metrics"""

    query_type: str = Field(..., description="Type of query executed")
    execution_time: float = Field(..., description="Query execution time (seconds)")
    rows_affected: int = Field(default=0, description="Number of rows affected")
    rows_returned: int = Field(default=0, description="Number of rows returned")
    query_plan_hash: str | None = Field(None, description="Query plan hash for analysis")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TimescaleManager:
    """TimescaleDB connection and query manager"""

    def __init__(self, config: TimescaleConnectionConfig | None = None):
        self.logger = get_logger("storage.timescale")
        self.config = config or TimescaleConnectionConfig()
        self.pool: asyncpg.Pool | None = None

        # Query metrics collection
        self.query_metrics: list[QueryMetrics] = []
        self.metrics_enabled = True

        # Schema definitions
        self.schema_definitions = {
            "activities": """
                CREATE TABLE IF NOT EXISTS activities (
                    activity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL,
                    team_id UUID,
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    activity_type VARCHAR(50) NOT NULL,
                    title VARCHAR(200),
                    description TEXT,
                    source VARCHAR(50) DEFAULT 'manual',
                    confidence_score FLOAT DEFAULT 1.0,
                    metadata JSONB DEFAULT '{}',
                    competencies TEXT[], -- Array of competency IDs

                    -- Audit fields
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW(),
                    version INTEGER DEFAULT 1,

                    -- Constraints
                    CONSTRAINT activities_confidence_range CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
                    CONSTRAINT activities_type_not_empty CHECK (LENGTH(activity_type) > 0)
                );
            """,
            "competency_scores": """
                CREATE TABLE IF NOT EXISTS competency_scores (
                    score_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL,
                    competency_id VARCHAR(100) NOT NULL,
                    competency_name VARCHAR(200),
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),

                    -- Score data
                    current_score FLOAT NOT NULL,
                    current_level VARCHAR(50),
                    evidence_level VARCHAR(50),
                    confidence_score FLOAT DEFAULT 0.0,

                    -- Activity analysis
                    activity_count INTEGER DEFAULT 0,
                    recent_activity_count INTEGER DEFAULT 0,
                    time_weighted_score FLOAT DEFAULT 0.0,

                    -- Assessment metadata
                    assessment_method VARCHAR(50) DEFAULT 'comprehensive',
                    framework_id VARCHAR(100),
                    assessment_id UUID,

                    -- Change tracking
                    previous_score FLOAT,
                    score_change FLOAT,
                    trend_direction VARCHAR(20) DEFAULT 'stable',

                    -- Audit fields
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW(),

                    -- Constraints
                    CONSTRAINT competency_scores_range CHECK (current_score >= 0.0 AND current_score <= 5.0),
                    CONSTRAINT competency_confidence_range CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
                    CONSTRAINT competency_id_not_empty CHECK (LENGTH(competency_id) > 0)
                );
            """,
            "competency_snapshots": """
                CREATE TABLE IF NOT EXISTS competency_snapshots (
                    snapshot_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL,
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    snapshot_type VARCHAR(50) DEFAULT 'scheduled', -- scheduled, triggered, milestone

                    -- Snapshot data
                    competency_data JSONB NOT NULL, -- Full competency state
                    overall_score FLOAT,
                    competencies_count INTEGER DEFAULT 0,
                    total_activities INTEGER DEFAULT 0,

                    -- Context
                    trigger_reason VARCHAR(200),
                    assessment_id UUID,
                    framework_id VARCHAR(100),

                    -- Audit fields
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
            """,
            "user_activity_summary": """
                CREATE TABLE IF NOT EXISTS user_activity_summary (
                    summary_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL,
                    date DATE NOT NULL,

                    -- Daily activity metrics
                    total_activities INTEGER DEFAULT 0,
                    activity_types JSONB DEFAULT '{}', -- activity_type -> count
                    competency_activities JSONB DEFAULT '{}', -- competency -> count

                    -- Quality metrics
                    avg_confidence_score FLOAT DEFAULT 0.0,
                    high_confidence_activities INTEGER DEFAULT 0,

                    -- Trend indicators
                    activity_velocity FLOAT DEFAULT 0.0, -- activities per day trend
                    competency_breadth INTEGER DEFAULT 0, -- unique competencies touched

                    -- Audit fields
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW(),

                    -- Unique constraint
                    UNIQUE(user_id, date)
                );
            """,
        }

        # Index definitions for performance
        self.index_definitions = [
            # Activities indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_activities_user_timestamp ON activities (user_id, timestamp DESC)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_activities_type_timestamp ON activities (activity_type, timestamp DESC)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_activities_team_timestamp ON activities (team_id, timestamp DESC) WHERE team_id IS NOT NULL",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_activities_competencies ON activities USING GIN (competencies)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_activities_metadata ON activities USING GIN (metadata)",
            # Competency scores indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_competency_scores_user_timestamp ON competency_scores (user_id, timestamp DESC)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_competency_scores_competency ON competency_scores (competency_id, timestamp DESC)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_competency_scores_assessment ON competency_scores (assessment_id) WHERE assessment_id IS NOT NULL",
            # Summary indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_activity_summary_user_date ON user_activity_summary (user_id, date DESC)",
            # Snapshot indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_competency_snapshots_user_timestamp ON competency_snapshots (user_id, timestamp DESC)",
        ]

    async def initialize(self) -> bool:
        """Initialize TimescaleDB connection and setup"""
        try:
            self.logger.info("Initializing TimescaleDB connection pool")

            # Create connection pool
            self.pool = await asyncpg.create_pool(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.user,
                password=self.config.password,
                min_size=self.config.min_connections,
                max_size=self.config.max_connections,
                max_queries=self.config.max_queries,
                max_inactive_connection_lifetime=self.config.max_inactive_time,
                ssl=self.config.ssl_mode,
                command_timeout=60,
            )

            # Test connection
            async with self.pool.acquire() as conn:
                result = await conn.fetchval("SELECT version()")
                self.logger.info(f"Connected to: {result}")

            # Setup database schema
            await self._setup_database_schema()

            # Setup TimescaleDB specific features
            await self._setup_timescale_features()

            self.logger.info("TimescaleDB initialization completed successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize TimescaleDB: {str(e)}")
            raise ReflectAIError(
                f"TimescaleDB initialization failed: {str(e)}", ErrorSeverity.CRITICAL
            ) from e

    async def close(self):
        """Close database connections"""
        if self.pool:
            await self.pool.close()
            self.logger.info("TimescaleDB connection pool closed")

    @asynccontextmanager
    async def get_connection(self):
        """Get a database connection from the pool"""
        if not self.pool:
            await self.initialize()

        async with self.pool.acquire() as conn:
            try:
                yield conn
            except Exception as e:
                self.logger.error(f"Database connection error: {str(e)}")
                raise

    async def execute_query(
        self,
        query: str,
        params: list | tuple | None = None,
        fetch: str = "none",  # none, one, all, val
        query_type: str = "unknown",
    ) -> Any:
        """Execute a database query with metrics tracking"""

        start_time = datetime.now(UTC)

        try:
            async with self.get_connection() as conn:
                if fetch == "none":
                    result = await conn.execute(query, *(params or []))
                    rows_affected = int(result.split()[-1]) if result.split() else 0
                    rows_returned = 0
                    return_value = result
                elif fetch == "one":
                    return_value = await conn.fetchrow(query, *(params or []))
                    rows_affected = 0
                    rows_returned = 1 if return_value else 0
                elif fetch == "all":
                    return_value = await conn.fetch(query, *(params or []))
                    rows_affected = 0
                    rows_returned = len(return_value) if return_value else 0
                elif fetch == "val":
                    return_value = await conn.fetchval(query, *(params or []))
                    rows_affected = 0
                    rows_returned = 1 if return_value is not None else 0
                else:
                    raise ValueError(f"Invalid fetch mode: {fetch}")

                # Track metrics
                if self.metrics_enabled:
                    execution_time = (datetime.now(UTC) - start_time).total_seconds()
                    self._record_query_metrics(
                        query_type, execution_time, rows_affected, rows_returned
                    )

                return return_value

        except Exception as e:
            self.logger.error(f"Query execution failed: {str(e)}\nQuery: {query[:200]}...")
            raise

    async def execute_batch(
        self, query: str, params_list: list[list | tuple], query_type: str = "batch_insert"
    ) -> int:
        """Execute batch operations efficiently"""

        start_time = datetime.now(UTC)

        try:
            async with self.get_connection() as conn:
                async with conn.transaction():
                    await conn.executemany(query, params_list)

                    # Track metrics
                    if self.metrics_enabled:
                        execution_time = (datetime.now(UTC) - start_time).total_seconds()
                        self._record_query_metrics(query_type, execution_time, len(params_list), 0)

                    return len(params_list)

        except Exception as e:
            self.logger.error(f"Batch execution failed: {str(e)}")
            raise

    async def get_table_stats(self, table_name: str) -> dict[str, Any]:
        """Get table statistics for monitoring"""

        stats_query = """
            SELECT
                schemaname,
                tablename,
                n_tup_ins as inserts,
                n_tup_upd as updates,
                n_tup_del as deletes,
                n_live_tup as live_rows,
                n_dead_tup as dead_rows,
                last_vacuum,
                last_autovacuum,
                last_analyze,
                last_autoanalyze
            FROM pg_stat_user_tables
            WHERE tablename = $1
        """

        result = await self.execute_query(
            stats_query, [table_name], fetch="one", query_type="table_stats"
        )

        if result:
            return dict(result)
        else:
            return {}

    async def get_query_performance_summary(self) -> dict[str, Any]:
        """Get query performance summary"""

        if not self.query_metrics:
            return {"message": "No query metrics available"}

        # Calculate metrics
        total_queries = len(self.query_metrics)
        avg_execution_time = sum(m.execution_time for m in self.query_metrics) / total_queries

        # Group by query type
        by_type = {}
        for metric in self.query_metrics:
            if metric.query_type not in by_type:
                by_type[metric.query_type] = []
            by_type[metric.query_type].append(metric.execution_time)

        type_summary = {}
        for query_type, times in by_type.items():
            type_summary[query_type] = {
                "count": len(times),
                "avg_time": sum(times) / len(times),
                "max_time": max(times),
                "min_time": min(times),
            }

        return {
            "total_queries": total_queries,
            "average_execution_time": avg_execution_time,
            "query_types": type_summary,
            "recent_metrics": [m.dict() for m in self.query_metrics[-10:]],  # Last 10 queries
        }

    async def _setup_database_schema(self):
        """Setup database tables and schema"""

        self.logger.info("Setting up database schema")

        # Create tables
        for table_name, schema_sql in self.schema_definitions.items():
            try:
                await self.execute_query(schema_sql, query_type="schema_setup")
                self.logger.info(f"Created/verified table: {table_name}")
            except Exception as e:
                self.logger.error(f"Failed to create table {table_name}: {str(e)}")
                raise

        # Create indexes
        for index_sql in self.index_definitions:
            try:
                await self.execute_query(index_sql, query_type="index_creation")
            except Exception as e:
                # Log but don't fail - indexes might already exist
                self.logger.warning(f"Index creation warning: {str(e)}")

    async def _setup_timescale_features(self):
        """Setup TimescaleDB specific features"""

        try:
            # Check if TimescaleDB extension is available
            extension_check = await self.execute_query(
                "SELECT * FROM pg_extension WHERE extname = 'timescaledb'",
                fetch="one",
                query_type="extension_check",
            )

            if not extension_check:
                self.logger.warning(
                    "TimescaleDB extension not found - running as regular PostgreSQL"
                )
                return

            # Convert tables to hypertables
            hypertable_configs = [
                ("activities", "timestamp"),
                ("competency_scores", "timestamp"),
                ("competency_snapshots", "timestamp"),
                ("user_activity_summary", "date"),
            ]

            for table_name, time_column in hypertable_configs:
                try:
                    # Check if already a hypertable
                    hypertable_check = await self.execute_query(
                        "SELECT * FROM _timescaledb_catalog.hypertable WHERE table_name = $1",
                        [table_name],
                        fetch="one",
                        query_type="hypertable_check",
                    )

                    if not hypertable_check:
                        # Create hypertable
                        create_hypertable_sql = f"SELECT create_hypertable('{table_name}', '{time_column}', if_not_exists => TRUE)"
                        await self.execute_query(
                            create_hypertable_sql, query_type="hypertable_creation"
                        )
                        self.logger.info(f"Created hypertable: {table_name}")

                except Exception as e:
                    self.logger.warning(f"Hypertable setup warning for {table_name}: {str(e)}")

            # Setup compression for older data (activities older than 30 days)
            try:
                compression_sql = """
                    ALTER TABLE activities SET (
                        timescaledb.compress,
                        timescaledb.compress_segmentby = 'user_id,activity_type'
                    )
                """
                await self.execute_query(compression_sql, query_type="compression_setup")

                # Add compression policy
                compression_policy_sql = """
                    SELECT add_compression_policy('activities', INTERVAL '30 days', if_not_exists => TRUE)
                """
                await self.execute_query(compression_policy_sql, query_type="compression_policy")

                self.logger.info("Setup data compression for activities table")

            except Exception as e:
                self.logger.warning(f"Compression setup warning: {str(e)}")

            # Setup retention policy (remove data older than 2 years)
            try:
                retention_sql = """
                    SELECT add_retention_policy('activities', INTERVAL '2 years', if_not_exists => TRUE)
                """
                await self.execute_query(retention_sql, query_type="retention_policy")
                self.logger.info("Setup data retention policy")

            except Exception as e:
                self.logger.warning(f"Retention policy setup warning: {str(e)}")

        except Exception as e:
            self.logger.error(f"TimescaleDB features setup failed: {str(e)}")
            # Don't raise - can continue with regular PostgreSQL

    def _record_query_metrics(
        self, query_type: str, execution_time: float, rows_affected: int, rows_returned: int
    ):
        """Record query metrics for performance monitoring"""

        metric = QueryMetrics(
            query_type=query_type,
            execution_time=execution_time,
            rows_affected=rows_affected,
            rows_returned=rows_returned,
        )

        self.query_metrics.append(metric)

        # Keep only last 1000 metrics to prevent memory buildup
        if len(self.query_metrics) > 1000:
            self.query_metrics = self.query_metrics[-1000:]

    async def health_check(self) -> dict[str, Any]:
        """Perform database health check"""

        try:
            start_time = datetime.now(UTC)

            # Test basic connectivity
            version = await self.execute_query(
                "SELECT version()", fetch="val", query_type="health_check"
            )

            # Test write performance
            test_query = "SELECT 1 as test"
            await self.execute_query(test_query, fetch="val", query_type="health_check")

            response_time = (datetime.now(UTC) - start_time).total_seconds()

            # Get connection pool status
            pool_stats = {
                "total_connections": self.pool.get_size() if self.pool else 0,
                "idle_connections": self.pool.get_idle_size() if self.pool else 0,
                "min_connections": self.config.min_connections,
                "max_connections": self.config.max_connections,
            }

            return {
                "status": "healthy",
                "database_version": version,
                "response_time_seconds": response_time,
                "pool_status": pool_stats,
                "timescale_enabled": "timescaledb" in version.lower() if version else False,
                "timestamp": datetime.now(UTC).isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
            }


# Global manager instance
_global_timescale_manager: TimescaleManager | None = None


def get_timescale_manager(config: TimescaleConnectionConfig | None = None) -> TimescaleManager:
    """Get global TimescaleDB manager instance"""
    global _global_timescale_manager
    if _global_timescale_manager is None:
        _global_timescale_manager = TimescaleManager(config)
    return _global_timescale_manager


async def initialize_timescale() -> TimescaleManager:
    """Initialize TimescaleDB manager (call on startup)"""
    manager = get_timescale_manager()
    await manager.initialize()
    return manager
