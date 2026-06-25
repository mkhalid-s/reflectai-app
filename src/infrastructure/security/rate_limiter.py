"""
Rate Limiting Middleware for FastAPI

Provides configurable rate limiting to protect API endpoints from abuse.
Supports both in-memory and Redis-based rate limiting for distributed systems.
"""

import hashlib
import time
from collections import defaultdict, deque
from collections.abc import Callable
from typing import Any

import redis.asyncio as redis
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware

from src.infrastructure.cache.redis_manager import get_redis_manager
from src.shared.logging import get_logger

logger = get_logger(__name__)


class RateLimitConfig(BaseModel):
    """Configuration for rate limiting"""

    # Global limits
    requests_per_second: int = Field(default=10, ge=1)
    requests_per_minute: int = Field(default=100, ge=1)
    requests_per_hour: int = Field(default=1000, ge=1)

    # Burst allowance
    burst_size: int = Field(default=20, ge=1)

    # Per-endpoint limits (path -> limits)
    endpoint_limits: dict[str, dict[str, int]] = Field(default_factory=dict)

    # User-based limits
    authenticated_multiplier: float = Field(default=2.0, ge=1.0)

    # Storage backend
    use_redis: bool = Field(default=True)
    redis_prefix: str = Field(default="ratelimit:")

    # Response headers
    include_headers: bool = Field(default=True)

    # Exemptions
    exempt_paths: list[str] = Field(
        default_factory=lambda: ["/health", "/metrics", "/docs", "/openapi.json"]
    )


class RateLimiter:
    """Rate limiter implementation with multiple strategies"""

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.redis_manager = None
        self._redis_checked = False

        # In-memory storage for fallback
        self.memory_storage: dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))

        # Store Redis manager reference for lazy initialization
        if config.use_redis:
            try:
                self.redis_manager = get_redis_manager()
                logger.info("Rate limiter will use Redis when available")
            except Exception as e:
                logger.warning(f"Failed to get Redis manager: {e}")
                logger.info("Falling back to in-memory rate limiting")

    def _get_redis_client(self) -> redis.Redis | None:
        """Lazily get Redis client (checks at runtime, not init time)"""
        if not self.config.use_redis or not self.redis_manager:
            return None

        # Only log once
        if not self._redis_checked:
            if hasattr(self.redis_manager, "redis_client") and self.redis_manager.redis_client:
                logger.info("Redis-based rate limiting active")
            else:
                logger.info("Redis not yet initialized, using in-memory rate limiting")
            self._redis_checked = True

        return getattr(self.redis_manager, "redis_client", None)

    def _get_client_id(self, request: Request) -> str:
        """Generate unique client identifier"""
        # Try to get authenticated user ID
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"

        # Fall back to IP address
        client_ip = request.client.host if request.client else "unknown"

        # Include user agent for better fingerprinting
        user_agent = request.headers.get("user-agent", "")

        # Create hash for consistent identification
        identifier = f"{client_ip}:{user_agent}"
        return hashlib.sha256(identifier.encode(), usedforsecurity=False).hexdigest()

    async def _check_redis_limit(self, key: str, limit: int, window: int) -> tuple[bool, int, int]:
        """Check rate limit using Redis sliding window"""
        redis_client = self._get_redis_client()
        if not redis_client:
            return await self._check_memory_limit(key, limit, window)

        try:
            now = time.time()
            pipeline = redis_client.pipeline()

            # Remove old entries outside the window
            pipeline.zremrangebyscore(key, 0, now - window)

            # Count current requests in window
            pipeline.zcard(key)

            # Add current request
            pipeline.zadd(key, {str(now): now})

            # Set expiry
            pipeline.expire(key, window + 1)

            # Execute pipeline
            results = await pipeline.execute()

            current_requests = results[1]

            # Check if limit exceeded
            if current_requests >= limit:
                return False, current_requests, limit

            return True, current_requests + 1, limit

        except Exception as e:
            logger.error(f"Redis rate limit check failed: {e}")
            # Fall back to memory
            return await self._check_memory_limit(key, limit, window)

    async def _check_memory_limit(self, key: str, limit: int, window: int) -> tuple[bool, int, int]:
        """Check rate limit using in-memory storage"""
        now = time.time()

        # Clean old entries
        if key in self.memory_storage:
            cutoff = now - window
            while self.memory_storage[key] and self.memory_storage[key][0] < cutoff:
                self.memory_storage[key].popleft()

        # Check current count
        current_count = len(self.memory_storage[key])

        if current_count >= limit:
            return False, current_count, limit

        # Add new request
        self.memory_storage[key].append(now)

        return True, current_count + 1, limit

    async def check_rate_limit(self, request: Request) -> tuple[bool, dict[str, Any]]:
        """Check if request should be rate limited"""

        # Check if path is exempt
        path = request.url.path
        if any(path.startswith(exempt) for exempt in self.config.exempt_paths):
            return True, {}

        client_id = self._get_client_id(request)

        # Get limits for this endpoint
        endpoint_limits = self.config.endpoint_limits.get(path, {})

        # Determine multiplier for authenticated users
        multiplier = 1.0
        if client_id.startswith("user:"):
            multiplier = self.config.authenticated_multiplier

        # Check all rate limits
        checks = [
            ("second", self.config.requests_per_second * multiplier, 1),
            ("minute", self.config.requests_per_minute * multiplier, 60),
            ("hour", self.config.requests_per_hour * multiplier, 3600),
        ]

        # Add endpoint-specific limits
        for period, limit in endpoint_limits.items():
            window = {"second": 1, "minute": 60, "hour": 3600}.get(period, 60)
            checks.append((period, limit * multiplier, window))

        # Perform checks
        for period, limit, window in checks:
            key = f"{self.config.redis_prefix}{client_id}:{path}:{period}"
            allowed, current, max_requests = await self._check_redis_limit(key, int(limit), window)

            if not allowed:
                return False, {
                    "period": period,
                    "current": current,
                    "limit": max_requests,
                    "retry_after": window,
                    "client_id": client_id,
                }

        return True, {"client_id": client_id, "limits_checked": len(checks)}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting"""

    def __init__(self, app, config: RateLimitConfig | None = None):
        super().__init__(app)
        self.config = config or RateLimitConfig()
        self.rate_limiter = RateLimiter(self.config)

    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting"""

        # Check rate limits
        allowed, info = await self.rate_limiter.check_rate_limit(request)

        if not allowed:
            # Log rate limit exceeded
            logger.warning(
                f"Rate limit exceeded for {info['client_id']} "
                f"on {request.url.path} ({info['period']} limit)"
            )

            # Prepare error response
            response = JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Please retry after {info['retry_after']} seconds.",
                    "retry_after": info["retry_after"],
                },
            )

            # Add rate limit headers
            if self.config.include_headers:
                response.headers["X-RateLimit-Limit"] = str(info["limit"])
                response.headers["X-RateLimit-Remaining"] = "0"
                response.headers["X-RateLimit-Reset"] = str(int(time.time()) + info["retry_after"])
                response.headers["Retry-After"] = str(info["retry_after"])

            return response

        # Process request
        response = await call_next(request)

        # Add rate limit headers to successful responses
        if self.config.include_headers and "limits_checked" in info:
            response.headers["X-RateLimit-Client"] = info.get("client_id", "unknown")

        return response


def create_rate_limiter(
    requests_per_second: int = 10,
    requests_per_minute: int = 100,
    requests_per_hour: int = 1000,
    use_redis: bool = True,
) -> RateLimitMiddleware:
    """Factory function to create rate limiter with common settings"""

    config = RateLimitConfig(
        requests_per_second=requests_per_second,
        requests_per_minute=requests_per_minute,
        requests_per_hour=requests_per_hour,
        use_redis=use_redis,
    )

    return lambda app: RateLimitMiddleware(app, config)


# Decorator for function-level rate limiting
class RateLimitDecorator:
    """Decorator for rate limiting individual functions"""

    def __init__(self, calls: int = 10, period: int = 60, key_func: Callable | None = None):
        self.calls = calls
        self.period = period
        self.key_func = key_func or (lambda *args, **kwargs: "default")
        self.limiter = RateLimiter(RateLimitConfig(use_redis=True))

    def __call__(self, func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            key = f"func:{func.__name__}:{self.key_func(*args, **kwargs)}"

            allowed, current, limit = await self.limiter._check_redis_limit(
                key, self.calls, self.period
            )

            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Max {limit} calls per {self.period} seconds.",
                )

            return await func(*args, **kwargs)

        return wrapper


# Endpoint-specific rate limits
ENDPOINT_RATE_LIMITS = {
    "/api/v1/llm/generate": {"second": 2, "minute": 20, "hour": 200},
    "/api/v1/analyze": {"second": 5, "minute": 50, "hour": 500},
    "/api/v1/slack/events": {"second": 10, "minute": 100, "hour": 1000},
    "/api/v1/workflows/start": {"second": 1, "minute": 10, "hour": 100},
}
