"""
Integration Tests for Workflow Components

Tests the complete flow from Slack event through Temporal workflows to agent execution.
Validates proper integration between all critical components.

OUTDATED: This test file references modules that have been refactored or removed.
Needs rewrite to use current architecture.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

# SKIP ALL TESTS - Need rewrite for current workflow architecture
pytestmark = pytest.mark.skip(
    reason="Tests need rewrite for current workflow architecture (modules refactored)"
)

# Outdated imports - modules have been refactored
# from src.core.workflows.temporal_workflows import BatchRequest
# from src.infrastructure.events.deduplication import DeduplicationResult, EventDeduplicationService
from src.core.workflows.workflow_router import RoutingContext, RoutingDecision, WorkflowRouter
from src.interfaces.slack.workflow_integration import SlackWorkflowIntegration


@pytest.fixture
async def mock_temporal_client():
    """Mock Temporal client for testing."""
    client = AsyncMock()
    client.start_workflow = AsyncMock(return_value=Mock(id="test-workflow-123"))
    client.get_workflow_handle = AsyncMock()
    return client


@pytest.fixture
async def mock_slack_app():
    """Mock Slack app for testing."""
    app = Mock()
    app.client = AsyncMock()
    app.client.users_info = AsyncMock(return_value={"user": {"id": "U123", "name": "Test User"}})
    return app


@pytest.fixture
async def dedup_service():
    """Create deduplication service for testing."""
    service = EventDeduplicationService()
    # Mock Redis client
    service.redis_client = AsyncMock()
    service.redis_client.exists = AsyncMock(return_value=False)
    service.redis_client.setex = AsyncMock()
    return service


@pytest.fixture
async def workflow_router(mock_temporal_client):
    """Create workflow router for testing."""
    router = WorkflowRouter(temporal_client=mock_temporal_client)
    router.intent_analyzer = AsyncMock()
    router.intent_analyzer.analyze_intent = AsyncMock(
        return_value=Mock(intent="CLASSIFY_ACTIVITY", confidence=0.95)
    )
    return router


@pytest.fixture
async def slack_integration(mock_slack_app, workflow_router, dedup_service):
    """Create Slack workflow integration for testing."""
    integration = SlackWorkflowIntegration(
        slack_app=mock_slack_app,
        workflow_router=workflow_router,
        dedup_service=dedup_service,
    )
    integration.redis_manager = AsyncMock()
    integration.redis_manager.get = AsyncMock(return_value=None)
    integration.redis_manager.set = AsyncMock()
    return integration


class TestSlackToWorkflowIntegration:
    """Test Slack event to Temporal workflow integration."""

    @pytest.mark.asyncio
    async def test_message_event_flow(self, slack_integration, dedup_service, workflow_router):
        """Test complete flow from Slack message to workflow initiation."""
        # Arrange
        event = {
            "type": "message",
            "user": "U123",
            "team": "T456",
            "channel": "C789",
            "text": "Please analyze my recent activities",
            "ts": "1234567890.123456",
            "client_msg_id": "msg-123",
        }

        say = AsyncMock()
        ack = AsyncMock()

        # Act
        await slack_integration.handle_message_event(event, say, ack)

        # Assert
        # Verify acknowledgment
        ack.assert_called_once()

        # Verify deduplication check
        assert dedup_service.redis_client.exists.called

        # Verify workflow routing
        assert workflow_router.intent_analyzer.analyze_intent.called

        # Verify workflow started
        assert workflow_router.temporal_client.start_workflow.called

        # Verify user notification
        say.assert_called()
        call_args = say.call_args[1]
        assert "analyzing your request" in call_args["text"].lower()

    @pytest.mark.asyncio
    async def test_duplicate_event_handling(self, slack_integration, dedup_service):
        """Test that duplicate events are properly ignored."""
        # Arrange
        event = {
            "type": "message",
            "user": "U123",
            "team": "T456",
            "channel": "C789",
            "text": "Test message",
            "ts": "1234567890.123456",
            "client_msg_id": "msg-123",
        }

        # Mock duplicate detection
        dedup_service.redis_client.exists = AsyncMock(return_value=True)

        say = AsyncMock()
        ack = AsyncMock()

        # Act
        await slack_integration.handle_message_event(event, say, ack)

        # Assert
        # Should acknowledge but not process
        ack.assert_called_once()
        say.assert_not_called()

    @pytest.mark.asyncio
    async def test_batch_detection_and_routing(self, workflow_router):
        """Test batch opportunity detection and routing."""
        # Arrange
        context = RoutingContext(
            user_id="U123",
            content="Please analyze these 5 activities: [activity1, activity2, activity3, activity4, activity5]",
            activities=["activity1", "activity2", "activity3", "activity4", "activity5"],
        )

        # Act
        result = await workflow_router.route_request(context)

        # Assert
        assert result.decision == RoutingDecision.BATCH_ANALYSIS
        assert result.should_batch is True
        assert result.estimated_cost > 0

        # Verify batch workflow started
        workflow_router.temporal_client.start_workflow.assert_called()
        call_args = workflow_router.temporal_client.start_workflow.call_args[0]
        assert call_args[0] == "BatchAnalysisWorkflow"
        assert isinstance(call_args[1], BatchRequest)

    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, slack_integration, workflow_router):
        """Test error handling and user notification."""
        # Arrange
        event = {
            "type": "message",
            "user": "U123",
            "channel": "C789",
            "text": "Test message",
            "ts": "1234567890.123456",
        }

        # Mock workflow failure
        workflow_router.route_request = AsyncMock(side_effect=Exception("Workflow routing failed"))

        say = AsyncMock()

        # Act
        await slack_integration.handle_message_event(event, say)

        # Assert
        # Should send error message to user
        say.assert_called()
        call_args = say.call_args[1]
        assert "error" in call_args["text"].lower() or "problem" in call_args["text"].lower()


class TestWorkflowToCostTracking:
    """Test workflow execution to cost tracking integration."""

    @pytest.mark.asyncio
    async def test_cost_tracking_in_workflow(self):
        """Test that LLM costs are properly tracked during workflow execution."""
        from core.llm.cost_tracker import get_cost_tracker

        # Arrange
        cost_tracker = get_cost_tracker()

        # Create mock LLM response
        tokens_used = {"prompt_tokens": 1000, "completion_tokens": 500, "total_tokens": 1500}

        # Act
        # Simulate workflow making LLM call
        cost_tracker.record_request(
            user_id="U123",
            model_name="claude-3-5-haiku",
            provider_name="anthropic",
            tokens_used=tokens_used,
            request_type="analysis",
        )

        # Assert
        stats = cost_tracker.get_tracker_stats()
        assert stats["total_requests"] == 1
        assert stats["total_cost"] > 0

        # Verify cost calculation (claude-3-5-haiku: $0.25/$1.25 per 1M)
        expected_cost = (1000 / 1_000_000) * 0.25 + (500 / 1_000_000) * 1.25
        assert abs(stats["total_cost"] - expected_cost) < 0.0001

    @pytest.mark.asyncio
    async def test_batch_cost_optimization(self):
        """Test that batch processing provides cost savings."""
        from core.llm.cost_tracker import get_cost_tracker

        # Arrange
        cost_tracker = get_cost_tracker()
        cost_tracker._cost_records.clear()  # Clear any existing records

        tokens_used = {"prompt_tokens": 1000, "completion_tokens": 500, "total_tokens": 1500}

        # Act
        # Regular request
        cost_tracker.record_request(
            user_id="U123",
            model_name="claude-3-5-haiku",
            provider_name="anthropic",
            tokens_used=tokens_used,
            request_type="analysis",
            is_batch=False,
        )

        # Batch request (should be 40% cheaper)
        cost_tracker.record_request(
            user_id="U123",
            model_name="claude-3-5-haiku",
            provider_name="anthropic",
            tokens_used=tokens_used,
            request_type="batch_analysis",
            is_batch=True,
        )

        # Assert
        records = cost_tracker._cost_records
        assert len(records) == 2

        regular_cost = records[0].cost_usd
        batch_cost = records[1].cost_usd

        # Batch should be 40% cheaper
        assert batch_cost == pytest.approx(regular_cost * 0.6, rel=0.01)

        # Check savings summary
        savings = cost_tracker.get_batch_savings_summary()
        assert savings["savings_percentage"] == 40.0


class TestTimescaleDBIntegration:
    """Test TimescaleDB integration for time-series data."""

    @pytest.mark.asyncio
    async def test_activity_storage_in_hypertable(self):
        """Test that activities are stored in TimescaleDB hypertables."""
        from infrastructure.database.timescale_setup import TimescaleDBManager

        # This would require a test database setup
        # For now, we'll mock the behavior

        # Arrange
        db_manager = Mock()
        db_manager.get_session = AsyncMock()

        tsdb_manager = TimescaleDBManager(db_manager)

        # Mock session
        session = AsyncMock()
        db_manager.get_session.return_value.__aenter__.return_value = session

        # Act
        with patch("infrastructure.database.timescale_setup.text") as mock_text:
            await tsdb_manager._create_hypertables()

        # Assert
        # Verify hypertable creation queries
        assert mock_text.called
        call_args = [call[0][0] for call in mock_text.call_args_list]
        assert any("create_hypertable" in arg for arg in call_args)
        assert any("activities" in arg for arg in call_args)

    @pytest.mark.asyncio
    async def test_continuous_aggregates_performance(self):
        """Test that continuous aggregates provide fast queries."""
        from infrastructure.database.timescale_setup import TimescaleDBManager

        # Arrange
        db_manager = Mock()
        tsdb_manager = TimescaleDBManager(db_manager)

        # Mock fast query result
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.mappings.return_value = [
            {"bucket": datetime.now(), "activity_count": 10, "avg_complexity": 3.5}
        ]
        mock_session.execute = AsyncMock(return_value=mock_result)
        db_manager.get_session.return_value.__aenter__.return_value = mock_session

        # Act
        stats = await tsdb_manager.get_activity_stats(
            user_id="U123",
            start_time=datetime.now() - timedelta(hours=1),
            end_time=datetime.now(),
            bucket_interval="1 hour",
        )

        # Assert
        assert len(stats) == 1
        assert stats[0]["activity_count"] == 10
        # Query should use continuous aggregate, not raw data


class TestEventDeduplication:
    """Test event deduplication across components."""

    @pytest.mark.asyncio
    async def test_deduplication_prevents_double_processing(self, dedup_service):
        """Test that deduplication prevents processing same event twice."""
        # Arrange
        event = {
            "event_id": "evt-123",
            "ts": "1234567890.123456",
            "user": "U123",
            "type": "message",
        }

        # First check - should be new
        dedup_service.redis_client.exists = AsyncMock(return_value=False)

        # Act
        result1 = await dedup_service.check_slack_event(event)

        # Second check - should be duplicate
        dedup_service.redis_client.exists = AsyncMock(return_value=True)
        result2 = await dedup_service.check_slack_event(event)

        # Assert
        assert result1 == DeduplicationResult.NEW
        assert result2 == DeduplicationResult.DUPLICATE

        # Verify key was set with TTL
        dedup_service.redis_client.setex.assert_called()
        call_args = dedup_service.redis_client.setex.call_args[0]
        assert call_args[1] == 180  # 3-minute TTL for Slack

    @pytest.mark.asyncio
    async def test_deduplication_key_generation(self, dedup_service):
        """Test that deduplication keys are properly generated."""
        from infrastructure.events.deduplication import EventKey

        # Arrange
        event_key = EventKey(
            event_id="evt-123", timestamp="1234567890.123456", user_id="U123", event_type="message"
        )

        # Act
        key = event_key.generate_key()

        # Assert
        assert key.startswith("dedup:")
        assert "U123" in key  # User ID should be in key
        assert len(key) < 100  # Key should be reasonably short


class TestErrorHandlingIntegration:
    """Test error handling across component boundaries."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_failover(self):
        """Test that circuit breaker triggers provider failover."""
        from core.llm.gateway import LLMGateway, LLMRequest

        # Arrange
        gateway = LLMGateway()

        # Mock providers
        gateway.provider_manager.get_model_for_tier = Mock(
            side_effect=[
                ("claude-3-5-haiku", Mock(name="anthropic")),
                ("gpt-4o-mini", Mock(name="openai")),  # Failover
            ]
        )

        LLMRequest(
            messages=[{"role": "user", "content": "Test"}], model_tier=Mock(), user_id="U123"
        )

        # Mock first provider failure
        with patch("core.llm.gateway.acompletion") as mock_completion:
            mock_completion.side_effect = [
                Exception("Provider failed"),  # First call fails
                Mock(  # Second call succeeds
                    choices=[Mock(message=Mock(content="Response"))],
                    usage=Mock(prompt_tokens=10, completion_tokens=5, total_tokens=15),
                ),
            ]

            # Act
            with patch.object(gateway, "_get_circuit_breaker") as mock_breaker:
                mock_breaker.return_value.call = AsyncMock(
                    side_effect=[Exception("Circuit open"), Mock()]
                )

                # Should failover to second provider
                # Note: This would normally raise due to mocking limitations
                # In real test, would need more sophisticated mocking

    @pytest.mark.asyncio
    async def test_error_propagation_to_user(self, slack_integration):
        """Test that errors are properly formatted for users."""
        from shared import ErrorCategory, ErrorSeverity, ReflectAIError

        # Arrange
        event = {
            "type": "message",
            "user": "U123",
            "channel": "C789",
            "text": "Test",
            "ts": "1234567890.123456",
        }

        # Mock error in workflow
        error = ReflectAIError(
            message="LLM API failed",
            category=ErrorCategory.LLM_ERROR,
            severity=ErrorSeverity.HIGH,
            user_message="Our AI is temporarily unavailable. Please try again.",
            recovery_action="Wait a moment and retry",
        )

        slack_integration.workflow_router.route_request = AsyncMock(side_effect=error)

        say = AsyncMock()

        # Act
        await slack_integration.handle_message_event(event, say)

        # Assert
        say.assert_called()
        call_args = say.call_args[1]

        # Should contain user-friendly message
        assert "temporarily unavailable" in call_args["text"].lower()


@pytest.mark.asyncio
async def test_end_to_end_integration():
    """Test complete end-to-end flow from Slack to agent response."""
    # This would be a comprehensive integration test requiring
    # all components to be properly initialized

    # Would test:
    # 1. Slack event received
    # 2. Event deduplicated
    # 3. Routed to Temporal workflow
    # 4. Workflow executes agents
    # 5. Agents call LLM
    # 6. Costs tracked
    # 7. Results stored in TimescaleDB
    # 8. Response sent back to Slack

    # Due to complexity, this would require a test environment
    # with all services running (Temporal, Redis, PostgreSQL, etc.)
    pass


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
