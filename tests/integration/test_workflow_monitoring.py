"""Tests for workflow monitoring timeout handling."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.interfaces.slack.workflow_integration import SlackContext, SlackWorkflowIntegration


@pytest.fixture
def slack_context():
    """Create test Slack context."""
    return SlackContext(
        user_id="U123",
        team_id="T123",
        channel_id="C123",
        thread_ts="123.456",
        message_ts="123.456",
        text="test message",
        event_type="message",
        event_id="evt_123",
        is_direct_message=False,
        is_bot_mention=False,
    )


@pytest.fixture
def workflow_integration():
    """Create test workflow integration."""
    mock_app = MagicMock()
    mock_app.client = AsyncMock()

    integration = SlackWorkflowIntegration(
        slack_app=mock_app, workflow_router=AsyncMock(), dedup_service=AsyncMock()
    )
    integration.redis_manager = AsyncMock()
    integration.block_builder = MagicMock()
    integration.block_builder.build_error_message = MagicMock(return_value=[])

    return integration


@pytest.mark.asyncio
async def test_workflow_monitoring_timeout(workflow_integration, slack_context):
    """Verify workflow monitoring respects timeout."""
    # Arrange
    workflow_id = "wf_123"
    say = AsyncMock()
    message_ts = "123.456"

    # Mock workflow that stays RUNNING
    workflow_integration.workflow_router.get_workflow_status = AsyncMock(
        return_value={"status": "RUNNING"}
    )

    # Act - Use small iterations for faster test
    with patch("asyncio.sleep", new_callable=AsyncMock):
        await workflow_integration._monitor_workflow(
            workflow_id=workflow_id,
            slack_context=slack_context,
            say=say,
            message_ts=message_ts,
            max_iterations=3,  # Small number for testing
            check_interval=0.1,  # Small interval for testing
        )

    # Assert - Should call _send_error_response with timeout message
    assert say.call_count >= 1
    # Check that timeout message was sent
    call_args = say.call_args_list[-1]
    assert "timed out" in call_args[1]["text"].lower()


@pytest.mark.asyncio
async def test_workflow_monitoring_completes_successfully(workflow_integration, slack_context):
    """Verify workflow monitoring handles successful completion."""
    # Arrange
    workflow_id = "wf_123"
    say = AsyncMock()
    message_ts = "123.456"

    call_count = 0

    async def mock_status(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            return {"status": "RUNNING"}
        return {"status": "COMPLETED"}

    workflow_integration.workflow_router.get_workflow_status = mock_status
    workflow_integration._get_workflow_result = AsyncMock(return_value={"result": "success"})
    workflow_integration._send_workflow_result = AsyncMock()
    workflow_integration._update_progress = AsyncMock()

    # Act
    with patch("asyncio.sleep", new_callable=AsyncMock):
        await workflow_integration._monitor_workflow(
            workflow_id=workflow_id,
            slack_context=slack_context,
            say=say,
            message_ts=message_ts,
            max_iterations=10,
            check_interval=0.1,
        )

    # Assert
    assert workflow_integration._send_workflow_result.called
    assert call_count == 3  # Checked 3 times before completing


@pytest.mark.asyncio
async def test_workflow_monitoring_handles_failure(workflow_integration, slack_context):
    """Verify workflow monitoring handles workflow failure."""
    # Arrange
    workflow_id = "wf_123"
    say = AsyncMock()
    message_ts = "123.456"

    # Mock workflow that fails after one iteration
    call_count = 0

    async def mock_status(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return {"status": "RUNNING"}
        return {"status": "FAILED"}

    workflow_integration.workflow_router.get_workflow_status = mock_status
    workflow_integration._send_workflow_failure = AsyncMock()
    workflow_integration._update_progress = AsyncMock()

    # Act
    with patch("asyncio.sleep", new_callable=AsyncMock):
        await workflow_integration._monitor_workflow(
            workflow_id=workflow_id,
            slack_context=slack_context,
            say=say,
            message_ts=message_ts,
            max_iterations=10,
            check_interval=0.1,
        )

    # Assert
    assert workflow_integration._send_workflow_failure.called
    assert call_count == 2  # Checked twice (RUNNING -> FAILED)
