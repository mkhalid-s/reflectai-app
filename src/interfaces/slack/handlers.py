"""
Slack Event and Command Handlers for ReflectAI

Implements unified event processing logic that works identically
in both Socket Mode and HTTP Mode (Requirement 16).
"""

from collections.abc import Callable
from typing import Any

from src.infrastructure.events.event_deduplicator import DeduplicationConfig, get_event_deduplicator
from src.infrastructure.monitoring import get_or_create_correlation_id
from src.shared import get_logger

from .intelligent_dm import get_intelligent_dm_system
from .response_formatter import ResponseFormatter
from .threading import ThreadingManager

logger = get_logger(__name__)


class SlackEventHandlers:
    """
    Unified event handlers that work identically in Socket and HTTP modes.

    Features:
    - Event deduplication with Redis
    - Intent classification
    - Threading management
    - Workflow routing integration
    """

    def __init__(self, threading_manager: ThreadingManager, response_formatter: ResponseFormatter):
        self.threading_manager = threading_manager
        self.response_formatter = response_formatter

        # Initialize Redis-based deduplication
        self.deduplicator = None
        self._init_deduplication()

        logger.info("Slack event handlers initialized with Redis deduplication")

    async def _init_deduplication(self):
        """Initialize Redis-based event deduplication."""
        try:
            dedup_config = DeduplicationConfig(
                default_ttl_seconds=3600,  # 1 hour deduplication window
                key_prefix="slack_event_dedup",
                temporal_window_seconds=300,  # 5 minutes for temporal dedup
                enable_metrics=True,
            )
            self.deduplicator = await get_event_deduplicator(dedup_config)
            logger.info("Redis event deduplication initialized")
        except Exception as e:
            logger.warning(
                f"Failed to initialize Redis deduplication, falling back to memory: {e}",
                exc_info=True,
            )
            # Fallback to in-memory deduplication
            self.processed_events = set()

    async def handle_app_mention(self, event: dict[str, Any], say: Callable):
        """
        Handle @ReflectAI mentions in channels.

        Implements Requirement 22: Hybrid threading strategy based on channel type.
        """
        correlation_id = get_or_create_correlation_id()

        try:
            # Extract event information
            user_id = event.get("user")
            channel_id = event.get("channel")
            text = event.get("text", "").strip()
            ts = event.get("ts")

            logger.info(
                "Processing app mention",
                extra={
                    "correlation_id": correlation_id,
                    "user_id": user_id,
                    "channel_id": channel_id,
                    "event_ts": ts,
                },
            )

            # Redis-based deduplication
            if await self._is_duplicate_event(event, "app_mention", user_id):
                logger.debug(
                    "Duplicate app mention event, skipping",
                    extra={"user_id": user_id, "channel_id": channel_id, "ts": ts},
                )
                return

            # Determine if we need threading
            should_thread = await self.threading_manager.should_create_thread(event, text)

            if should_thread:
                # Create thread and process in thread
                thread_ts = await self.threading_manager.create_thread(event, say)

                # Process the request in the created thread
                response = await self._process_mention_request(text, user_id, correlation_id)

                await say(text=response["text"], thread_ts=thread_ts, blocks=response.get("blocks"))
            else:
                # Simple direct response
                response = await self._process_simple_mention(text, user_id, correlation_id)
                await say(text=response["text"], blocks=response.get("blocks"))

        except Exception as e:
            logger.error(
                "Error handling app mention",
                extra={"correlation_id": correlation_id, "error": str(e)},
                exc_info=True,
            )

            await say(
                text="I encountered an error processing your request. Please try again in a moment.",
                thread_ts=event.get("thread_ts"),  # Maintain thread context if applicable
            )

    async def handle_direct_message(self, event: dict[str, Any], say: Callable):
        """
        Handle direct messages to ReflectAI.

        Implements Requirement 22: No threading in DMs for simple conversation flow.
        """
        correlation_id = get_or_create_correlation_id()

        try:
            user_id = event.get("user")
            text = event.get("text", "").strip()

            logger.info(
                "Processing direct message",
                extra={"correlation_id": correlation_id, "user_id": user_id},
            )

            # Redis-based deduplication for DMs
            if await self._is_duplicate_event(event, "direct_message", user_id):
                logger.debug("Duplicate direct message event, skipping", extra={"user_id": user_id})
                return

            # DMs are always processed without threading (Requirement 22)
            response = await self._process_direct_message(text, user_id, correlation_id)

            await say(text=response["text"], blocks=response.get("blocks"))

        except Exception as e:
            logger.error(
                "Error handling direct message",
                extra={"correlation_id": correlation_id, "user_id": user_id, "error": str(e)},
                exc_info=True,
            )

            await say(text="Sorry, I encountered an error. Please try again.")

    async def _is_duplicate_event(
        self, event: dict[str, Any], event_type: str, user_id: str | None = None
    ) -> bool:
        """
        Check if event is a duplicate using Redis deduplication.

        Args:
            event: Slack event data
            event_type: Type of event (app_mention, message, etc.)
            user_id: User ID associated with the event

        Returns:
            True if event is a duplicate, False otherwise
        """
        if self.deduplicator:
            try:
                # Use custom key fields for Slack-specific deduplication
                custom_key_fields = ["user", "channel", "ts", "text"]

                result = await self.deduplicator.check_and_store(
                    event_data=event,
                    event_type=event_type,
                    user_id=user_id,
                    custom_key_fields=custom_key_fields,
                )

                if result.is_duplicate:
                    logger.debug(
                        "Event marked as duplicate",
                        extra={
                            "event_type": event_type,
                            "event_key": result.event_key,
                            "duplicate_count": result.duplicate_count,
                            "first_seen": result.first_seen,
                        },
                    )

                return result.is_duplicate

            except Exception as e:
                logger.warning(
                    f"Redis deduplication failed, falling back to memory check: {e}",
                    extra={"event_type": event_type, "user_id": user_id},
                )

        # Fallback to memory-based deduplication if Redis is not available
        if hasattr(self, "processed_events"):
            event_key = f"{user_id}:{event.get('channel')}:{event.get('ts')}"
            if event_key in self.processed_events:
                return True
            self.processed_events.add(event_key)

        return False

    async def _process_mention_request(
        self, text: str, user_id: str, correlation_id: str
    ) -> dict[str, Any]:
        """Process complex mention requests that may need analysis workflows."""

        # Intent classification (simplified for production)
        if any(word in text.lower() for word in ["analyze", "analysis", "competency", "skill"]):
            # This would route to Analysis + Advisor agent workflow
            return await self._create_analysis_response(text, user_id, correlation_id)
        elif any(word in text.lower() for word in ["report", "summary", "progress"]):
            # This would route to report generation workflow
            return await self._create_report_response(text, user_id, correlation_id)
        else:
            # Route to simple conversation handling
            return await self._create_conversation_response(text, user_id, correlation_id)

    async def _process_simple_mention(
        self, text: str, user_id: str, correlation_id: str
    ) -> dict[str, Any]:
        """Process simple mentions like greetings."""

        # Greeting detection
        if any(word in text.lower() for word in ["hello", "hi", "hey", "help"]):
            return {
                "text": f"Hi <@{user_id}>! I'm ReflectAI, your competency development assistant. I can help you analyze activities, track progress, and generate reports. What would you like to explore?",
                "blocks": self.response_formatter.create_greeting_blocks(user_id),
            }

        return {
            "text": "I'm here to help with competency analysis and career development. Try mentioning keywords like 'analyze', 'report', or 'help' to get started!"
        }

    async def _process_direct_message(
        self, text: str, user_id: str, correlation_id: str
    ) -> dict[str, Any]:
        """Process direct messages with intelligent analysis and responses."""
        try:
            # Use intelligent DM system for sophisticated processing
            intelligent_dm = await get_intelligent_dm_system()

            response = await intelligent_dm.process_dm_message(
                user_id=user_id,
                message=text,
                metadata={"correlation_id": correlation_id, "message_type": "direct_message"},
            )

            return response

        except Exception as e:
            logger.error(
                f"Intelligent DM processing failed, falling back to basic response: {e}",
                extra={"user_id": user_id, "correlation_id": correlation_id},
            )

            # Fallback to basic response system
            if any(word in text.lower() for word in ["hello", "hi", "hey"]):
                return {
                    "text": "Hello! I'm ReflectAI. I can help you with competency analysis, skill development tracking, and career guidance. What can I help you with today?",
                    "blocks": self.response_formatter.create_dm_greeting_blocks(user_id),
                }

            return {
                "text": "I'm here to help with your professional development! Try `/help` to see what I can do for you, or just tell me what you're looking for."
            }

    async def _create_analysis_response(
        self, text: str, user_id: str, correlation_id: str
    ) -> dict[str, Any]:
        """Create response for analysis requests (production+ will integrate with agents)."""
        return {
            "text": "I'd love to help you with competency analysis! This feature is coming in the next phase. For now, I can help with basic questions and guidance.",
            "blocks": self.response_formatter.create_coming_soon_blocks("Competency Analysis"),
        }

    async def _create_report_response(
        self, text: str, user_id: str, correlation_id: str
    ) -> dict[str, Any]:
        """Create response for report requests (production+ will integrate with agents)."""
        return {
            "text": "Report generation is a powerful feature coming soon! I'll be able to create detailed competency reports, progress summaries, and development plans.",
            "blocks": self.response_formatter.create_coming_soon_blocks("Report Generation"),
        }

    async def _create_conversation_response(
        self, text: str, user_id: str, correlation_id: str
    ) -> dict[str, Any]:
        """Create response for general conversation."""
        return {
            "text": "I'm here to help with competency development and career guidance. While my full capabilities are still being developed, I can provide information about the system and upcoming features. What specific area interests you?",
            "blocks": self.response_formatter.create_help_blocks(),
        }


class SlackCommandHandlers:
    """
    Slash command handlers for ReflectAI.

    Handles commands like /reflect, /analyze, /help, /report, etc.
    """

    def __init__(self, response_formatter: ResponseFormatter):
        self.response_formatter = response_formatter

        # Initialize Redis-based deduplication
        self.deduplicator = None
        self._init_deduplication()

        logger.info("Slack command handlers initialized with Redis deduplication")

    async def _init_deduplication(self):
        """Initialize Redis-based event deduplication for commands."""
        try:
            dedup_config = DeduplicationConfig(
                default_ttl_seconds=300,  # 5 minutes for command deduplication
                key_prefix="slack_command_dedup",
                temporal_window_seconds=60,  # 1 minute temporal window
                enable_metrics=True,
            )
            self.deduplicator = await get_event_deduplicator(dedup_config)
            logger.info("Redis command deduplication initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Redis command deduplication: {e}", exc_info=True)

    async def _is_duplicate_event(
        self, event: dict[str, Any], event_type: str, user_id: str | None = None
    ) -> bool:
        """Check if command is a duplicate using Redis deduplication."""
        if self.deduplicator:
            try:
                custom_key_fields = ["user_id", "command", "text", "trigger_id"]

                result = await self.deduplicator.check_and_store(
                    event_data=event,
                    event_type=event_type,
                    user_id=user_id,
                    custom_key_fields=custom_key_fields,
                )

                return result.is_duplicate

            except Exception as e:
                logger.warning(
                    f"Redis command deduplication failed: {e}",
                    extra={"event_type": event_type, "user_id": user_id},
                )

        return False

    async def handle_reflect_command(
        self, ack: Callable, respond: Callable, command: dict[str, Any]
    ):
        """Handle /reflect slash command."""
        await ack()  # Acknowledge the command immediately

        correlation_id = get_or_create_correlation_id()
        user_id = command.get("user_id")
        text = command.get("text", "").strip()

        logger.info(
            "Processing /reflect command",
            extra={"correlation_id": correlation_id, "user_id": user_id, "command_text": text},
        )

        # Redis-based deduplication for slash commands
        if await self._is_duplicate_event(command, "slash_command_reflect", user_id):
            logger.debug("Duplicate /reflect command, skipping", extra={"user_id": user_id})
            return

        try:
            if not text or text.lower() == "help":
                # Show help information
                response = {
                    "response_type": "ephemeral",  # Only visible to user
                    "text": "ReflectAI Commands",
                    "blocks": self.response_formatter.create_command_help_blocks(),
                }
            else:
                # Process the command (production+ will route to agents)
                response = {
                    "response_type": "in_channel",  # Visible to everyone
                    "text": f"Processing your request: {text}",
                    "blocks": self.response_formatter.create_processing_blocks(text),
                }

            await respond(response)

        except Exception as e:
            logger.error(
                "Error handling /reflect command",
                extra={"correlation_id": correlation_id, "error": str(e)},
                exc_info=True,
            )

            await respond(
                {
                    "response_type": "ephemeral",
                    "text": "Sorry, I encountered an error processing your command. Please try again.",
                }
            )

    async def handle_help_command(self, ack: Callable, respond: Callable, command: dict[str, Any]):
        """Handle /help command."""
        await ack()

        user_id = command.get("user_id")

        # Redis-based deduplication for help commands
        if await self._is_duplicate_event(command, "slash_command_help", user_id):
            logger.debug("Duplicate /help command, skipping", extra={"user_id": user_id})
            return

        await respond(
            {
                "response_type": "ephemeral",
                "text": "ReflectAI Help & Documentation",
                "blocks": self.response_formatter.create_comprehensive_help_blocks(user_id),
            }
        )
