"""
Integration Tests for Enterprise LLM Gateway Authentication

Tests OAuth2 authentication, token management, and API calls
with comprehensive coverage of all enhancements:
- Token acquisition and refresh
- Exponential backoff retry
- Metrics tracking
- Token pre-fetching
- Tenant/star path construction
"""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import httpx
import pytest

from src.core.llm.enterprise_gateway_client import (
    EnterpriseGatewayClient,
    OAuthMetrics,
)


@pytest.fixture
def mock_token_response():
    """Mock successful token response."""
    return {
        "access_token": "test_access_token_12345",
        "token_type": "Bearer",
        "expires_in": 3600,
        "refresh_token": "test_refresh_token_67890",
    }


@pytest.fixture
def mock_chat_completion_response():
    """Mock successful chat completion response."""
    return {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "created": 1677652288,
        "model": "gpt-4",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Hello! How can I assist you today?"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
    }


@pytest.fixture
async def ai_connect_client():
    """Create Enterprise LLM Gateway client for testing."""
    client = EnterpriseGatewayClient(
        base_url="https://llm-gateway.test.example.com",
        client_id="test_client_id",
        client_secret="test_client_secret",
        tenant="test_tenant",
        star="test_star",
        enable_token_prefetch=False,  # Disable for testing
    )
    yield client
    await client.close()


class TestOAuthMetrics:
    """Test OAuth metrics tracking."""

    def test_metrics_initialization(self):
        """Test metrics initialize with correct defaults."""
        metrics = OAuthMetrics()

        assert metrics.total_requests == 0
        assert metrics.successful_acquisitions == 0
        assert metrics.failed_acquisitions == 0
        assert metrics.refresh_token_uses == 0
        assert metrics.total_latency_ms == 0.0
        assert metrics.max_latency_ms == 0.0
        assert metrics.min_latency_ms == float("inf")

    def test_record_successful_acquisition(self):
        """Test recording successful token acquisition."""
        metrics = OAuthMetrics()

        metrics.record_acquisition(latency_ms=150.5, success=True)

        assert metrics.total_requests == 1
        assert metrics.successful_acquisitions == 1
        assert metrics.failed_acquisitions == 0
        assert metrics.total_latency_ms == 150.5
        assert metrics.max_latency_ms == 150.5
        assert metrics.min_latency_ms == 150.5
        assert metrics.average_latency_ms == 150.5

    def test_record_failed_acquisition(self):
        """Test recording failed token acquisition."""
        metrics = OAuthMetrics()

        metrics.record_acquisition(latency_ms=200.0, success=False)

        assert metrics.total_requests == 1
        assert metrics.successful_acquisitions == 0
        assert metrics.failed_acquisitions == 1
        assert metrics.total_latency_ms == 0.0  # Failed doesn't count in latency

    def test_record_refresh_token_use(self):
        """Test recording refresh token usage."""
        metrics = OAuthMetrics()

        metrics.record_acquisition(latency_ms=100.0, success=True, used_refresh=True)

        assert metrics.successful_acquisitions == 1
        assert metrics.refresh_token_uses == 1

    def test_average_latency_calculation(self):
        """Test average latency calculation."""
        metrics = OAuthMetrics()

        metrics.record_acquisition(100.0, True)
        metrics.record_acquisition(200.0, True)
        metrics.record_acquisition(300.0, True)

        assert metrics.average_latency_ms == 200.0
        assert metrics.max_latency_ms == 300.0
        assert metrics.min_latency_ms == 100.0


class TestEnterpriseGatewayClientInitialization:
    """Test EnterpriseGatewayClient initialization and configuration."""

    @pytest.mark.asyncio
    async def test_client_initialization(self):
        """Test client initializes with correct parameters."""
        client = EnterpriseGatewayClient(
            base_url="https://llm-gateway.test.example.com",
            client_id="test_client",
            client_secret="test_secret",
            tenant="my_tenant",
            star="my_star",
            enable_token_prefetch=False,
        )

        assert client.base_url == "https://llm-gateway.test.example.com"
        assert client.client_id == "test_client"
        assert client.client_secret == "test_secret"
        assert client.tenant == "my_tenant"
        assert client.star == "my_star"
        assert client.metrics is not None
        assert client.http_client is not None

        await client.close()

    @pytest.mark.asyncio
    async def test_client_with_trailing_slash(self):
        """Test client handles base URL with trailing slash."""
        client = EnterpriseGatewayClient(
            base_url="https://llm-gateway.test.example.com/",
            client_id="test",
            client_secret="test",
            enable_token_prefetch=False,
        )

        assert client.base_url == "https://llm-gateway.test.example.com"
        await client.close()

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test client works as async context manager."""
        async with EnterpriseGatewayClient(
            base_url="https://llm-gateway.test.example.com",
            client_id="test",
            client_secret="test",
            enable_token_prefetch=False,
        ) as client:
            assert client.http_client is not None


class TestTokenAcquisition:
    """Test token acquisition with various scenarios."""

    @pytest.mark.asyncio
    async def test_successful_token_acquisition(self, ai_connect_client, mock_token_response):
        """Test successful token acquisition."""
        with patch.object(
            ai_connect_client.http_client, "post", new_callable=AsyncMock
        ) as mock_post:
            # Mock successful response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_token_response
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            token = await ai_connect_client._get_access_token()

            assert token == "test_access_token_12345"
            assert ai_connect_client.access_token == "test_access_token_12345"
            assert ai_connect_client.refresh_token == "test_refresh_token_67890"
            assert ai_connect_client.token_expires_at is not None

            # Verify metrics
            assert ai_connect_client.metrics.successful_acquisitions == 1
            assert ai_connect_client.metrics.failed_acquisitions == 0

    @pytest.mark.asyncio
    async def test_token_caching(self, ai_connect_client, mock_token_response):
        """Test that valid tokens are cached and reused."""
        with patch.object(
            ai_connect_client.http_client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = mock_token_response
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            # First call should fetch token
            token1 = await ai_connect_client._get_access_token()

            # Second call should use cached token (no new API call)
            token2 = await ai_connect_client._get_access_token()

            assert token1 == token2
            assert mock_post.call_count == 1  # Only one API call

    @pytest.mark.asyncio
    async def test_token_refresh_on_expiry(self, ai_connect_client, mock_token_response):
        """Test token is refreshed when expired."""
        with patch.object(
            ai_connect_client.http_client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = mock_token_response
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            # Get initial token
            await ai_connect_client._get_access_token()

            # Expire the token
            ai_connect_client.token_expires_at = datetime.now(UTC) - timedelta(seconds=10)

            # Next call should fetch new token
            await ai_connect_client._get_access_token()

            assert mock_post.call_count == 2  # Two API calls


class TestRefreshToken:
    """Test refresh token functionality."""

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, ai_connect_client):
        """Test successful refresh token usage."""
        # Set up refresh token
        ai_connect_client.refresh_token = "existing_refresh_token"
        ai_connect_client.token_expires_at = datetime.now(UTC) - timedelta(seconds=10)

        refresh_response = {
            "access_token": "new_access_token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": "new_refresh_token",
        }

        with patch.object(
            ai_connect_client.http_client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = refresh_response
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            token = await ai_connect_client._get_access_token()

            assert token == "new_access_token"
            assert ai_connect_client.refresh_token == "new_refresh_token"
            assert ai_connect_client.metrics.refresh_token_uses == 1

    @pytest.mark.asyncio
    async def test_refresh_token_fallback_on_failure(self, ai_connect_client, mock_token_response):
        """Test fallback to client credentials when refresh fails."""
        ai_connect_client.refresh_token = "invalid_refresh_token"
        ai_connect_client.token_expires_at = datetime.now(UTC) - timedelta(seconds=10)

        with patch.object(
            ai_connect_client.http_client, "post", new_callable=AsyncMock
        ) as mock_post:
            # First call (refresh) fails, second call (client credentials) succeeds
            mock_refresh_response = Mock()
            mock_refresh_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Refresh failed", request=None, response=MagicMock(status_code=401)
            )

            mock_success_response = Mock()
            mock_success_response.json.return_value = mock_token_response
            mock_success_response.raise_for_status = MagicMock()

            mock_post.side_effect = [mock_refresh_response, mock_success_response]

            token = await ai_connect_client._get_access_token()

            assert token == "test_access_token_12345"
            assert ai_connect_client.refresh_token == "test_refresh_token_67890"
            assert mock_post.call_count == 2  # Refresh + client credentials


class TestExponentialBackoffRetry:
    """Test exponential backoff retry logic."""

    @pytest.mark.asyncio
    async def test_retry_on_500_error(self, ai_connect_client, mock_token_response):
        """Test retry on 500 error with exponential backoff."""
        with patch.object(
            ai_connect_client.http_client, "post", new_callable=AsyncMock
        ) as mock_post:
            # First two attempts fail, third succeeds
            mock_error_response = Mock()
            mock_error_response.status_code = 500
            mock_error_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Server error", request=None, response=MagicMock(status_code=500)
            )

            mock_success_response = Mock()
            mock_success_response.json.return_value = mock_token_response
            mock_success_response.raise_for_status = MagicMock()

            mock_post.side_effect = [
                mock_error_response,
                mock_error_response,
                mock_success_response,
            ]

            token = await ai_connect_client._acquire_new_token(max_retries=3)

            assert token == "test_access_token_12345"
            assert mock_post.call_count == 3

    @pytest.mark.asyncio
    async def test_no_retry_on_400_error(self, ai_connect_client):
        """Test no retry on 4xx client errors."""
        with patch.object(
            ai_connect_client.http_client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.text = "Bad request"
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Bad request", request=None, response=mock_response
            )
            mock_post.return_value = mock_response

            with pytest.raises(httpx.HTTPStatusError):
                await ai_connect_client._acquire_new_token(max_retries=3)

            assert mock_post.call_count == 1  # No retries

    @pytest.mark.asyncio
    async def test_retry_on_429_rate_limit(self, ai_connect_client, mock_token_response):
        """Test retry on 429 rate limit error."""
        with patch.object(
            ai_connect_client.http_client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_rate_limit_response = Mock()
            mock_rate_limit_response.status_code = 429
            mock_rate_limit_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Rate limited", request=None, response=MagicMock(status_code=429)
            )

            mock_success_response = Mock()
            mock_success_response.json.return_value = mock_token_response
            mock_success_response.raise_for_status = MagicMock()

            mock_post.side_effect = [mock_rate_limit_response, mock_success_response]

            token = await ai_connect_client._acquire_new_token(max_retries=3)

            assert token == "test_access_token_12345"
            assert mock_post.call_count == 2


class TestChatCompletionWithTenantStar:
    """Test chat completion with correct tenant/star path construction."""

    @pytest.mark.asyncio
    async def test_chat_completion_url_construction(
        self, ai_connect_client, mock_token_response, mock_chat_completion_response
    ):
        """Test that chat completion uses correct /genai/v1/{tenant}/{star} path."""
        with patch.object(
            ai_connect_client.http_client, "post", new_callable=AsyncMock
        ) as mock_post:
            # Mock token acquisition
            token_response = Mock()
            token_response.json.return_value = mock_token_response
            token_response.raise_for_status = MagicMock()

            # Mock chat completion
            chat_response = Mock()
            chat_response.json.return_value = mock_chat_completion_response
            chat_response.raise_for_status = MagicMock()

            mock_post.side_effect = [token_response, chat_response]

            messages = [{"role": "user", "content": "Hello"}]
            await ai_connect_client.chat_completion(messages=messages)

            # Verify chat completion URL
            assert mock_post.call_count == 2
            chat_call = mock_post.call_args_list[1]
            chat_url = chat_call[0][0]

            expected_url = (
                f"{ai_connect_client.base_url}/genai/v1/"
                f"{ai_connect_client.tenant}/{ai_connect_client.star}/chat/completions"
            )
            assert chat_url == expected_url

    @pytest.mark.asyncio
    async def test_chat_completion_with_custom_tenant_star(
        self, mock_token_response, mock_chat_completion_response
    ):
        """Test chat completion with custom tenant and star values."""
        client = EnterpriseGatewayClient(
            base_url="https://llm-gateway.test.example.com",
            client_id="test",
            client_secret="test",
            tenant="custom_tenant",
            star="production",
            enable_token_prefetch=False,
        )

        with patch.object(client.http_client, "post", new_callable=AsyncMock) as mock_post:
            token_response = Mock()
            token_response.json.return_value = mock_token_response
            token_response.raise_for_status = MagicMock()

            chat_response = Mock()
            chat_response.json.return_value = mock_chat_completion_response
            chat_response.raise_for_status = MagicMock()

            mock_post.side_effect = [token_response, chat_response]

            messages = [{"role": "user", "content": "Test"}]
            await client.chat_completion(messages=messages)

            # Verify correct URL with custom tenant/star
            chat_call = mock_post.call_args_list[1]
            chat_url = chat_call[0][0]

            assert "custom_tenant" in chat_url
            assert "production" in chat_url
            assert "/genai/v1/custom_tenant/production/chat/completions" in chat_url

        await client.close()


class TestOAuthMetricsAPI:
    """Test OAuth metrics API."""

    @pytest.mark.asyncio
    async def test_get_oauth_metrics(self, ai_connect_client, mock_token_response):
        """Test getting OAuth metrics."""
        with patch.object(
            ai_connect_client.http_client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = mock_token_response
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            # Perform some token acquisitions
            await ai_connect_client._get_access_token()

            metrics = ai_connect_client.get_oauth_metrics()

            assert "total_requests" in metrics
            assert "successful_acquisitions" in metrics
            assert "failed_acquisitions" in metrics
            assert "refresh_token_uses" in metrics
            assert "average_latency_ms" in metrics
            assert "max_latency_ms" in metrics
            assert "min_latency_ms" in metrics
            assert "success_rate" in metrics

            assert metrics["total_requests"] == 1
            assert metrics["successful_acquisitions"] == 1
            assert metrics["success_rate"] == 100.0


class TestConcurrentTokenAcquisition:
    """Test concurrent token acquisition with locking."""

    @pytest.mark.asyncio
    async def test_concurrent_acquisitions_use_lock(self, ai_connect_client, mock_token_response):
        """Test that concurrent token acquisitions use lock correctly."""
        with patch.object(
            ai_connect_client.http_client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = mock_token_response
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            # Expire token to force acquisition
            ai_connect_client.token_expires_at = datetime.now(UTC) - timedelta(seconds=10)

            # Concurrent token acquisitions
            results = await asyncio.gather(
                ai_connect_client._get_access_token(),
                ai_connect_client._get_access_token(),
                ai_connect_client._get_access_token(),
            )

            # All should get the same token
            assert all(token == "test_access_token_12345" for token in results)

            # Due to locking, only one acquisition should happen
            assert mock_post.call_count == 1
