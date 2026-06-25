"""Tests for enhanced error handling in workflow integration."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from slack_sdk.errors import SlackApiError

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
    integration.redis_manager.get = AsyncMock(return_value=None)
    integration.block_builder = MagicMock()
    integration.block_builder.build_error_message = MagicMock(return_value=[])

    return integration


@pytest.mark.asyncio
async def test_load_user_profile_network_error(workflow_integration):
    """Verify network error returns minimal profile."""
    # Arrange
    user_id = "U123"
    workflow_integration.slack_client.users_info = AsyncMock(
        side_effect=httpx.NetworkError("Network unreachable")
    )

    # Act
    result = await workflow_integration._load_user_profile(user_id)

    # Assert
    assert result == {"id": user_id, "name": "Unknown User"}


@pytest.mark.asyncio
async def test_load_user_profile_timeout_error(workflow_integration):
    """Verify timeout returns minimal profile."""
    # Arrange
    user_id = "U456"
    workflow_integration.slack_client.users_info = AsyncMock(
        side_effect=httpx.TimeoutException("Request timed out")
    )

    # Act
    result = await workflow_integration._load_user_profile(user_id)

    # Assert
    assert result == {"id": user_id, "name": "Unknown User"}


@pytest.mark.asyncio
async def test_load_user_profile_slack_api_error(workflow_integration):
    """Verify Slack API error returns minimal profile."""
    # Arrange
    user_id = "U789"
    workflow_integration.slack_client.users_info = AsyncMock(
        side_effect=SlackApiError(message="user_not_found", response={"error": "user_not_found"})
    )

    # Act
    result = await workflow_integration._load_user_profile(user_id)

    # Assert
    assert result == {"id": user_id, "name": "Unknown User"}


@pytest.mark.asyncio
async def test_handle_message_network_error(workflow_integration, slack_context):
    """Verify handle_message_event handles network errors gracefully."""
    # Arrange
    event = {
        "user": "U123",
        "team": "T123",
        "channel": "C123",
        "text": "test message",
        "type": "message",
        "ts": "123.456",
        "client_msg_id": "msg_123",
    }
    say = AsyncMock()

    workflow_integration.dedup_service.check_slack_event = AsyncMock(
        side_effect=httpx.NetworkError("Network error")
    )
    workflow_integration._send_error_response = AsyncMock()

    # Act
    await workflow_integration.handle_message_event(event, say)

    # Assert
    assert workflow_integration._send_error_response.called
    call_args = workflow_integration._send_error_response.call_args
    assert "connect" in call_args[0][2].lower()  # Error message mentions connectivity


@pytest.mark.asyncio
async def test_handle_message_timeout_error(workflow_integration, slack_context):
    """Verify handle_message_event handles timeout errors gracefully."""
    # Arrange
    event = {
        "user": "U123",
        "team": "T123",
        "channel": "C123",
        "text": "test message",
        "type": "message",
        "ts": "123.456",
        "client_msg_id": "msg_123",
    }
    say = AsyncMock()

    workflow_integration.dedup_service.check_slack_event = AsyncMock(
        side_effect=httpx.TimeoutException("Request timeout")
    )
    workflow_integration._send_error_response = AsyncMock()

    # Act
    await workflow_integration.handle_message_event(event, say)

    # Assert
    assert workflow_integration._send_error_response.called
    call_args = workflow_integration._send_error_response.call_args
    assert "longer than expected" in call_args[0][2].lower() or "timeout" in call_args[0][2].lower()


@pytest.mark.asyncio
async def test_monitor_workflow_network_error(workflow_integration, slack_context):
    """Verify _monitor_workflow handles network errors during status checks."""
    # Arrange
    workflow_id = "wf_123"
    say = AsyncMock()
    message_ts = "123.456"

    workflow_integration.workflow_router.get_workflow_status = AsyncMock(
        side_effect=httpx.NetworkError("Connection failed")
    )
    workflow_integration._send_error_response = AsyncMock()

    # Act
    with patch("asyncio.sleep", new_callable=AsyncMock):
        await workflow_integration._monitor_workflow(
            workflow_id=workflow_id,
            slack_context=slack_context,
            say=say,
            message_ts=message_ts,
            max_iterations=5,
            check_interval=0.1,
        )

    # Assert
    assert workflow_integration._send_error_response.called
    call_args = workflow_integration._send_error_response.call_args
    assert "connect" in call_args[0][2].lower()  # Error message mentions connectivity


@pytest.mark.asyncio
async def test_update_progress_slack_api_error(workflow_integration, slack_context):
    """Verify _update_progress handles Slack API errors gracefully."""
    # Arrange
    message_ts = "123.456"
    status_text = "Processing..."

    workflow_integration.slack_client.chat_update = AsyncMock(
        side_effect=SlackApiError(
            message="message_not_found", response={"error": "message_not_found"}
        )
    )

    # Act - Should not raise, just log warning
    await workflow_integration._update_progress(
        slack_context=slack_context, message_ts=message_ts, status_text=status_text
    )

    # Assert - No exception raised, method completes gracefully
    assert True  # If we get here, error was handled gracefully
