#!/usr/bin/env python3
"""
Slack API Mock Infrastructure for ReflectAI Testing

Provides comprehensive Slack API mocking including:
- Event generation and simulation
- Response simulation for different event types
- Webhook and OAuth simulation
- Home tab interactions
- Message thread handling
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from unittest.mock import AsyncMock, Mock


class SlackEventType(str, Enum):
    """Types of Slack events for testing."""

    MESSAGE = "message"
    APP_MENTION = "app_mention"
    REACTION_ADDED = "reaction_added"
    REACTION_REMOVED = "reaction_removed"
    CHANNEL_JOINED = "channel_joined"
    USER_JOINED = "member_joined_channel"
    HOME_OPENED = "app_home_opened"
    SLASH_COMMAND = "slash_command"


@dataclass
class MockSlackEvent:
    """Mock Slack event configuration."""

    type: SlackEventType
    user: str = "U1234567890"
    channel: str = "C1234567890"
    text: str = "Test message"
    ts: str = "1609459200.000100"
    thread_ts: str | None = None
    team: str = "T1234567890"
    bot_id: str | None = None
    bot_profile: dict | None = None


@dataclass
class MockSlackUser:
    """Mock Slack user configuration."""

    id: str = "U1234567890"
    name: str = "testuser"
    real_name: str = "Test User"
    email: str = "test@example.com"
    is_bot: bool = False
    profile: dict = field(
        default_factory=lambda: {
            "display_name": "Test User",
            "status_text": "Available",
            "image_512": "https://example.com/avatar.jpg",
        }
    )


@dataclass
class MockSlackChannel:
    """Mock Slack channel configuration."""

    id: str = "C1234567890"
    name: str = "general"
    is_private: bool = False
    members: list[str] = field(default_factory=lambda: ["U1234567890", "U0987654321"])


class SlackEventFactory:
    """Factory for generating Slack events."""

    def __init__(self):
        self.users = self._initialize_users()
        self.channels = self._initialize_channels()

    def _initialize_users(self) -> dict[str, MockSlackUser]:
        """Initialize mock users."""
        return {
            "U1234567890": MockSlackUser(id="U1234567890", name="testuser"),
            "U0987654321": MockSlackUser(id="U0987654321", name="manager"),
            "U1111111111": MockSlackUser(id="U1111111111", name="botuser", is_bot=True),
        }

    def _initialize_channels(self) -> dict[str, MockSlackChannel]:
        """Initialize mock channels."""
        return {
            "C1234567890": MockSlackChannel(id="C1234567890", name="general"),
            "C0987654321": MockSlackChannel(id="C0987654321", name="random"),
            "C1111111111": MockSlackChannel(id="C1111111111", name="private", is_private=True),
        }

    def create_message_event(
        self, text: str = "Test message", user: str = "U1234567890", channel: str = "C1234567890"
    ) -> MockSlackEvent:
        """Create a mock message event."""
        return MockSlackEvent(
            type=SlackEventType.MESSAGE,
            user=user,
            channel=channel,
            text=text,
            ts="1609459200.000100",
        )

    def create_app_mention_event(
        self, text: str = "Test <@BOT123> message", user: str = "U1234567890"
    ) -> MockSlackEvent:
        """Create a mock app mention event."""
        return MockSlackEvent(
            type=SlackEventType.APP_MENTION,
            user=user,
            channel="C1234567890",
            text=text,
            ts="1609459200.000200",
        )

    def create_reaction_event(
        self, reaction: str = "thumbsup", user: str = "U1234567890"
    ) -> MockSlackEvent:
        """Create a mock reaction event."""
        return MockSlackEvent(
            type=SlackEventType.REACTION_ADDED,
            user=user,
            channel="C1234567890",
            text=f"reacted with {reaction}",
            ts="1609459200.000300",
        )

    def create_home_opened_event(self, user: str = "U1234567890") -> MockSlackEvent:
        """Create a mock home opened event."""
        return MockSlackEvent(
            type=SlackEventType.HOME_OPENED,
            user=user,
            channel=None,
            text="",
            ts="1609459200.000400",
        )

    def create_slash_command(
        self, command: str = "/reflectai help", user: str = "U1234567890"
    ) -> MockSlackEvent:
        """Create a mock slash command event."""
        return MockSlackEvent(
            type=SlackEventType.SLASH_COMMAND,
            user=user,
            channel="C1234567890",
            text=command,
            ts="1609459200.000500",
        )


class SlackResponseFactory:
    """Factory for generating Slack API responses."""

    def __init__(self):
        self.event_factory = SlackEventFactory()

    def create_message_response(
        self,
        text: str = "Response message",
        channel: str = "C1234567890",
        ts: str = "1609459200.000600",
    ) -> dict[str, Any]:
        """Create a mock message response."""
        return {
            "ok": True,
            "channel": channel,
            "ts": ts,
            "message": {"text": text, "user": "U1111111111", "ts": ts, "channel": channel},
        }

    def create_home_tab_response(self, user: str = "U1234567890") -> dict[str, Any]:
        """Create a mock home tab response."""
        return {
            "ok": True,
            "view": {
                "type": "home",
                "blocks": [
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": "*Welcome to ReflectAI!*"},
                    }
                ],
            },
        }

    def create_error_response(self, error: str = "invalid_auth") -> dict[str, Any]:
        """Create a mock error response."""
        return {"ok": False, "error": error}


class SlackAPIMock:
    """Comprehensive Slack API mock."""

    def __init__(self):
        self.event_factory = SlackEventFactory()
        self.response_factory = SlackResponseFactory()
        self.message_history: list[dict] = []
        self.event_handlers: dict[str, Callable] = {}

    def create_client_mock(self) -> AsyncMock:
        """Create a mock Slack client."""
        mock_client = AsyncMock()

        # Mock message sending
        async def mock_chat_postMessage(**kwargs):
            message = {
                "channel": kwargs.get("channel", "C1234567890"),
                "text": kwargs.get("text", "Mock response"),
                "ts": "1609459200.000600",
                "user": "U1111111111",
            }
            self.message_history.append(message)
            return self.response_factory.create_message_response(
                text=kwargs.get("text", "Mock response"),
                channel=kwargs.get("channel", "C1234567890"),
            )

        # Mock home tab publishing
        async def mock_views_publish(**kwargs):
            return self.response_factory.create_home_tab_response(
                user=kwargs.get("user", "U1234567890")
            )

        # Mock user info
        async def mock_users_info(user: str):
            user_data = self.event_factory.users.get(user, self.event_factory.users["U1234567890"])
            return {
                "ok": True,
                "user": {"id": user_data.id, "name": user_data.name, "profile": user_data.profile},
            }

        # Mock channel info
        async def mock_conversations_info(channel: str):
            channel_data = self.event_factory.channels.get(
                channel, self.event_factory.channels["C1234567890"]
            )
            return {
                "ok": True,
                "channel": {
                    "id": channel_data.id,
                    "name": channel_data.name,
                    "is_private": channel_data.is_private,
                },
            }

        # Set up mock methods
        mock_client.chat.postMessage = mock_chat_postMessage
        mock_client.views.publish = mock_views_publish
        mock_client.users.info = mock_users_info
        mock_client.conversations.info = mock_conversations_info

        return mock_client

    def create_webhook_mock(self, event_type: SlackEventType = SlackEventType.MESSAGE) -> Mock:
        """Create a mock webhook server for testing."""
        mock_webhook = Mock()

        def simulate_event(event_data: dict | None = None):
            """Simulate receiving a Slack event."""
            if event_data is None:
                event = self.event_factory.create_message_event()
                event_data = {
                    "type": event.type,
                    "user": event.user,
                    "channel": event.channel,
                    "text": event.text,
                    "ts": event.ts,
                }

            # Call registered event handlers
            for handler in self.event_handlers.values():
                handler(event_data)

        mock_webhook.simulate_event = simulate_event
        return mock_webhook

    def register_event_handler(self, event_type: str, handler: Callable):
        """Register an event handler for testing."""
        self.event_handlers[event_type] = handler

    def get_message_history(self) -> list[dict]:
        """Get the history of sent messages."""
        return self.message_history.copy()

    def clear_message_history(self):
        """Clear the message history."""
        self.message_history.clear()


# Global instances for easy access
slack_event_factory = SlackEventFactory()
slack_response_factory = SlackResponseFactory()
slack_api_mock = SlackAPIMock()


def get_slack_client_mock() -> AsyncMock:
    """Get a pre-configured Slack client mock."""
    return slack_api_mock.create_client_mock()


def get_slack_webhook_mock(event_type: SlackEventType = SlackEventType.MESSAGE) -> Mock:
    """Get a pre-configured Slack webhook mock."""
    return slack_api_mock.create_webhook_mock(event_type)


def create_test_event(event_type: SlackEventType, **kwargs) -> MockSlackEvent:
    """Create a test event with custom parameters."""
    factory = SlackEventFactory()
    if event_type == SlackEventType.MESSAGE:
        return factory.create_message_event(**kwargs)
    elif event_type == SlackEventType.APP_MENTION:
        return factory.create_app_mention_event(**kwargs)
    elif event_type == SlackEventType.REACTION_ADDED:
        return factory.create_reaction_event(**kwargs)
    elif event_type == SlackEventType.HOME_OPENED:
        return factory.create_home_opened_event(**kwargs)
    elif event_type == SlackEventType.SLASH_COMMAND:
        return factory.create_slash_command(**kwargs)
    else:
        return factory.create_message_event()
