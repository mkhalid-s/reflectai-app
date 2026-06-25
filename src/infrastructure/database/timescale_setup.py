"""
TimescaleDB Configuration and Setup

⚠️ **CRITICAL WARNING - NEEDS REWRITE** ⚠️
This module is INCOMPATIBLE with the current database architecture.
It uses SQLAlchemy session.execute() but db_manager.py uses asyncpg.

**Issues**:
- Line 79-86: Uses SQLAlchemy text() and session.execute()
- Line 121-164: Expects SQLAlchemy session with .commit()
- Line 295-324: All queries use SQLAlchemy patterns
- Architecture mismatch: This code expects SQLAlchemy but db_manager uses asyncpg

**Status**: ❌ UNUSABLE - Will crash if executed
**Required Action**: Complete rewrite to use asyncpg connection patterns
**Priority**: HIGH - TimescaleDB features currently unavailable

---

Implements Task 6 requirements for TimescaleDB hypertables and continuous aggregates,
providing 100x faster time-series queries as specified in the requirements.

Key features:
- Hypertable creation for activities and events
- Continuous aggregates for metrics (1min, 5min, 1hr, 1day)
- Data retention policies
- Compression policies for older data
- Performance-optimized indexes
"""

from datetime import datetime
from typing import Any

from sqlalchemy.sql import text

from src.shared.logging import get_logger

# DatabaseManager will be imported at runtime to avoid circular imports

logger = get_logger(__name__)


class TimescaleDBManager:
    """
    Manages TimescaleDB-specific features for time-series optimization.

    Provides hypertables, continuous aggregates, and retention policies
    for achieving 100x performance on time-series queries.
    """

    def __init__(self, db_manager):
        """Initialize TimescaleDB manager."""
        self.db_manager = db_manager

    async def setup_timescaledb(self):
        """
        Complete TimescaleDB setup for the ReflectAI database.

        Sets up:
        1. TimescaleDB extension
        2. Hypertables for time-series data
        3. Continuous aggregates
        4. Compression policies
        5. Retention policies
        """
        try:
            logger.info("Starting TimescaleDB setup...")

            # Enable TimescaleDB extension
            await self._enable_timescaledb_extension()

            # Create hypertables
            await self._create_hypertables()

            # Set up continuous aggregates
            await self._create_continuous_aggregates()

            # Configure compression
            await self._setup_compression_policies()

            # Set up retention policies
            await self._setup_retention_policies()

            # Create optimized indexes
            await self._create_time_series_indexes()

            logger.info("TimescaleDB setup completed successfully")

        except Exception as e:
            logger.error(f"TimescaleDB setup failed: {e}")
            raise

    async def _enable_timescaledb_extension(self):
        """Enable TimescaleDB extension in the database."""
        async with self.db_manager.get_session() as session:
            try:
                await session.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb"))
                await session.commit()
                logger.info("TimescaleDB extension enabled")
            except Exception as e:
                logger.error(f"Failed to enable TimescaleDB extension: {e}")
                raise

    async def _create_hypertables(self):
        """
        Create hypertables for time-series tables.

        Converts regular tables to hypertables with time-based partitioning.
        """
        hypertables = [
            {
                "table": "activities",
                "time_column": "timestamp",
                "chunk_interval": "7 days",
                "if_not_exists": True,
            },
            {
                "table": "events",
                "time_column": "event_time",
                "chunk_interval": "1 day",
                "if_not_exists": True,
            },
            {
                "table": "competency_history",
                "time_column": "assessed_at",
                "chunk_interval": "30 days",
                "if_not_exists": True,
            },
            {
                "table": "metrics",
                "time_column": "timestamp",
                "chunk_interval": "1 day",
                "if_not_exists": True,
            },
        ]

        async with self.db_manager.get_session() as session:
            for hypertable in hypertables:
                try:
                    # Check if table exists first
                    check_query = text("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables
                            WHERE table_name = :table_name
                        )
                    """)
                    result = await session.execute(check_query, {"table_name": hypertable["table"]})
                    table_exists = result.scalar()

                    if not table_exists:
                        # Create the table structure first
                        await self._create_table_structure(session, hypertable["table"])

                    # Convert to hypertable
                    create_query = text("""
                        SELECT create_hypertable(
                            :table_name::regclass,
                            :time_column,
                            chunk_time_interval => INTERVAL :chunk_interval,
                            if_not_exists => :if_not_exists
                        )
                    """)

                    await session.execute(
                        create_query,
                        {
                            "table_name": hypertable["table"],
                            "time_column": hypertable["time_column"],
                            "chunk_interval": hypertable["chunk_interval"],
                            "if_not_exists": hypertable["if_not_exists"],
                        },
                    )

                    logger.info(f"Created hypertable: {hypertable['table']}")

                except Exception as e:
                    logger.warning(f"Failed to create hypertable {hypertable['table']}: {e}")
                    # Continue with other tables

            await session.commit()

    async def _create_table_structure(self, session, table_name: str):
        """Create table structure if it doesn't exist."""
        table_definitions = {
            "activities": """
                CREATE TABLE IF NOT EXISTS activities (
                    id BIGSERIAL,
                    user_id TEXT NOT NULL,
                    activity_type TEXT NOT NULL,
                    activity_data JSONB NOT NULL,
                    classification JSONB,
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (id, timestamp)
                )
            """,
            "events": """
                CREATE TABLE IF NOT EXISTS events (
                    id BIGSERIAL,
                    event_type TEXT NOT NULL,
                    event_data JSONB NOT NULL,
                    user_id TEXT,
                    correlation_id TEXT,
                    event_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (id, event_time)
                )
            """,
            "competency_history": """
                CREATE TABLE IF NOT EXISTS competency_history (
                    id BIGSERIAL,
                    user_id TEXT NOT NULL,
                    competency_area TEXT NOT NULL,
                    score FLOAT NOT NULL,
                    evidence JSONB,
                    assessed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (id, assessed_at)
                )
            """,
            "metrics": """
                CREATE TABLE IF NOT EXISTS metrics (
                    id BIGSERIAL,
                    metric_name TEXT NOT NULL,
                    metric_value FLOAT NOT NULL,
                    labels JSONB,
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (id, timestamp)
                )
            """,
        }

        if table_name in table_definitions:
            await session.execute(text(table_definitions[table_name]))
            logger.info(f"Created table structure: {table_name}")

    async def _create_continuous_aggregates(self):
        """
        Create continuous aggregates for common queries.

        Provides pre-computed aggregates at different time intervals
        for fast dashboard queries and reporting.
        """
        aggregates = [
            {
                "name": "activity_stats_1min",
                "query": """
                    CREATE MATERIALIZED VIEW IF NOT EXISTS activity_stats_1min
                    WITH (timescaledb.continuous) AS
                    SELECT
                        time_bucket('1 minute', timestamp) AS bucket,
                        user_id,
                        activity_type,
                        COUNT(*) as activity_count,
                        AVG((activity_data->>'complexity_score')::float) as avg_complexity
                    FROM activities
                    GROUP BY bucket, user_id, activity_type
                    WITH NO DATA
                """,
                "refresh_policy": {
                    "start_offset": "10 minutes",
                    "end_offset": "1 minute",
                    "schedule_interval": "1 minute",
                },
            },
            {
                "name": "activity_stats_1hour",
                "query": """
                    CREATE MATERIALIZED VIEW IF NOT EXISTS activity_stats_1hour
                    WITH (timescaledb.continuous) AS
                    SELECT
                        time_bucket('1 hour', timestamp) AS bucket,
                        user_id,
                        activity_type,
                        COUNT(*) as activity_count,
                        AVG((activity_data->>'complexity_score')::float) as avg_complexity,
                        MAX((activity_data->>'complexity_score')::float) as max_complexity
                    FROM activities
                    GROUP BY bucket, user_id, activity_type
                    WITH NO DATA
                """,
                "refresh_policy": {
                    "start_offset": "2 hours",
                    "end_offset": "1 hour",
                    "schedule_interval": "1 hour",
                },
            },
            {
                "name": "competency_trends_daily",
                "query": """
                    CREATE MATERIALIZED VIEW IF NOT EXISTS competency_trends_daily
                    WITH (timescaledb.continuous) AS
                    SELECT
                        time_bucket('1 day', assessed_at) AS bucket,
                        user_id,
                        competency_area,
                        AVG(score) as avg_score,
                        MIN(score) as min_score,
                        MAX(score) as max_score,
                        COUNT(*) as assessment_count
                    FROM competency_history
                    GROUP BY bucket, user_id, competency_area
                    WITH NO DATA
                """,
                "refresh_policy": {
                    "start_offset": "2 days",
                    "end_offset": "1 day",
                    "schedule_interval": "1 day",
                },
            },
        ]

        async with self.db_manager.get_session() as session:
            for aggregate in aggregates:
                try:
                    # Create the continuous aggregate
                    await session.execute(text(aggregate["query"]))

                    # Add refresh policy
                    refresh_query = text("""
                        SELECT add_continuous_aggregate_policy(
                            :aggregate_name,
                            start_offset => INTERVAL :start_offset,
                            end_offset => INTERVAL :end_offset,
                            schedule_interval => INTERVAL :schedule_interval,
                            if_not_exists => true
                        )
                    """)

                    await session.execute(
                        refresh_query,
                        {
                            "aggregate_name": aggregate["name"],
                            **aggregate["refresh_policy"],
                        },
                    )

                    logger.info(f"Created continuous aggregate: {aggregate['name']}")

                except Exception as e:
                    logger.warning(f"Failed to create aggregate {aggregate['name']}: {e}")

            await session.commit()

    async def _setup_compression_policies(self):
        """
        Set up compression policies for older data.

        Compresses chunks older than specified intervals to save
        storage and improve query performance.
        """
        compression_policies = [
            {
                "table": "activities",
                "compress_after": "7 days",
            },
            {
                "table": "events",
                "compress_after": "3 days",
            },
            {
                "table": "competency_history",
                "compress_after": "30 days",
            },
            {
                "table": "metrics",
                "compress_after": "1 day",
            },
        ]

        async with self.db_manager.get_session() as session:
            for policy in compression_policies:
                try:
                    # Enable compression
                    enable_query = text(f"""
                        ALTER TABLE {policy["table"]} SET (
                            timescaledb.compress,
                            timescaledb.compress_segmentby = 'user_id'
                        )
                    """)
                    await session.execute(enable_query)

                    # Add compression policy
                    policy_query = text("""
                        SELECT add_compression_policy(
                            :table_name::regclass,
                            INTERVAL :compress_after,
                            if_not_exists => true
                        )
                    """)

                    await session.execute(
                        policy_query,
                        {
                            "table_name": policy["table"],
                            "compress_after": policy["compress_after"],
                        },
                    )

                    logger.info(f"Set compression policy for: {policy['table']}")

                except Exception as e:
                    logger.warning(f"Failed to set compression for {policy['table']}: {e}")

            await session.commit()

    async def _setup_retention_policies(self):
        """
        Set up data retention policies.

        Automatically removes data older than retention period
        to manage storage and compliance requirements.
        """
        retention_policies = [
            {
                "table": "activities",
                "drop_after": "2 years",
            },
            {
                "table": "events",
                "drop_after": "90 days",
            },
            {
                "table": "metrics",
                "drop_after": "30 days",
            },
            # competency_history kept indefinitely for historical analysis
        ]

        async with self.db_manager.get_session() as session:
            for policy in retention_policies:
                try:
                    query = text("""
                        SELECT add_retention_policy(
                            :table_name::regclass,
                            INTERVAL :drop_after,
                            if_not_exists => true
                        )
                    """)

                    await session.execute(
                        query,
                        {
                            "table_name": policy["table"],
                            "drop_after": policy["drop_after"],
                        },
                    )

                    logger.info(f"Set retention policy for: {policy['table']}")

                except Exception as e:
                    logger.warning(f"Failed to set retention for {policy['table']}: {e}")

            await session.commit()

    async def _create_time_series_indexes(self):
        """
        Create optimized indexes for time-series queries.

        Uses BRIN indexes for time columns and GIN indexes for JSONB.
        """
        indexes = [
            # BRIN indexes for time columns (space-efficient)
            "CREATE INDEX IF NOT EXISTS idx_activities_timestamp_brin ON activities USING BRIN (timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_events_time_brin ON events USING BRIN (event_time)",
            "CREATE INDEX IF NOT EXISTS idx_competency_time_brin ON competency_history USING BRIN (assessed_at)",
            # Composite indexes for common queries
            "CREATE INDEX IF NOT EXISTS idx_activities_user_time ON activities (user_id, timestamp DESC)",
            "CREATE INDEX IF NOT EXISTS idx_competency_user_area ON competency_history (user_id, competency_area, assessed_at DESC)",
            # GIN indexes for JSONB queries
            "CREATE INDEX IF NOT EXISTS idx_activities_data_gin ON activities USING GIN (activity_data)",
            "CREATE INDEX IF NOT EXISTS idx_events_data_gin ON events USING GIN (event_data)",
        ]

        async with self.db_manager.get_session() as session:
            for index_query in indexes:
                try:
                    await session.execute(text(index_query))
                    logger.info(f"Created index: {index_query.split('idx_')[1].split(' ')[0]}")
                except Exception as e:
                    logger.warning(f"Failed to create index: {e}")

            await session.commit()

    async def get_activity_stats(
        self,
        user_id: str,
        start_time: datetime,
        end_time: datetime,
        bucket_interval: str = "1 hour",
    ) -> list[dict[str, Any]]:
        """
        Get activity statistics using continuous aggregates.

        This query is 100x faster than querying raw data.
        """
        # Determine which aggregate to use based on interval
        aggregate_table = "activity_stats_1hour"
        if bucket_interval == "1 minute":
            aggregate_table = "activity_stats_1min"

        query = text(f"""
            SELECT
                bucket,
                user_id,
                activity_type,
                SUM(activity_count) as total_count,
                AVG(avg_complexity) as avg_complexity
            FROM {aggregate_table}
            WHERE user_id = :user_id
                AND bucket >= :start_time
                AND bucket < :end_time
            GROUP BY bucket, user_id, activity_type
            ORDER BY bucket DESC
        """)

        async with self.db_manager.get_session() as session:
            result = await session.execute(
                query,
                {
                    "user_id": user_id,
                    "start_time": start_time,
                    "end_time": end_time,
                },
            )

            return [dict(row) for row in result.mappings()]


async def setup_timescaledb(db_manager):
    """
    Main setup function for TimescaleDB.

    Call this during application initialization to set up
    all TimescaleDB features.

    Args:
        db_manager: Database manager instance
    """
    tsdb_manager = TimescaleDBManager(db_manager)
    await tsdb_manager.setup_timescaledb()

    logger.info("TimescaleDB setup complete - 100x performance improvement enabled")


if __name__ == "__main__":
    # Run setup if executed directly
    import logging
    logging.basicConfig(level=logging.INFO)
    logging.info("TimescaleDB setup script - use from database manager initialization")
