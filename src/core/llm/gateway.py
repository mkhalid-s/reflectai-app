"""
LLM Gateway Implementation

Core gateway for LLM requests with provider management, cost tracking,
and response caching. Implements  LiteLLM Gateway Setup.
"""

import asyncio
import hashlib
import json
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

# Optional imports for graceful degradation
try:
    from litellm import acompletion, completion_cost

    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False

from src.infrastructure.config import get_secrets_manager
from src.infrastructure.monitoring import get_circuit_breaker, get_or_create_correlation_id
from src.shared import ErrorCategory, ErrorSeverity, ReflectAIError, get_logger
from src.shared.error_handlers import CircuitBreaker

from .cost_tracker import get_cost_tracker
from .oauth2_provider import get_llm_auth_headers
from .providers import ModelTier, ProviderConfig, get_provider_manager

logger = get_logger(__name__)


@dataclass
class LLMRequest:
    """Standardized LLM request format."""

    messages: list[dict[str, str]]
    model_tier: ModelTier
    user_id: str
    request_id: str = field(default_factory=lambda: str(uuid4()))
    correlation_id: str = field(default_factory=get_or_create_correlation_id)
    temperature: float = 0.7
    max_tokens: int | None = None
    system_prompt: str | None = None
    context: dict[str, Any] = field(default_factory=dict)
    cache_strategy: str = "default"  # default, aggressive, disabled
    retry_attempts: int = 2
    timeout_seconds: int = 30


@dataclass
class LLMResponse:
    """Standardized LLM response format."""

    request_id: str
    content: str
    model_used: str
    provider_used: str
    tokens_used: dict[str, int]
    cost_usd: float
    processing_time_ms: int
    from_cache: bool = False
    confidence_score: float | None = None
    structured_data: dict[str, Any] | None = None
    correlation_id: str = ""


class LLMGateway:
    """
    LLM Gateway with provider management and cost optimization.

    Features:
    - Multi-provider support with failover
    - Cost tracking and optimization
    - Response caching with TTL
    - Circuit breaker protection
    - Request batching capabilities
    """

    def __init__(self) -> None:
        self.provider_manager = get_provider_manager()
        self.cost_tracker = get_cost_tracker()
        self.secrets_manager = get_secrets_manager()

        # Circuit breakers per provider (LRU eviction to prevent memory leak)
        self._circuit_breakers: OrderedDict[str, CircuitBreaker] = OrderedDict()
        self._max_circuit_breakers = 50  # Maximum circuit breakers to cache

        # Response cache (in-memory for production, Redis in production+)
        self._response_cache: dict[str, tuple[LLMResponse, datetime]] = {}
        self._cache_ttl = {
            "default": timedelta(minutes=30),
            "aggressive": timedelta(hours=1),
            "disabled": timedelta(0),
        }

        # Request batching
        self._batch_queue: dict[str, list[LLMRequest]] = {}  # user_id -> requests
        self._batch_timeout = timedelta(milliseconds=100)
        self._max_batch_size = 10

        # Performance metrics
        self._request_count = 0
        self._total_processing_time = 0
        self._cache_hits = 0
        self._cache_misses = 0

        if LITELLM_AVAILABLE:
            logger.info(
                "LLM Gateway initialized with LiteLLM integration",
                extra={
                    "litellm_available": True,
                    "providers_count": len(self.provider_manager.get_all_providers()),
                },
            )
        else:
            logger.warning(
                "LLM Gateway initialized without LiteLLM - install litellm package",
                extra={
                    "litellm_available": False,
                    "providers_count": len(self.provider_manager.get_all_providers()),
                    "install_command": "pip install litellm",
                },
            )

    async def process_request(self, request: LLMRequest) -> LLMResponse:
        """
        Process LLM request with caching, failover, and cost tracking.

        Args:
            request: LLM request configuration

        Returns:
            LLM response with metadata

        Raises:
            ReflectAIError: When all providers fail or request is invalid
        """
        start_time = time.time()
        self._request_count += 1

        try:
            # Check cache first
            cached_response = self._get_cached_response(request)
            if cached_response:
                self._cache_hits += 1
                logger.info(
                    "LLM request served from cache",
                    extra={
                        "request_id": request.request_id,
                        "correlation_id": request.correlation_id,
                        "cache_strategy": request.cache_strategy,
                    },
                )
                return cached_response

            self._cache_misses += 1

            # Get provider and model for tier
            model_info = await self.provider_manager.get_model_for_tier(request.model_tier)
            if not model_info:
                raise ReflectAIError(
                    message=f"No available provider for tier {request.model_tier.value}",
                    error_code="NO_PROVIDER_AVAILABLE",
                    category=ErrorCategory.LLM_PROVIDER_ERROR,
                    severity=ErrorSeverity.ERROR,
                    context={"tier": request.model_tier.value},
                )

            model_name, provider = model_info

            # Process request with circuit breaker
            response = await self._process_with_provider(request, provider, model_name)

            # Cache response if not disabled
            if request.cache_strategy != "disabled":
                self._cache_response(request, response)

            # Update metrics
            processing_time = int((time.time() - start_time) * 1000)
            self._total_processing_time += processing_time

            logger.info(
                "LLM request completed",
                extra={
                    "request_id": request.request_id,
                    "model": model_name,
                    "provider": provider.name,
                    "cost_usd": response.cost_usd,
                    "processing_time_ms": processing_time,
                },
            )

            return response

        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)

            logger.error(
                "LLM request failed",
                extra={
                    "request_id": request.request_id,
                    "error": str(e),
                    "processing_time_ms": processing_time,
                },
                exc_info=True,
            )

            raise ReflectAIError(
                message=f"LLM request failed: {str(e)}",
                error_code="LLM_REQUEST_FAILED",
                category=ErrorCategory.LLM_PROVIDER_ERROR,
                severity=ErrorSeverity.ERROR,
                context={
                    "request_id": request.request_id,
                    "tier": request.model_tier.value,
                    "processing_time_ms": processing_time,
                },
                cause=e,
            ) from e

    async def _process_with_provider(
        self, request: LLMRequest, provider: ProviderConfig, model_name: str
    ) -> LLMResponse:
        """Process request with specific provider using circuit breaker."""

        # Get or create circuit breaker for this provider
        circuit_breaker = self._get_circuit_breaker(provider.name)

        async def make_llm_call() -> LLMResponse:
            return await self._make_llm_call(request, provider, model_name)

        try:
            # CircuitBreaker.call handles both sync and async functions
            return await circuit_breaker.call(make_llm_call)  # type: ignore[arg-type]
        except Exception as e:
            # Mark provider as unhealthy and try next one
            self.provider_manager.mark_provider_unhealthy(provider.name)

            # Try next available provider
            next_provider_info = await self.provider_manager.get_model_for_tier(
                request.model_tier, exclude_unhealthy=True
            )

            if next_provider_info:
                next_model, next_provider = next_provider_info
                logger.warning(
                    f"Failing over from {provider.name} to {next_provider.name}",
                    extra={"request_id": request.request_id},
                )
                return await self._process_with_provider(request, next_provider, next_model)

            # No more providers available
            raise e

    async def _make_llm_call(
        self, request: LLMRequest, provider: ProviderConfig, model_name: str
    ) -> LLMResponse:
        """Make actual LLM API call using LiteLLM."""

        if not LITELLM_AVAILABLE:
            raise ReflectAIError(
                message="LiteLLM is not available. Please install litellm package.",
                error_code="LITELLM_NOT_AVAILABLE",
                category=ErrorCategory.CONFIGURATION_ERROR,
                severity=ErrorSeverity.ERROR,
                context={"install_command": "pip install litellm"},
            )

        try:
            # Try OAuth authentication first, fallback to API key
            auth_headers = {}
            api_key = None

            try:
                # Get OAuth authentication headers
                auth_headers = await get_llm_auth_headers(
                    provider_name=provider.name,
                    request_url=getattr(provider, "base_url", None),
                    request_method="POST",
                )
                logger.debug(f"Using OAuth authentication for {provider.name}")

            except Exception as oauth_error:
                logger.debug(
                    f"OAuth authentication failed for {provider.name}, falling back to API key",
                    extra={"oauth_error": str(oauth_error)},
                )

                # Fallback to API key authentication
                api_key = self.secrets_manager.get_secret(provider.api_key_secret)
                if not api_key:
                    raise ReflectAIError(
                        message=f"Both OAuth and API key authentication failed for {provider.name}",
                        error_code="AUTHENTICATION_FAILED",
                        category=ErrorCategory.AUTHENTICATION_ERROR,
                        severity=ErrorSeverity.ERROR,
                        context={"oauth_error": str(oauth_error)},
                        cause=oauth_error,
                    ) from oauth_error

            # Prepare messages
            messages = request.messages.copy()
            if request.system_prompt:
                messages.insert(0, {"role": "system", "content": request.system_prompt})

            # Build LiteLLM parameters
            litellm_params = {
                "model": model_name,
                "messages": messages,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens or 4000,
                "timeout": request.timeout_seconds,
            }

            # Add authentication - prefer OAuth headers over API key
            if auth_headers:
                litellm_params["headers"] = auth_headers
                logger.debug(f"Using OAuth authentication headers for {provider.name}")
            elif api_key:
                litellm_params["api_key"] = api_key
                logger.debug(f"Using API key authentication for {provider.name}")

            # Add base URL if specified
            if getattr(provider, "base_url", None):
                litellm_params["base_url"] = provider.base_url

            # Add provider-specific configuration if available
            if hasattr(provider, "litellm_params") and provider.litellm_params:
                litellm_params.update(provider.litellm_params)

            # Make LiteLLM call
            start_time = time.time()
            logger.debug(
                "Making LiteLLM API call",
                extra={
                    "model": model_name,
                    "provider": provider.name,
                    "request_id": request.request_id,
                },
            )

            response = await acompletion(**litellm_params)

            processing_time = int((time.time() - start_time) * 1000)

            # Validate response structure
            if not response or not hasattr(response, "choices") or not response.choices:
                raise ReflectAIError(
                    message="Invalid response from LLM provider",
                    error_code="INVALID_LLM_RESPONSE",
                    category=ErrorCategory.LLM_PROVIDER_ERROR,
                    severity=ErrorSeverity.ERROR,
                )

            # Extract response data
            content = response.choices[0].message.content
            if not content:
                raise ReflectAIError(
                    message="Empty content in LLM response",
                    error_code="EMPTY_LLM_RESPONSE",
                    category=ErrorCategory.LLM_PROVIDER_ERROR,
                    severity=ErrorSeverity.WARNING,
                )

            # Extract token usage (with fallbacks for different providers)
            tokens_used = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

            if hasattr(response, "usage") and response.usage:
                tokens_used = {
                    "prompt_tokens": getattr(response.usage, "prompt_tokens", 0),
                    "completion_tokens": getattr(response.usage, "completion_tokens", 0),
                    "total_tokens": getattr(response.usage, "total_tokens", 0),
                }

            # Calculate cost using LiteLLM's cost calculation
            cost_usd = 0.0
            try:
                cost_usd = completion_cost(response)
            except Exception as e:
                logger.warning(
                    f"Cost calculation failed: {e}",
                    extra={"model": model_name, "provider": provider.name},
                )
                # Fallback to manual cost calculation if available
                pricing = provider.get_pricing_for_model(model_name)
                if pricing and tokens_used["total_tokens"] > 0:
                    cost_usd = (tokens_used["prompt_tokens"] / 1000) * pricing.input_cost_per_1k + (
                        tokens_used["completion_tokens"] / 1000
                    ) * pricing.output_cost_per_1k

            # Track cost
            self.cost_tracker.record_request(
                user_id=request.user_id,
                model_name=model_name,
                provider_name=provider.name,
                tokens_used=tokens_used,
                cost_usd=cost_usd,
            )

            logger.info(
                "LiteLLM call completed successfully",
                extra={
                    "model": model_name,
                    "provider": provider.name,
                    "tokens_used": tokens_used["total_tokens"],
                    "cost_usd": cost_usd,
                    "processing_time_ms": processing_time,
                    "request_id": request.request_id,
                },
            )

            return LLMResponse(
                request_id=request.request_id,
                content=content,
                model_used=model_name,
                provider_used=provider.name,
                tokens_used=tokens_used,
                cost_usd=cost_usd,
                processing_time_ms=processing_time,
                correlation_id=request.correlation_id,
            )

        except ReflectAIError:
            # Re-raise ReflectAI errors as-is
            raise
        except Exception as e:
            logger.error(
                f"LLM API call failed for {provider.name}",
                extra={
                    "model": model_name,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "request_id": request.request_id,
                },
                exc_info=True,
            )

            # Convert to ReflectAI error with proper context
            raise ReflectAIError(
                message=f"LLM API call failed: {str(e)}",
                error_code="LLM_API_CALL_FAILED",
                category=ErrorCategory.LLM_PROVIDER_ERROR,
                severity=ErrorSeverity.ERROR,
                context={
                    "provider": provider.name,
                    "model": model_name,
                    "error_type": type(e).__name__,
                },
                cause=e,
            ) from e

    def _get_circuit_breaker(self, provider_name: str) -> CircuitBreaker:
        """
        Get circuit breaker for provider with LRU eviction.

        Implements LRU cache to prevent unbounded memory growth:
        - Tracks up to max_circuit_breakers circuit breakers
        - Evicts least recently used when at capacity
        - Moves accessed items to end (marks as recently used)
        """
        if provider_name not in self._circuit_breakers:
            # Check if we need to evict oldest circuit breaker
            if len(self._circuit_breakers) >= self._max_circuit_breakers:
                # Remove least recently used (first item in OrderedDict)
                oldest_provider, oldest_cb = self._circuit_breakers.popitem(last=False)
                logger.debug(
                    f"Evicted circuit breaker for {oldest_provider} (LRU policy)",
                    extra={
                        "evicted_provider": oldest_provider,
                        "cache_size": len(self._circuit_breakers),
                    },
                )

            # Create new circuit breaker
            self._circuit_breakers[provider_name] = get_circuit_breaker(
                name=f"llm_provider_{provider_name}",
                failure_threshold=3,
                recovery_timeout=300,  # 5 minutes
            )
        else:
            # Move to end to mark as recently used (LRU tracking)
            self._circuit_breakers.move_to_end(provider_name)

        return self._circuit_breakers[provider_name]

    def _get_cached_response(self, request: LLMRequest) -> LLMResponse | None:
        """Check cache for existing response."""
        if request.cache_strategy == "disabled":
            return None

        cache_key = self._generate_cache_key(request)

        if cache_key in self._response_cache:
            response, cached_at = self._response_cache[cache_key]
            ttl = self._cache_ttl[request.cache_strategy]

            if datetime.now(UTC) - cached_at < ttl:
                # Return cached response with updated metadata
                cached_response = LLMResponse(
                    request_id=request.request_id,  # New request ID
                    content=response.content,
                    model_used=response.model_used,
                    provider_used=response.provider_used,
                    tokens_used=response.tokens_used,
                    cost_usd=0.0,  # No cost for cached response
                    processing_time_ms=1,  # Minimal processing time
                    from_cache=True,
                    correlation_id=request.correlation_id,
                )
                return cached_response
            else:
                # Remove expired cache entry
                del self._response_cache[cache_key]

        return None

    def _cache_response(self, request: LLMRequest, response: LLMResponse) -> None:
        """Cache response for future requests."""
        cache_key = self._generate_cache_key(request)
        self._response_cache[cache_key] = (response, datetime.now(UTC))

        # Simple cache eviction (keep last 1000 entries)
        if len(self._response_cache) > 1000:
            oldest_keys = sorted(
                self._response_cache.keys(), key=lambda k: self._response_cache[k][1]
            )[:100]  # Remove oldest 100 entries

            for key in oldest_keys:
                del self._response_cache[key]

    def _generate_cache_key(self, request: LLMRequest) -> str:
        """Generate cache key for request."""
        # Create hash from messages, tier, and temperature
        key_data = {
            "messages": request.messages,
            "tier": request.model_tier.value,
            "temperature": request.temperature,
            "system_prompt": request.system_prompt,
        }

        key_json = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_json.encode(), usedforsecurity=False).hexdigest()

    async def batch_process_requests(self, requests: list[LLMRequest]) -> list[LLMResponse]:
        """
        Process multiple requests with batching optimization.

        Groups requests by user and processes concurrently for efficiency.
        """
        if not requests:
            return []

        logger.info(
            f"Processing batch of {len(requests)} LLM requests", extra={"batch_size": len(requests)}
        )

        # Process requests concurrently
        tasks = [self.process_request(request) for request in requests]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to error responses
        processed_responses: list[LLMResponse] = []
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                logger.error(
                    f"Batch request {i} failed: {response}",
                    extra={"request_id": requests[i].request_id},
                )
                # Create error response
                error_response = LLMResponse(
                    request_id=requests[i].request_id,
                    content=f"Error: {str(response)}",
                    model_used="error",
                    provider_used="error",
                    tokens_used={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                    cost_usd=0.0,
                    processing_time_ms=0,
                    correlation_id=requests[i].correlation_id,
                )
                processed_responses.append(error_response)
            else:
                # Type narrowing: response is LLMResponse here
                processed_responses.append(response)  # type: ignore[arg-type]

        return processed_responses

    async def get_gateway_stats(self) -> dict[str, Any]:
        """Get gateway performance and usage statistics."""
        avg_processing_time = (
            self._total_processing_time / self._request_count if self._request_count > 0 else 0
        )

        cache_hit_rate = (
            self._cache_hits / (self._cache_hits + self._cache_misses)
            if (self._cache_hits + self._cache_misses) > 0
            else 0
        )

        return {
            "gateway_status": "active",
            "requests": {
                "total": self._request_count,
                "average_processing_time_ms": avg_processing_time,
            },
            "cache": {
                "hits": self._cache_hits,
                "misses": self._cache_misses,
                "hit_rate": cache_hit_rate,
                "entries": len(self._response_cache),
            },
            "providers": await self.provider_manager.get_provider_health_status(),
            "cost_summary": self.cost_tracker.get_usage_summary(),
        }

    def get_available_providers(self) -> list[ProviderConfig]:
        """Get list of all configured providers."""
        return self.provider_manager.get_all_providers()

    def clear_cache(self) -> None:
        """Clear response cache."""
        cache_entries = len(self._response_cache)
        self._response_cache.clear()
        logger.info(f"Cleared {cache_entries} cache entries")


# Global gateway instance
_llm_gateway: LLMGateway | None = None


def get_llm_gateway() -> LLMGateway:
    """Get or create global LLM gateway instance."""
    global _llm_gateway
    if _llm_gateway is None:
        _llm_gateway = LLMGateway()
    return _llm_gateway
