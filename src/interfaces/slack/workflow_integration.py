"""
Slack to Temporal Workflow Integration

Connects Slack events to Temporal workflows, implementing the complete
end-to-end flow from user interaction to agent processing.

Key features:
- Routes Slack events to appropriate workflows
- Maintains conversation context
- Handles threading strategy
- Provides real-time updates to users
- Integrates deduplication and error handling
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx
from slack_bolt.async_app import AsyncApp
from slack_sdk.errors import SlackApiError

from src.core.workflows.workflow_router import (
    RoutingContext,
    RoutingDecision,
    WorkflowRouter,
    get_workflow_router,
)
from src.infrastructure.cache.redis_manager import RedisManager
from src.infrastructure.events.event_deduplicator import (
    DeduplicationResult,
    get_event_deduplicator,
)
from src.interfaces.slack.block_builder import SlackBlockBuilder
from src.shared import get_config, get_logger

logger = get_logger(__name__)


@dataclass
class SlackContext:
    """Context for Slack message processing."""

    user_id: str
    team_id: str
    channel_id: str
    thread_ts: str | None
    message_ts: str
    text: str
    event_type: str
    event_id: str
    is_direct_message: bool
    is_bot_mention: bool


class SlackWorkflowIntegration:
    """
    Integrates Slack events with Temporal workflows.

    Handles the complete flow from Slack event to workflow execution
    and response formatting.
    """

    def __init__(
        self,
        slack_app: AsyncApp,
        workflow_router: WorkflowRouter = None,
        dedup_service=None,
        redis_manager=None,
    ):
        """Initialize Slack workflow integration."""
        self.config = get_config()
        self.slack_app = slack_app
        self.slack_client = slack_app.client
        self.workflow_router = workflow_router
        self.dedup_service = dedup_service
        self.redis_manager = redis_manager
        self.block_builder = SlackBlockBuilder()

        # Threading configuration
        self.use_threading_in_channels = True
        self.use_threading_in_dm = False
        self.thread_for_complex_workflows = True

    async def initialize(self):
        """Initialize integration components."""
        # Initialize workflow router
        if not self.workflow_router:
            self.workflow_router = await get_workflow_router()

        # Initialize deduplication service
        if not self.dedup_service:
            self.dedup_service = await get_event_deduplicator()

        # Initialize Redis for conversation context only if not provided
        if not self.redis_manager:
            from src.infrastructure.cache.redis_manager import get_redis_manager
            self.redis_manager = get_redis_manager()

        logger.info("Slack workflow integration initialized")

    async def handle_message_event(self, event: dict[str, Any], say: Any, ack: Any = None):
        """
        Handle Slack message events and route to workflows.

        This is the main entry point for processing user messages.
        """
        try:
            # Acknowledge event immediately
            if ack:
                await ack()

            # Extract context
            slack_context = self._extract_slack_context(event)

            # Check for duplicate
            dedup_result = await self.dedup_service.check_duplicate(
                event_id=slack_context.event_id,
                timestamp=slack_context.message_ts,
                user_id=slack_context.user_id,
                event_type="slack_message",
            )
            if dedup_result == DeduplicationResult.DUPLICATE:
                logger.info(
                    "Duplicate Slack event ignored",
                    extra={
                        "event_id": slack_context.event_id,
                        "user_id": slack_context.user_id,
                    },
                )
                return

            # Load user profile
            user_profile = await self._load_user_profile(slack_context.user_id)

            # Load conversation history if in thread
            conversation_history = None
            if slack_context.thread_ts:
                conversation_history = await self._load_conversation_history(
                    slack_context.channel_id, slack_context.thread_ts
                )

            # Create routing context
            routing_context = RoutingContext(
                user_id=slack_context.user_id,
                content=slack_context.text,
                thread_id=slack_context.thread_ts,
                channel_type="direct_message" if slack_context.is_direct_message else "channel",
                user_profile=user_profile,
                conversation_history=conversation_history,
                correlation_id=slack_context.event_id,
            )

            # Route to workflow
            routing_result = await self.workflow_router.route_request(routing_context)

            # Handle routing decision
            await self._handle_routing_decision(routing_result, slack_context, say)

        except httpx.NetworkError as e:
            logger.error(
                "Network error handling Slack message",
                extra={"event": event, "error": str(e), "error_type": "network"},
                exc_info=True,
            )
            await self._send_error_response(
                slack_context,
                say,
                "I'm having trouble connecting to our services. Please try again in a moment.",
            )

        except httpx.TimeoutException as e:
            logger.error(
                "Timeout handling Slack message",
                extra={"event": event, "error": str(e), "error_type": "timeout"},
                exc_info=True,
            )
            await self._send_error_response(
                slack_context, say, "Your request is taking longer than expected. Please try again."
            )

        except SlackApiError as e:
            logger.error(
                "Slack API error handling message",
                extra={
                    "event": event,
                    "error": e.response.get("error", str(e)),
                    "error_type": "slack_api",
                },
                exc_info=True,
            )
            await self._send_error_response(
                slack_context, say, "I encountered an issue with Slack. Please try again."
            )

        except Exception as e:
            logger.error(
                "Unexpected error handling Slack message",
                extra={"event": event, "error": str(e), "error_type": "unexpected"},
                exc_info=True,
            )
            await self._send_error_response(
                slack_context, say, "An unexpected error occurred. Our team has been notified."
            )

    async def handle_slash_command(self, command: dict[str, Any], ack: Any, respond: Any):
        """
        Handle Slack slash commands and route to workflows.
        """
        try:
            # Acknowledge command immediately
            await ack()

            # Extract context from command
            slack_context = SlackContext(
                user_id=command.get("user_id"),
                team_id=command.get("team_id"),
                channel_id=command.get("channel_id"),
                thread_ts=None,  # Commands don't have threads initially
                message_ts=str(datetime.now().timestamp()),
                text=command.get("text", ""),
                event_type="slash_command",
                event_id=command.get("trigger_id"),
                is_direct_message=command.get("channel_name") == "directmessage",
                is_bot_mention=False,
            )

            # Check for duplicate
            dedup_result = await self.dedup_service.check_duplicate(
                event_id=slack_context.event_id,
                timestamp=slack_context.message_ts,
                user_id=slack_context.user_id,
                event_type="slash_command",
            )

            if dedup_result == DeduplicationResult.DUPLICATE:
                await respond(
                    {"text": "This command was already processed.", "response_type": "ephemeral"}
                )
                return

            # Process command based on type
            command_name = command.get("command", "")

            if command_name == "/reflect":
                await self._handle_reflect_command(slack_context, respond)
            elif command_name == "/analyze":
                await self._handle_analyze_command(slack_context, respond)
            elif command_name == "/report":
                await self._handle_report_command(slack_context, respond)
            elif command_name == "/help":
                await self._handle_help_command(slack_context, respond)
            else:
                await respond(
                    {"text": f"Unknown command: {command_name}", "response_type": "ephemeral"}
                )

        except httpx.NetworkError as e:
            logger.error(
                "Network error handling slash command",
                extra={
                    "command": command.get("command"),
                    "user_id": command.get("user_id"),
                    "error": str(e),
                    "error_type": "network",
                },
                exc_info=True,
            )
            await respond(
                {
                    "text": "Network connectivity issue. Please try again in a moment.",
                    "response_type": "ephemeral",
                }
            )

        except httpx.TimeoutException as e:
            logger.error(
                "Timeout handling slash command",
                extra={
                    "command": command.get("command"),
                    "user_id": command.get("user_id"),
                    "error": str(e),
                    "error_type": "timeout",
                },
                exc_info=True,
            )
            await respond(
                {"text": "Request timed out. Please try again.", "response_type": "ephemeral"}
            )

        except SlackApiError as e:
            logger.error(
                "Slack API error handling command",
                extra={
                    "command": command.get("command"),
                    "user_id": command.get("user_id"),
                    "error": e.response.get("error", str(e)),
                    "error_type": "slack_api",
                },
                exc_info=True,
            )
            await respond(
                {"text": "Slack API issue. Please try again.", "response_type": "ephemeral"}
            )

        except Exception as e:
            logger.error(
                "Unexpected error handling slash command",
                extra={
                    "command": command.get("command"),
                    "user_id": command.get("user_id"),
                    "error": str(e),
                    "error_type": "unexpected",
                },
                exc_info=True,
            )
            await respond(
                {
                    "text": "An unexpected error occurred. Our team has been notified.",
                    "response_type": "ephemeral",
                }
            )

    async def _handle_routing_decision(
        self, routing_result: Any, slack_context: SlackContext, say: Any
    ):
        """Handle different routing decisions."""

        decision = routing_result.decision

        if decision == RoutingDecision.GREETING:
            # Handle greeting immediately without workflow
            await self._send_greeting_response(slack_context, say)

        elif decision == RoutingDecision.HELP:
            # Handle help request immediately
            await self._send_help_response(slack_context, say)

        elif decision == RoutingDecision.SEQUENTIAL_ANALYSIS:
            # Start analysis workflow
            await self._handle_analysis_workflow(routing_result, slack_context, say)

        elif decision == RoutingDecision.BATCH_ANALYSIS:
            # Start batch workflow
            await self._handle_batch_workflow(routing_result, slack_context, say)

        elif decision == RoutingDecision.CONVERSATION:
            # Continue conversation workflow
            await self._handle_conversation_workflow(routing_result, slack_context, say)

        elif decision == RoutingDecision.ERROR:
            # Handle error
            await self._send_error_response(
                slack_context, say, "I couldn't understand your request. Please try rephrasing."
            )

    async def _handle_analysis_workflow(
        self, routing_result: Any, slack_context: SlackContext, say: Any
    ):
        """Handle sequential analysis workflow."""

        # Determine if we should use threading
        should_thread = self._should_use_thread(slack_context)

        # Send initial acknowledgment
        initial_message = await say(
            text="I'm analyzing your request...",
            thread_ts=slack_context.thread_ts if should_thread else None,
            blocks=self.block_builder.build_processing_indicator(
                "Starting analysis", "Your request is being processed by our AI agents."
            ),
        )

        # Create thread if needed
        if should_thread and not slack_context.thread_ts:
            slack_context.thread_ts = initial_message.get("ts")

        # Store workflow ID for tracking
        await self._store_workflow_mapping(
            slack_context.thread_ts or initial_message.get("ts"), routing_result.workflow_id
        )

        # Start monitoring workflow status
        asyncio.create_task(
            self._monitor_workflow(
                routing_result.workflow_id, slack_context, say, initial_message.get("ts")
            )
        )

    async def _handle_batch_workflow(
        self, routing_result: Any, slack_context: SlackContext, say: Any
    ):
        """Handle batch analysis workflow."""

        # Always use threading for batch processing

        # Send initial message
        initial_message = await say(
            text="Processing batch analysis...",
            thread_ts=slack_context.thread_ts,
            blocks=self.block_builder.build_batch_processing_indicator(
                routing_result.estimated_cost, "Batch processing optimized for cost savings"
            ),
        )

        # Create thread
        if not slack_context.thread_ts:
            slack_context.thread_ts = initial_message.get("ts")

        # Monitor batch workflow
        asyncio.create_task(
            self._monitor_batch_workflow(
                routing_result.workflow_id, slack_context, say, initial_message.get("ts")
            )
        )

    async def _monitor_workflow(
        self,
        workflow_id: str,
        slack_context: SlackContext,
        say: Any,
        message_ts: str,
        max_iterations: int = 150,  # 150 iterations * 2s = 5 minutes
        check_interval: int = 2,  # seconds
    ):
        """
        Monitor workflow execution and update user.

        Args:
            workflow_id: Workflow ID to monitor
            slack_context: Slack context for updates
            say: Slack say function
            message_ts: Message timestamp for updates
            max_iterations: Maximum iterations before timeout (default: 150 = 5 minutes)
            check_interval: Seconds between checks (default: 2)
        """

        try:
            iteration_count = 0

            while iteration_count < max_iterations:
                iteration_count += 1

                # Get workflow status
                status = await self.workflow_router.get_workflow_status(workflow_id)

                if status["status"] == "COMPLETED":
                    # Get workflow result
                    result = await self._get_workflow_result(workflow_id)

                    # Format and send result
                    await self._send_workflow_result(result, slack_context, say)
                    break

                elif status["status"] == "FAILED":
                    # Send failure message
                    await self._send_workflow_failure(workflow_id, slack_context, say)
                    break

                elif status["status"] == "RUNNING":
                    # Update progress
                    await self._update_progress(
                        slack_context, message_ts, "Processing your request..."
                    )

                # Wait before next check
                await asyncio.sleep(check_interval)

            # Handle timeout if max iterations reached
            if iteration_count >= max_iterations:
                timeout_seconds = max_iterations * check_interval
                logger.warning(
                    f"Workflow monitoring timeout after {timeout_seconds}s",
                    extra={
                        "workflow_id": workflow_id,
                        "iterations": iteration_count,
                        "timeout_seconds": timeout_seconds,
                    },
                )

                # Send timeout message to user
                await self._send_error_response(
                    slack_context,
                    say,
                    f"Workflow monitoring timed out after {timeout_seconds} seconds. "
                    f"The workflow may still be running. Please check back later or contact support.",
                )

        except httpx.NetworkError as e:
            logger.error(
                "Network error while monitoring workflow",
                extra={"workflow_id": workflow_id, "error": str(e), "error_type": "network"},
                exc_info=True,
            )
            await self._send_error_response(
                slack_context,
                say,
                "Network connectivity issue while processing your request. Please try again.",
            )
        except httpx.TimeoutException as e:
            logger.error(
                "Timeout while monitoring workflow",
                extra={"workflow_id": workflow_id, "error": str(e), "error_type": "timeout"},
                exc_info=True,
            )
            await self._send_error_response(
                slack_context,
                say,
                "Request timed out. Please try again or contact support if the issue persists.",
            )
        except Exception as e:
            logger.error(
                "Unexpected error monitoring workflow",
                extra={"workflow_id": workflow_id, "error": str(e), "error_type": "unexpected"},
                exc_info=True,
            )
            await self._send_error_response(
                slack_context, say, "An unexpected error occurred. Our team has been notified."
            )

    async def _get_workflow_result(self, workflow_id: str) -> dict[str, Any]:
        """
        Get the result of a completed workflow.

        Args:
            workflow_id: The workflow ID to get results for

        Returns:
            Dictionary containing workflow results
        """
        try:
            # Get full workflow status from router
            status_dict = await self.workflow_router.get_workflow_status(workflow_id)

            if not status_dict or status_dict.get("status") == "NOT_FOUND":
                logger.error(f"Workflow {workflow_id} not found")
                return {"error": "Workflow not found", "workflow_id": workflow_id}

            # Extract result from status
            result = status_dict.get("result", {})

            # If result is empty, provide basic information
            if not result:
                result = {
                    "status": status_dict.get("status"),
                    "workflow_id": workflow_id,
                    "message": "Workflow completed successfully",
                }

            return result

        except Exception as e:
            logger.error(f"Error getting workflow result for {workflow_id}: {e}", exc_info=True)
            return {"error": str(e), "workflow_id": workflow_id}

    async def _send_workflow_result(
        self, result: dict[str, Any], slack_context: SlackContext, say: Any
    ):
        """Send formatted workflow result to user."""

        # Build result blocks based on result type
        if result.get("analysis"):
            blocks = self.block_builder.build_analysis_result(
                result["analysis"], result.get("advice"), result.get("cost_usd", 0)
            )
        else:
            blocks = self.block_builder.build_generic_result(result)

        # Send result
        await say(text="Analysis complete!", thread_ts=slack_context.thread_ts, blocks=blocks)

    def _should_use_thread(self, slack_context: SlackContext) -> bool:
        """Determine if threading should be used."""

        # No threading in DMs
        if slack_context.is_direct_message and not self.use_threading_in_dm:
            return False

        # Always thread in channels for complex workflows
        if not slack_context.is_direct_message and self.thread_for_complex_workflows:
            return True

        # Continue existing thread
        if slack_context.thread_ts:
            return True

        return self.use_threading_in_channels and not slack_context.is_direct_message

    def _extract_slack_context(self, event: dict[str, Any]) -> SlackContext:
        """Extract context from Slack event."""

        return SlackContext(
            user_id=event.get("user", ""),
            team_id=event.get("team", ""),
            channel_id=event.get("channel", ""),
            thread_ts=event.get("thread_ts"),
            message_ts=event.get("ts", str(datetime.now().timestamp())),
            text=event.get("text", ""),
            event_type=event.get("type", "message"),
            event_id=event.get("client_msg_id") or event.get("event_id", ""),
            is_direct_message=event.get("channel_type") == "im",
            is_bot_mention="<@" in event.get("text", ""),
        )

    async def _load_user_profile(self, user_id: str) -> dict[str, Any]:
        """Load user profile from cache or database."""

        # Try cache first
        cache_key = f"user_profile:{user_id}"
        cached = await self.redis_manager.get(cache_key)

        if cached:
            return cached

        # Load from Slack API
        try:
            response = await self.slack_client.users_info(user=user_id)
            profile = response.get("user", {})

            # Cache for 1 hour
            await self.redis_manager.set(cache_key, profile, ttl=3600)

            return profile

        except httpx.NetworkError as e:
            logger.warning(
                "Network error loading user profile - proceeding with minimal profile",
                extra={"user_id": user_id, "error": str(e), "error_type": "network"},
            )
            return {"id": user_id, "name": "Unknown User"}

        except httpx.TimeoutException as e:
            logger.warning(
                "Timeout loading user profile - proceeding with minimal profile",
                extra={"user_id": user_id, "error": str(e), "error_type": "timeout"},
            )
            return {"id": user_id, "name": "Unknown User"}

        except SlackApiError as e:
            logger.error(
                "Slack API error loading user profile",
                extra={
                    "user_id": user_id,
                    "error": e.response.get("error", str(e)),
                    "error_type": "slack_api",
                },
            )
            return {"id": user_id, "name": "Unknown User"}

        except Exception as e:
            logger.error(
                "Unexpected error loading user profile",
                extra={"user_id": user_id, "error": str(e), "error_type": "unexpected"},
                exc_info=True,
            )
            return {"id": user_id, "name": "Unknown User"}

    async def _send_error_response(self, slack_context: SlackContext, say: Any, error_message: str):
        """Send user-friendly error message to Slack."""
        try:
            error_blocks = self.block_builder.build_error_message(
                error_message, show_support_contact=True
            )

            await say(
                text=f"Error: {error_message}",
                thread_ts=slack_context.thread_ts,
                blocks=error_blocks,
            )
        except Exception as e:
            logger.error(
                "Failed to send error response to Slack",
                extra={
                    "error": str(e),
                    "original_error": error_message,
                    "channel_id": slack_context.channel_id,
                },
                exc_info=True,
            )

    async def _send_workflow_failure(self, workflow_id: str, slack_context: SlackContext, say: Any):
        """Send workflow failure notification to user."""
        try:
            failure_message = (
                "I encountered an issue processing your request. "
                "Our team has been notified and will investigate."
            )

            failure_blocks = self.block_builder.build_error_message(
                failure_message, show_support_contact=True
            )

            await say(
                text=failure_message, thread_ts=slack_context.thread_ts, blocks=failure_blocks
            )

            logger.error(
                "Workflow failed",
                extra={
                    "workflow_id": workflow_id,
                    "user_id": slack_context.user_id,
                    "channel_id": slack_context.channel_id,
                },
            )
        except Exception as e:
            logger.error(
                "Failed to send workflow failure notification",
                extra={
                    "error": str(e),
                    "workflow_id": workflow_id,
                    "channel_id": slack_context.channel_id,
                },
                exc_info=True,
            )

    async def _update_progress(
        self, slack_context: SlackContext, message_ts: str, status_text: str
    ):
        """Update progress message in Slack."""
        try:
            await self.slack_client.chat_update(
                channel=slack_context.channel_id,
                ts=message_ts,
                text=status_text,
                blocks=self.block_builder.build_progress_message(status_text),
            )
        except SlackApiError as e:
            logger.warning(
                "Failed to update progress message",
                extra={
                    "error": e.response.get("error", str(e)),
                    "channel_id": slack_context.channel_id,
                    "message_ts": message_ts,
                },
            )
        except Exception as e:
            logger.error(
                "Unexpected error updating progress",
                extra={
                    "error": str(e),
                    "channel_id": slack_context.channel_id,
                    "message_ts": message_ts,
                },
                exc_info=True,
            )

    async def _load_conversation_history(
        self, channel_id: str, thread_ts: str
    ) -> list[dict[str, Any]]:
        """Load conversation history using ConversationIntelligence."""
        try:
            # Use ConversationIntelligence to get conversation summary
            from src.core.conversation.intelligence import ConversationIntelligence

            conversation_intelligence = ConversationIntelligence(
                redis_client=self.redis_manager if hasattr(self, "redis_manager") else None
            )

            # Get conversation summary which includes message history
            conversation_summary = await conversation_intelligence.get_conversation_summary(
                user_id=self._extract_user_from_thread(thread_ts),  # We'll need to extract this
                thread_id=thread_ts,
            )

            # Return the messages or empty list
            return conversation_summary.get("message_history", [])

        except Exception as e:
            logger.error(f"Error loading conversation history: {e}")
            return []

    def _extract_user_from_thread(self, thread_ts: str) -> str:
        """Extract user ID from thread timestamp - simplified implementation."""
        # In practice, you'd look up the thread owner from Slack API or database
        # For now, return a placeholder
        return "unknown_user"

    async def _store_workflow_mapping(self, thread_id: str, workflow_id: str):
        """Store mapping between Slack thread and workflow."""

        key = f"workflow_mapping:{thread_id}"
        await self.redis_manager.set(key, workflow_id, ttl=3600)

    async def _handle_reflect_command(self, slack_context: SlackContext, respond: Any):
        """Handle /reflect command - allow users to reflect on their activities."""
        try:
            # Send initial acknowledgment
            await respond(
                {
                    "text": "💭 Let's reflect on your recent activities...",
                    "response_type": "ephemeral",
                    "blocks": self.block_builder.build_processing_indicator(
                        "Analyzing your activities",
                        "I'm reviewing your recent work to provide insights on your professional growth.",
                    ),
                }
            )

            # Create routing context for analysis workflow
            routing_context = RoutingContext(
                user_id=slack_context.user_id,
                content="Reflect on my recent activities and provide competency insights",
                thread_id=None,
                channel_type="direct_message" if slack_context.is_direct_message else "channel",
                user_profile={},
                conversation_history=None,
                correlation_id=slack_context.event_id,
            )

            # Route to sequential analysis workflow
            routing_result = await self.workflow_router.route_request(routing_context)

            # Handle the workflow execution
            await self._handle_analysis_workflow(routing_result, slack_context, respond)

        except Exception as e:
            logger.error(f"Error handling reflect command: {e}", exc_info=True)
            await respond(
                {
                    "text": "I encountered an issue processing your reflection request. Please try again.",
                    "response_type": "ephemeral",
                }
            )

    async def _handle_analyze_command(self, slack_context: SlackContext, respond: Any):
        """Handle /analyze command - analyze user competencies."""
        try:
            # Parse command text for specific activity or general analysis
            activity_text = slack_context.text.strip()

            if activity_text:
                message = (
                    f"📊 Analyzing: '{activity_text[:100]}...'"
                    if len(activity_text) > 100
                    else f"📊 Analyzing: '{activity_text}'"
                )
            else:
                message = "📊 Analyzing your competency profile..."

            await respond(
                {
                    "text": message,
                    "response_type": "ephemeral",
                    "blocks": self.block_builder.build_processing_indicator(
                        "Starting competency analysis",
                        "I'm evaluating your skills and identifying development opportunities.",
                    ),
                }
            )

            # Create routing context with activity text or general analysis
            content = activity_text if activity_text else "Analyze my overall competency profile"
            routing_context = RoutingContext(
                user_id=slack_context.user_id,
                content=content,
                thread_id=None,
                channel_type="direct_message" if slack_context.is_direct_message else "channel",
                user_profile={},
                conversation_history=None,
                correlation_id=slack_context.event_id,
            )

            # Route to appropriate workflow
            routing_result = await self.workflow_router.route_request(routing_context)

            # Handle the workflow execution
            await self._handle_analysis_workflow(routing_result, slack_context, respond)

        except Exception as e:
            logger.error(f"Error handling analyze command: {e}", exc_info=True)
            await respond(
                {
                    "text": "I encountered an issue with your analysis request. Please try again.",
                    "response_type": "ephemeral",
                }
            )

    async def _handle_report_command(self, slack_context: SlackContext, respond: Any):
        """Handle /report command - generate competency reports."""
        try:
            # Parse command text for report type and date range
            command_text = slack_context.text.strip().lower()

            # Default report parameters
            report_type = "competency_assessment"
            date_range_days = 90

            # Parse command text
            if "weekly" in command_text or "week" in command_text:
                date_range_days = 7
            elif "monthly" in command_text or "month" in command_text:
                date_range_days = 30
            elif "quarterly" in command_text or "quarter" in command_text:
                date_range_days = 90

            await respond(
                {
                    "text": f"📄 Generating your competency report ({date_range_days} days)...",
                    "response_type": "ephemeral",
                    "blocks": self.block_builder.build_processing_indicator(
                        "Generating report",
                        f"I'm compiling your competency data for the last {date_range_days} days. This may take a few minutes.",
                    ),
                }
            )

            # Start report generation workflow
            from src.services.workflow.models import WorkflowRequest, WorkflowType

            WorkflowRequest(
                workflow_type=WorkflowType.REPORT_GENERATION,
                user_id=slack_context.user_id,
                input_data={
                    "report_type": report_type,
                    "date_range_days": date_range_days,
                    "channel_id": slack_context.channel_id,
                    "include_recommendations": True,
                },
                correlation_id=slack_context.event_id,
            )

            # Execute workflow via router
            routing_context = RoutingContext(
                user_id=slack_context.user_id,
                content=f"Generate {report_type} report for {date_range_days} days",
                thread_id=None,
                channel_type="direct_message" if slack_context.is_direct_message else "channel",
                user_profile={},
                conversation_history=None,
                correlation_id=slack_context.event_id,
            )

            routing_result = await self.workflow_router.route_request(routing_context)

            # Monitor workflow
            asyncio.create_task(
                self._monitor_workflow(
                    routing_result.workflow_id, slack_context, respond, slack_context.message_ts
                )
            )

        except Exception as e:
            logger.error(f"Error handling report command: {e}", exc_info=True)
            await respond(
                {
                    "text": "I encountered an issue generating your report. Please try again.",
                    "response_type": "ephemeral",
                }
            )

    async def _handle_help_command(self, slack_context: SlackContext, respond: Any):
        """Handle /help command - show available commands and usage."""
        try:
            help_blocks = [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": "🤖 ReflectAI Help", "emoji": True},
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "I'm your AI-powered competency development assistant. Here's how I can help:",
                    },
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Available Commands:*\n\n"
                        "• `/reflect` - Reflect on your recent activities and get competency insights\n"
                        "• `/analyze [activity]` - Analyze a specific activity or your overall competency profile\n"
                        "• `/report [timeframe]` - Generate a detailed competency report (weekly, monthly, quarterly)\n"
                        "• `/help` - Show this help message",
                    },
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*How to Use:*\n\n"
                        "*1. Track Activities*\n"
                        "Just tell me what you're working on! Example:\n"
                        '"I implemented OAuth2 authentication"\n\n'
                        "*2. Get Analysis*\n"
                        "Use `/analyze` to understand your competency levels and growth areas\n\n"
                        "*3. Generate Reports*\n"
                        "Use `/report monthly` to get a comprehensive PDF report",
                    },
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Examples:*\n\n"
                        '• "Analyze this: I led a team of 5 engineers to migrate our infrastructure to Kubernetes"\n'
                        "• `/analyze system design skills`\n"
                        "• `/reflect`\n"
                        "• `/report quarterly`",
                    },
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": "💡 *Tip:* You can also just chat with me naturally about your work and professional development!",
                        }
                    ],
                },
            ]

            await respond(
                {"text": "ReflectAI Help", "response_type": "ephemeral", "blocks": help_blocks}
            )

        except Exception as e:
            logger.error(f"Error handling help command: {e}", exc_info=True)
            await respond(
                {
                    "text": "I encountered an issue displaying help. Please try again.",
                    "response_type": "ephemeral",
                }
            )

    async def _send_greeting_response(self, slack_context: SlackContext, say: Any):
        """Send greeting message to user."""
        try:
            greeting_blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "👋 Hello! I'm ReflectAI, your AI-powered competency development assistant.",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "I can help you:\n"
                        "• Track and analyze your professional activities\n"
                        "• Identify your competency strengths and development areas\n"
                        "• Generate personalized development recommendations\n"
                        "• Create detailed competency reports",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "Try asking me to analyze an activity, or use `/help` to see all available commands!",
                    },
                },
            ]

            await say(
                text="Hello! I'm ReflectAI, your competency development assistant.",
                thread_ts=slack_context.thread_ts,
                blocks=greeting_blocks,
            )

        except Exception as e:
            logger.error(f"Error sending greeting response: {e}", exc_info=True)
            await say(
                text="Hello! I'm ReflectAI. How can I help you today?",
                thread_ts=slack_context.thread_ts,
            )

    async def _send_help_response(self, slack_context: SlackContext, say: Any):
        """Send help information to user."""
        try:
            # Reuse help blocks from _handle_help_command
            help_blocks = [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": "🤖 ReflectAI Help", "emoji": True},
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "Here's what I can do for you:"},
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Available Commands:*\n"
                        "• `/reflect` - Get insights on your recent activities\n"
                        "• `/analyze [activity]` - Analyze specific activities or your competency profile\n"
                        "• `/report [timeframe]` - Generate competency reports\n"
                        "• `/help` - Show this help message\n\n"
                        "*Or just chat naturally!*\n"
                        "Tell me about your work and I'll help you track your professional growth.",
                    },
                },
            ]

            await say(
                text="Here's how I can help you:",
                thread_ts=slack_context.thread_ts,
                blocks=help_blocks,
            )

        except Exception as e:
            logger.error(f"Error sending help response: {e}", exc_info=True)
            await say(
                text="I can help you analyze activities, track competencies, and generate development reports. Try `/help` for more details!",
                thread_ts=slack_context.thread_ts,
            )

    async def _handle_conversation_workflow(
        self, routing_result: Any, slack_context: SlackContext, say: Any
    ):
        """Handle conversational workflow execution."""
        try:
            # Determine if we should use threading
            should_thread = self._should_use_thread(slack_context)

            # Send initial acknowledgment
            initial_message = await say(
                text="I'm processing your message...",
                thread_ts=slack_context.thread_ts if should_thread else None,
                blocks=self.block_builder.build_processing_indicator(
                    "Understanding your message",
                    "I'm analyzing your message and preparing a response.",
                ),
            )

            # Create thread if needed
            if should_thread and not slack_context.thread_ts:
                slack_context.thread_ts = initial_message.get("ts")

            # Store workflow mapping
            await self._store_workflow_mapping(
                slack_context.thread_ts or initial_message.get("ts"), routing_result.workflow_id
            )

            # Monitor conversation workflow
            asyncio.create_task(
                self._monitor_workflow(
                    routing_result.workflow_id, slack_context, say, initial_message.get("ts")
                )
            )

        except Exception as e:
            logger.error(f"Error handling conversation workflow: {e}", exc_info=True)
            await self._send_error_response(
                slack_context,
                say,
                "I encountered an issue processing your message. Please try again.",
            )

    async def _monitor_batch_workflow(
        self,
        workflow_id: str,
        slack_context: SlackContext,
        say: Any,
        message_ts: str,
        max_iterations: int = 300,  # 300 iterations * 2s = 10 minutes (batch processing can take longer)
        check_interval: int = 2,  # seconds
    ):
        """
        Monitor batch workflow execution and update user.

        Similar to _monitor_workflow but with longer timeout for batch processing.

        Args:
            workflow_id: Workflow ID to monitor
            slack_context: Slack context for updates
            say: Slack say function
            message_ts: Message timestamp for updates
            max_iterations: Maximum iterations before timeout (default: 300 = 10 minutes)
            check_interval: Seconds between checks (default: 2)
        """
        try:
            iteration_count = 0
            last_update_iteration = 0
            update_frequency = 15  # Update every 30 seconds (15 * 2s)

            while iteration_count < max_iterations:
                iteration_count += 1

                # Get workflow status
                status = await self.workflow_router.get_workflow_status(workflow_id)

                if status["status"] == "COMPLETED":
                    # Get workflow result
                    result = await self._get_workflow_result(workflow_id)

                    # Format and send result
                    await self._send_batch_workflow_result(result, slack_context, say)
                    break

                elif status["status"] == "FAILED":
                    # Send failure message
                    await self._send_workflow_failure(workflow_id, slack_context, say)
                    break

                elif status["status"] == "RUNNING":
                    # Update progress periodically (not every iteration to avoid rate limits)
                    if iteration_count - last_update_iteration >= update_frequency:
                        progress_info = status.get("progress", {})
                        processed = progress_info.get("processed", 0)
                        total = progress_info.get("total", 0)

                        if total > 0:
                            progress_text = f"Processing batch: {processed}/{total} items completed"
                        else:
                            progress_text = "Processing your batch request..."

                        await self._update_progress(slack_context, message_ts, progress_text)
                        last_update_iteration = iteration_count

                # Wait before next check
                await asyncio.sleep(check_interval)

            # Handle timeout if max iterations reached
            if iteration_count >= max_iterations:
                timeout_seconds = max_iterations * check_interval
                logger.warning(
                    f"Batch workflow monitoring timeout after {timeout_seconds}s",
                    extra={
                        "workflow_id": workflow_id,
                        "iterations": iteration_count,
                        "timeout_seconds": timeout_seconds,
                    },
                )

                await self._send_error_response(
                    slack_context,
                    say,
                    f"Batch workflow monitoring timed out after {timeout_seconds} seconds. "
                    f"The workflow may still be running. Please check back later.",
                )

        except Exception as e:
            logger.error(
                "Unexpected error monitoring batch workflow",
                extra={"workflow_id": workflow_id, "error": str(e), "error_type": "unexpected"},
                exc_info=True,
            )
            await self._send_error_response(
                slack_context,
                say,
                "An unexpected error occurred while monitoring your batch request.",
            )

    async def _send_batch_workflow_result(
        self, result: dict[str, Any], slack_context: SlackContext, say: Any
    ):
        """Send formatted batch workflow result to user."""
        try:
            processed = result.get("processed", 0)
            successful = result.get("successful", 0)
            failed = result.get("failed", 0)

            # Build result blocks
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "✅ Batch Processing Complete",
                        "emoji": True,
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Total Processed:*\n{processed}"},
                        {"type": "mrkdwn", "text": f"*Successful:*\n{successful}"},
                        {"type": "mrkdwn", "text": f"*Failed:*\n{failed}"},
                        {
                            "type": "mrkdwn",
                            "text": f"*Success Rate:*\n{(successful / processed * 100) if processed > 0 else 0:.1f}%",
                        },
                    ],
                },
            ]

            # Add summary of results if available
            if result.get("results"):
                blocks.append({"type": "divider"})
                blocks.append(
                    {"type": "section", "text": {"type": "mrkdwn", "text": "*Sample Results:*"}}
                )

            await say(
                text=f"Batch processing complete: {successful}/{processed} successful",
                thread_ts=slack_context.thread_ts,
                blocks=blocks,
            )

        except Exception as e:
            logger.error(f"Error sending batch workflow result: {e}", exc_info=True)
            await say(
                text="Batch processing complete. Results available.",
                thread_ts=slack_context.thread_ts,
            )


# Singleton instance
_slack_workflow_integration = None


async def get_slack_workflow_integration() -> SlackWorkflowIntegration:
    """Get or create Slack workflow integration singleton."""
    global _slack_workflow_integration
    if _slack_workflow_integration is None:
        from interfaces.slack.app import get_slack_app

        slack_app = await get_slack_app()
        _slack_workflow_integration = SlackWorkflowIntegration(slack_app)
        await _slack_workflow_integration.initialize()
    return _slack_workflow_integration
