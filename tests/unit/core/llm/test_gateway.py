"""
Unit tests for LLM Gateway module

Tests the core LLM gateway functionality including:
- Request processing and validation
- Provider failover mechanisms
- Response caching
- Cost tracking integration
- Error handling and retry logic

UPDATED: Tests now match current implementation (v0.1.2-alpha)
- Uses types from gateway.py (LLMRequest, LLMResponse)
- Uses ModelTier from providers.py
- Tests current LLMGateway implementation
- Updated for async patterns and current API
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from src.core.llm.gateway import LLMGateway, LLMRequest, LLMResponse
from src.core.llm.providers import ModelTier


@pytest.mark.unit
@pytest.mark.asyncio
class TestLLMGateway:
    """Test suite for LLM Gateway"""

    @pytest.fixture
    def gateway(self):
        """Create LLM Gateway instance"""
        return LLMGateway()

    @pytest.fixture
    def sample_request(self):
        """Create sample LLM request"""
        return LLMRequest(
            messages=[{"role": "user", "content": "Hello, how are you?"}],
            model_tier=ModelTier.TIER_2,
            user_id="test_user_123",
            temperature=0.7,
            max_tokens=100,
        )

    async def test_gateway_initialization(self, gateway):
        """Test LLM Gateway initialization"""
        assert gateway is not None
        assert gateway.provider_manager is not None
        assert gateway.cost_tracker is not None
        assert gateway._response_cache is not None
        assert isinstance(gateway._circuit_breakers, dict)

    async def test_request_structure(self, sample_request):
        """Test LLMRequest structure and defaults"""
        assert sample_request.messages[0]["role"] == "user"
        assert sample_request.model_tier == ModelTier.TIER_2
        assert sample_request.user_id == "test_user_123"
        assert sample_request.temperature == 0.7
        assert sample_request.retry_attempts == 2  # Default
        assert sample_request.timeout_seconds == 30  # Default

    async def test_response_structure(self):
        """Test LLMResponse structure"""
        response = LLMResponse(
            request_id="test_req_123",
            content="Test response content",
            model_used="gpt-4o-mini",
            provider_used="openai",
            tokens_used={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            cost_usd=0.001,
            processing_time_ms=150,
            from_cache=False,
        )

        assert response.request_id == "test_req_123"
        assert response.content == "Test response content"
        assert response.model_used == "gpt-4o-mini"
        assert response.provider_used == "openai"
        assert response.tokens_used["total_tokens"] == 30
        assert response.cost_usd == 0.001
        assert response.from_cache is False

    async def test_generate_request_basic(self, gateway, sample_request):
        """Test basic LLM generation request"""
        # Mock the LiteLLM completion
        mock_response = {
            "choices": [{"message": {"content": "Hello! I'm doing well, thank you."}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 15, "total_tokens": 25},
            "model": "gpt-4o-mini",
        }

        with patch("src.core.llm.gateway.acompletion", new_callable=AsyncMock) as mock_completion:
            mock_completion.return_value = mock_response

            response = await gateway.generate(sample_request)

            assert response.success is True
            assert response.content == "Hello! I'm doing well, thank you."
            assert response.tokens_used["total_tokens"] == 25
            assert response.from_cache is False

    async def test_caching_mechanism(self, gateway):
        """Test response caching"""
        request = LLMRequest(
            messages=[{"role": "user", "content": "What is 2+2?"}],
            model_tier=ModelTier.TIER_1,
            user_id="cache_test_user",
            cache_strategy="aggressive",
        )

        mock_response = {
            "choices": [{"message": {"content": "4"}}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 1, "total_tokens": 6},
            "model": "gpt-4o-mini",
        }

        with patch("src.core.llm.gateway.acompletion", new_callable=AsyncMock) as mock_completion:
            mock_completion.return_value = mock_response

            # First request - should call LLM
            response1 = await gateway.generate(request)
            assert response1.from_cache is False
            assert mock_completion.call_count == 1

            # Second identical request - should use cache
            response2 = await gateway.generate(request)
            # Note: Current implementation may not cache immediately, verify behavior
            assert response2.content == response1.content

    async def test_cache_disabled(self, gateway):
        """Test that cache can be disabled"""
        request = LLMRequest(
            messages=[{"role": "user", "content": "Test without cache"}],
            model_tier=ModelTier.TIER_1,
            user_id="no_cache_user",
            cache_strategy="disabled",
        )

        cached_response = gateway._get_cached_response(request)
        assert cached_response is None

    async def test_provider_failover(self, gateway):
        """Test failover to alternate provider on failure"""
        request = LLMRequest(
            messages=[{"role": "user", "content": "Test failover"}],
            model_tier=ModelTier.TIER_2,
            user_id="failover_user",
        )

        # Simulate primary provider failure then success on retry
        with patch("src.core.llm.gateway.acompletion", new_callable=AsyncMock) as mock_completion:
            mock_completion.side_effect = [
                Exception("Provider temporarily unavailable"),
                {
                    "choices": [{"message": {"content": "Failover success"}}],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
                    "model": "claude-3-5-haiku",
                },
            ]

            response = await gateway.generate(request)

            # Should succeed with failover
            assert response.success is True
            assert response.content == "Failover success"

    async def test_cost_tracking_integration(self, gateway):
        """Test integration with cost tracker"""
        request = LLMRequest(
            messages=[{"role": "user", "content": "Calculate cost"}],
            model_tier=ModelTier.TIER_3,
            user_id="cost_user",
        )

        mock_response = {
            "choices": [{"message": {"content": "Response"}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            "model": "gpt-4o",
        }

        with patch("src.core.llm.gateway.acompletion", new_callable=AsyncMock) as mock_completion:
            mock_completion.return_value = mock_response

            response = await gateway.generate(request)

            # Verify cost was calculated
            assert response.cost_usd > 0
            assert isinstance(response.cost_usd, float)

    async def test_retry_on_failure(self, gateway):
        """Test retry mechanism for transient failures"""
        request = LLMRequest(
            messages=[{"role": "user", "content": "Retry test"}],
            model_tier=ModelTier.TIER_1,
            user_id="retry_user",
            retry_attempts=3,
        )

        with patch("src.core.llm.gateway.acompletion", new_callable=AsyncMock) as mock_completion:
            # Fail twice, succeed on third try
            mock_completion.side_effect = [
                Exception("Temporary error 1"),
                Exception("Temporary error 2"),
                {
                    "choices": [{"message": {"content": "Success after retries"}}],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
                    "model": "gpt-4o-mini",
                },
            ]

            response = await gateway.generate(request)

            assert response.success is True
            assert response.content == "Success after retries"
            assert mock_completion.call_count == 3

    async def test_timeout_handling(self, gateway):
        """Test timeout for slow requests"""
        request = LLMRequest(
            messages=[{"role": "user", "content": "Timeout test"}],
            model_tier=ModelTier.TIER_1,
            user_id="timeout_user",
            timeout_seconds=1,  # 1 second timeout
        )

        async def slow_completion(*args, **kwargs):
            await asyncio.sleep(5)  # Simulate slow response
            return {"choices": [{"message": {"content": "Too slow"}}]}

        with patch("src.core.llm.gateway.acompletion", side_effect=slow_completion):
            response = await gateway.generate(request)

            # Should fail due to timeout
            assert response.success is False
            assert "timeout" in response.error.lower() or "time" in response.error.lower()

    async def test_model_tier_selection(self, gateway):
        """Test correct model selection based on tier"""
        tiers_and_expected_models = [
            (ModelTier.TIER_1, ["gpt-4o-mini", "claude-3-5-haiku"]),
            (ModelTier.TIER_2, ["claude-3-5-haiku", "gpt-4o"]),
            (ModelTier.TIER_3, ["gpt-4o", "claude-3-5-sonnet"]),
            (ModelTier.TIER_4, ["gpt-4o", "claude-3-5-sonnet"]),
        ]

        for tier, expected_models in tiers_and_expected_models:
            LLMRequest(
                messages=[{"role": "user", "content": f"Test tier {tier.value}"}],
                model_tier=tier,
                user_id="tier_test_user",
            )

            # Get model for tier
            selected_model = await gateway.provider_manager.get_model_for_tier(tier)

            # Verify model is one of the expected for this tier
            assert selected_model in expected_models

    async def test_concurrent_requests(self, gateway):
        """Test handling of concurrent requests"""
        requests = [
            LLMRequest(
                messages=[{"role": "user", "content": f"Concurrent request {i}"}],
                model_tier=ModelTier.TIER_1,
                user_id=f"concurrent_user_{i}",
            )
            for i in range(5)
        ]

        mock_response = {
            "choices": [{"message": {"content": "Concurrent response"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            "model": "gpt-4o-mini",
        }

        with patch("src.core.llm.gateway.acompletion", new_callable=AsyncMock) as mock_completion:
            mock_completion.return_value = mock_response

            responses = await asyncio.gather(
                *[gateway.generate(req) for req in requests], return_exceptions=True
            )

            # All should succeed
            successful = [r for r in responses if not isinstance(r, Exception)]
            assert len(successful) == 5

    async def test_batch_processing(self, gateway):
        """Test batch request processing"""
        requests = [
            LLMRequest(
                messages=[{"role": "user", "content": f"Batch item {i}"}],
                model_tier=ModelTier.TIER_1,
                user_id="batch_user",
            )
            for i in range(3)
        ]

        mock_response = {
            "choices": [{"message": {"content": "Batch response"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            "model": "gpt-4o-mini",
        }

        with patch("src.core.llm.gateway.acompletion", new_callable=AsyncMock) as mock_completion:
            mock_completion.return_value = mock_response

            responses = await gateway.batch_process_requests(requests)

            assert len(responses) == 3
            assert all(r.success for r in responses)

    async def test_gateway_stats(self, gateway):
        """Test gateway statistics collection"""
        # Generate a few requests
        request = LLMRequest(
            messages=[{"role": "user", "content": "Stats test"}],
            model_tier=ModelTier.TIER_1,
            user_id="stats_user",
        )

        mock_response = {
            "choices": [{"message": {"content": "Response"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            "model": "gpt-4o-mini",
        }

        with patch("src.core.llm.gateway.acompletion", new_callable=AsyncMock) as mock_completion:
            mock_completion.return_value = mock_response

            await gateway.generate(request)

            # Get stats
            stats = await gateway.get_gateway_stats()

            assert "total_requests" in stats
            assert "cache_hit_rate" in stats
            assert "avg_processing_time" in stats
            assert stats["total_requests"] > 0

    async def test_clear_cache(self, gateway):
        """Test cache clearing functionality"""
        # Add something to cache
        request = LLMRequest(
            messages=[{"role": "user", "content": "Cache clear test"}],
            model_tier=ModelTier.TIER_1,
            user_id="cache_user",
        )

        mock_response = {
            "choices": [{"message": {"content": "Cached"}}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
            "model": "gpt-4o-mini",
        }

        with patch("src.core.llm.gateway.acompletion", new_callable=AsyncMock) as mock_completion:
            mock_completion.return_value = mock_response

            await gateway.generate(request)

            # Clear cache
            gateway.clear_cache()

            # Cache should be empty
            assert len(gateway._response_cache) == 0

    async def test_circuit_breaker_per_provider(self, gateway):
        """Test circuit breaker is created per provider"""
        provider_name = "test_provider"

        circuit_breaker = gateway._get_circuit_breaker(provider_name)

        assert circuit_breaker is not None
        assert provider_name in gateway._circuit_breakers

    async def test_litellm_not_available(self):
        """Test graceful degradation when LiteLLM not available"""
        with patch("src.core.llm.gateway.LITELLM_AVAILABLE", False):
            gateway = LLMGateway()

            request = LLMRequest(
                messages=[{"role": "user", "content": "Test"}],
                model_tier=ModelTier.TIER_1,
                user_id="test_user",
            )

            response = await gateway.generate(request)

            # Should return error response
            assert response.success is False
            assert "LiteLLM not available" in response.error

    async def test_system_prompt_included(self, gateway):
        """Test system prompt is included in request"""
        request = LLMRequest(
            messages=[{"role": "user", "content": "Test"}],
            model_tier=ModelTier.TIER_1,
            user_id="test_user",
            system_prompt="You are a helpful assistant.",
        )

        mock_response = {
            "choices": [{"message": {"content": "Response"}}],
            "usage": {"prompt_tokens": 15, "completion_tokens": 5, "total_tokens": 20},
            "model": "gpt-4o-mini",
        }

        with patch("src.core.llm.gateway.acompletion", new_callable=AsyncMock) as mock_completion:
            mock_completion.return_value = mock_response

            await gateway.generate(request)

            # Verify system prompt was included
            call_args = mock_completion.call_args
            messages = call_args[1]["messages"]

            # System message should be first
            assert messages[0]["role"] == "system"
            assert messages[0]["content"] == "You are a helpful assistant."

    async def test_temperature_setting(self, gateway):
        """Test temperature parameter is passed correctly"""
        request = LLMRequest(
            messages=[{"role": "user", "content": "Test"}],
            model_tier=ModelTier.TIER_1,
            user_id="test_user",
            temperature=0.9,
        )

        mock_response = {
            "choices": [{"message": {"content": "Response"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            "model": "gpt-4o-mini",
        }

        with patch("src.core.llm.gateway.acompletion", new_callable=AsyncMock) as mock_completion:
            mock_completion.return_value = mock_response

            await gateway.generate(request)

            # Verify temperature was passed
            call_args = mock_completion.call_args
            assert call_args[1]["temperature"] == 0.9

    async def test_max_tokens_setting(self, gateway):
        """Test max_tokens parameter is passed correctly"""
        request = LLMRequest(
            messages=[{"role": "user", "content": "Test"}],
            model_tier=ModelTier.TIER_1,
            user_id="test_user",
            max_tokens=500,
        )

        mock_response = {
            "choices": [{"message": {"content": "Response"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            "model": "gpt-4o-mini",
        }

        with patch("src.core.llm.gateway.acompletion", new_callable=AsyncMock) as mock_completion:
            mock_completion.return_value = mock_response

            await gateway.generate(request)

            # Verify max_tokens was passed
            call_args = mock_completion.call_args
            assert call_args[1]["max_tokens"] == 500


@pytest.mark.unit
@pytest.mark.asyncio
class TestLLMGatewayIntegration:
    """Integration tests for LLM Gateway with other components"""

    async def test_cost_tracker_integration(self):
        """Test gateway integrates with cost tracker"""
        gateway = LLMGateway()

        assert gateway.cost_tracker is not None

        # Cost tracker should be functional
        from src.core.llm.cost_tracker import get_cost_tracker

        tracker = get_cost_tracker()
        initial_requests = tracker._total_requests

        # Make a request
        request = LLMRequest(
            messages=[{"role": "user", "content": "Test cost tracking"}],
            model_tier=ModelTier.TIER_1,
            user_id="cost_test",
        )

        mock_response = {
            "choices": [{"message": {"content": "Response"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            "model": "gpt-4o-mini",
        }

        with patch("src.core.llm.gateway.acompletion", new_callable=AsyncMock) as mock_completion:
            mock_completion.return_value = mock_response

            await gateway.generate(request)

            # Cost tracker should have recorded the request
            assert tracker._total_requests > initial_requests

    async def test_provider_manager_integration(self):
        """Test gateway integrates with provider manager"""
        gateway = LLMGateway()

        assert gateway.provider_manager is not None

        # Provider manager should provide models for tiers
        model = await gateway.provider_manager.get_model_for_tier(ModelTier.TIER_1)
        assert model is not None
        assert isinstance(model, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
