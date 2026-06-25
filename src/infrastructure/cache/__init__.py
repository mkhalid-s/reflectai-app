"""
Cache Infrastructure for ReflectAI

Provides Redis-based caching with memory fallback:
- Production: Redis with automatic memory fallback
- Development/Testing: In-memory cache fallback
- Namespace-based cache organization
- Consistent async API

MIGRATION NOTE:
- Use get_redis_manager() from redis_manager.py for all cache operations
- CacheManager, RedisCacheManager, and cache_factory.py are deprecated
- MemoryCacheManager is used internally by RedisManager for fallback
"""

from .memory_cache import MemoryCacheManager
from .memory_cache import get_cache_manager as get_memory_cache
from .redis_manager import RedisManager, get_redis_manager

__all__ = [
    # Primary cache interface (use this!)
    "RedisManager",
    "get_redis_manager",
    # Memory fallback (internal use by RedisManager)
    "MemoryCacheManager",
    "get_memory_cache",
]
