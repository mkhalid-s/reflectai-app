"""
Unit tests for async provider health checks (Plan 2 implementation)

Tests the refactored async health check system including:
- Async health check methods
- Timeout handling
- Concurrent health checks
- Lock-based synchronization
- Provider failover with async
"""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from src.core.llm.model_mapper import ModelTier
from src.core.llm.providers import ModelPricing, ProviderConfig, ProviderManager


class TestAsyncHealthChecks:
    """Test suite for async provider health checks"""

    @pytest.fixture
    def provider_manager(self):
        """Create provider manager instance"""
        return ProviderManager()

    @pytest.fixture
    def mock_provider_config(self):
        """Create mock provider configuration"""
        return ProviderConfig(
            name="test_provider",
            priority=1,
            models={ModelTier.TIER_1.value: "gpt-4o-mini", ModelTier.TIER_3.value: "gpt-4o"},
            pricing={
                "gpt-4o-mini": ModelPricing(
                    input_cost_per_1k=0.15,
                    output_cost_per_1k=0.60,
                    max_response_time_s=3,
                    max_tokens=16000,
                    context_window=128000,
                )
            },
            api_key_secret="TEST_API_KEY",
            health_check_url="https://api.test.com/health",
        )

    @pytest.mark.asyncio
    async def test_is_provider_healthy_async(self, provider_manager):
        """Test async health check method"""
        # Arrange
        provider_name = "openai"
        # Expire the cache to force a new check
        provider_manager._last_health_check[provider_name] = datetime.now(UTC) - timedelta(
            minutes=10
        )

        # Mock the actual health check to return True
        with patch.object(
            provider_manager, "_check_provider_health_async", new_callable=AsyncMock
        ) as mock_check:
            mock_check.return_value = True

            # Act
            result = await provider_manager._is_provider_healthy(provider_name)

            # Assert
            assert result is True
            mock_check.assert_called_once_with(provider_name)

    @pytest.mark.asyncio
    async def test_health_check_with_timeout(self, provider_manager):
        """Test health check respects timeout"""
        # Arrange
        provider_name = "slow_provider"

        async def slow_health_check(name):
            await asyncio.sleep(10)  # Simulate slow response
            return True

        # Mock the health check to be slow
        with patch.object(
            provider_manager, "_check_provider_health_async", side_effect=slow_health_check
        ):
            # Act
            start_time = asyncio.get_event_loop().time()
            result = await provider_manager._is_provider_healthy(provider_name)
            end_time = asyncio.get_event_loop().time()

            # Assert
            assert result is False  # Should timeout and return False
            assert (end_time - start_time) < 7  # Should timeout in ~5 seconds, not 10
            assert provider_manager._provider_health[provider_name] is False

    @pytest.mark.asyncio
    async def test_health_check_caching(self, provider_manager):
        """Test health check result caching within interval"""
        # Arrange
        provider_name = "openai"
        provider_manager._provider_health[provider_name] = True
        provider_manager._last_health_check[provider_name] = datetime.now(UTC)

        # Mock the actual health check
        with patch.object(
            provider_manager, "_check_provider_health_async", new_callable=AsyncMock
        ) as mock_check:
            mock_check.return_value = True

            # Act - Should use cached value
            result = await provider_manager._is_provider_healthy(provider_name)

            # Assert
            assert result is True
            mock_check.assert_not_called()  # Should not call actual check due to cache

    @pytest.mark.asyncio
    async def test_health_check_cache_expiration(self, provider_manager):
        """Test health check cache expires after interval"""
        # Arrange
        provider_name = "openai"
        provider_manager._provider_health[provider_name] = True
        # Set last check time to 6 minutes ago (past the 5-minute interval)
        provider_manager._last_health_check[provider_name] = datetime.now(UTC) - timedelta(
            minutes=6
        )

        # Mock the actual health check
        with patch.object(
            provider_manager, "_check_provider_health_async", new_callable=AsyncMock
        ) as mock_check:
            mock_check.return_value = True

            # Act - Should perform new check
            result = await provider_manager._is_provider_healthy(provider_name)

            # Assert
            assert result is True
            mock_check.assert_called_once_with(provider_name)  # Should call due to expired cache

    @pytest.mark.asyncio
    async def test_concurrent_health_checks(self, provider_manager):
        """Test concurrent health checks use locking correctly"""
        # Arrange
        provider_name = "test_provider"
        call_count = 0

        async def health_check_with_delay(name):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.1)  # Simulate network delay
            return True

        # Expire the cache to force checks
        provider_manager._last_health_check[provider_name] = datetime.now(UTC) - timedelta(
            minutes=10
        )

        with patch.object(
            provider_manager, "_check_provider_health_async", side_effect=health_check_with_delay
        ):
            # Act - Start multiple concurrent health checks
            results = await asyncio.gather(
                provider_manager._is_provider_healthy(provider_name),
                provider_manager._is_provider_healthy(provider_name),
                provider_manager._is_provider_healthy(provider_name),
            )

            # Assert
            assert all(r is True for r in results)
            # Due to locking and caching, only one actual check should be made
            assert call_count == 1  # Lock prevents concurrent checks

    @pytest.mark.asyncio
    async def test_get_provider_for_tier_async(self, provider_manager):
        """Test get_provider_for_tier is async and calls async health check"""
        # Arrange
        with patch.object(
            provider_manager, "_is_provider_healthy", new_callable=AsyncMock
        ) as mock_health:
            mock_health.return_value = True

            # Act
            provider = await provider_manager.get_provider_for_tier(ModelTier.TIER_1)

            # Assert
            assert provider is not None
            assert provider.name in ["openai", "enterprise_gateway", "bedrock"]
            mock_health.assert_called()  # Should check health

    @pytest.mark.asyncio
    async def test_get_model_for_tier_async(self, provider_manager):
        """Test get_model_for_tier is async"""
        # Arrange
        with patch.object(
            provider_manager, "_is_provider_healthy", new_callable=AsyncMock
        ) as mock_health:
            mock_health.return_value = True

            # Act
            result = await provider_manager.get_model_for_tier(ModelTier.TIER_1)

            # Assert
            assert result is not None
            model_name, provider = result
            assert isinstance(model_name, str)
            assert isinstance(provider, ProviderConfig)
            assert provider.name in ["openai", "enterprise_gateway", "bedrock"]

    @pytest.mark.asyncio
    async def test_get_provider_health_status_async(self, provider_manager):
        """Test get_provider_health_status checks all providers concurrently"""
        # Arrange
        health_check_times = {}

        async def track_health_check(name):
            health_check_times[name] = asyncio.get_event_loop().time()
            await asyncio.sleep(0.1)  # Simulate network delay
            return True

        with patch.object(provider_manager, "_is_provider_healthy", side_effect=track_health_check):
            # Act
            start_time = asyncio.get_event_loop().time()
            status = await provider_manager.get_provider_health_status()
            end_time = asyncio.get_event_loop().time()

            # Assert
            assert "providers" in status
            assert status["total_providers"] == len(provider_manager.providers)

            # All checks should run concurrently, so total time should be ~0.1s not 0.3s
            assert (end_time - start_time) < 0.3  # Concurrent execution

            # Verify all checks started around the same time
            if len(health_check_times) > 1:
                times = list(health_check_times.values())
                time_spread = max(times) - min(times)
                assert time_spread < 0.05  # All should start within 50ms

    @pytest.mark.asyncio
    async def test_health_check_with_exception(self, provider_manager):
        """Test health check handles exceptions gracefully"""
        # Arrange
        provider_name = "failing_provider"

        async def failing_health_check(name):
            raise Exception("Network error")

        with patch.object(
            provider_manager, "_check_provider_health_async", side_effect=failing_health_check
        ):
            # Act
            result = await provider_manager._is_provider_healthy(provider_name)

            # Assert
            assert result is False
            assert provider_manager._provider_health[provider_name] is False

    @pytest.mark.asyncio
    async def test_check_provider_health_async_success(self, provider_manager):
        """Test actual health check implementation with success"""
        # Arrange
        provider_name = "openai"

        # Create proper async context manager mock
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            with patch.object(
                provider_manager, "_get_api_key", new_callable=AsyncMock
            ) as mock_get_key:
                mock_get_key.return_value = "test_key"

                # Act
                result = await provider_manager._check_provider_health_async(provider_name)

                # Assert
                assert result is True

    @pytest.mark.asyncio
    async def test_check_provider_health_async_failure(self, provider_manager):
        """Test actual health check implementation with failure"""
        # Arrange
        provider_name = "openai"

        # Mock aiohttp session to raise exception
        mock_session = AsyncMock()
        mock_session.get.side_effect = aiohttp.ClientError("Connection failed")
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        with patch("aiohttp.ClientSession", return_value=mock_session):
            # Act
            result = await provider_manager._check_provider_health_async(provider_name)

            # Assert
            assert result is False

    @pytest.mark.asyncio
    async def test_check_provider_health_async_timeout(self, provider_manager):
        """Test health check handles timeout correctly"""
        # Arrange
        provider_name = "openai"

        # Mock aiohttp session to timeout
        mock_session = AsyncMock()
        mock_session.get.side_effect = TimeoutError()
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        with patch("aiohttp.ClientSession", return_value=mock_session):
            # Act
            result = await provider_manager._check_provider_health_async(provider_name)

            # Assert
            assert result is False

    @pytest.mark.asyncio
    async def test_provider_failover_with_async_health_checks(self, provider_manager):
        """Test provider failover works with async health checks"""
        # Arrange - Make first provider unhealthy
        provider_manager._provider_health["openai"] = False
        provider_manager._last_health_check["openai"] = datetime.now(UTC)

        with patch.object(
            provider_manager, "_is_provider_healthy", new_callable=AsyncMock
        ) as mock_health:
            # First provider (openai) is unhealthy, second (enterprise_gateway) is healthy
            mock_health.side_effect = lambda name: name != "openai"

            # Act
            provider = await provider_manager.get_provider_for_tier(ModelTier.TIER_1)

            # Assert
            assert provider is not None
            assert provider.name != "openai"  # Should skip unhealthy provider
            assert provider.name in ["enterprise_gateway", "bedrock"]

    @pytest.mark.asyncio
    async def test_no_deadlock_in_async_context(self, provider_manager):
        """Test no deadlocks when called from async context"""
        # Arrange
        provider_name = "openai"

        async def nested_async_operation():
            # This simulates calling health check from within an async context
            result = await provider_manager._is_provider_healthy(provider_name)
            return result

        with patch.object(
            provider_manager, "_check_provider_health_async", new_callable=AsyncMock
        ) as mock_check:
            mock_check.return_value = True

            # Act - Should not deadlock
            result = await nested_async_operation()

            # Assert
            assert result is True
            # Should not hang or raise RuntimeError about event loop


class TestAsyncHealthCheckIntegration:
    """Integration tests for async health checks"""

    @pytest.mark.asyncio
    async def test_full_request_flow_with_async_health_checks(self):
        """Test full request flow uses async health checks"""
        # This would be an integration test with actual gateway
        # Skipping for unit test file - would go in integration tests
        pass

    @pytest.mark.asyncio
    async def test_multiple_providers_concurrent_check(self):
        """Test checking multiple providers concurrently"""
        manager = ProviderManager()

        # Expire all caches to force checks
        for provider_name in [p.name for p in manager.providers]:
            manager._last_health_check[provider_name] = datetime.now(UTC) - timedelta(minutes=10)

        with patch.object(
            manager, "_check_provider_health_async", new_callable=AsyncMock
        ) as mock_check:
            mock_check.return_value = True

            # Act - Get health status (checks all providers)
            status = await manager.get_provider_health_status()

            # Assert
            assert status["total_providers"] > 0
            assert status["healthy_providers"] > 0
            assert len(status["providers"]) == status["total_providers"]

            # Verify concurrent checks
            assert mock_check.call_count == status["total_providers"]
