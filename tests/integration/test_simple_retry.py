"""Tests for simple rate limit retry logic."""

from unittest.mock import patch

import pytest
from slack_sdk.errors import SlackApiError

from src.interfaces.slack.adapter import SlackAdapter, SlackMode


@pytest.mark.asyncio
async def test_simple_retry_on_rate_limit():
    """Verify 429 rate limit triggers one retry."""
    # Arrange
    adapter = SlackAdapter(mode=SlackMode.SOCKET)
    await adapter.initialize()

    call_count = 0

    async def mock_method(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise SlackApiError(
                message="rate_limited", response={"error": "rate_limited", "retry_after": 1}
            )
        return {"ok": True}

    adapter.client.chat_postMessage = mock_method

    with patch("asyncio.sleep") as mock_sleep:
        # Act
        result = await adapter._api_call_with_retry("chat_postMessage", channel="C123", text="Test")

    # Assert
    assert call_count == 2  # Failed once, succeeded on retry
    assert result["ok"] is True
    assert mock_sleep.call_count == 1
    assert mock_sleep.call_args[0][0] == 1.0  # Retry after 1 second


@pytest.mark.asyncio
async def test_simple_retry_exhausted():
    """Verify retry limit is respected."""
    # Arrange
    adapter = SlackAdapter(mode=SlackMode.SOCKET)
    await adapter.initialize()

    async def mock_method(**kwargs):
        raise SlackApiError(message="rate_limited", response={"error": "rate_limited"})

    adapter.client.chat_postMessage = mock_method

    with patch("asyncio.sleep"):
        # Act & Assert
        with pytest.raises(SlackApiError):
            await adapter._api_call_with_retry(
                "chat_postMessage", channel="C123", text="Test", max_retries=1
            )


@pytest.mark.asyncio
async def test_non_rate_limit_error_no_retry():
    """Verify non-rate-limit errors fail immediately."""
    # Arrange
    adapter = SlackAdapter(mode=SlackMode.SOCKET)
    await adapter.initialize()

    async def mock_method(**kwargs):
        raise SlackApiError(message="invalid_auth", response={"error": "invalid_auth"})

    adapter.client.chat_postMessage = mock_method

    with patch("asyncio.sleep") as mock_sleep:
        # Act & Assert
        with pytest.raises(SlackApiError):
            await adapter._api_call_with_retry("chat_postMessage", channel="C123", text="Test")

    # Should not retry
    assert mock_sleep.call_count == 0


@pytest.mark.asyncio
async def test_safe_post_message_uses_retry():
    """Verify safe_post_message uses retry logic."""
    # Arrange
    adapter = SlackAdapter(mode=SlackMode.SOCKET)
    await adapter.initialize()

    call_count = 0

    async def mock_method(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise SlackApiError(
                message="rate_limited", response={"error": "rate_limited", "retry_after": 0.1}
            )
        return {"ok": True, "ts": "123.456"}

    adapter.client.chat_postMessage = mock_method

    with patch("asyncio.sleep"):
        # Act
        result = await adapter.safe_post_message(channel="C123", text="Test message")

    # Assert
    assert result["ok"] is True
    assert call_count == 2  # Retried once


@pytest.mark.asyncio
async def test_safe_update_message_uses_retry():
    """Verify safe_update_message uses retry logic."""
    # Arrange
    adapter = SlackAdapter(mode=SlackMode.SOCKET)
    await adapter.initialize()

    call_count = 0

    async def mock_method(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise SlackApiError(
                message="rate_limited", response={"error": "rate_limited", "retry_after": 0.1}
            )
        return {"ok": True, "ts": "123.456"}

    adapter.client.chat_update = mock_method

    with patch("asyncio.sleep"):
        # Act
        result = await adapter.safe_update_message(
            channel="C123", ts="123.456", text="Updated message"
        )

    # Assert
    assert result["ok"] is True
    assert call_count == 2  # Retried once
