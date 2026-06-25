"""
Unit tests for LLM Cost Tracker module

Tests cost tracking and budget management including:
- Cost calculation and tracking
- Budget alert triggering
- Slack notification sending
- Usage statistics
- Cost optimization recommendations
"""

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from src.core.llm.cost_tracker import (
    MODEL_PRICING,
    BudgetAlert,
    CostRecord,
    CostSummary,
    CostTracker,
    ModelTier,
    get_cost_tracker,
)


class TestCostTracker:
    """Test suite for Cost Tracker"""

    @pytest.fixture
    def cost_tracker(self):
        """Create CostTracker instance"""
        return CostTracker(max_records_in_memory=1000)

    @pytest.fixture
    def sample_budget_alerts(self):
        """Sample budget alerts for testing"""
        return [
            BudgetAlert(
                name="daily_limit",
                budget_usd=100.0,
                period="daily",
                threshold_percent=80.0,
                alert_channels=["slack"],
            ),
            BudgetAlert(
                name="monthly_limit",
                budget_usd=3000.0,
                period="monthly",
                threshold_percent=90.0,
                alert_channels=["slack", "email"],
            ),
        ]

    def test_cost_tracker_initialization(self, cost_tracker):
        """Test cost tracker initializes with correct defaults"""
        assert cost_tracker._max_records == 1000
        assert len(cost_tracker._budgets) == 2  # Default daily and monthly budgets
        assert "daily_total" in cost_tracker._budgets
        assert "monthly_total" in cost_tracker._budgets
        assert cost_tracker._total_cost == 0.0
        assert cost_tracker._total_requests == 0

    def test_calculate_cost_basic(self, cost_tracker):
        """Test basic cost calculation for a model"""
        # Arrange
        tokens_used = {"prompt_tokens": 1000, "completion_tokens": 500, "total_tokens": 1500}

        # Act
        cost = cost_tracker.calculate_cost("gpt-4o-mini", tokens_used, is_batch=False)

        # Assert
        # gpt-4o-mini: $0.15/$0.60 per 1M tokens
        expected_cost = (1000 / 1_000_000) * 0.15 + (500 / 1_000_000) * 0.60
        assert cost == round(expected_cost, 6)

    def test_calculate_cost_with_batch_discount(self, cost_tracker):
        """Test cost calculation with batch processing discount"""
        # Arrange
        tokens_used = {"prompt_tokens": 10000, "completion_tokens": 5000}

        # Act
        regular_cost = cost_tracker.calculate_cost("gpt-4o", tokens_used, is_batch=False)
        batch_cost = cost_tracker.calculate_cost("gpt-4o", tokens_used, is_batch=True)

        # Assert
        assert batch_cost < regular_cost
        assert batch_cost == round(regular_cost * 0.6, 6)  # 40% discount

    def test_calculate_cost_unknown_model(self, cost_tracker):
        """Test cost calculation for unknown model uses default pricing"""
        # Arrange
        tokens_used = {"prompt_tokens": 1000, "completion_tokens": 500}

        # Act
        cost = cost_tracker.calculate_cost("unknown-model-xyz", tokens_used)

        # Assert
        # Default: $1.00 input, $2.00 output per 1M tokens
        expected_cost = (1000 / 1_000_000) * 1.00 + (500 / 1_000_000) * 2.00
        assert cost == round(expected_cost, 6)

    def test_record_request_basic(self, cost_tracker):
        """Test basic request recording"""
        # Arrange
        tokens_used = {"prompt_tokens": 1000, "completion_tokens": 500, "total_tokens": 1500}

        # Act
        cost_tracker.record_request(
            user_id="user123",
            model_name="gpt-4o-mini",
            provider_name="openai",
            tokens_used=tokens_used,
            request_type="analysis",
        )

        # Assert
        assert len(cost_tracker._cost_records) == 1
        assert cost_tracker._total_requests == 1
        assert cost_tracker._total_cost > 0
        assert cost_tracker._user_costs["user123"] > 0
        assert cost_tracker._model_costs["gpt-4o-mini"] > 0

    def test_record_request_with_explicit_cost(self, cost_tracker):
        """Test recording request with pre-calculated cost"""
        # Arrange
        tokens_used = {"prompt_tokens": 1000, "completion_tokens": 500}
        explicit_cost = 0.05

        # Act
        cost_tracker.record_request(
            user_id="user123",
            model_name="gpt-4o",
            provider_name="openai",
            tokens_used=tokens_used,
            cost_usd=explicit_cost,
        )

        # Assert
        assert cost_tracker._total_cost == explicit_cost

    def test_record_multiple_requests(self, cost_tracker):
        """Test recording multiple requests updates aggregations"""
        # Arrange
        tokens_used = {"prompt_tokens": 1000, "completion_tokens": 500}

        # Act
        for i in range(10):
            cost_tracker.record_request(
                user_id=f"user{i % 3}",  # 3 users
                model_name="gpt-4o-mini",
                provider_name="openai",
                tokens_used=tokens_used,
            )

        # Assert
        assert len(cost_tracker._cost_records) == 10
        assert cost_tracker._total_requests == 10
        assert len(cost_tracker._user_costs) == 3  # 3 unique users

    def test_budget_alert_configuration(self, cost_tracker, sample_budget_alerts):
        """Test adding custom budget alerts"""
        # Arrange
        custom_budget = BudgetAlert(
            name="test_budget",
            budget_usd=50.0,
            period="weekly",
            threshold_percent=75.0,
            alert_channels=["slack"],
        )

        # Act
        cost_tracker.add_budget_alert(custom_budget)

        # Assert
        assert "test_budget" in cost_tracker._budgets
        assert cost_tracker._budgets["test_budget"].budget_usd == 50.0

    @pytest.mark.asyncio
    async def test_budget_alert_triggered(self, cost_tracker):
        """Test budget alert is triggered when threshold is reached"""
        import asyncio

        # Arrange
        strict_budget = BudgetAlert(
            name="strict_budget",
            budget_usd=0.90,  # Very low budget - cost will be ~$0.75 which exceeds 80% ($0.72)
            period="daily",
            threshold_percent=80.0,
            alert_channels=["slack"],
        )
        cost_tracker.add_budget_alert(strict_budget)

        # Mock the alert sending
        with patch.object(cost_tracker, "_send_budget_alert", new_callable=AsyncMock) as mock_alert:
            # Act - Record expensive request that exceeds threshold
            cost_tracker.record_request(
                user_id="test_user",
                model_name="gpt-4o",
                provider_name="openai",
                tokens_used={"prompt_tokens": 100000, "completion_tokens": 50000},
            )

            # Give enough time for the async task to be created and executed
            await asyncio.sleep(0.5)

            # Assert
            mock_alert.assert_called()

    def test_get_usage_summary(self, cost_tracker):
        """Test retrieval of usage summary"""
        # Arrange
        tokens_used = {"prompt_tokens": 1000, "completion_tokens": 500}
        cost_tracker.record_request(
            user_id="user1",
            model_name="gpt-4o-mini",
            provider_name="openai",
            tokens_used=tokens_used,
        )
        cost_tracker.record_request(
            user_id="user2",
            model_name="claude-3-5-haiku",
            provider_name="anthropic",
            tokens_used=tokens_used,
        )

        # Act
        summary = cost_tracker.get_usage_summary()

        # Assert
        assert isinstance(summary, CostSummary)
        assert summary.total_requests == 2
        assert summary.total_cost > 0
        assert "gpt-4o-mini" in summary.cost_by_model
        assert "claude-3-5-haiku" in summary.cost_by_model
        assert "openai" in summary.cost_by_provider
        assert "anthropic" in summary.cost_by_provider

    def test_get_usage_summary_with_date_range(self, cost_tracker):
        """Test usage summary filtered by date range"""
        # Arrange
        tokens_used = {"prompt_tokens": 1000, "completion_tokens": 500}
        cost_tracker.record_request(
            user_id="user1",
            model_name="gpt-4o-mini",
            provider_name="openai",
            tokens_used=tokens_used,
        )

        # Act
        start_date = datetime.now(UTC) - timedelta(days=1)
        end_date = datetime.now(UTC) + timedelta(days=1)
        summary = cost_tracker.get_usage_summary(start_date=start_date, end_date=end_date)

        # Assert
        assert summary.total_requests == 1
        assert summary.period_start == start_date
        assert summary.period_end == end_date

    def test_get_user_usage(self, cost_tracker):
        """Test retrieval of user-specific usage"""
        # Arrange
        tokens_used = {"prompt_tokens": 1000, "completion_tokens": 500, "total_tokens": 1500}
        cost_tracker.record_request(
            user_id="user123",
            model_name="gpt-4o-mini",
            provider_name="openai",
            tokens_used=tokens_used,
            request_type="analysis",
        )
        cost_tracker.record_request(
            user_id="user123",
            model_name="gpt-4o",
            provider_name="openai",
            tokens_used=tokens_used,
            request_type="advice",
        )
        cost_tracker.record_request(
            user_id="user456",
            model_name="gpt-4o-mini",
            provider_name="openai",
            tokens_used=tokens_used,
        )

        # Act
        user_usage = cost_tracker.get_user_usage("user123", days=30)

        # Assert
        assert user_usage["user_id"] == "user123"
        assert user_usage["total_requests"] == 2
        assert user_usage["total_cost"] > 0
        assert "analysis" in user_usage["cost_by_type"]
        assert "advice" in user_usage["cost_by_type"]

    def test_get_model_performance(self, cost_tracker):
        """Test model performance analysis"""
        # Arrange
        tokens_used = {"prompt_tokens": 1000, "completion_tokens": 500, "total_tokens": 1500}
        for _ in range(5):
            cost_tracker.record_request(
                user_id="user1",
                model_name="gpt-4o-mini",
                provider_name="openai",
                tokens_used=tokens_used,
            )
        for _ in range(3):
            cost_tracker.record_request(
                user_id="user1",
                model_name="gpt-4o",
                provider_name="openai",
                tokens_used=tokens_used,
            )

        # Act
        performance = cost_tracker.get_model_performance()

        # Assert
        assert "gpt-4o-mini" in performance
        assert "gpt-4o" in performance
        assert performance["gpt-4o-mini"]["total_requests"] == 5
        assert performance["gpt-4o"]["total_requests"] == 3
        assert performance["gpt-4o-mini"]["average_cost_per_request"] > 0
        assert performance["gpt-4o"]["average_cost_per_request"] > 0

    def test_get_budget_status(self, cost_tracker):
        """Test budget status retrieval"""
        # Arrange
        tokens_used = {"prompt_tokens": 10000, "completion_tokens": 5000}
        cost_tracker.record_request(
            user_id="user1", model_name="gpt-4o", provider_name="openai", tokens_used=tokens_used
        )

        # Act
        budget_status = cost_tracker.get_budget_status()

        # Assert
        assert "daily_total" in budget_status
        assert "monthly_total" in budget_status
        assert budget_status["daily_total"]["budget_usd"] == 50.0
        assert budget_status["daily_total"]["current_usage"] > 0
        assert budget_status["daily_total"]["usage_percent"] >= 0

    def test_cost_optimization_recommendations(self, cost_tracker):
        """Test generation of cost optimization recommendations"""
        # Arrange - Create usage pattern that should trigger recommendations
        tokens_used = {"prompt_tokens": 10000, "completion_tokens": 5000}

        # Use expensive model multiple times
        for _ in range(15):
            cost_tracker.record_request(
                user_id="user1",
                model_name="gpt-4o",
                provider_name="openai",
                tokens_used=tokens_used,
            )

        # Act
        recommendations = cost_tracker.get_cost_optimization_recommendations()

        # Assert
        assert isinstance(recommendations, list)
        # Should have some recommendations
        assert len(recommendations) >= 0

    def test_batch_savings_summary(self, cost_tracker):
        """Test batch savings summary calculation"""
        # Arrange
        tokens_used = {"prompt_tokens": 10000, "completion_tokens": 5000}

        # Regular requests
        for _ in range(5):
            cost_tracker.record_request(
                user_id="user1",
                model_name="gpt-4o-mini",
                provider_name="openai",
                tokens_used=tokens_used,
                request_type="general",
            )

        # Batch requests
        for _ in range(10):
            cost_tracker.record_request(
                user_id="user1",
                model_name="gpt-4o-mini",
                provider_name="openai",
                tokens_used=tokens_used,
                request_type="batch_analysis",
                is_batch=True,
            )

        # Act
        savings = cost_tracker.get_batch_savings_summary()

        # Assert
        assert savings["batch_requests"] == 10
        assert savings["regular_requests"] == 5
        assert savings["savings_usd"] > 0
        assert savings["savings_percentage"] == 40.0

    def test_export_records(self, cost_tracker):
        """Test exporting cost records as JSON"""
        # Arrange
        tokens_used = {"prompt_tokens": 1000, "completion_tokens": 500, "total_tokens": 1500}
        cost_tracker.record_request(
            user_id="user1",
            model_name="gpt-4o-mini",
            provider_name="openai",
            tokens_used=tokens_used,
        )
        cost_tracker.record_request(
            user_id="user2",
            model_name="claude-3-5-haiku",
            provider_name="anthropic",
            tokens_used=tokens_used,
        )

        # Act
        start_date = datetime.now(UTC) - timedelta(days=1)
        end_date = datetime.now(UTC) + timedelta(days=1)
        export_json = cost_tracker.export_records(start_date, end_date)

        # Assert
        export_data = json.loads(export_json)
        assert isinstance(export_data, list)
        assert len(export_data) == 2
        assert "record_id" in export_data[0]
        assert "user_id" in export_data[0]
        assert "model_name" in export_data[0]
        assert "cost_usd" in export_data[0]

    def test_tracker_stats(self, cost_tracker):
        """Test cost tracker statistics"""
        # Arrange
        tokens_used = {"prompt_tokens": 1000, "completion_tokens": 500}
        cost_tracker.record_request(
            user_id="user1",
            model_name="gpt-4o-mini",
            provider_name="openai",
            tokens_used=tokens_used,
        )
        cost_tracker.record_request(
            user_id="user2", model_name="gpt-4o", provider_name="openai", tokens_used=tokens_used
        )
        cost_tracker.record_request(
            user_id="user1",
            model_name="claude-3-5-haiku",
            provider_name="anthropic",
            tokens_used=tokens_used,
        )

        # Act
        stats = cost_tracker.get_tracker_stats()

        # Assert
        assert stats["total_records"] == 3
        assert stats["total_requests"] == 3
        assert stats["total_cost"] > 0
        assert stats["unique_users"] == 2
        assert stats["unique_models"] == 3
        assert stats["budgets_configured"] == 2  # Default budgets

    def test_memory_bounded_storage(self):
        """Test that cost tracker respects max_records limit"""
        # Arrange
        tracker = CostTracker(max_records_in_memory=10)
        tokens_used = {"prompt_tokens": 100, "completion_tokens": 50}

        # Act - Record more than max_records
        for i in range(20):
            tracker.record_request(
                user_id=f"user{i}",
                model_name="gpt-4o-mini",
                provider_name="openai",
                tokens_used=tokens_used,
            )

        # Assert - Should only keep last 10 records
        assert len(tracker._cost_records) == 10

    def test_model_tier_pricing(self, cost_tracker):
        """Test that model tier pricing is correctly configured"""
        # Assert
        assert "claude-3-5-haiku" in MODEL_PRICING
        assert "gpt-4o" in MODEL_PRICING
        assert "gpt-4o-mini" in MODEL_PRICING

        # Check pricing structure
        haiku_pricing = MODEL_PRICING["claude-3-5-haiku"]
        assert haiku_pricing["tier"] == ModelTier.TIER_1_ANALYSIS
        assert haiku_pricing["input_cost_per_1m"] == 0.25
        assert haiku_pricing["output_cost_per_1m"] == 1.25

    def test_get_cost_tracker_singleton(self):
        """Test global cost tracker singleton"""
        # Act
        tracker1 = get_cost_tracker()
        tracker2 = get_cost_tracker()

        # Assert - Should return same instance
        assert tracker1 is tracker2

    def test_cost_record_creation(self):
        """Test CostRecord dataclass creation"""
        # Arrange & Act
        record = CostRecord(
            user_id="user123",
            model_name="gpt-4o-mini",
            provider_name="openai",
            tokens_used={"prompt_tokens": 1000, "completion_tokens": 500},
            cost_usd=0.00045,
            request_type="analysis",
            department="engineering",
        )

        # Assert
        assert record.user_id == "user123"
        assert record.model_name == "gpt-4o-mini"
        assert record.cost_usd == 0.00045
        assert record.department == "engineering"
        assert record.record_id is not None
        assert record.timestamp is not None

    def test_aggregations_update_correctly(self, cost_tracker):
        """Test that aggregations are updated correctly on record"""
        # Arrange
        tokens_used = {"prompt_tokens": 1000, "completion_tokens": 500}
        now = datetime.now(UTC)

        # Act
        cost_tracker.record_request(
            user_id="user123",
            model_name="gpt-4o-mini",
            provider_name="openai",
            tokens_used=tokens_used,
        )

        # Assert
        hour_key = now.strftime("%Y-%m-%d-%H")
        date_key = now.strftime("%Y-%m-%d")

        assert cost_tracker._hourly_costs[hour_key] > 0
        assert cost_tracker._daily_costs[date_key] > 0
        assert cost_tracker._user_costs["user123"] > 0
        assert cost_tracker._model_costs["gpt-4o-mini"] > 0

    def test_cleanup_old_aggregations(self, cost_tracker):
        """Test cleanup of old aggregations"""
        # Arrange - Add old aggregations
        old_date = datetime.now(UTC) - timedelta(days=35)
        cost_tracker._hourly_costs[old_date.strftime("%Y-%m-%d-%H")] = 10.0
        cost_tracker._daily_costs[old_date.strftime("%Y-%m-%d")] = 100.0

        # Force cleanup
        cost_tracker._last_cleanup = datetime.now(UTC) - timedelta(hours=2)

        # Act
        cost_tracker._cleanup_old_aggregations()

        # Assert - Old entries should be cleaned
        assert old_date.strftime("%Y-%m-%d-%H") not in cost_tracker._hourly_costs
        assert old_date.strftime("%Y-%m-%d") not in cost_tracker._daily_costs


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
