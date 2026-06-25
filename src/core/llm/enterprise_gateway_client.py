"""
Enterprise LLM Gateway Client Implementation

This module provides a client for Enterprise LLM Gateway API with OAuth2 authentication
and chat completion capabilities following the OpenAPI specification provided.

Enhanced with:
- Tenant/star path parameter support
- Exponential backoff retry for token acquisition
- Refresh token support
- OAuth metrics tracking
- Token pre-fetching
"""

import asyncio
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from src.shared import get_logger

logger = get_logger(__name__)


@dataclass
class OAuthMetrics:
    """OAuth token acquisition metrics."""

    total_requests: int = 0
    successful_acquisitions: int = 0
    failed_acquisitions: int = 0
    refresh_token_uses: int = 0
    total_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    min_latency_ms: float = float("inf")

    @property
    def average_latency_ms(self) -> float:
        """Calculate average token acquisition latency."""
        if self.successful_acquisitions == 0:
            return 0.0
        return self.total_latency_ms / self.successful_acquisitions

    def record_acquisition(self, latency_ms: float, success: bool, used_refresh: bool = False):
        """Record a token acquisition attempt."""
        self.total_requests += 1
        if success:
            self.successful_acquisitions += 1
            self.total_latency_ms += latency_ms
            self.max_latency_ms = max(self.max_latency_ms, latency_ms)
            self.min_latency_ms = min(self.min_latency_ms, latency_ms)
            if used_refresh:
                self.refresh_token_uses += 1
        else:
            self.failed_acquisitions += 1


@dataclass
class TokenResponse:
    """OAuth2 token response structure."""

    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str | None = None


@dataclass
class Message:
    """Chat message structure."""

    role: str
    content: str | list[dict[str, Any]]
    name: str | None = None


@dataclass
class ChatCompletionRequest:
    """Chat completion request structure."""

    messages: list[Message]
    model: str
    max_tokens: int | None = None
    temperature: float | None = None
    top_p: float | None = None
    stream: bool | None = False
    stop: str | list[str] | None = None
    presence_penalty: float | None = None
    frequency_penalty: float | None = None
    logit_bias: dict[str, float] | None = None
    user: str | None = None


@dataclass
class ChatCompletionResponse:
    """Chat completion response structure."""

    id: str
    object: str
    created: int
    model: str
    choices: list[dict[str, Any]]
    usage: dict[str, int]


class EnterpriseGatewayClient:
    """
    Client for Enterprise LLM Gateway API with OAuth2 authentication.

    This client handles:
    - OAuth2 token management with automatic refresh
    - Chat completions API
    - Error handling and retries
    - Rate limiting
    """

    def __init__(
        self,
        base_url: str,
        client_id: str,
        client_secret: str,
        tenant: str = "default",
        star: str = "default",
        token_endpoint: str | None = None,
        scope: str | None = "api.chat",
        enable_token_prefetch: bool = True,
    ):
        """
        Initialize Enterprise LLM Gateway client.

        Args:
            base_url: Base URL for Enterprise LLM Gateway API
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret
            tenant: Tenant identifier (default: "default")
            star: Star/environment identifier (default: "default")
            token_endpoint: Token endpoint URL (defaults to base_url + /oauth/token)
            scope: OAuth2 scope for access
            enable_token_prefetch: Enable token pre-fetching to avoid first-request latency
        """
        self.base_url = base_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant = tenant
        self.star = star
        self.token_endpoint = token_endpoint or f"{self.base_url}/oauth/token"
        self.scope = scope
        self.enable_token_prefetch = enable_token_prefetch

        # Token management
        self.access_token: str | None = None
        self.token_expires_at: datetime | None = None
        self.refresh_token: str | None = None
        self._token_lock = asyncio.Lock()  # Prevent concurrent token acquisitions

        # Metrics
        self.metrics = OAuthMetrics()

        # HTTP client
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=5.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )

        # Token pre-fetching task
        self._prefetch_task: asyncio.Task | None = None
        if enable_token_prefetch:
            # Start background task to pre-fetch token
            self._prefetch_task = asyncio.create_task(self._prefetch_token())

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def close(self):
        """Close HTTP client connections and cancel background tasks."""
        # Cancel prefetch task if running
        if self._prefetch_task and not self._prefetch_task.done():
            self._prefetch_task.cancel()
            try:
                await self._prefetch_task
            except asyncio.CancelledError:
                pass

        await self.http_client.aclose()

    async def _prefetch_token(self):
        """
        Background task to pre-fetch authentication token.

        This avoids first-request latency by acquiring a token in the background.
        """
        try:
            logger.info("Starting token pre-fetch")
            await self._get_access_token()
            logger.info("Token pre-fetch completed successfully")
        except asyncio.CancelledError:
            logger.debug("Token pre-fetch cancelled")
        except Exception as e:
            logger.warning(f"Token pre-fetch failed: {e}")

    async def _get_access_token(self) -> str:
        """
        Get valid access token with exponential backoff retry and refresh support.

        Returns:
            Valid access token

        Raises:
            Exception: If token acquisition fails after all retries
        """
        # Check if we have a valid token
        if self.access_token and self.token_expires_at:
            if datetime.now(UTC) < self.token_expires_at - timedelta(seconds=60):
                return self.access_token

        # Use lock to prevent concurrent token acquisitions
        async with self._token_lock:
            # Double-check after acquiring lock
            if self.access_token and self.token_expires_at:
                if datetime.now(UTC) < self.token_expires_at - timedelta(seconds=60):
                    return self.access_token

            # Try refresh token first if available
            if self.refresh_token:
                try:
                    token = await self._refresh_access_token()
                    if token:
                        return token
                except Exception as e:
                    logger.warning(f"Refresh token failed, falling back to client credentials: {e}")

            # Acquire new token with exponential backoff
            return await self._acquire_new_token()

    async def _refresh_access_token(self) -> str | None:
        """
        Refresh access token using refresh token.

        Returns:
            New access token or None if refresh fails
        """
        if not self.refresh_token:
            return None

        logger.info("Refreshing access token using refresh token")
        start_time = time.time()

        token_data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        try:
            response = await self.http_client.post(
                self.token_endpoint,
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()

            token_response = response.json()
            self.access_token = token_response["access_token"]
            self.token_expires_at = datetime.now(UTC) + timedelta(
                seconds=token_response.get("expires_in", 3600)
            )

            # Update refresh token if provided
            if "refresh_token" in token_response:
                self.refresh_token = token_response["refresh_token"]

            # Record metrics
            latency_ms = (time.time() - start_time) * 1000
            self.metrics.record_acquisition(latency_ms, success=True, used_refresh=True)

            logger.info(
                "Successfully refreshed access token", extra={"latency_ms": f"{latency_ms:.2f}"}
            )
            return self.access_token

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self.metrics.record_acquisition(latency_ms, success=False, used_refresh=True)
            logger.warning(f"Failed to refresh access token: {e}")
            # Clear refresh token on failure
            self.refresh_token = None
            return None

    async def _acquire_new_token(self, max_retries: int = 3) -> str:
        """
        Acquire new access token with exponential backoff retry.

        Args:
            max_retries: Maximum number of retry attempts

        Returns:
            New access token

        Raises:
            Exception: If acquisition fails after all retries
        """
        logger.info("Acquiring new access token from Enterprise LLM Gateway")

        token_data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": self.scope,
        }

        last_exception = None

        for attempt in range(max_retries):
            start_time = time.time()

            try:
                response = await self.http_client.post(
                    self.token_endpoint,
                    data=token_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                response.raise_for_status()

                token_response = response.json()
                self.access_token = token_response["access_token"]
                self.token_expires_at = datetime.now(UTC) + timedelta(
                    seconds=token_response.get("expires_in", 3600)
                )

                if "refresh_token" in token_response:
                    self.refresh_token = token_response["refresh_token"]

                # Record metrics
                latency_ms = (time.time() - start_time) * 1000
                self.metrics.record_acquisition(latency_ms, success=True)

                logger.info(
                    "Successfully acquired access token",
                    extra={"latency_ms": f"{latency_ms:.2f}", "attempt": attempt + 1},
                )
                return self.access_token

            except httpx.HTTPStatusError as e:
                last_exception = e
                latency_ms = (time.time() - start_time) * 1000
                self.metrics.record_acquisition(latency_ms, success=False)

                # Don't retry on 4xx errors (except 429)
                if 400 <= e.response.status_code < 500 and e.response.status_code != 429:
                    logger.error(
                        "Client error acquiring token: "
                        f"{e.response.status_code} - {e.response.text}"
                    )
                    raise

                # Calculate exponential backoff
                if attempt < max_retries - 1:
                    wait_time = min(2**attempt, 10)  # Cap at 10 seconds
                    logger.warning(
                        f"Token acquisition failed (attempt {attempt + 1}/{max_retries}), "
                        f"retrying in {wait_time}s: {e.response.status_code}"
                    )
                    await asyncio.sleep(wait_time)

            except Exception as e:
                last_exception = e
                latency_ms = (time.time() - start_time) * 1000
                self.metrics.record_acquisition(latency_ms, success=False)

                if attempt < max_retries - 1:
                    wait_time = min(2**attempt, 10)
                    logger.warning(
                        f"Token acquisition failed (attempt {attempt + 1}/{max_retries}), "
                        f"retrying in {wait_time}s: {str(e)}"
                    )
                    await asyncio.sleep(wait_time)

        # All retries exhausted
        logger.error(f"Token acquisition failed after {max_retries} attempts")
        raise last_exception or Exception("Token acquisition failed after all retries")

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        model: str = "gpt-4",
        max_tokens: int | None = None,
        temperature: float = 0.7,
        top_p: float = 1.0,
        stream: bool = False,
        stop: str | list[str] | None = None,
        presence_penalty: float = 0.0,
        frequency_penalty: float = 0.0,
        user: str | None = None,
        retry_attempts: int = 3,
    ) -> ChatCompletionResponse:
        """
        Create a chat completion.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model to use for completion
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Nucleus sampling parameter
            stream: Whether to stream the response
            stop: Stop sequences
            presence_penalty: Presence penalty
            frequency_penalty: Frequency penalty
            user: User identifier for tracking
            retry_attempts: Number of retry attempts

        Returns:
            ChatCompletionResponse with the completion

        Raises:
            Exception: If the request fails after retries
        """
        # Get valid access token
        access_token = await self._get_access_token()

        # Prepare request
        request_data = {
            "messages": messages,
            "model": model,
            "temperature": temperature,
            "top_p": top_p,
            "stream": stream,
            "presence_penalty": presence_penalty,
            "frequency_penalty": frequency_penalty,
        }

        if max_tokens is not None:
            request_data["max_tokens"] = max_tokens
        if stop is not None:
            request_data["stop"] = stop
        if user is not None:
            request_data["user"] = user

        # Make request with retries
        # Construct correct Enterprise LLM Gateway URL with tenant and star parameters
        chat_url = f"{self.base_url}/genai/v1/{self.tenant}/{self.star}/chat/completions"

        last_exception = None
        for attempt in range(retry_attempts):
            try:
                response = await self.http_client.post(
                    chat_url,
                    json=request_data,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                    },
                )
                response.raise_for_status()

                response_data = response.json()

                return ChatCompletionResponse(
                    id=response_data["id"],
                    object=response_data["object"],
                    created=response_data["created"],
                    model=response_data["model"],
                    choices=response_data["choices"],
                    usage=response_data["usage"],
                )

            except httpx.HTTPStatusError as e:
                last_exception = e
                if e.response.status_code == 401:
                    # Token might be invalid, try refreshing
                    logger.warning("Got 401, refreshing token")
                    self.access_token = None
                    access_token = await self._get_access_token()
                elif e.response.status_code == 429:
                    # Rate limited, wait before retry
                    wait_time = min(2**attempt, 10)
                    logger.warning(f"Rate limited, waiting {wait_time}s before retry")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Request failed: {e.response.status_code} - {e.response.text}")
                    if attempt == retry_attempts - 1:
                        raise

            except Exception as e:
                last_exception = e
                logger.error(f"Request failed: {str(e)}")
                if attempt == retry_attempts - 1:
                    raise

            # Wait before retry
            if attempt < retry_attempts - 1:
                await asyncio.sleep(1)

        raise last_exception or Exception("Chat completion failed after retries")

    async def health_check(self) -> dict[str, Any]:
        """
        Check API health status.

        Returns:
            Health status dictionary
        """
        try:
            access_token = await self._get_access_token()
            response = await self.http_client.get(
                f"{self.base_url}/health", headers={"Authorization": f"Bearer {access_token}"}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {"status": "unhealthy", "error": str(e)}

    async def get_models(self) -> list[dict[str, Any]]:
        """
        Get available models.

        Returns:
            List of available models
        """
        try:
            access_token = await self._get_access_token()
            # Use correct Enterprise LLM Gateway path with tenant/star
            models_url = f"{self.base_url}/genai/v1/{self.tenant}/{self.star}/models"
            response = await self.http_client.get(
                models_url, headers={"Authorization": f"Bearer {access_token}"}
            )
            response.raise_for_status()
            return response.json().get("data", [])
        except Exception as e:
            logger.error(f"Failed to get models: {str(e)}")
            return []

    async def get_available_models(self) -> dict[str, Any]:
        """
        Compatibility wrapper for get_models().

        This method exists for backward compatibility with code that expects
        the models response in {"data": [...]} format (as used by model_mapper).

        Returns:
            Dictionary with "data" key containing list of models
        """
        models = await self.get_models()
        return {"data": models}

    def get_oauth_metrics(self) -> dict[str, Any]:
        """
        Get OAuth token acquisition metrics.

        Returns:
            Dictionary with metrics including:
            - total_requests: Total token acquisition attempts
            - successful_acquisitions: Successful token acquisitions
            - failed_acquisitions: Failed token acquisitions
            - refresh_token_uses: Number of times refresh token was used
            - average_latency_ms: Average token acquisition latency
            - max_latency_ms: Maximum token acquisition latency
            - min_latency_ms: Minimum token acquisition latency
        """
        return {
            "total_requests": self.metrics.total_requests,
            "successful_acquisitions": self.metrics.successful_acquisitions,
            "failed_acquisitions": self.metrics.failed_acquisitions,
            "refresh_token_uses": self.metrics.refresh_token_uses,
            "average_latency_ms": round(self.metrics.average_latency_ms, 2),
            "max_latency_ms": round(self.metrics.max_latency_ms, 2),
            "min_latency_ms": round(self.metrics.min_latency_ms, 2)
            if self.metrics.min_latency_ms != float("inf")
            else 0.0,
            "success_rate": round(
                self.metrics.successful_acquisitions / self.metrics.total_requests * 100, 2
            )
            if self.metrics.total_requests > 0
            else 0.0,
        }


# Singleton instance management
_client_instance: EnterpriseGatewayClient | None = None


def get_enterprise_gateway_client(
    base_url: str | None = None,
    client_id: str | None = None,
    client_secret: str | None = None,
    tenant: str | None = None,
    star: str | None = None,
) -> EnterpriseGatewayClient:
    """
    Get or create Enterprise LLM Gateway client instance.

    Args:
        base_url: Override base URL
        client_id: Override client ID
        client_secret: Override client secret
        tenant: Override tenant identifier
        star: Override star/environment identifier

    Returns:
        EnterpriseGatewayClient instance
    """
    global _client_instance

    if _client_instance is None:
        from src.infrastructure.config import get_secrets_manager

        secrets = get_secrets_manager()
        enterprise_gateway_secrets = secrets.get_enterprise_gateway_secrets()

        _client_instance = EnterpriseGatewayClient(
            base_url=base_url or enterprise_gateway_secrets["base_url"],
            client_id=client_id or enterprise_gateway_secrets["client_id"],
            client_secret=client_secret or enterprise_gateway_secrets["client_secret"],
            tenant=tenant or enterprise_gateway_secrets.get("tenant", "default"),
            star=star or enterprise_gateway_secrets.get("star", "default"),
        )

    return _client_instance
