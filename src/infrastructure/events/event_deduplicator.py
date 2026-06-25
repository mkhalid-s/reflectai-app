"""
Redis-Based Event Deduplication System

Production-grade event deduplication using Redis with:
- Composite key generation for unique event identification
- TTL-based automatic cleanup
- High-performance deduplication checks
- Scalable across multiple instances
"""

import hashlib
import json
from datetime import datetime
from typing import Any

# Optional pydantic import
try:
    from pydantic import BaseModel, Field, validator

    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False

    # Fallback BaseModel
    class BaseModel:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    def Field(default=None, **kwargs):
        return default

    def validator(field_name):
        def decorator(func):
            return func

        return decorator


from dataclasses import dataclass
from enum import Enum

from src.shared.logging import get_logger

from ..cache.redis_manager import get_redis_manager

logger = get_logger(__name__)


class DeduplicationStrategy(str, Enum):
    """Event deduplication strategies"""

    STRICT = "strict"  # Exact match on all fields
    CONTENT_HASH = "content_hash"  # Hash-based on content only
    COMPOSITE_KEY = "composite_key"  # Custom composite key
    TEMPORAL = "temporal"  # Time-window based deduplication


class DeduplicationResult(BaseModel):
    """Result of event deduplication check"""

    is_duplicate: bool = Field(description="Whether event is a duplicate")
    event_key: str = Field(description="Generated deduplication key")
    first_seen: datetime | None = Field(description="When event was first processed")
    duplicate_count: int = Field(default=0, description="Number of times event was seen")
    ttl_seconds: int = Field(description="TTL remaining on deduplication key")
    strategy_used: DeduplicationStrategy = Field(description="Deduplication strategy applied")

    class Config:
        arbitrary_types_allowed = True


@dataclass
class DeduplicationConfig:
    """Configuration for event deduplication"""

    default_ttl_seconds: int = 3600  # 1 hour default
    key_prefix: str = "event_dedup"
    strategy: DeduplicationStrategy = DeduplicationStrategy.COMPOSITE_KEY
    max_key_length: int = 250
    include_timestamp: bool = False
    temporal_window_seconds: int = 300  # 5 minutes for temporal deduplication
    cleanup_batch_size: int = 1000
    enable_metrics: bool = True


class EventDeduplicator:
    """Production-grade Redis-based event deduplicator"""

    def __init__(self, config: DeduplicationConfig | None = None):
        self.config = config or DeduplicationConfig()
        self.redis_manager = None
        self._initialized = False

        # Metrics
        self._dedup_hits = 0
        self._dedup_misses = 0
        self._total_checks = 0

    async def initialize(self):
        """Initialize Redis connection"""
        if not self._initialized:
            self.redis_manager = get_redis_manager()
            self._initialized = True
            logger.info("Event deduplicator initialized with Redis backend")

    async def check_and_store(
        self,
        event_data: dict[str, Any],
        event_type: str,
        user_id: str | None = None,
        ttl_seconds: int | None = None,
        custom_key_fields: list[str] | None = None,
    ) -> DeduplicationResult:
        """
        Check if event is duplicate and store for future deduplication

        Args:
            event_data: Event data dictionary
            event_type: Type/category of event
            user_id: User associated with event (if any)
            ttl_seconds: Custom TTL for this event (overrides default)
            custom_key_fields: Custom fields to include in deduplication key

        Returns:
            DeduplicationResult with deduplication status and metadata
        """
        await self.initialize()

        self._total_checks += 1
        ttl = ttl_seconds or self.config.default_ttl_seconds

        try:
            # Generate deduplication key
            dedup_key = await self._generate_deduplication_key(
                event_data=event_data,
                event_type=event_type,
                user_id=user_id,
                custom_key_fields=custom_key_fields,
            )

            # Check for existing event
            existing_data = await self._get_existing_event(dedup_key)

            if existing_data:
                # Event is a duplicate
                self._dedup_hits += 1
                # Convert to int since Redis stores as string
                duplicate_count = int(existing_data.get("duplicate_count", "0")) + 1

                # Update duplicate count and extend TTL
                await self._update_duplicate_count(dedup_key, duplicate_count, ttl)

                return DeduplicationResult(
                    is_duplicate=True,
                    event_key=dedup_key,
                    first_seen=datetime.fromisoformat(existing_data["first_seen"]),
                    duplicate_count=duplicate_count,
                    ttl_seconds=ttl,
                    strategy_used=self.config.strategy,
                )
            else:
                # Event is new - store it
                self._dedup_misses += 1
                await self._store_new_event(
                    dedup_key=dedup_key,
                    event_data=event_data,
                    event_type=event_type,
                    user_id=user_id,
                    ttl=ttl,
                )

                return DeduplicationResult(
                    is_duplicate=False,
                    event_key=dedup_key,
                    first_seen=datetime.now(),
                    duplicate_count=0,
                    ttl_seconds=ttl,
                    strategy_used=self.config.strategy,
                )

        except Exception as e:
            logger.error(
                f"Event deduplication failed: {str(e)}",
                exc_info=True,  # Include full traceback for debugging
                extra={"event_type": event_type, "user_id": user_id, "error": str(e)},
            )

            # In case of error, treat as non-duplicate to avoid blocking events
            return DeduplicationResult(
                is_duplicate=False,
                event_key="error_fallback",
                first_seen=datetime.now(),
                duplicate_count=0,
                ttl_seconds=ttl,
                strategy_used=self.config.strategy,
            )

    async def is_duplicate(
        self,
        event_data: dict[str, Any],
        event_type: str,
        user_id: str | None = None,
        custom_key_fields: list[str] | None = None,
    ) -> bool:
        """
        Quick duplicate check without storing the event

        Returns:
            True if event is a duplicate, False otherwise
        """
        result = await self.check_and_store(
            event_data=event_data,
            event_type=event_type,
            user_id=user_id,
            custom_key_fields=custom_key_fields,
        )
        return result.is_duplicate

    async def mark_processed(
        self, event_key: str, processing_result: dict[str, Any] | None = None
    ) -> bool:
        """
        Mark an event as successfully processed

        Args:
            event_key: Deduplication key from check_and_store
            processing_result: Optional result data to store

        Returns:
            True if marked successfully, False otherwise
        """
        await self.initialize()

        try:
            update_data = {
                "processed_at": datetime.now().isoformat(),
                "processing_status": "completed",
            }

            if processing_result:
                update_data["processing_result"] = json.dumps(processing_result)

            # Update the stored event data using raw Redis client
            async with self.redis_manager.get_client() as client:
                success = await client.hset(event_key, mapping=update_data)

            if success:
                logger.debug(f"Event marked as processed: {event_key}")
                return True
            else:
                logger.warning(f"Failed to mark event as processed: {event_key}")
                return False

        except Exception as e:
            logger.error(
                f"Failed to mark event as processed: {str(e)}",
                extra={"event_key": event_key, "error": str(e)},
            )
            return False

    async def cleanup_expired_events(self, batch_size: int | None = None) -> int:
        """
        Clean up expired deduplication entries

        Args:
            batch_size: Number of keys to process in each batch

        Returns:
            Number of expired entries cleaned up
        """
        await self.initialize()

        batch_size = batch_size or self.config.cleanup_batch_size
        cleaned_count = 0

        try:
            # Scan for deduplication keys
            pattern = f"{self.config.key_prefix}:*"

            async for keys_batch in self.redis_manager.scan_iter(pattern=pattern, count=batch_size):
                # Check TTL for each key
                expired_keys = []
                for key in keys_batch:
                    ttl = await self.redis_manager.ttl(key)
                    if ttl == -1:  # No TTL set
                        expired_keys.append(key)
                    elif ttl == -2:  # Key doesn't exist
                        continue

                # Delete expired keys
                if expired_keys:
                    deleted = await self.redis_manager.delete(*expired_keys)
                    cleaned_count += deleted

                    logger.debug(f"Cleaned up {deleted} expired deduplication entries")

            if cleaned_count > 0:
                logger.info(f"Deduplication cleanup completed: {cleaned_count} entries removed")

            return cleaned_count

        except Exception as e:
            logger.error(f"Deduplication cleanup failed: {str(e)}")
            return 0

    async def get_metrics(self) -> dict[str, Any]:
        """Get deduplication metrics"""
        await self.initialize()

        hit_rate = (self._dedup_hits / max(1, self._total_checks)) * 100

        # Get Redis-based metrics
        pattern = f"{self.config.key_prefix}:*"
        active_keys = 0

        try:
            async for keys_batch in self.redis_manager.scan_iter(pattern=pattern, count=100):
                active_keys += len(keys_batch)
        except Exception:
            active_keys = -1  # Indicate error

        return {
            "total_checks": self._total_checks,
            "duplicate_hits": self._dedup_hits,
            "duplicate_misses": self._dedup_misses,
            "hit_rate_percent": hit_rate,
            "active_dedup_keys": active_keys,
            "redis_connected": self.redis_manager is not None,
            "strategy": self.config.strategy.value,
            "default_ttl_seconds": self.config.default_ttl_seconds,
        }

    async def _generate_deduplication_key(
        self,
        event_data: dict[str, Any],
        event_type: str,
        user_id: str | None = None,
        custom_key_fields: list[str] | None = None,
    ) -> str:
        """Generate a unique deduplication key for the event"""

        key_components = [self.config.key_prefix, event_type]

        if self.config.strategy == DeduplicationStrategy.STRICT:
            # Include all event data in key generation
            content_hash = self._hash_event_data(event_data)
            key_components.append(content_hash)

        elif self.config.strategy == DeduplicationStrategy.CONTENT_HASH:
            # Hash only the content, ignore metadata
            content_data = {
                k: v
                for k, v in event_data.items()
                if not k.startswith("_") and k not in ["timestamp", "id"]
            }
            content_hash = self._hash_event_data(content_data)
            key_components.append(content_hash)

        elif self.config.strategy == DeduplicationStrategy.COMPOSITE_KEY:
            # Use custom fields or smart field selection
            if custom_key_fields:
                key_data = {k: event_data.get(k) for k in custom_key_fields if k in event_data}
            else:
                key_data = self._extract_key_fields(event_data)

            if user_id:
                key_data["user_id"] = user_id

            content_hash = self._hash_event_data(key_data)
            key_components.append(content_hash)

        elif self.config.strategy == DeduplicationStrategy.TEMPORAL:
            # Include time window in key for temporal deduplication
            window_size = self.config.temporal_window_seconds
            current_time = datetime.now()
            window_start = current_time.timestamp() // window_size * window_size

            key_data = self._extract_key_fields(event_data)
            key_data["time_window"] = window_start
            if user_id:
                key_data["user_id"] = user_id

            content_hash = self._hash_event_data(key_data)
            key_components.append(content_hash)

        # Include timestamp if configured
        if self.config.include_timestamp:
            timestamp = datetime.now().strftime("%Y%m%d%H")  # Hourly precision
            key_components.append(timestamp)

        # Generate final key
        key = ":".join(str(comp) for comp in key_components)

        # Ensure key length doesn't exceed limits
        if len(key) > self.config.max_key_length:
            # Hash the entire key if too long
            key = f"{self.config.key_prefix}:{self._hash_string(key)}"

        return key

    def _extract_key_fields(self, event_data: dict[str, Any]) -> dict[str, Any]:
        """Extract key fields from event data for composite key generation"""
        # Priority fields for deduplication
        priority_fields = [
            "message_id",
            "event_id",
            "user",
            "channel",
            "text",
            "action",
            "callback_id",
            "trigger_id",
            "response_url",
            "value",
        ]

        key_fields = {}

        # Include priority fields if present
        for field in priority_fields:
            if field in event_data:
                key_fields[field] = event_data[field]

        # If no priority fields found, include all simple fields
        if not key_fields:
            for key, value in event_data.items():
                if isinstance(value, (str, int, float, bool)):
                    key_fields[key] = value

        return key_fields

    def _hash_event_data(self, data: dict[str, Any]) -> str:
        """Generate consistent hash for event data"""
        # Sort keys for consistent hashing
        sorted_data = dict(sorted(data.items()))

        # Convert to JSON with consistent formatting
        json_str = json.dumps(sorted_data, sort_keys=True, default=str)

        # Generate SHA-256 hash
        return hashlib.sha256(json_str.encode("utf-8")).hexdigest()[:16]  # 16 chars

    def _hash_string(self, text: str) -> str:
        """Generate hash for string"""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

    async def _get_existing_event(self, dedup_key: str) -> dict[str, Any] | None:
        """Get existing event data from Redis"""
        try:
            async with self.redis_manager.get_client() as client:
                event_data = await client.hgetall(dedup_key)

                if event_data:
                    # Convert bytes to strings
                    event_data = {
                        k.decode() if isinstance(k, bytes) else k:
                        v.decode() if isinstance(v, bytes) else v
                        for k, v in event_data.items()
                    }

                    # Parse JSON fields
                    if "event_data" in event_data:
                        event_data["event_data"] = json.loads(event_data["event_data"])

                    return event_data

                return None

        except Exception as e:
            logger.error(f"Failed to get existing event: {str(e)}")
            return None

    async def _store_new_event(
        self,
        dedup_key: str,
        event_data: dict[str, Any],
        event_type: str,
        user_id: str | None,
        ttl: int,
    ) -> bool:
        """Store new event in Redis with TTL"""
        try:
            stored_data = {
                "event_type": event_type,
                "event_data": json.dumps(event_data, default=str),
                "user_id": user_id or "",
                "first_seen": datetime.now().isoformat(),
                "duplicate_count": "0",
                "processing_status": "pending",
            }

            # Store with TTL using raw Redis client
            async with self.redis_manager.get_client() as client:
                # Use hset to store hash fields
                success = await client.hset(dedup_key, mapping=stored_data)
                if success:
                    await client.expire(dedup_key, ttl)
                    logger.debug(f"Stored new event for deduplication: {dedup_key}")
                    return True

            return False

        except Exception as e:
            logger.error(f"Failed to store new event: {str(e)}")
            return False

    async def _update_duplicate_count(self, dedup_key: str, duplicate_count: int, ttl: int) -> bool:
        """Update duplicate count and extend TTL"""
        try:
            async with self.redis_manager.get_client() as client:
                # Update count
                await client.hset(dedup_key, "duplicate_count", str(duplicate_count))

                # Extend TTL
                await client.expire(dedup_key, ttl)

            logger.debug(f"Updated duplicate count for {dedup_key}: {duplicate_count}")
            return True

        except Exception as e:
            logger.error(f"Failed to update duplicate count: {str(e)}")
            return False


# Global instance
_event_deduplicator = None


async def get_event_deduplicator(config: DeduplicationConfig | None = None) -> EventDeduplicator:
    """Get singleton event deduplicator instance"""
    global _event_deduplicator
    if _event_deduplicator is None:
        _event_deduplicator = EventDeduplicator(config)
    return _event_deduplicator
