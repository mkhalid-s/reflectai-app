"""
Redis Cache Backend for LLM Responses

Provides Redis-backed caching with:
- Distributed caching across multiple instances
- Automatic TTL management
- Fallback to in-memory cache
- Exact match caching only (semantic search removed for performance)
"""

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from src.infrastructure.cache.redis_manager import get_redis_manager
from src.shared import get_logger

from .cache import CacheEntry, CacheStats, CacheStrategy

logger = get_logger(__name__)


class RedisCacheBackend:
    """
    Redis-backed cache implementation with fallback to in-memory.

    Features:
    - Distributed caching for horizontal scaling
    - Automatic TTL in Redis
    - Fallback to in-memory if Redis unavailable
    - Exact match caching (semantic search removed for performance)
    """

    def __init__(
        self, namespace: str = "llm_cache", max_size: int = 1000, enable_fallback: bool = True
    ):
        """
        Initialize Redis cache backend.

        Args:
            namespace: Redis key namespace
            max_size: Max entries for in-memory fallback
            enable_fallback: Enable in-memory fallback if Redis fails
        """
        self.namespace = namespace
        self.max_size = max_size
        self.enable_fallback = enable_fallback

        # Redis manager (initialized lazily)
        self._redis_manager = None
        self._redis_available = None  # Tri-state: None (unknown), True, False

        # In-memory fallback cache
        self._fallback_entries: dict[str, CacheEntry] = {}

        # Statistics
        self.stats = CacheStats()

        # TTL configurations (same as SemanticCache)
        self.ttl_config = {
            "intent_classification": 30 * 60,
            "analysis": 60 * 60,
            "help": 24 * 60 * 60,
            "greeting": 60 * 60,
            "competency_assessment": 45 * 60,
            "career_advice": 2 * 60 * 60,
            "synthesis": 30 * 60,
            "default": 30 * 60,
        }

        logger.info(
            "Redis cache backend initialized",
            extra={"namespace": namespace, "fallback_enabled": enable_fallback},
        )

    async def _get_redis(self):
        """Get or initialize Redis manager."""
        if self._redis_manager is None:
            try:
                self._redis_manager = await get_redis_manager()
                self._redis_available = True
                logger.info("Redis cache backend connected to Redis")
            except Exception as e:
                logger.warning(
                    f"Redis unavailable, using in-memory fallback: {e}",
                    extra={"fallback_enabled": self.enable_fallback},
                )
                self._redis_available = False
                if not self.enable_fallback:
                    raise

        return self._redis_manager if self._redis_available else None

    def _make_redis_key(self, cache_key: str) -> str:
        """Create namespaced Redis key."""
        return f"{self.namespace}:{cache_key}"

    def _make_metadata_key(self, cache_key: str) -> str:
        """Create Redis key for metadata."""
        return f"{self.namespace}:meta:{cache_key}"

    async def get(
        self,
        query: str,
        context: dict[str, Any] | None = None,
        strategy: CacheStrategy = CacheStrategy.DEFAULT,
    ) -> dict[str, Any] | None:
        """
        Retrieve cached response with Redis or fallback.

        Args:
            query: Query text to match
            context: Additional context for matching
            strategy: Cache strategy to use

        Returns:
            Cached response data or None if not found
        """

        if strategy == CacheStrategy.DISABLED:
            return None

        self.stats.total_requests += 1

        # Generate cache key
        cache_key = self._generate_key(query, context)

        # Try Redis first
        redis = await self._get_redis()
        if redis:
            try:
                return await self._get_from_redis(redis, cache_key, query, context)
            except Exception as e:
                logger.warning(
                    f"Redis get failed, trying fallback: {e}", extra={"key": cache_key[:16]}
                )
                if self.enable_fallback:
                    return self._get_from_fallback(cache_key, query, context)
                self.stats.cache_misses += 1
                return None

        # Use fallback if Redis unavailable
        if self.enable_fallback:
            return self._get_from_fallback(cache_key, query, context)

        self.stats.cache_misses += 1
        return None

    async def _get_from_redis(
        self, redis, cache_key: str, query: str, context: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        """Get entry from Redis with exact matching."""

        redis_key = self._make_redis_key(cache_key)
        meta_key = self._make_metadata_key(cache_key)

        # Try exact match first
        content = await redis.get(redis_key)
        if content:
            metadata_raw = await redis.get(meta_key)
            metadata = json.loads(metadata_raw) if metadata_raw else {}

            self.stats.cache_hits += 1
            logger.debug("Redis cache hit (exact match)", extra={"key": cache_key[:16]})

            # Increment access count
            access_count_key = f"{redis_key}:access_count"
            await redis.incr(access_count_key)

            return {
                "content": content.decode() if isinstance(content, bytes) else content,
                "metadata": metadata,
                "from_cache": True,
                "cache_type": "exact_match_redis",
            }

        # Cache miss - no exact match found
        self.stats.cache_misses += 1
        return None

    def _get_from_fallback(
        self, cache_key: str, query: str, context: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        """Get entry from in-memory fallback."""

        # Clean expired entries
        self._clean_fallback_expired()

        # Exact match
        if cache_key in self._fallback_entries:
            entry = self._fallback_entries[cache_key]
            if not entry.is_expired:
                entry.access()
                self.stats.cache_hits += 1
                logger.debug("Fallback cache hit (exact match)", extra={"key": cache_key[:16]})
                return {
                    "content": entry.content,
                    "metadata": entry.metadata,
                    "from_cache": True,
                    "cache_type": "exact_match_fallback",
                }

        # No match found in fallback
        self.stats.cache_misses += 1
        return None

    async def set(
        self,
        query: str,
        response: str,
        metadata: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        intent: str = "default",
        tags: list[str] | None = None,
        strategy: CacheStrategy = CacheStrategy.DEFAULT,
    ):
        """
        Cache response in Redis or fallback.

        Args:
            query: Original query
            response: Response to cache
            metadata: Additional metadata
            context: Query context
            intent: Intent type for TTL calculation
            tags: Tags for cache invalidation
            strategy: Cache strategy
        """

        if strategy == CacheStrategy.DISABLED:
            return

        # Generate cache key
        cache_key = self._generate_key(query, context)

        # Determine TTL
        ttl_seconds = self._calculate_ttl(intent, strategy)

        # Enhance metadata with original query for debugging and analytics
        full_metadata = metadata or {}
        full_metadata["original_query"] = query
        full_metadata["intent"] = intent
        full_metadata["tags"] = tags or []
        full_metadata["created_at"] = datetime.now(UTC).isoformat()

        # Try Redis first
        redis = await self._get_redis()
        if redis:
            try:
                await self._set_in_redis(redis, cache_key, response, full_metadata, ttl_seconds)
                logger.debug(
                    "Response cached in Redis",
                    extra={"key": cache_key[:16], "intent": intent, "ttl_seconds": ttl_seconds},
                )
                return
            except Exception as e:
                logger.warning(
                    f"Redis set failed, using fallback: {e}", extra={"key": cache_key[:16]}
                )
                if not self.enable_fallback:
                    raise

        # Use fallback if Redis unavailable
        if self.enable_fallback:
            self._set_in_fallback(cache_key, response, full_metadata, ttl_seconds, tags)
            logger.debug(
                "Response cached in fallback",
                extra={"key": cache_key[:16], "intent": intent, "ttl_seconds": ttl_seconds},
            )

    async def _set_in_redis(
        self, redis, cache_key: str, response: str, metadata: dict[str, Any], ttl_seconds: int
    ):
        """Set entry in Redis with TTL."""

        redis_key = self._make_redis_key(cache_key)
        meta_key = self._make_metadata_key(cache_key)

        # Store content with TTL
        await redis.setex(redis_key, ttl_seconds, response)

        # Store metadata with TTL
        await redis.setex(meta_key, ttl_seconds, json.dumps(metadata))

        # Initialize access count
        access_count_key = f"{redis_key}:access_count"
        await redis.setex(access_count_key, ttl_seconds, "0")

    def _set_in_fallback(
        self,
        cache_key: str,
        response: str,
        metadata: dict[str, Any],
        ttl_seconds: int,
        tags: list[str] | None,
    ):
        """Set entry in in-memory fallback."""

        entry = CacheEntry(
            key=cache_key,
            content=response,
            metadata=metadata,
            ttl_seconds=ttl_seconds,
            tags=tags or [],
        )

        self._fallback_entries[cache_key] = entry

        # Evict if necessary
        self._evict_fallback_if_necessary()

    def _generate_key(self, query: str, context: dict[str, Any] | None = None) -> str:
        """Generate cache key from query and context."""

        normalized_query = query.lower().strip()

        key_data = {"query": normalized_query}

        if context:
            relevant_context = {
                k: v
                for k, v in context.items()
                if k in ["user_role", "department", "intent", "complexity"]
            }
            if relevant_context:
                key_data["context"] = relevant_context

        key_json = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_json.encode()).hexdigest()

    def _calculate_ttl(self, intent: str, strategy: CacheStrategy) -> int:
        """Calculate TTL based on intent and strategy."""

        base_ttl = self.ttl_config.get(intent, self.ttl_config["default"])

        if strategy == CacheStrategy.AGGRESSIVE:
            return base_ttl * 2
        elif strategy == CacheStrategy.INTENT_BASED:
            return base_ttl
        else:  # DEFAULT
            return 30 * 60

    def _clean_fallback_expired(self):
        """Remove expired entries from fallback cache."""

        expired_keys = [key for key, entry in self._fallback_entries.items() if entry.is_expired]

        for key in expired_keys:
            del self._fallback_entries[key]
            self.stats.expired_entries += 1

    def _evict_fallback_if_necessary(self):
        """Evict least recently used entries from fallback if full."""

        if len(self._fallback_entries) <= self.max_size:
            return

        # Sort by last accessed time
        sorted_entries = sorted(self._fallback_entries.items(), key=lambda x: x[1].last_accessed)

        # Evict oldest 10%
        evict_count = len(self._fallback_entries) - self.max_size
        for key, _ in sorted_entries[:evict_count]:
            del self._fallback_entries[key]
            self.stats.evicted_entries += 1

        logger.debug(f"Evicted {evict_count} fallback cache entries")

    async def clear(self, pattern: str | None = None):
        """Clear cache entries matching pattern."""

        redis = await self._get_redis()
        if redis:
            try:
                if pattern:
                    search_pattern = f"{self.namespace}:{pattern}"
                else:
                    search_pattern = f"{self.namespace}:*"

                deleted_count = 0
                async for key in redis.scan_iter(match=search_pattern):
                    await redis.delete(key)
                    deleted_count += 1

                logger.info(
                    f"Cleared {deleted_count} Redis cache entries", extra={"pattern": pattern}
                )
            except Exception as e:
                logger.error(f"Failed to clear Redis cache: {e}")

        # Clear fallback
        if pattern:
            keys_to_delete = [key for key in self._fallback_entries.keys() if pattern in key]
            for key in keys_to_delete:
                del self._fallback_entries[key]
        else:
            self._fallback_entries.clear()

        logger.info("Cleared fallback cache")

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""

        return {
            "total_requests": self.stats.total_requests,
            "cache_hits": self.stats.cache_hits,
            "cache_misses": self.stats.cache_misses,
            "hit_rate": self.stats.hit_rate,
            "expired_entries": self.stats.expired_entries,
            "evicted_entries": self.stats.evicted_entries,
            "redis_available": self._redis_available,
            "fallback_entries": len(self._fallback_entries),
        }


# Global instance
_redis_cache_backend: RedisCacheBackend | None = None


def get_redis_cache_backend(
    namespace: str = "llm_cache", max_size: int = 1000, enable_fallback: bool = True
) -> RedisCacheBackend:
    """Get or create Redis cache backend instance."""
    global _redis_cache_backend

    if _redis_cache_backend is None:
        _redis_cache_backend = RedisCacheBackend(
            namespace=namespace, max_size=max_size, enable_fallback=enable_fallback
        )

    return _redis_cache_backend
