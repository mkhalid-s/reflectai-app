"""
Slack Socket Mode Handler

Implements dual-mode Slack connectivity (Socket Mode for development,
HTTP Mode for production) as specified in Requirements 12 and 16.
"""

import asyncio
from datetime import UTC, datetime
from typing import Any

import redis.asyncio as redis
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_bolt.async_app import AsyncApp
from slack_sdk.web.async_client import AsyncWebClient

from src.infrastructure.events.event_deduplicator import get_event_deduplicator
from src.shared import ReflectAIError, get_logger

from .conversation_manager import ConversationManager

logger = get_logger(__name__)


class SlackSocketModeHandler:
    """
    Unified Slack handler supporting both Socket Mode (development)
    and HTTP Mode (production) with identical event processing logic.
    """

    def __init__(self, redis_client: redis.Redis, conversation_manager: ConversationManager):
        self.redis = redis_client
        self.conversation_manager = conversation_manager
        self.event_deduplicator = None  # Will be initialized in async start()

        # Get configuration from streamlined config system
        from src.infrastructure.config import get_config_manager

        config = get_config_manager().get_config()

        self.mode = config.app.environment if hasattr(config.app, "slack_mode") else "socket"
        self.logger = get_logger(__name__)

        # Initialize Slack app based on mode
        self.app = self._initialize_slack_app()
        self.socket_mode_handler: AsyncSocketModeHandler | None = None

        # Register event handlers
        self._register_event_handlers()

    def _initialize_slack_app(self) -> AsyncApp:
        """Initialize Slack app with appropriate configuration for the mode"""
        from src.infrastructure.config import get_secrets_manager

        secrets = get_secrets_manager()
        slack_secrets = secrets.get_slack_secrets()

        # Explicitly disable OAuth by setting oauth_settings=None
        # This prevents Bolt from auto-detecting OAuth via SLACK_CLIENT_ID/SLACK_CLIENT_SECRET env vars
        if self.mode == "socket":
            # Socket Mode configuration
            return AsyncApp(
                token=slack_secrets["bot_token"],
                signing_secret=slack_secrets["signing_secret"],
                oauth_settings=None,  # Explicitly disable OAuth
            )
        else:
            # HTTP Mode configuration
            return AsyncApp(
                token=slack_secrets["bot_token"],
                signing_secret=slack_secrets["signing_secret"],
                process_before_response=True,
                oauth_settings=None,  # Explicitly disable OAuth
            )

    def _register_event_handlers(self):
        """Register unified event handlers that work in both modes"""

        # App mention handler
        @self.app.event("app_mention")
        async def handle_app_mention(event: dict[str, Any], say, ack):
            await ack()
            await self._process_mention_event(event, say)

        # Direct message handler
        @self.app.event("message")
        async def handle_direct_message(event: dict[str, Any], say, ack):
            await ack()
            # Only handle direct messages, not channel messages
            if event.get("channel_type") == "im":
                await self._process_direct_message(event, say)

        # Interactive component handler
        @self.app.action("button_click")
        async def handle_button_click(ack, body, respond):
            await ack()
            await self._process_interactive_component(body, respond)

        # Slash command handler
        @self.app.command("/reflectai")
        async def handle_slash_command(ack, body, respond):
            await ack()
            await self._process_slash_command(body, respond)

        # Home tab handler
        @self.app.event("app_home_opened")
        async def handle_app_home_opened(event: dict[str, Any], client: AsyncWebClient):
            await self._process_home_tab_open(event, client)

        self.logger.info(f"Slack event handlers registered for {self.mode} mode")

    async def start(self):
        """Start the appropriate handler based on mode"""

        try:
            # Initialize event deduplicator
            if not self.event_deduplicator:
                self.event_deduplicator = await get_event_deduplicator()

            if self.mode == "socket":
                await self._start_socket_mode()
            else:
                await self._start_http_mode()

        except Exception as e:
            self.logger.error(f"Failed to start Slack handler in {self.mode} mode: {str(e)}")
            raise ReflectAIError(f"Slack handler startup failed: {str(e)}") from e

    async def _start_socket_mode(self):
        """Start Socket Mode handler for development"""

        from src.infrastructure.config import get_secrets_manager

        secrets = get_secrets_manager()
        slack_secrets = secrets.get_slack_secrets()
        app_token = slack_secrets.get("app_token")

        if not app_token:
            raise ReflectAIError("SLACK_APP_TOKEN required for Socket Mode")

        self.socket_mode_handler = AsyncSocketModeHandler(self.app, app_token)

        self.logger.info("Starting Slack Socket Mode handler...")
        await self.socket_mode_handler.start_async()

        # Keep the handler running
        while True:
            await asyncio.sleep(1)

    async def _start_http_mode(self):
        """Start HTTP Mode handler for production"""

        # In HTTP mode, the app is typically started by a web server
        # This method prepares the app but doesn't start a server
        self.logger.info("Slack app ready for HTTP Mode (production)")

        # The actual HTTP server would be started by FastAPI/uvicorn
        # with the app handler integrated

    async def _process_mention_event(self, event: dict[str, Any], say):
        """Process app mention events with deduplication"""

        if await self.event_deduplicator.is_duplicate(
            event_data=event,
            event_type="app_mention",
            user_id=event.get("user")
        ):
            self.logger.debug(f"Duplicate mention event ignored: {event.get('ts')}")
            return

        try:
            user_id = event.get("user")
            channel_id = event.get("channel")
            text = (
                event.get("text", "")
                .replace(f"<@{self.app.client.auth_test()['user_id']}>", "")
                .strip()
            )
            thread_ts = event.get("thread_ts")

            # Determine if we should use threading based on channel type
            channel_info = await self.app.client.conversations_info(channel=channel_id)
            is_dm = channel_info["channel"]["is_im"]

            # Apply hybrid threading strategy (Requirement 22)
            response_thread_ts = None if is_dm else self._determine_thread_strategy(text, thread_ts)

            # Process through conversation manager
            response = await self.conversation_manager.process_message(
                user_id=user_id,
                message=text,
                channel_id=channel_id,
                thread_ts=response_thread_ts,
                context={"event_type": "app_mention", "original_event": event, "is_dm": is_dm},
            )

            await say(
                text=response.get("text", "I'm processing your request..."),
                blocks=response.get("blocks"),
                thread_ts=response_thread_ts,
            )

        except Exception as e:
            self.logger.error(f"Error processing mention event: {str(e)}")
            await say(
                text="I encountered an error processing your request. Please try again.",
                thread_ts=event.get("thread_ts") if not is_dm else None,
            )

    async def _process_direct_message(self, event: dict[str, Any], say):
        """Process direct message events"""

        if await self.event_deduplicator.is_duplicate(
            event_data=event,
            event_type="direct_message",
            user_id=event.get("user")
        ):
            return

        try:
            user_id = event.get("user")
            channel_id = event.get("channel")
            text = event.get("text", "")

            # Process through conversation manager (no threading in DMs)
            response = await self.conversation_manager.process_message(
                user_id=user_id,
                message=text,
                channel_id=channel_id,
                thread_ts=None,  # Never thread in DMs
                context={"event_type": "direct_message", "original_event": event, "is_dm": True},
            )

            await say(text=response.get("text"), blocks=response.get("blocks"))

        except Exception as e:
            self.logger.error(f"Error processing direct message: {str(e)}")
            await say("I encountered an error. Please try again.")

    async def _process_interactive_component(self, body: dict[str, Any], respond):
        """Process interactive component events (buttons, menus, etc.)"""

        if await self.event_deduplicator.is_duplicate(
            event_data=body,
            event_type="interactive_component",
            user_id=body.get("user", {}).get("id")
        ):
            return

        try:
            action = body.get("actions", [{}])[0]
            action_id = action.get("action_id")
            user_id = body.get("user", {}).get("id")

            # Process through conversation manager
            response = await self.conversation_manager.process_interaction(
                user_id=user_id,
                action_id=action_id,
                action_value=action.get("value"),
                context={"event_type": "interactive_component", "original_body": body},
            )

            await respond(response)

        except Exception as e:
            self.logger.error(f"Error processing interactive component: {str(e)}")
            await respond(
                {
                    "text": "I encountered an error processing your interaction.",
                    "response_type": "ephemeral",
                }
            )

    async def _process_slash_command(self, body: dict[str, Any], respond):
        """Process slash command events"""

        if await self.event_deduplicator.is_duplicate(
            event_data=body,
            event_type="slash_command",
            user_id=body.get("user_id")
        ):
            return

        try:
            command = body.get("command")
            text = body.get("text", "")
            user_id = body.get("user_id")

            # Process through conversation manager
            response = await self.conversation_manager.process_slash_command(
                user_id=user_id,
                command=command,
                text=text,
                context={"event_type": "slash_command", "original_body": body},
            )

            await respond(response)

        except Exception as e:
            self.logger.error(f"Error processing slash command: {str(e)}")
            await respond(
                {
                    "text": "I encountered an error processing your command.",
                    "response_type": "ephemeral",
                }
            )

    async def _process_home_tab_open(self, event: dict[str, Any], client: AsyncWebClient):
        """Process home tab open events"""

        try:
            user_id = event.get("user")

            # Get home tab view from conversation manager
            home_view = await self.conversation_manager.get_home_tab_view(user_id)

            await client.views_publish(user_id=user_id, view=home_view)

        except Exception as e:
            self.logger.error(f"Error updating home tab: {str(e)}")
            # Fallback to basic home tab
            await self._publish_fallback_home_tab(client, event.get("user"))

    def _determine_thread_strategy(self, text: str, existing_thread_ts: str | None) -> str | None:
        """
        Implement hybrid threading strategy (Requirement 22):
        - Simple greetings: No threading
        - Analysis workflows: Create new thread or continue existing
        - Follow-up questions: Continue existing thread if related
        """

        # Simple greetings don't need threading
        simple_greetings = ["hi", "hello", "hey", "thanks", "thank you", "ok", "okay"]
        if (
            any(greeting in text.lower() for greeting in simple_greetings)
            and len(text.split()) <= 3
        ):
            return None

        # If there's an existing thread and this seems like a follow-up, continue it
        if existing_thread_ts:
            follow_up_indicators = [
                "also",
                "and",
                "additionally",
                "furthermore",
                "what about",
                "how about",
            ]
            if any(indicator in text.lower() for indicator in follow_up_indicators):
                return existing_thread_ts

        # Analysis workflows should create new threads
        analysis_keywords = [
            "analyze",
            "report",
            "show me",
            "generate",
            "create",
            "competency",
            "skill",
        ]
        if any(keyword in text.lower() for keyword in analysis_keywords):
            # Create new thread (will be the current message timestamp)
            return None  # Slack will create thread automatically

        # Default: no threading for simple interactions
        return None

    async def _publish_fallback_home_tab(self, client: AsyncWebClient, user_id: str):
        """Publish basic fallback home tab when main logic fails"""

        try:
            await client.views_publish(
                user_id=user_id,
                view={
                    "type": "home",
                    "blocks": [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": "👋 Welcome to ReflectAI!\n\nI'm here to help you with competency development and insights.",
                            },
                        },
                        {
                            "type": "actions",
                            "elements": [
                                {
                                    "type": "button",
                                    "text": {"type": "plain_text", "text": "Get Started"},
                                    "action_id": "get_started",
                                }
                            ],
                        },
                    ],
                },
            )
        except Exception as e:
            self.logger.error(f"Failed to publish fallback home tab: {str(e)}")

    async def get_app_for_http_mode(self) -> AsyncApp:
        """Get the configured Slack app for HTTP mode integration"""
        return self.app

    async def stop(self):
        """Stop the handler gracefully"""

        try:
            if self.socket_mode_handler:
                await self.socket_mode_handler.close_async()
                self.logger.info("Socket Mode handler stopped")

            self.logger.info(f"Slack {self.mode} mode handler stopped")

        except Exception as e:
            self.logger.error(f"Error stopping Slack handler: {str(e)}")

    async def health_check(self) -> dict[str, Any]:
        """Health check endpoint for monitoring"""

        try:
            if self.mode == "socket":
                # For socket mode, check if handler is connected
                is_connected = (
                    self.socket_mode_handler is not None
                    and hasattr(self.socket_mode_handler, "client")
                    and self.socket_mode_handler.client is not None
                )
            else:
                # For HTTP mode, test the Slack client
                auth_test = await self.app.client.auth_test()
                is_connected = auth_test.get("ok", False)

            return {
                "status": "healthy" if is_connected else "unhealthy",
                "mode": self.mode,
                "connected": is_connected,
                "timestamp": datetime.now(UTC).isoformat(),
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "mode": self.mode,
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
            }
