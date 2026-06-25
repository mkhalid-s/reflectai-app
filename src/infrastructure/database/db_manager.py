"""
Database Management and Initialization for ReflectAI

Implements complete database infrastructure (
- Database connection management and pooling
- Schema initialization from schema.sql
- Health checking and monitoring
- Integration with TimescaleDB manager
- Database lifecycle management

Provides centralized database management for ReflectAI platform.
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import asyncpg
from pydantic import BaseModel, Field

from src.shared import ErrorCategory, ErrorSeverity, ReflectAIError, get_logger

from ..config import get_config_manager

# Lazy import to avoid circular dependency
if TYPE_CHECKING:
    from src.core.storage.timescale_manager import TimescaleManager


class DatabaseConfig(BaseModel):
    """Database configuration"""

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

    # Schema management
    auto_create_database: bool = Field(
        default=True, description="Auto-create database if not exists"
    )
    auto_initialize_schema: bool = Field(
        default=False, description="Auto-initialize schema on startup"  # Disabled: tables already exist
    )


class DatabaseManager:
    """Centralized database management for ReflectAI"""

    def __init__(self, config: DatabaseConfig | None = None):
        self.logger = get_logger("infrastructure.database")
        self.config = config or self._load_config()

        # Managers
        self.timescale_manager: TimescaleManager | None = None
        self.admin_pool: asyncpg.Pool | None = None  # For admin operations

        # Schema path
        self.schema_path = Path(__file__).parent / "schema.sql"

        # Health status
        self.is_initialized = False
        self.last_health_check: datetime | None = None
        self.health_status: dict[str, Any] = {"status": "unknown"}

    def _load_config(self) -> DatabaseConfig:
        """Load database configuration from config manager"""
        try:
            config_manager = get_config_manager()

            # Get database configuration from streamlined config system
            config = config_manager.get_config()

            # Check for AUTO_INITIALIZE_SCHEMA environment variable
            import os
            auto_init_schema = os.getenv("AUTO_INITIALIZE_SCHEMA", "false").lower() in ("true", "1", "yes")

            db_config = {
                "host": config.database.host,
                "port": config.database.port,
                "database": config.database.name,
                "user": config.database.username,
                "password": config.database.password,
                "ssl_mode": "prefer",  # Default SSL mode
                "auto_initialize_schema": auto_init_schema,
            }

            return DatabaseConfig(**db_config)

        except Exception as e:
            self.logger.warning(f"Failed to load database config: {e}. Using defaults.")
            return DatabaseConfig()

    async def initialize(self) -> bool:
        """Initialize database infrastructure"""
        try:
            self.logger.info("Starting database infrastructure initialization")

            # Step 1: Ensure database exists
            if self.config.auto_create_database:
                await self._ensure_database_exists()

            # Step 2: Initialize TimescaleDB manager with our schema
            await self._initialize_timescale_manager()

            # Step 3: Initialize database schema
            if self.config.auto_initialize_schema:
                await self._initialize_schema()

            # Step 4: Perform health check
            health_status = await self.health_check()
            if health_status["status"] != "healthy":
                raise ReflectAIError(
                    message=f"Database health check failed: {health_status.get('error')}",
                    error_code="DATABASE_HEALTH_CHECK_FAILED",
                    category=ErrorCategory.DATABASE_ERROR,
                    severity=ErrorSeverity.CRITICAL,
                )

            self.is_initialized = True
            self.logger.info("Database infrastructure initialization completed successfully")
            return True

        except Exception as e:
            self.logger.error(f"Database initialization failed: {str(e)}")
            raise ReflectAIError(
                message=f"Database initialization failed: {str(e)}",
                error_code="DATABASE_INIT_FAILED",
                category=ErrorCategory.DATABASE_ERROR,
                severity=ErrorSeverity.CRITICAL
            ) from e

    async def close(self):
        """Close all database connections"""
        try:
            if self.timescale_manager:
                await self.timescale_manager.close()

            if self.admin_pool:
                await self.admin_pool.close()

            self.logger.info("Database connections closed")

        except Exception as e:
            self.logger.error(f"Error closing database connections: {str(e)}")

    async def _ensure_database_exists(self):
        """Ensure the target database exists"""
        try:
            # Connect to 'postgres' database to check/create target database
            admin_pool = await asyncpg.create_pool(
                host=self.config.host,
                port=self.config.port,
                database="postgres",  # Connect to default postgres database
                user=self.config.user,
                password=self.config.password,
                min_size=1,
                max_size=2,
                ssl=self.config.ssl_mode,
            )

            async with admin_pool.acquire() as conn:
                # Check if database exists
                db_exists = await conn.fetchval(
                    "SELECT 1 FROM pg_database WHERE datname = $1", self.config.database
                )

                if not db_exists:
                    self.logger.info(f"Creating database: {self.config.database}")

                    # Create database (cannot be done in transaction)
                    await conn.execute(f'CREATE DATABASE "{self.config.database}"')
                    self.logger.info(f"Database created: {self.config.database}")
                else:
                    self.logger.info(f"Database already exists: {self.config.database}")

            await admin_pool.close()

        except Exception as e:
            self.logger.error(f"Failed to ensure database exists: {str(e)}")
            raise

    async def _initialize_timescale_manager(self):
        """Initialize TimescaleDB manager"""
        # Import here to avoid circular dependency
        from src.core.storage.timescale_manager import TimescaleConnectionConfig, TimescaleManager

        try:
            # Convert our config to TimescaleConnectionConfig
            timescale_config = TimescaleConnectionConfig(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.user,
                password=self.config.password,
                min_connections=self.config.min_connections,
                max_connections=self.config.max_connections,
                max_queries=self.config.max_queries,
                max_inactive_time=self.config.max_inactive_time,
                ssl_mode=self.config.ssl_mode,
                ssl_cert_path=self.config.ssl_cert_path,
            )

            # Create and initialize TimescaleDB manager
            # NOTE: We'll override its schema setup to use our comprehensive schema
            self.timescale_manager = TimescaleManager(timescale_config)

            # Initialize connection pool (but skip schema setup for now)
            await self._initialize_timescale_pool_only()

            self.logger.info("TimescaleDB manager initialized")

        except Exception as e:
            self.logger.error(f"Failed to initialize TimescaleDB manager: {str(e)}")
            raise

    async def _initialize_timescale_pool_only(self):
        """Initialize TimescaleDB connection pool without schema setup"""
        try:
            # Create connection pool
            self.timescale_manager.pool = await asyncpg.create_pool(
                host=self.timescale_manager.config.host,
                port=self.timescale_manager.config.port,
                database=self.timescale_manager.config.database,
                user=self.timescale_manager.config.user,
                password=self.timescale_manager.config.password,
                min_size=self.timescale_manager.config.min_connections,
                max_size=self.timescale_manager.config.max_connections,
                max_queries=self.timescale_manager.config.max_queries,
                max_inactive_connection_lifetime=self.timescale_manager.config.max_inactive_time,
                ssl=self.timescale_manager.config.ssl_mode,
                command_timeout=60,
            )

            # Test connection
            async with self.timescale_manager.pool.acquire() as conn:
                result = await conn.fetchval("SELECT version()")
                self.logger.info(f"Connected to: {result}")

        except Exception as e:
            self.logger.error(f"Failed to initialize TimescaleDB pool: {str(e)}")
            raise

    async def _initialize_schema(self):
        """Initialize database schema from schema.sql"""
        try:
            if not self.schema_path.exists():
                raise ReflectAIError(
                    message=f"Schema file not found: {self.schema_path}",
                    error_code="SCHEMA_FILE_NOT_FOUND",
                    category=ErrorCategory.DATABASE_ERROR,
                    severity=ErrorSeverity.CRITICAL,
                )

            # Check if schema is already initialized by checking for ALL core tables
            # Verify all essential tables exist before skipping initialization
            core_tables = [
                'users',           # Core entity
                'activities',      # TimescaleDB hypertable
                'competencies',    # Core entity
                'workflows',       # Core entity
                'events',          # TimescaleDB hypertable
                'audit_events'     # TimescaleDB hypertable
            ]

            async with self.timescale_manager.get_connection() as conn:
                # Check if ALL core tables exist
                for table in core_tables:
                    exists = await conn.fetchval(
                        f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{table}')"
                    )
                    if not exists:
                        self.logger.info(
                            f"Core table '{table}' missing - will initialize full schema"
                        )
                        break
                else:
                    # All core tables exist
                    self.logger.info(
                        "Database schema already fully initialized (all core tables present), skipping schema.sql execution"
                    )
                    return

            self.logger.info("Initializing database schema from schema.sql")

            # Read schema SQL
            schema_sql = self.schema_path.read_text(encoding="utf-8")

            # Execute schema using TimescaleDB connection
            # Note: Cannot use transaction wrapper because TimescaleDB continuous aggregates
            # (CREATE MATERIALIZED VIEW ... WITH timescaledb.continuous)
            # cannot run inside a transaction block
            async with self.timescale_manager.get_connection() as conn:
                await conn.execute(schema_sql)

            self.logger.info("Database schema initialized successfully")

            # Now setup TimescaleDB-specific features
            await self._setup_timescale_features()

        except Exception as e:
            self.logger.error(f"Failed to initialize database schema: {str(e)}")
            raise

    async def _setup_timescale_features(self):
        """Setup TimescaleDB-specific features for our schema"""
        try:
            # Check if TimescaleDB extension is available
            extension_check = await self.timescale_manager.execute_query(
                "SELECT * FROM pg_extension WHERE extname = 'timescaledb'",
                fetch="one",
                query_type="extension_check",
            )

            if not extension_check:
                self.logger.warning(
                    "TimescaleDB extension not found - running as regular PostgreSQL"
                )
                return

            self.logger.info("Setting up TimescaleDB features")

            # Convert tables to hypertables (based on our schema)
            hypertable_configs = [
                ("activities", "created_at"),
                ("competency_history", "timestamp"),
                ("events", "timestamp"),
                ("audit_events", "timestamp"),
                ("user_sessions", "created_at"),
            ]

            for table_name, time_column in hypertable_configs:
                try:
                    # Check if already a hypertable
                    hypertable_check = await self.timescale_manager.execute_query(
                        "SELECT * FROM _timescaledb_catalog.hypertable WHERE table_name = $1",
                        [table_name],
                        fetch="one",
                        query_type="hypertable_check",
                    )

                    if not hypertable_check:
                        # Create hypertable
                        create_hypertable_sql = f"SELECT create_hypertable('{table_name}', '{time_column}', if_not_exists => TRUE)"
                        await self.timescale_manager.execute_query(
                            create_hypertable_sql, query_type="hypertable_creation"
                        )
                        self.logger.info(f"Created hypertable: {table_name}")
                    else:
                        self.logger.info(f"Hypertable already exists: {table_name}")

                except Exception as e:
                    self.logger.warning(f"Hypertable setup warning for {table_name}: {str(e)}")

            # Setup compression for older data
            await self._setup_compression_policies()

            # Setup retention policies
            await self._setup_retention_policies()

            self.logger.info("TimescaleDB features setup completed")

        except Exception as e:
            self.logger.error(f"TimescaleDB features setup failed: {str(e)}")
            # Don't raise - can continue with regular PostgreSQL

    async def _setup_compression_policies(self):
        """Setup compression policies for TimescaleDB"""
        try:
            # Activities compression (compress data older than 30 days)
            compression_sql = """
                ALTER TABLE activities SET (
                    timescaledb.compress,
                    timescaledb.compress_segmentby = 'user_id,activity_type'
                )
            """
            await self.timescale_manager.execute_query(
                compression_sql, query_type="compression_setup"
            )

            # Add compression policy
            compression_policy_sql = """
                SELECT add_compression_policy('activities', INTERVAL '30 days', if_not_exists => TRUE)
            """
            await self.timescale_manager.execute_query(
                compression_policy_sql, query_type="compression_policy"
            )

            # Events compression (compress data older than 7 days)
            events_compression_sql = """
                ALTER TABLE events SET (
                    timescaledb.compress,
                    timescaledb.compress_segmentby = 'event_type,source'
                )
            """
            await self.timescale_manager.execute_query(
                events_compression_sql, query_type="compression_setup"
            )

            events_compression_policy_sql = """
                SELECT add_compression_policy('events', INTERVAL '7 days', if_not_exists => TRUE)
            """
            await self.timescale_manager.execute_query(
                events_compression_policy_sql, query_type="compression_policy"
            )

            self.logger.info("Compression policies setup completed")

        except Exception as e:
            self.logger.warning(f"Compression policies setup warning: {str(e)}")

    async def _setup_retention_policies(self):
        """Setup retention policies for TimescaleDB"""
        try:
            # Activities retention (keep for 2 years)
            activities_retention_sql = """
                SELECT add_retention_policy('activities', INTERVAL '2 years', if_not_exists => TRUE)
            """
            await self.timescale_manager.execute_query(
                activities_retention_sql, query_type="retention_policy"
            )

            # Events retention (keep for 6 months)
            events_retention_sql = """
                SELECT add_retention_policy('events', INTERVAL '6 months', if_not_exists => TRUE)
            """
            await self.timescale_manager.execute_query(
                events_retention_sql, query_type="retention_policy"
            )

            # Audit events retention (keep for 3 years for compliance)
            audit_retention_sql = """
                SELECT add_retention_policy('audit_events', INTERVAL '3 years', if_not_exists => TRUE)
            """
            await self.timescale_manager.execute_query(
                audit_retention_sql, query_type="retention_policy"
            )

            self.logger.info("Retention policies setup completed")

        except Exception as e:
            self.logger.warning(f"Retention policies setup warning: {str(e)}")

    async def health_check(self) -> dict[str, Any]:
        """Comprehensive database health check"""
        try:
            start_time = datetime.now(UTC)

            if not self.timescale_manager or not self.timescale_manager.pool:
                return {
                    "status": "unhealthy",
                    "error": "Database not initialized",
                    "timestamp": datetime.now(UTC).isoformat(),
                }

            # Test basic connectivity and get TimescaleDB health
            timescale_health = await self.timescale_manager.health_check()

            # Additional checks specific to our schema
            table_checks = await self._check_schema_tables()

            # Check critical indexes
            index_checks = await self._check_critical_indexes()

            response_time = (datetime.now(UTC) - start_time).total_seconds()

            # Determine overall health
            overall_status = "healthy"
            if timescale_health["status"] != "healthy":
                overall_status = "unhealthy"
            elif not all(table_checks.values()):
                overall_status = "degraded"
            elif not all(index_checks.values()):
                overall_status = "degraded"

            health_result = {
                "status": overall_status,
                "response_time_seconds": response_time,
                "timescale_status": timescale_health,
                "schema_tables": table_checks,
                "critical_indexes": index_checks,
                "timestamp": datetime.now(UTC).isoformat(),
            }

            self.health_status = health_result
            self.last_health_check = datetime.now(UTC)

            return health_result

        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
            error_result = {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
            }
            self.health_status = error_result
            return error_result

    async def _check_schema_tables(self) -> dict[str, bool]:
        """Check that all required schema tables exist"""
        required_tables = [
            "users",
            "activities",
            "competencies",
            "competency_history",
            "workflows",
            "reports",
            "events",
            "audit_events",
            "user_preferences",
            "user_sessions",
        ]

        results = {}

        try:
            for table_name in required_tables:
                exists = await self.timescale_manager.execute_query(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = $1
                    )
                    """,
                    [table_name],
                    fetch="val",
                    query_type="table_check",
                )
                results[table_name] = bool(exists)

        except Exception as e:
            self.logger.error(f"Table check failed: {str(e)}")
            # Return False for all tables if check fails
            results = dict.fromkeys(required_tables, False)

        return results

    async def _check_critical_indexes(self) -> dict[str, bool]:
        """Check that critical indexes exist"""
        critical_indexes = [
            "idx_activities_user_id_timestamp",
            "idx_activities_type_timestamp",
            "idx_competency_history_user_competency_time",
            "idx_events_type_timestamp",
            "idx_users_email",
            "idx_users_slack_user_id",
        ]

        results = {}

        try:
            for index_name in critical_indexes:
                exists = await self.timescale_manager.execute_query(
                    """
                    SELECT EXISTS (
                        SELECT FROM pg_indexes
                        WHERE indexname = $1
                    )
                    """,
                    [index_name],
                    fetch="val",
                    query_type="index_check",
                )
                results[index_name] = bool(exists)

        except Exception as e:
            self.logger.error(f"Index check failed: {str(e)}")
            # Return False for all indexes if check fails
            results = dict.fromkeys(critical_indexes, False)

        return results

    def get_timescale_manager(self) -> "TimescaleManager":
        """Get the TimescaleDB manager instance"""
        if not self.timescale_manager:
            raise ReflectAIError(
                message="TimescaleDB manager not initialized",
                error_code="TIMESCALE_NOT_INITIALIZED",
                category=ErrorCategory.DATABASE_ERROR,
                severity=ErrorSeverity.CRITICAL,
            )
        return self.timescale_manager

    async def get_database_stats(self) -> dict[str, Any]:
        """Get comprehensive database statistics"""
        if not self.is_initialized:
            return {"error": "Database not initialized"}

        try:
            # Get TimescaleDB performance summary
            perf_summary = await self.timescale_manager.get_query_performance_summary()

            # Get table statistics for key tables
            table_stats = {}
            key_tables = ["activities", "users", "competencies", "events"]

            for table in key_tables:
                stats = await self.timescale_manager.get_table_stats(table)
                table_stats[table] = stats

            return {
                "performance_summary": perf_summary,
                "table_statistics": table_stats,
                "health_status": self.health_status,
                "last_health_check": self.last_health_check.isoformat()
                if self.last_health_check
                else None,
                "is_initialized": self.is_initialized,
            }

        except Exception as e:
            self.logger.error(f"Failed to get database stats: {str(e)}")
            return {"error": str(e)}


# Global database manager instance
_global_database_manager: DatabaseManager | None = None


def get_database_manager(config: DatabaseConfig | None = None) -> DatabaseManager:
    """Get global database manager instance"""
    global _global_database_manager
    if _global_database_manager is None:
        _global_database_manager = DatabaseManager(config)
    return _global_database_manager


async def initialize_database() -> DatabaseManager:
    """Initialize database manager (call on startup)"""
    manager = get_database_manager()
    await manager.initialize()
    return manager


async def close_database():
    """Close database connections (call on shutdown)"""
    global _global_database_manager
    if _global_database_manager:
        await _global_database_manager.close()
        _global_database_manager = None


async def get_database_health() -> dict[str, Any]:
    """Get database health status"""
    manager = get_database_manager()
    if not manager.is_initialized:
        return {"status": "not_initialized", "error": "Database not initialized"}
    return await manager.health_check()
