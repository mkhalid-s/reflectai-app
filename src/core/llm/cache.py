"""
Semantic Cache for LLM Responses

Implements  Response Caching Layer with semantic similarity matching,
TTL configuration, and cache effectiveness monitoring.
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from src.shared import get_logger

logger = get_logger(__name__)


class CacheStrategy(str, Enum):
    """Cache strategy configurations."""

    DISABLED = "disabled"  # No caching
    DEFAULT = "default"  # Standard caching (30min TTL)
    AGGRESSIVE = "aggressive"  # Long-term caching (1hr TTL)
    INTENT_BASED = "intent_based"  # TTL based on intent type


@dataclass
class CacheEntry:
    """Individual cache entry with metadata."""

    key: str
    content: str
    metadata: dict[str, Any]
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_accessed: datetime = field(default_factory=lambda: datetime.now(UTC))
    access_count: int = 0
    ttl_seconds: int = 1800  # 30 minutes default
    tags: list[str] = field(default_factory=list)

    @property
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return datetime.now(UTC) - self.created_at > timedelta(seconds=self.ttl_seconds)

    def access(self):
        """Mark entry as accessed."""
        self.last_accessed = datetime.now(UTC)
        self.access_count += 1


@dataclass
class CacheStats:
    """Cache performance statistics."""

    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    expired_entries: int = 0
    evicted_entries: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0


class SemanticSimilarity:
    """Simple semantic similarity calculator for cache matching."""

    def __init__(self, similarity_threshold: float = 0.95):
        self.similarity_threshold = similarity_threshold

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate semantic similarity between two texts.

        For production, using simple token-based similarity.
        production+ will implement proper embedding-based similarity.
        """

        # Normalize texts
        text1 = text1.lower().strip()
        text2 = text2.lower().strip()

        # Exact match
        if text1 == text2:
            return 1.0

        # Token-based similarity (Jaccard similarity)
        tokens1 = set(text1.split())
        tokens2 = set(text2.split())

        if not tokens1 and not tokens2:
            return 1.0

        if not tokens1 or not tokens2:
            return 0.0

        intersection = len(tokens1.intersection(tokens2))
        union = len(tokens1.union(tokens2))

        return intersection / union if union > 0 else 0.0

    def is_similar(self, text1: str, text2: str) -> bool:
        """Check if two texts are similar enough for cache matching."""
        return self.calculate_similarity(text1, text2) >= self.similarity_threshold


class SemanticCache:
    """
    Semantic cache with similarity-based matching and intelligent TTL.

    Features:
    - Semantic similarity matching for cache hits
    - Intent-based TTL configuration
    - LRU eviction policy
    - Cache effectiveness monitoring
    - Tag-based cache invalidation
    """

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.entries: dict[str, CacheEntry] = {}
        self.stats = CacheStats()
        self.similarity_calculator = SemanticSimilarity()

        # TTL configurations by intent/category
        self.ttl_config = {
            "intent_classification": 30 * 60,  # 30 minutes
            "analysis": 60 * 60,  # 1 hour
            "help": 24 * 60 * 60,  # 24 hours
            "greeting": 60 * 60,  # 1 hour
            "competency_assessment": 45 * 60,  # 45 minutes
            "career_advice": 2 * 60 * 60,  # 2 hours
            "synthesis": 30 * 60,  # 30 minutes
            "default": 30 * 60,  # 30 minutes
        }

        logger.info(
            "Semantic cache initialized",
            extra={
                "max_size": max_size,
                "similarity_threshold": self.similarity_calculator.similarity_threshold,
            },
        )

    def get(
        self,
        query: str,
        context: dict[str, Any] | None = None,
        strategy: CacheStrategy = CacheStrategy.DEFAULT,
    ) -> dict[str, Any] | None:
        """
        Retrieve cached response with semantic similarity matching.

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

        # Clean expired entries first
        self._clean_expired_entries()

        # Look for exact match first
        exact_key = self._generate_key(query, context)
        if exact_key in self.entries:
            entry = self.entries[exact_key]
            if not entry.is_expired:
                entry.access()
                self.stats.cache_hits += 1

                logger.debug(
                    "Cache hit (exact match)",
                    extra={"key": exact_key[:16], "access_count": entry.access_count},
                )

                return {
                    "content": entry.content,
                    "metadata": entry.metadata,
                    "from_cache": True,
                    "cache_type": "exact_match",
                }

        # Look for semantic similarity match
        similar_entry = self._find_similar_entry(query, context)
        if similar_entry:
            similar_entry.access()
            self.stats.cache_hits += 1

            logger.debug(
                "Cache hit (semantic match)",
                extra={"key": similar_entry.key[:16], "access_count": similar_entry.access_count},
            )

            return {
                "content": similar_entry.content,
                "metadata": similar_entry.metadata,
                "from_cache": True,
                "cache_type": "semantic_match",
            }

        # No cache hit
        self.stats.cache_misses += 1
        return None

    def set(
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
        Cache response with metadata and TTL configuration.

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

        # Determine TTL based on strategy and intent
        ttl_seconds = self._calculate_ttl(intent, strategy)

        # Create cache entry
        entry = CacheEntry(
            key=cache_key,
            content=response,
            metadata=metadata or {},
            ttl_seconds=ttl_seconds,
            tags=tags or [],
        )

        # Store entry
        self.entries[cache_key] = entry

        # Evict if necessary
        self._evict_if_necessary()

        logger.debug(
            "Response cached",
            extra={
                "key": cache_key[:16],
                "intent": intent,
                "ttl_seconds": ttl_seconds,
                "strategy": strategy.value,
            },
        )

    def _generate_key(self, query: str, context: dict[str, Any] | None = None) -> str:
        """Generate cache key from query and context."""

        # Normalize query
        normalized_query = query.lower().strip()

        # Include relevant context in key
        key_data = {"query": normalized_query}

        if context:
            # Include only cache-relevant context fields
            relevant_context = {
                k: v
                for k, v in context.items()
                if k in ["user_role", "department", "intent", "complexity"]
            }
            if relevant_context:
                key_data["context"] = relevant_context

        # Generate hash
        key_json = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_json.encode()).hexdigest()

    def _find_similar_entry(
        self, query: str, context: dict[str, Any] | None = None
    ) -> CacheEntry | None:
        """Find semantically similar cache entry."""

        for entry in self.entries.values():
            if entry.is_expired:
                continue

            # Extract original query from metadata or use content for comparison
            original_query = entry.metadata.get("original_query", "")

            if self.similarity_calculator.is_similar(query, original_query):
                return entry

        return None

    def _calculate_ttl(self, intent: str, strategy: CacheStrategy) -> int:
        """Calculate TTL based on intent and strategy."""

        base_ttl = self.ttl_config.get(intent, self.ttl_config["default"])

        if strategy == CacheStrategy.AGGRESSIVE:
            return base_ttl * 2  # Double TTL for aggressive caching
        elif strategy == CacheStrategy.INTENT_BASED:
            return base_ttl  # Use intent-specific TTL
        else:  # DEFAULT
            return 30 * 60  # 30 minutes standard

    def _clean_expired_entries(self):
        """Remove expired entries from cache."""

        expired_keys = [key for key, entry in self.entries.items() if entry.is_expired]

        for key in expired_keys:
            del self.entries[key]
            self.stats.expired_entries += 1

        if expired_keys:
            logger.debug(f"Cleaned {len(expired_keys)} expired cache entries")

    def _evict_if_necessary(self):
        """Evict least recently used entries if cache is full."""

        if len(self.entries) <= self.max_size:
            return

        # Sort by last access time (LRU)
        sorted_entries = sorted(self.entries.items(), key=lambda x: x[1].last_accessed)

        # Remove oldest entries
        entries_to_remove = len(self.entries) - self.max_size + 10  # Remove extra for buffer

        for i in range(entries_to_remove):
            if i < len(sorted_entries):
                key_to_remove = sorted_entries[i][0]
                del self.entries[key_to_remove]
                self.stats.evicted_entries += 1

        logger.debug(f"Evicted {entries_to_remove} LRU cache entries")

    def invalidate_by_tag(self, tag: str):
        """Invalidate all cache entries with specified tag."""

        keys_to_remove = [key for key, entry in self.entries.items() if tag in entry.tags]

        for key in keys_to_remove:
            del self.entries[key]

        logger.info(f"Invalidated {len(keys_to_remove)} cache entries with tag: {tag}")

    def invalidate_by_user(self, user_id: str):
        """Invalidate all cache entries for specific user."""

        keys_to_remove = [
            key for key, entry in self.entries.items() if entry.metadata.get("user_id") == user_id
        ]

        for key in keys_to_remove:
            del self.entries[key]

        logger.info(f"Invalidated {len(keys_to_remove)} cache entries for user: {user_id}")

    def clear(self):
        """Clear all cache entries."""

        entry_count = len(self.entries)
        self.entries.clear()

        logger.info(f"Cleared all {entry_count} cache entries")

    def get_stats(self) -> dict[str, Any]:
        """Get cache performance statistics."""

        # Calculate additional metrics
        total_entries = len(self.entries)
        expired_count = sum(1 for entry in self.entries.values() if entry.is_expired)

        # Most accessed entries
        top_entries = sorted(self.entries.values(), key=lambda e: e.access_count, reverse=True)[:5]

        return {
            "performance": {
                "total_requests": self.stats.total_requests,
                "cache_hits": self.stats.cache_hits,
                "cache_misses": self.stats.cache_misses,
                "hit_rate": self.stats.hit_rate,
                "expired_entries": self.stats.expired_entries,
                "evicted_entries": self.stats.evicted_entries,
            },
            "storage": {
                "total_entries": total_entries,
                "max_size": self.max_size,
                "utilization": total_entries / self.max_size if self.max_size > 0 else 0,
                "expired_count": expired_count,
            },
            "top_entries": [
                {
                    "key": entry.key[:16],
                    "access_count": entry.access_count,
                    "created_at": entry.created_at.isoformat(),
                    "tags": entry.tags,
                }
                for entry in top_entries
            ],
            "ttl_config": self.ttl_config.copy(),
        }

    def get_effectiveness_report(self) -> dict[str, Any]:
        """Generate cache effectiveness analysis."""

        if self.stats.total_requests == 0:
            return {"message": "No cache requests yet"}

        # Calculate effectiveness metrics
        hit_rate = self.stats.hit_rate
        miss_rate = 1.0 - hit_rate

        # Categorize effectiveness
        if hit_rate >= 0.5:
            effectiveness = "Excellent"
        elif hit_rate >= 0.3:
            effectiveness = "Good"
        elif hit_rate >= 0.15:
            effectiveness = "Fair"
        else:
            effectiveness = "Poor"

        # Generate recommendations
        recommendations = []

        if hit_rate < 0.3:
            recommendations.append("Consider increasing TTL for frequently accessed content")
            recommendations.append("Review query similarity threshold")

        if self.stats.evicted_entries > self.stats.cache_hits:
            recommendations.append("Consider increasing cache size")

        if self.stats.expired_entries > self.stats.cache_hits * 2:
            recommendations.append("Review TTL configuration - too many entries expiring unused")

        return {
            "effectiveness_rating": effectiveness,
            "hit_rate": hit_rate,
            "miss_rate": miss_rate,
            "total_requests": self.stats.total_requests,
            "recommendations": recommendations,
            "cost_savings_estimate": f"{hit_rate * 100:.1f}% reduction in LLM API calls",
        }


# Global semantic cache instance
_semantic_cache: SemanticCache | None = None


def get_semantic_cache() -> SemanticCache:
    """Get or create global semantic cache instance."""
    global _semantic_cache
    if _semantic_cache is None:
        _semantic_cache = SemanticCache()
    return _semantic_cache


def create_cache_backend(
    backend_type: str = "memory",
    namespace: str = "llm_cache",
    max_size: int = 1000,
    enable_fallback: bool = True,
):
    """
    Factory function to create appropriate cache backend.

    Args:
        backend_type: 'memory' for in-memory, 'redis' for Redis-backed
        namespace: Redis namespace (only used for Redis backend)
        max_size: Max cache size
        enable_fallback: Enable fallback to in-memory if Redis fails

    Returns:
        Cache backend instance (SemanticCache or RedisCacheBackend)
    """
    if backend_type == "redis":
        try:
            from .redis_cache_backend import get_redis_cache_backend

            logger.info("Creating Redis cache backend")
            return get_redis_cache_backend(
                namespace=namespace, max_size=max_size, enable_fallback=enable_fallback
            )
        except ImportError as e:
            logger.warning(f"Redis backend not available, using in-memory cache: {e}")
            return SemanticCache(max_size=max_size)
    elif backend_type == "memory":
        logger.info("Creating in-memory cache backend")
        return SemanticCache(max_size=max_size)
    else:
        raise ValueError(f"Unknown cache backend type: {backend_type}")


def get_cache_backend_from_env():
    """
    Get cache backend based on environment configuration.

    Reads CACHE_BACKEND environment variable:
    - 'redis': Use Redis-backed cache
    - 'memory' or not set: Use in-memory cache
    """
    import os

    backend_type = os.getenv("CACHE_BACKEND", "memory").lower()
    max_size = int(os.getenv("CACHE_MAX_SIZE", "1000"))
    enable_fallback = os.getenv("CACHE_ENABLE_FALLBACK", "true").lower() == "true"

    return create_cache_backend(
        backend_type=backend_type, max_size=max_size, enable_fallback=enable_fallback
    )
