"""
Hybrid Threading Manager for Slack Conversations

Implements Requirement 22: Hybrid Threading Strategy
- Direct Messages: No threading for simple conversation flow
- Shared Channels: Threading for multi-step workflows (analysis, reports)
- Simple Greetings: Direct response without threading regardless of channel type
- Complex Analysis: Always threaded to maintain context and organization
"""

from collections.abc import Callable
from enum import Enum
from typing import Any

from src.infrastructure.monitoring import get_or_create_correlation_id
from src.shared import get_logger

logger = get_logger(__name__)


class ChannelType(str, Enum):
    """Types of Slack channels/conversations."""

    DIRECT_MESSAGE = "im"
    PUBLIC_CHANNEL = "channel"
    PRIVATE_CHANNEL = "group"
    MULTIPARTY_IM = "mpim"


class ThreadingDecision(str, Enum):
    """Threading decisions based on context."""

    NO_THREAD = "no_thread"
    CREATE_THREAD = "create_thread"
    CONTINUE_THREAD = "continue_thread"


class ThreadingManager:
    """
    Manages threading decisions and thread creation for Slack conversations.

    Decision Matrix (Requirement 22):
    - DM = no thread
    - Greeting = no thread (any channel)
    - Analysis workflow = thread (shared channels)
    - Shared channel = thread by default
    """

    def __init__(self):
        self.active_threads: dict[str, dict[str, Any]] = {}
        logger.info("Threading manager initialized")

    async def should_create_thread(self, event: dict[str, Any], text: str) -> bool:
        """
        Determine if a thread should be created based on Requirement 22 logic.

        Args:
            event: Slack event data
            text: Message text content

        Returns:
            True if a thread should be created, False otherwise
        """
        channel_type = self._get_channel_type(event)
        is_greeting = self._is_greeting(text)
        is_complex_workflow = self._is_complex_workflow(text)

        correlation_id = get_or_create_correlation_id()

        logger.debug(
            "Threading decision analysis",
            extra={
                "correlation_id": correlation_id,
                "channel_type": channel_type.value,
                "is_greeting": is_greeting,
                "is_complex_workflow": is_complex_workflow,
                "text_preview": text[:50] + "..." if len(text) > 50 else text,
            },
        )

        # Decision Matrix Implementation
        if channel_type == ChannelType.DIRECT_MESSAGE:
            # Rule: DM = no thread
            return False

        if is_greeting:
            # Rule: greeting = no thread (any channel)
            return False

        if is_complex_workflow:
            # Rule: analysis/reports = thread (shared channels)
            return True

        if channel_type in [ChannelType.PUBLIC_CHANNEL, ChannelType.PRIVATE_CHANNEL]:
            # Rule: shared channel = thread by default
            return True

        # Default: no thread for edge cases
        return False

    def _get_channel_type(self, event: dict[str, Any]) -> ChannelType:
        """Determine the type of Slack channel."""
        channel_info = event.get("channel_type") or event.get("channel", "")

        # Direct channel type mapping from Slack
        if channel_info == "im":
            return ChannelType.DIRECT_MESSAGE
        elif channel_info == "channel":
            return ChannelType.PUBLIC_CHANNEL
        elif channel_info == "group":
            return ChannelType.PRIVATE_CHANNEL
        elif channel_info == "mpim":
            return ChannelType.MULTIPARTY_IM

        # Fallback: analyze channel ID pattern
        channel_id = event.get("channel", "")
        if channel_id.startswith("D"):
            return ChannelType.DIRECT_MESSAGE
        elif channel_id.startswith("C"):
            return ChannelType.PUBLIC_CHANNEL
        elif channel_id.startswith("G"):
            return ChannelType.PRIVATE_CHANNEL

        # Conservative default
        return ChannelType.PUBLIC_CHANNEL

    def _is_greeting(self, text: str) -> bool:
        """Detect if message is a simple greeting."""
        greeting_words = {
            "hello",
            "hi",
            "hey",
            "good morning",
            "good afternoon",
            "good evening",
            "greetings",
            "what's up",
            "how are you",
            "howdy",
            "sup",
            "yo",
            "hiya",
            "help",
        }

        # Clean and normalize text
        clean_text = text.lower().strip()

        # Remove @mentions and clean up
        import re

        clean_text = re.sub(r"<@[^>]+>", "", clean_text).strip()

        # Check if the message consists primarily of greeting words
        words = clean_text.split()
        if len(words) <= 3:  # Short messages are likely greetings
            return any(greeting in clean_text for greeting in greeting_words)

        return False

    def _is_complex_workflow(self, text: str) -> bool:
        """Detect if message requires complex multi-step processing."""
        workflow_keywords = {
            "analyze",
            "analysis",
            "competency",
            "skill",
            "skills",
            "report",
            "generate",
            "create report",
            "summary",
            "assessment",
            "evaluate",
            "breakdown",
            "detailed",
            "workflow",
            "process",
            "step by step",
        }

        clean_text = text.lower().strip()

        return any(keyword in clean_text for keyword in workflow_keywords)

    async def create_thread(self, event: dict[str, Any], say: Callable) -> str:
        """
        Create a new thread and return thread timestamp.

        Args:
            event: Original Slack event
            say: Slack say function

        Returns:
            Thread timestamp for continuing conversation
        """
        correlation_id = get_or_create_correlation_id()
        channel_id = event.get("channel")
        user_id = event.get("user")
        original_ts = event.get("ts")

        try:
            # Send initial thread message
            thread_response = await say(
                text="I'll help you with that! Let me process your request...",
                thread_ts=original_ts,  # This creates the thread
            )

            # Store thread information for context management
            thread_ts = thread_response.get("ts") or original_ts
            thread_key = f"{channel_id}:{thread_ts}"

            self.active_threads[thread_key] = {
                "channel_id": channel_id,
                "user_id": user_id,
                "thread_ts": thread_ts,
                "original_ts": original_ts,
                "created_at": event.get("ts"),
                "correlation_id": correlation_id,
                "context": "multi_step_workflow",
            }

            logger.info(
                "Created new thread",
                extra={
                    "correlation_id": correlation_id,
                    "channel_id": channel_id,
                    "thread_ts": thread_ts,
                    "user_id": user_id,
                },
            )

            return thread_ts

        except Exception as e:
            logger.error(
                "Error creating thread",
                extra={"correlation_id": correlation_id, "error": str(e)},
                exc_info=True,
            )

            # Return original timestamp as fallback
            return original_ts

    def get_thread_context(self, channel_id: str, thread_ts: str) -> dict[str, Any] | None:
        """Get context information for an active thread."""
        thread_key = f"{channel_id}:{thread_ts}"
        return self.active_threads.get(thread_key)

    def update_thread_context(self, channel_id: str, thread_ts: str, updates: dict[str, Any]):
        """Update thread context with new information."""
        thread_key = f"{channel_id}:{thread_ts}"
        if thread_key in self.active_threads:
            self.active_threads[thread_key].update(updates)

    def close_thread(self, channel_id: str, thread_ts: str):
        """Mark thread as completed and clean up context."""
        thread_key = f"{channel_id}:{thread_ts}"
        if thread_key in self.active_threads:
            correlation_id = self.active_threads[thread_key].get("correlation_id")
            del self.active_threads[thread_key]

            logger.info(
                "Thread closed",
                extra={
                    "correlation_id": correlation_id,
                    "channel_id": channel_id,
                    "thread_ts": thread_ts,
                },
            )

    def get_threading_stats(self) -> dict[str, Any]:
        """Get statistics about threading usage."""
        return {
            "active_threads": len(self.active_threads),
            "thread_details": [
                {
                    "channel_id": thread["channel_id"],
                    "created_at": thread["created_at"],
                    "context": thread["context"],
                }
                for thread in self.active_threads.values()
            ],
        }
