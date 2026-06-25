"""
In-Memory Cache Manager for Development
Simulates Redis functionality without external dependencies.
"""

import builtins
import json
import time
from collections import defaultdict
from typing import Any

from src.shared.logging import get_logger

logger = get_logger(__name__)


class MemoryCacheManager:
    """In-memory cache manager that simulates Redis functionality."""

    def __init__(self):
        """Initialize memory cache."""
        self._data: dict[str, Any] = {}
        self._expiry: dict[str, float] = {}
        self._pubsub_channels: dict[str, list[callable]] = defaultdict(list)
        self._sets: dict[str, set[str]] = defaultdict(set)
        self._hashes: dict[str, dict[str, str]] = defaultdict(dict)
        logger.info("Memory cache initialized")

    def _is_expired(self, key: str) -> bool:
        """Check if a key has expired."""
        if key in self._expiry:
            if time.time() > self._expiry[key]:
                del self._data[key]
                del self._expiry[key]
                return True
        return False

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """Set a key-value pair with optional TTL."""
        try:
            # Serialize value if it's complex
            if isinstance(value, (dict, list)):
                value = json.dumps(value)

            self._data[key] = value

            if ttl:
                self._expiry[key] = time.time() + ttl

            logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Cache SET error: {e}")
            return False

    async def get(self, key: str) -> str | None:
        """Get value for a key."""
        if self._is_expired(key):
            return None

        value = self._data.get(key)
        if value:
            logger.debug(f"Cache HIT: {key}")
        else:
            logger.debug(f"Cache MISS: {key}")

        return value

    async def delete(self, key: str) -> bool:
        """Delete a key."""
        if key in self._data:
            del self._data[key]
            if key in self._expiry:
                del self._expiry[key]
            logger.debug(f"Cache DELETE: {key}")
            return True
        return False

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        if self._is_expired(key):
            return False
        return key in self._data

    async def expire(self, key: str, ttl: int) -> bool:
        """Set TTL for a key."""
        if key in self._data:
            self._expiry[key] = time.time() + ttl
            return True
        return False

    async def ttl(self, key: str) -> int:
        """Get remaining TTL for a key."""
        if key not in self._expiry:
            return -1

        remaining = self._expiry[key] - time.time()
        if remaining < 0:
            self._is_expired(key)
            return -2

        return int(remaining)

    # Hash operations
    async def hset(self, key: str, field: str, value: str) -> bool:
        """Set field in hash."""
        self._hashes[key][field] = value
        logger.debug(f"Cache HSET: {key}[{field}]")
        return True

    async def hget(self, key: str, field: str) -> str | None:
        """Get field from hash."""
        return self._hashes.get(key, {}).get(field)

    async def hgetall(self, key: str) -> dict[str, str]:
        """Get all fields from hash."""
        return dict(self._hashes.get(key, {}))

    async def hdel(self, key: str, field: str) -> bool:
        """Delete field from hash."""
        if key in self._hashes and field in self._hashes[key]:
            del self._hashes[key][field]
            return True
        return False

    # Set operations
    async def sadd(self, key: str, *members: str) -> int:
        """Add members to set."""
        before = len(self._sets[key])
        self._sets[key].update(members)
        added = len(self._sets[key]) - before
        logger.debug(f"Cache SADD: {key} ({added} members)")
        return added

    async def srem(self, key: str, *members: str) -> int:
        """Remove members from set."""
        if key not in self._sets:
            return 0

        removed = 0
        for member in members:
            if member in self._sets[key]:
                self._sets[key].remove(member)
                removed += 1

        return removed

    async def smembers(self, key: str) -> builtins.set[str]:
        """Get all members of set."""
        return set(self._sets.get(key, set()))

    async def sismember(self, key: str, member: str) -> bool:
        """Check if member is in set."""
        return member in self._sets.get(key, set())

    # Pub/Sub operations
    async def publish(self, channel: str, message: str) -> int:
        """Publish message to channel."""
        subscribers = self._pubsub_channels.get(channel, [])

        for callback in subscribers:
            try:
                await callback(channel, message)
            except Exception as e:
                logger.error(f"PubSub callback error: {e}")

        logger.debug(f"Cache PUBLISH: {channel} ({len(subscribers)} subscribers)")
        return len(subscribers)

    def subscribe(self, channel: str, callback: callable):
        """Subscribe to channel."""
        self._pubsub_channels[channel].append(callback)
        logger.info(f"Subscribed to channel: {channel}")

    def unsubscribe(self, channel: str, callback: callable):
        """Unsubscribe from channel."""
        if channel in self._pubsub_channels:
            try:
                self._pubsub_channels[channel].remove(callback)
                logger.info(f"Unsubscribed from channel: {channel}")
            except ValueError:
                pass

    # Utility methods
    async def flushall(self):
        """Clear all data."""
        self._data.clear()
        self._expiry.clear()
        self._sets.clear()
        self._hashes.clear()
        logger.info("Cache flushed")

    async def keys(self, pattern: str = "*") -> list[str]:
        """Get keys matching pattern."""
        # Simple pattern matching (only supports * at end)
        if pattern == "*":
            return list(self._data.keys())
        elif pattern.endswith("*"):
            prefix = pattern[:-1]
            return [k for k in self._data.keys() if k.startswith(prefix)]
        else:
            return [k for k in self._data.keys() if k == pattern]

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return {
            "keys": len(self._data),
            "sets": len(self._sets),
            "hashes": len(self._hashes),
            "channels": len(self._pubsub_channels),
            "subscribers": sum(len(subs) for subs in self._pubsub_channels.values()),
            "memory_usage": "N/A (in-memory)",
        }

    async def get_health(self) -> dict[str, Any]:
        """Get cache health status."""
        stats = self.get_stats()
        return {"status": "healthy", "type": "memory", "stats": stats}


# Global instance
_cache_manager: MemoryCacheManager | None = None


def get_cache_manager() -> MemoryCacheManager:
    """Get or create cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = MemoryCacheManager()
    return _cache_manager


async def get_cache_health() -> dict[str, Any]:
    """Get cache health status."""
    manager = get_cache_manager()
    return await manager.get_health()
