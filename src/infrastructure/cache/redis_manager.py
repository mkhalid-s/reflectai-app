"""
Redis Stack Manager for ReflectAI

Implements  User Profile Store and Cache Management with Redis Stack:
- Intelligent caching with hierarchical cache keys
- Session management with TTL and sliding windows
- Cache warming strategies and invalidation
- Redis Stack modules: JSON, Search, TimeSeries, Graph
- Connection pooling and high availability

Provides high-performance caching and session management for ReflectAI.
"""

import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import redis.asyncio as redis
from pydantic import BaseModel, Field

from src.shared import ErrorCategory, ErrorSeverity, ReflectAIError, get_logger


class TTLPolicy(Enum):
    """TTL policy types"""

    FIXED = "fixed"  # Fixed expiration time
    SLIDING = "sliding"  # Sliding window expiration (renews on access)


class RedisConnectionConfig(BaseModel):
    """Redis connection configuration"""

    host: str = Field(default="localhost", description="Redis host")
    port: int = Field(default=6379, description="Redis port")
    password: str | None = Field(None, description="Redis password")
    database: int = Field(default=0, description="Redis database number")

    # Connection pool settings
    max_connections: int = Field(default=100, description="Maximum connections in pool")
    retry_on_timeout: bool = Field(default=True, description="Retry on timeout")
    health_check_interval: int = Field(default=30, description="Health check interval (seconds)")

    # Redis Stack module settings
    enable_json: bool = Field(default=True, description="Enable RedisJSON")
    enable_search: bool = Field(default=True, description="Enable RediSearch")
    enable_timeseries: bool = Field(default=True, description="Enable RedisTimeSeries")
    enable_graph: bool = Field(default=False, description="Enable RedisGraph")

    # SSL settings
    ssl: bool = Field(default=False, description="Use SSL")
    ssl_cert_path: str | None = Field(None, description="SSL certificate path")


class CacheKeyConfig(BaseModel):
    """Cache key namespace configuration"""

    namespace: str = Field(..., description="Cache namespace")
    ttl_seconds: int = Field(default=3600, description="Default TTL in seconds")
    ttl_policy: TTLPolicy = Field(default=TTLPolicy.FIXED, description="TTL policy")
    compress_values: bool = Field(default=False, description="Compress cached values")
    max_value_size: int = Field(default=1024 * 1024, description="Max value size in bytes")


class CacheMetrics(BaseModel):
    """Cache performance metrics"""

    namespace: str = Field(..., description="Cache namespace")
    hit_count: int = Field(default=0, description="Cache hits")
    miss_count: int = Field(default=0, description="Cache misses")
    set_count: int = Field(default=0, description="Cache sets")
    delete_count: int = Field(default=0, description="Cache deletes")

    # Performance metrics
    avg_get_time: float = Field(default=0.0, description="Average get time (ms)")
    avg_set_time: float = Field(default=0.0, description="Average set time (ms)")

    # Size metrics
    total_keys: int = Field(default=0, description="Total keys in namespace")
    total_memory_bytes: int = Field(default=0, description="Total memory used")

    # Calculated metrics
    @property
    def hit_rate(self) -> float:
        total = self.hit_count + self.miss_count
        return (self.hit_count / total) if total > 0 else 0.0

    @property
    def miss_rate(self) -> float:
        return 1.0 - self.hit_rate


def parse_redis_url(redis_url: str) -> RedisConnectionConfig:
    """
    Parse Redis URL into RedisConnectionConfig.

    Supports formats:
    - redis://localhost:6379/0
    - redis://:password@localhost:6379/0
    - redis://username:password@localhost:6379/0
    """
    from urllib.parse import urlparse

    parsed = urlparse(redis_url)

    return RedisConnectionConfig(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        password=parsed.password,
        database=int(parsed.path.lstrip("/")) if parsed.path and parsed.path != "/" else 0,
    )


class RedisManager:
    """
    Redis Stack manager with advanced caching features and memory fallback.

    Features:
    - Redis Stack support (JSON, Search, TimeSeries)
    - Automatic fallback to in-memory cache when Redis unavailable
    - Connection pooling and health monitoring
    - Namespace-based cache organization
    """

    def __init__(
        self,
        config: RedisConnectionConfig | None = None,
        fallback_to_memory: bool = True
    ):
        self.logger = get_logger("storage.redis")
        self.config = config or RedisConnectionConfig()
        self.redis_pool: redis.ConnectionPool | None = None
        self.redis_client: redis.Redis | None = None
        self.fallback_to_memory = fallback_to_memory
        self._using_fallback = False
        self._memory_cache = None

        # Cache namespace configurations
        self.namespace_configs = {
            "user": CacheKeyConfig(
                namespace="user",
                ttl_seconds=3600,  # 1 hour
                ttl_policy=TTLPolicy.FIXED,
            ),
            "session": CacheKeyConfig(
                namespace="session",
                ttl_seconds=86400,  # 24 hours
                ttl_policy=TTLPolicy.FIXED,
            ),
            "activity": CacheKeyConfig(
                namespace="activity",
                ttl_seconds=1800,  # 30 minutes
                ttl_policy=TTLPolicy.FIXED,
            ),
            "home_tab": CacheKeyConfig(
                namespace="home_tab",
                ttl_seconds=3600,  # 1 hour
                ttl_policy=TTLPolicy.FIXED,
            ),
            "llm": CacheKeyConfig(
                namespace="llm",
                ttl_seconds=1800,  # 30 minutes
                ttl_policy=TTLPolicy.FIXED,
                compress_values=True,
            ),
            "competency": CacheKeyConfig(
                namespace="competency",
                ttl_seconds=7200,  # 2 hours
                ttl_policy=TTLPolicy.FIXED,
            ),
            "api": CacheKeyConfig(
                namespace="api",
                ttl_seconds=3600,  # 1 hour
                ttl_policy=TTLPolicy.FIXED,
            ),
            "workflow": CacheKeyConfig(
                namespace="workflow",
                ttl_seconds=86400,  # 24 hours
                ttl_policy=TTLPolicy.FIXED,
            ),
            "agent": CacheKeyConfig(
                namespace="agent",
                ttl_seconds=1800,  # 30 minutes
                ttl_policy=TTLPolicy.FIXED,
            ),
            "slack": CacheKeyConfig(
                namespace="slack",
                ttl_seconds=3600,  # 1 hour
                ttl_policy=TTLPolicy.FIXED,
            ),
        }

        # Metrics tracking
        self.metrics: dict[str, CacheMetrics] = {}
        for namespace in self.namespace_configs:
            self.metrics[namespace] = CacheMetrics(namespace=namespace)

    async def initialize(self) -> bool:
        """Initialize Redis connection and setup"""
        try:
            self.logger.info("Initializing Redis connection pool")

            # Create connection pool
            pool_kwargs = {
                "host": self.config.host,
                "port": self.config.port,
                "password": self.config.password,
                "db": self.config.database,
                "max_connections": self.config.max_connections,
                "retry_on_timeout": self.config.retry_on_timeout,
                "health_check_interval": self.config.health_check_interval,
            }

            # Add SSL parameters only if SSL is enabled
            if self.config.ssl:
                import ssl as ssl_module
                pool_kwargs["ssl_cert_reqs"] = ssl_module.CERT_REQUIRED
                if self.config.ssl_cert_path:
                    pool_kwargs["ssl_ca_certs"] = self.config.ssl_cert_path

            self.redis_pool = redis.ConnectionPool(**pool_kwargs)

            # Create Redis client
            self.redis_client = redis.Redis(connection_pool=self.redis_pool)

            # Test connection
            await self.redis_client.ping()
            self.logger.info("Redis connection established successfully")

            # Setup Redis Stack modules
            await self._setup_redis_modules()

            self._using_fallback = False
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize Redis: {str(e)}")

            if self.fallback_to_memory:
                self.logger.warning("Redis unavailable, falling back to in-memory cache")
                from .memory_cache import MemoryCacheManager

                self._memory_cache = MemoryCacheManager()
                self._using_fallback = True
                self.logger.info("Memory fallback cache initialized successfully")
                return True
            else:
                raise ReflectAIError(
                    message=f"Redis initialization failed: {str(e)}",
                    error_code="REDIS_INIT_FAILED",
                    category=ErrorCategory.INFRASTRUCTURE_ERROR,
                    severity=ErrorSeverity.CRITICAL,
                    recovery_suggestions=[
                        "Check Redis server status",
                        "Verify REDIS_URL configuration",
                        "Ensure Redis is accessible from application",
                        "Enable fallback_to_memory for graceful degradation",
                    ],
                    cause=e,
                ) from e

    async def close(self):
        """Close Redis connections"""
        if self.redis_client:
            await self.redis_client.close()
        if self.redis_pool:
            await self.redis_pool.disconnect()
        self.logger.info("Redis connections closed")

    @asynccontextmanager
    async def get_client(self):
        """Get Redis client (for advanced operations)"""
        if not self.redis_client:
            await self.initialize()

        try:
            yield self.redis_client
        except Exception as e:
            self.logger.error(f"Redis client error: {str(e)}")
            raise

    def _build_cache_key(
        self, namespace: str, key: str, user_context: dict[str, Any] | None = None
    ) -> str:
        """Build hierarchical cache key"""

        parts = [namespace]

        # Add user context for user-dependent operations
        if user_context and namespace in ["llm", "competency"]:
            user_id = user_context.get("user_id", "unknown")
            role_level = user_context.get("role_level", "generic")
            parts.extend([user_id, role_level])

        parts.append(key)
        return ":".join(parts)

    def _calculate_ttl(self, namespace: str, user_context: dict[str, Any] | None = None) -> int:
        """Calculate TTL based on namespace configuration"""
        config = self.namespace_configs.get(namespace, CacheKeyConfig(namespace=namespace))
        return config.ttl_seconds

    async def get(
        self,
        namespace: str,
        key: str,
        user_context: dict[str, Any] | None = None,
        default: Any = None,
    ) -> Any:
        """Get value from cache with metrics tracking"""

        # Use memory fallback if Redis unavailable
        if self._using_fallback and self._memory_cache:
            cache_key = self._build_cache_key(namespace, key, user_context)
            return await self._memory_cache.get(cache_key) or default

        start_time = datetime.now(UTC)
        cache_key = self._build_cache_key(namespace, key, user_context)

        try:
            async with self.get_client() as client:
                # Check if we should use JSON operations
                if self._should_use_json(namespace):
                    value = await client.execute_command("JSON.GET", cache_key)
                    if value:
                        result = json.loads(value)
                    else:
                        result = default
                else:
                    value = await client.get(cache_key)
                    if value:
                        result = json.loads(value) if isinstance(value, (str, bytes)) else value
                    else:
                        result = default

                # Update metrics
                metrics = self.metrics[namespace]
                if result is not None and result != default:
                    metrics.hit_count += 1

                    # Update TTL if sliding policy
                    config = self.namespace_configs.get(namespace)
                    if config and config.ttl_policy == TTLPolicy.SLIDING:
                        ttl = self._calculate_ttl(namespace, user_context)
                        await client.expire(cache_key, ttl)
                else:
                    metrics.miss_count += 1

                # Track timing
                elapsed = (datetime.now(UTC) - start_time).total_seconds() * 1000
                metrics.avg_get_time = (metrics.avg_get_time + elapsed) / 2

                return result

        except Exception as e:
            self.logger.error(f"Cache get error for {cache_key}: {str(e)}")
            self.metrics[namespace].miss_count += 1
            return default

    async def set(
        self,
        namespace: str,
        key: str,
        value: Any,
        user_context: dict[str, Any] | None = None,
        ttl_override: int | None = None,
    ) -> bool:
        """Set value in cache with TTL and strategy handling"""

        # Use memory fallback if Redis unavailable
        if self._using_fallback and self._memory_cache:
            cache_key = self._build_cache_key(namespace, key, user_context)
            ttl = ttl_override or self._calculate_ttl(namespace, user_context)
            return await self._memory_cache.set(cache_key, value, ttl)

        start_time = datetime.now(UTC)
        cache_key = self._build_cache_key(namespace, key, user_context)

        try:
            # Calculate TTL
            ttl = ttl_override or self._calculate_ttl(namespace, user_context)

            # Serialize value to JSON for consistency
            serialized_value = json.dumps(value, default=str)

            async with self.get_client() as client:
                # Use appropriate Redis operation
                if self._should_use_json(namespace) and isinstance(value, (dict, list)):
                    success = await client.execute_command(
                        "JSON.SET", cache_key, ".", serialized_value, "EX", ttl
                    )
                else:
                    success = await client.setex(cache_key, ttl, serialized_value)

                # Update metrics
                metrics = self.metrics[namespace]
                if success:
                    metrics.set_count += 1

                # Track timing
                elapsed = (datetime.now(UTC) - start_time).total_seconds() * 1000
                metrics.avg_set_time = (metrics.avg_set_time + elapsed) / 2

                return bool(success)

        except Exception as e:
            self.logger.error(f"Cache set error for {cache_key}: {str(e)}")
            return False

    async def delete(
        self, namespace: str, key: str, user_context: dict[str, Any] | None = None
    ) -> bool:
        """Delete key from cache"""

        # Use memory fallback if Redis unavailable
        if self._using_fallback and self._memory_cache:
            cache_key = self._build_cache_key(namespace, key, user_context)
            return await self._memory_cache.delete(cache_key)

        cache_key = self._build_cache_key(namespace, key, user_context)

        try:
            async with self.get_client() as client:
                result = await client.delete(cache_key)

                if result > 0:
                    self.metrics[namespace].delete_count += 1
                    return True
                return False

        except Exception as e:
            self.logger.error(f"Cache delete error for {cache_key}: {str(e)}")
            return False

    async def invalidate_pattern(self, namespace: str, pattern: str) -> int:
        """Invalidate cache keys matching pattern"""

        cache_pattern = f"{namespace}:{pattern}"

        try:
            async with self.get_client() as client:
                keys = await client.keys(cache_pattern)
                if keys:
                    deleted = await client.delete(*keys)
                    self.metrics[namespace].delete_count += deleted
                    self.logger.info(f"Invalidated {deleted} keys matching {cache_pattern}")
                    return deleted
                return 0

        except Exception as e:
            self.logger.error(f"Cache pattern invalidation error for {cache_pattern}: {str(e)}")
            return 0

    # Utility operations

    async def ping(self) -> bool:
        """
        Ping Redis server to test connectivity.

        Returns:
            True if Redis is reachable, False otherwise
        """
        if self._using_fallback and self._memory_cache:
            return True  # Memory cache is always "available"

        try:
            async with self.get_client() as client:
                response = await client.ping()
                return response
        except Exception as e:
            self.logger.error(f"Redis ping failed: {str(e)}")
            return False

    # Pub/Sub operations for event bus

    async def publish(self, channel: str, message: str) -> int:
        """
        Publish message to Redis pub/sub channel.

        Args:
            channel: Channel name
            message: Message to publish (should be JSON string)

        Returns:
            Number of subscribers that received the message
        """
        # Use memory fallback if Redis unavailable (returns 0 for pub/sub)
        if self._using_fallback and self._memory_cache:
            self.logger.warning(f"Pub/sub not available in memory fallback mode for channel: {channel}")
            return 0

        try:
            async with self.get_client() as client:
                subscribers = await client.publish(channel, message)
                self.logger.debug(f"Published to channel '{channel}': {subscribers} subscribers")
                return subscribers
        except Exception as e:
            self.logger.error(f"Failed to publish to channel '{channel}': {str(e)}")
            return 0

    async def create_pubsub(self):
        """
        Create a Redis PubSub client for pub/sub operations.

        IMPORTANT: The caller is responsible for managing the pubsub lifecycle:
        1. Subscribe to channels using pubsub.subscribe(*channels)
        2. Listen for messages using pubsub.get_message()
        3. Clean up using pubsub.unsubscribe() and pubsub.close()

        Example:
            pubsub = await redis_manager.create_pubsub()
            await pubsub.subscribe("my_channel")
            try:
                while True:
                    message = await pubsub.get_message(ignore_subscribe_messages=True)
                    if message:
                        print(message["data"])
            finally:
                await pubsub.unsubscribe()
                await pubsub.close()

        Returns:
            Redis PubSub object with persistent connection

        Raises:
            ReflectAIError: If pub/sub not available (e.g., using memory fallback)
        """
        if self._using_fallback and self._memory_cache:
            raise ReflectAIError(
                message="Pub/sub not available in memory fallback mode",
                error_category=ErrorCategory.EXTERNAL_SERVICE_ERROR,
            )

        try:
            # Create a persistent Redis client for pub/sub (not using context manager)
            # The pub/sub connection must remain open for listening
            if not self.redis_client:
                raise ReflectAIError(
                    message="Redis client not initialized",
                    error_category=ErrorCategory.INFRASTRUCTURE_ERROR,
                )

            # Create pubsub from the persistent client
            pubsub = self.redis_client.pubsub()
            self.logger.debug("Created Redis PubSub client")
            return pubsub

        except Exception as e:
            self.logger.error(f"Failed to create PubSub client: {str(e)}")
            raise ReflectAIError(
                message=f"Failed to create Redis PubSub: {str(e)}",
                error_category=ErrorCategory.INFRASTRUCTURE_ERROR,
            ) from e

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Get session data with automatic TTL refresh"""

        session_data = await self.get("session", session_id)

        if session_data:
            # Update last accessed timestamp
            session_data["last_accessed"] = datetime.now(UTC).isoformat()
            await self.set("session", session_id, session_data)

        return session_data

    async def set_session(
        self, session_id: str, session_data: dict[str, Any], user_id: str | None = None
    ) -> bool:
        """Set session data with sliding TTL"""

        # Add metadata
        session_data.update(
            {
                "session_id": session_id,
                "user_id": user_id,
                "created_at": session_data.get("created_at", datetime.now(UTC).isoformat()),
                "last_accessed": datetime.now(UTC).isoformat(),
            }
        )

        return await self.set("session", session_id, session_data)

    async def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions (background job)"""

        try:
            pattern = "session:*"
            async with self.get_client() as client:
                keys = await client.keys(pattern)
                expired_count = 0

                for key in keys:
                    ttl = await client.ttl(key)
                    if ttl <= 0:  # Expired or no TTL
                        await client.delete(key)
                        expired_count += 1

                if expired_count > 0:
                    self.logger.info(f"Cleaned up {expired_count} expired sessions")

                return expired_count

        except Exception as e:
            self.logger.error(f"Session cleanup error: {str(e)}")
            return 0

    async def warm_cache(self, namespace: str, warm_data: dict[str, Any]) -> int:
        """Warm cache with frequently accessed data"""

        warmed_count = 0

        try:
            for key, value in warm_data.items():
                success = await self.set(namespace, key, value)
                if success:
                    warmed_count += 1

            self.logger.info(f"Warmed {warmed_count} keys in {namespace} cache")
            return warmed_count

        except Exception as e:
            self.logger.error(f"Cache warming error for {namespace}: {str(e)}")
            return warmed_count

    async def get_cache_metrics(self, namespace: str | None = None) -> dict[str, Any]:
        """Get cache performance metrics"""

        if namespace:
            if namespace in self.metrics:
                return self.metrics[namespace].dict()
            else:
                return {"error": f"Namespace {namespace} not found"}

        # Return all metrics
        all_metrics = {}
        total_metrics = CacheMetrics(namespace="total")

        for ns, metrics in self.metrics.items():
            all_metrics[ns] = metrics.dict()

            # Aggregate totals
            total_metrics.hit_count += metrics.hit_count
            total_metrics.miss_count += metrics.miss_count
            total_metrics.set_count += metrics.set_count
            total_metrics.delete_count += metrics.delete_count

        all_metrics["total"] = total_metrics.dict()
        return all_metrics

    async def _setup_redis_modules(self):
        """Setup Redis Stack modules"""

        try:
            async with self.get_client() as client:
                # Check available modules
                modules = await client.execute_command("MODULE", "LIST")
                available_modules = [
                    mod[1].decode() if isinstance(mod[1], bytes) else mod[1]
                    for mod in modules
                    if len(mod) > 1
                ]

                self.logger.info(f"Available Redis modules: {available_modules}")

                # Setup module-specific configurations
                if self.config.enable_json and "ReJSON" in available_modules:
                    self.logger.info("RedisJSON module available")

                if self.config.enable_search and "search" in available_modules:
                    self.logger.info("RediSearch module available")
                    # Could setup search indexes here

                if self.config.enable_timeseries and "timeseries" in available_modules:
                    self.logger.info("RedisTimeSeries module available")
                    # Could setup time series configurations

        except Exception as e:
            self.logger.warning(f"Redis modules setup warning: {str(e)}")

    def _should_use_json(self, namespace: str) -> bool:
        """Determine if JSON operations should be used for namespace"""
        return self.config.enable_json and namespace in [
            "user",
            "session",
            "competency",
            "home_tab",
        ]

    async def health_check(self) -> dict[str, Any]:
        """Perform Redis health check"""

        try:
            start_time = datetime.now(UTC)

            async with self.get_client() as client:
                # Test basic operations
                await client.ping()

                # Test set/get
                test_key = "health_check_test"
                await client.set(test_key, "test_value", ex=60)
                await client.get(test_key)
                await client.delete(test_key)

                # Get Redis info
                info = await client.info()

                response_time = (datetime.now(UTC) - start_time).total_seconds()

                return {
                    "status": "healthy",
                    "response_time_seconds": response_time,
                    "redis_version": info.get("redis_version", "unknown"),
                    "connected_clients": info.get("connected_clients", 0),
                    "used_memory": info.get("used_memory", 0),
                    "used_memory_human": info.get("used_memory_human", "0B"),
                    "total_commands_processed": info.get("total_commands_processed", 0),
                    "cache_metrics": await self.get_cache_metrics(),
                    "timestamp": datetime.now(UTC).isoformat(),
                }

        except Exception as e:
            self.logger.error(f"Redis health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
            }


# Global manager instance
_global_redis_manager: RedisManager | None = None


def get_redis_manager(
    config: RedisConnectionConfig | None = None,
    fallback_to_memory: bool = True
) -> RedisManager:
    """
    Get global Redis manager instance with automatic memory fallback.

    If no config is provided, loads from ConfigManager (centralized configuration).

    Args:
        config: Optional Redis configuration
        fallback_to_memory: If True, falls back to in-memory cache when Redis unavailable

    Returns:
        RedisManager instance (may be using memory fallback)
    """
    global _global_redis_manager
    if _global_redis_manager is None:
        # If no config provided, load from ConfigManager
        if config is None:
            from src.infrastructure.config import get_config_manager

            config_manager = get_config_manager()
            app_config = config_manager.get_config()
            if app_config.cache.redis_url:
                config = parse_redis_url(app_config.cache.redis_url)

        _global_redis_manager = RedisManager(config, fallback_to_memory=fallback_to_memory)
    return _global_redis_manager


async def initialize_redis() -> RedisManager:
    """Initialize Redis manager (call on startup)"""
    manager = get_redis_manager()
    await manager.initialize()
    return manager
