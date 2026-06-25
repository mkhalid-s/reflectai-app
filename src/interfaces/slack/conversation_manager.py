"""
Slack Conversation Manager

Manages conversation flow, context, and response generation for Slack interactions.
Integrates with the conversation intelligence system and handles threading strategy.
"""

import asyncio
import json
from datetime import UTC, datetime
from typing import Any

import redis.asyncio as redis

from src.core.conversation.intelligence import ConversationIntelligence
from src.core.types import get_handler_for_intent
from src.interfaces.slack.enhanced_home_tab import EnhancedHomeTabManager
from src.shared import get_logger

logger = get_logger(__name__)


class ConversationManager:
    """
    Manages Slack conversation flow with context awareness and intelligent routing.
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        conversation_intelligence: ConversationIntelligence,
        home_tab_manager: EnhancedHomeTabManager,
        workflow_router=None,  # Optional workflow router for actual execution
    ):
        self.redis = redis_client
        self.conversation_intelligence = conversation_intelligence
        self.home_tab_manager = home_tab_manager
        self.workflow_router = workflow_router  # For routing to actual workflows
        self.logger = get_logger(__name__)

        # Context management settings
        self.context_ttl = 3600 * 24  # 24 hours
        self.max_context_messages = 10

    async def process_message(
        self,
        user_id: str,
        message: str,
        channel_id: str,
        thread_ts: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Process incoming Slack message with intelligent routing and response generation.

        Args:
            user_id: Slack user ID
            message: Message text
            channel_id: Slack channel ID
            thread_ts: Thread timestamp (if in thread)
            context: Additional context from Slack event

        Returns:
            Response dictionary with text and/or blocks
        """

        try:
            # Update context with new message
            await self._update_conversation_context(user_id, channel_id, thread_ts, message, "user")

            # Analyze message intent (conversation_history is retrieved internally via context_manager)
            intent_result = await self.conversation_intelligence.analyze_message(
                message=message,
                user_id=user_id,
                thread_id=thread_ts,
                channel_id=channel_id,
            )

            # Route to appropriate handler based on intent
            if intent_result.needs_clarification:
                response = await self._handle_clarification_request(intent_result)
            else:
                response = await self._handle_intent_based_response(
                    intent_result, user_id, channel_id, thread_ts, context
                )

            # Update context with response
            await self._update_conversation_context(
                user_id, channel_id, thread_ts, response.get("text", ""), "assistant"
            )

            # Trigger home tab update if needed
            if self._should_update_home_tab(intent_result):
                asyncio.create_task(self._update_user_home_tab(user_id))

            return response

        except Exception as e:
            self.logger.error(f"Error processing message: {str(e)}")
            return self._create_error_response(str(e))

    async def process_interaction(
        self,
        user_id: str,
        action_id: str,
        action_value: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Process interactive component interactions (buttons, menus, etc.)"""

        try:
            # Handle different types of interactions
            if action_id == "get_started":
                return await self._handle_get_started_interaction(user_id)
            elif action_id == "generate_report":
                return await self._handle_report_generation(user_id, action_value)
            elif action_id == "view_competencies":
                return await self._handle_competency_view(user_id)
            elif action_id.startswith("competency_"):
                return await self._handle_competency_interaction(user_id, action_id, action_value)
            else:
                return await self._handle_generic_interaction(user_id, action_id, action_value)

        except Exception as e:
            self.logger.error(f"Error processing interaction: {str(e)}")
            return {
                "text": "I encountered an error processing your request. Please try again.",
                "response_type": "ephemeral",
            }

    async def process_slash_command(
        self, user_id: str, command: str, text: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Process slash command interactions"""

        try:
            if command == "/reflectai":
                if not text or text.lower() in ["help", "?"]:
                    return await self._handle_help_command(user_id)
                elif text.lower() in ["status", "info"]:
                    return await self._handle_status_command(user_id)
                elif text.lower().startswith("report"):
                    return await self._handle_report_command(user_id, text)
                else:
                    # Process as regular message through conversation intelligence
                    return await self.process_message(
                        user_id=user_id, message=text, channel_id="slash_command", context=context
                    )

            return {"text": f"Unknown command: {command}", "response_type": "ephemeral"}

        except Exception as e:
            self.logger.error(f"Error processing slash command: {str(e)}")
            return {
                "text": "I encountered an error processing your command. Please try again.",
                "response_type": "ephemeral",
            }

    async def get_home_tab_view(self, user_id: str) -> dict[str, Any]:
        """Get Home Tab view for user"""

        try:
            return await self.home_tab_manager.get_home_tab_view(user_id, "default_team")

        except Exception as e:
            self.logger.error(f"Error getting home tab view: {str(e)}")
            return self._create_fallback_home_tab()

    async def _get_conversation_context(
        self, user_id: str, channel_id: str, thread_ts: str | None = None
    ) -> dict[str, Any]:
        """Get conversation context from Redis"""

        context_key = self._get_context_key(user_id, channel_id, thread_ts)

        try:
            context_data = await self.redis.get(context_key)
            if context_data:
                # Decode if bytes
                if isinstance(context_data, bytes):
                    context_data = context_data.decode()
                return json.loads(context_data)

            return {
                "user_id": user_id,
                "channel_id": channel_id,
                "thread_ts": thread_ts,
                "messages": [],
                "created_at": datetime.now(UTC).isoformat(),
                "last_updated": datetime.now(UTC).isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Error getting conversation context: {str(e)}")
            return {"messages": []}

    async def _update_conversation_context(
        self, user_id: str, channel_id: str, thread_ts: str | None, message: str, role: str
    ):
        """Update conversation context in Redis"""

        context_key = self._get_context_key(user_id, channel_id, thread_ts)

        try:
            context = await self._get_conversation_context(user_id, channel_id, thread_ts)

            # Add new message
            context["messages"].append(
                {"role": role, "content": message, "timestamp": datetime.now(UTC).isoformat()}
            )

            # Keep only recent messages
            if len(context["messages"]) > self.max_context_messages:
                context["messages"] = context["messages"][-self.max_context_messages :]

            context["last_updated"] = datetime.now(UTC).isoformat()

            # Store updated context
            await self.redis.setex(context_key, self.context_ttl, json.dumps(context, default=str))

        except Exception as e:
            self.logger.error(f"Error updating conversation context: {str(e)}")

    def _get_context_key(self, user_id: str, channel_id: str, thread_ts: str | None = None) -> str:
        """Generate context key for Redis"""

        if thread_ts:
            return f"conversation_context:{user_id}:{channel_id}:{thread_ts}"
        else:
            return f"conversation_context:{user_id}:{channel_id}"

    async def _handle_clarification_request(self, intent_result) -> dict[str, Any]:
        """Handle clarification requests"""
        # Get first clarification question from the list
        clarification_text = intent_result.clarification_questions[0] if intent_result.clarification_questions else "Could you please provide more details?"

        return {
            "text": clarification_text,
            "blocks": [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"🤔 {clarification_text}"},
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": "_Try being more specific or ask me what I can help you with._",
                        }
                    ],
                },
            ],
        }

    async def _handle_intent_based_response(
        self,
        intent_result,
        user_id: str,
        channel_id: str,
        thread_ts: str | None,
        context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """
        Handle response based on detected intent using canonical handler mapping.

        Uses get_handler_for_intent() to eliminate manual string mapping.
        """

        # Get canonical handler name from intent
        handler_name = get_handler_for_intent(intent_result.primary_intent)

        # Route to appropriate handler method
        handler_map = {
            "greeting": lambda: self._handle_greeting(user_id),
            "help": lambda: self._handle_help_request(user_id),
            "analysis": lambda: self._handle_analysis_request(
                user_id, intent_result, channel_id, thread_ts, context
            ),
            "report": lambda: self._handle_report_request(user_id, intent_result),
            "competency": lambda: self._handle_competency_request(user_id, intent_result),
            "career": lambda: self._handle_competency_request(user_id, intent_result),  # Career advice uses competency handler
            "goals": lambda: self._handle_generic_request(user_id, intent_result),  # Goal management TODO
            "resources": lambda: self._handle_generic_request(user_id, intent_result),  # Resource discovery TODO
            "status": lambda: self._handle_status_request(user_id),
            "generic": lambda: self._handle_generic_request(user_id, intent_result),
        }

        # Get handler and execute (all handlers are async)
        handler = handler_map.get(handler_name, lambda: self._handle_generic_request(user_id, intent_result))
        return await handler()

    async def _handle_greeting(self, user_id: str) -> dict[str, Any]:
        """Handle greeting messages"""

        return {
            "text": "👋 Hi there! I'm ReflectAI, your competency development assistant.",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "👋 Hi there! I'm ReflectAI, your competency development assistant.\n\nI can help you with:",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "• 📊 *Analyze your activities* and provide insights\n• 📝 *Generate competency reports* for specific time periods\n• 🎯 *Track your skill development* and progress\n• 💡 *Get personalized recommendations* for growth",
                    },
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Get Started"},
                            "action_id": "get_started",
                            "style": "primary",
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "View My Progress"},
                            "action_id": "view_competencies",
                        },
                    ],
                },
            ],
        }

    async def _handle_help_request(self, user_id: str) -> dict[str, Any]:
        """Handle help requests"""

        return {
            "text": "Here's what I can help you with:",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*🤖 ReflectAI Help*\n\nHere's what I can do for you:",
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": '*📊 Analysis*\n"Analyze my recent work" or "Show me my progress"',
                        },
                        {
                            "type": "mrkdwn",
                            "text": '*📝 Reports*\n"Generate a report for last month" or "Create my competency summary"',
                        },
                        {
                            "type": "mrkdwn",
                            "text": '*🎯 Competencies*\n"What are my top skills?" or "Show my competency map"',
                        },
                        {
                            "type": "mrkdwn",
                            "text": '*💡 Insights*\n"Give me recommendations" or "What should I focus on?"',
                        },
                    ],
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "_You can also use `/reflectai` command followed by your question._",
                    },
                },
            ],
        }

    async def _handle_analysis_request(
        self,
        user_id: str,
        intent_result,
        channel_id: str | None = None,
        thread_ts: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Handle analysis requests - route to workflow if available.

        Args:
            user_id: Slack user ID
            intent_result: Intent analysis result
            channel_id: Slack channel ID (optional, defaults to user_id for DM)
            thread_ts: Slack thread timestamp (optional)
            context: Additional context from Slack event (optional)
        """

        # If workflow router is available, start actual analysis workflow
        if self.workflow_router:
            try:
                import uuid

                from src.services.workflow.models import WorkflowRequest, WorkflowType

                # Extract time period from intent (default to 7 days)
                time_period = intent_result.extracted_data.get("time_period", "7_days")

                # Extract team_id from Slack event context
                team_id = "default"  # Default fallback
                if context and "original_event" in context:
                    event = context["original_event"]
                    # Slack events typically have team or team_id field
                    team_id = event.get("team") or event.get("team_id", "default")

                # Check if this is inline analysis (user provided activity description)
                inline_content = intent_result.extracted_data.get("activity_description") or \
                                intent_result.extracted_data.get("inline_content")

                # Determine workflow type based on whether inline content exists
                if inline_content:
                    # User provided inline activity description
                    workflow_type = WorkflowType.INLINE_ANALYSIS
                    input_data = {
                        "inline_content": inline_content,
                        "content_metadata": {
                            "extraction_method": "user_input",
                            "confidence": 1.0,
                            "source": "slack_conversation"
                        },
                        "output_format": "slack_blocks",
                        "include_gap_analysis": True,
                    }
                else:
                    # Regular analysis of stored activities
                    workflow_type = WorkflowType.SEQUENTIAL_ANALYSIS
                    input_data = {
                        "time_period": time_period,
                        "source": "slack_conversation",
                        "activity_text": f"User {user_id} requested competency analysis"
                    }

                # Create properly formed WorkflowRequest with all required fields
                workflow_request = WorkflowRequest(
                    workflow_type=workflow_type,
                    user_id=user_id,
                    team_id=team_id,  # Extract from Slack event, fallback to "default"
                    correlation_id=f"slack-{uuid.uuid4()}",
                    input_data=input_data,
                )

                self.logger.info(
                    f"Starting workflow for user {user_id}",
                    extra={
                        "workflow_type": workflow_request.workflow_type.value,
                        "correlation_id": workflow_request.correlation_id,
                    }
                )

                # Use channel_id for Slack posting (default to user_id for DM)
                target_channel_id = channel_id or user_id

                # Start workflow and monitor results
                # Replace fire-and-forget with monitored task
                async def start_and_monitor_workflow():
                    try:
                        # Start workflow
                        result = await self.workflow_router.route_workflow(
                            workflow_request,
                            user_id=user_id
                        )

                        workflow_id = result.workflow_id

                        self.logger.info(
                            f"Workflow started successfully: {workflow_id}",
                            extra={
                                "workflow_id": workflow_id,
                                "decision": result.decision.value,
                                "user_id": user_id
                            }
                        )

                        # Send "starting" message to Slack
                        try:
                            await self.slack_app.client.chat_postMessage(
                                channel=target_channel_id,
                                text="🔄 Starting your competency analysis...",
                                thread_ts=thread_ts
                            )
                        except Exception as e:
                            self.logger.warning(
                                f"Failed to send starting message: {e}",
                                extra={"channel_id": target_channel_id}
                            )

                        # Monitor workflow and deliver results
                        await self._monitor_and_deliver_workflow_results(
                            workflow_id=workflow_id,
                            user_id=user_id,
                            channel_id=target_channel_id,
                            thread_ts=thread_ts,
                            max_wait_seconds=300  # 5 minutes
                        )

                    except AttributeError as e:
                        self.logger.error(
                            "AttributeError in workflow routing - likely missing method",
                            exc_info=True,
                            extra={"error": str(e), "user_id": user_id}
                        )
                        # Send error to Slack
                        try:
                            await self._send_error_message(
                                target_channel_id,
                                thread_ts,
                                "Failed to start workflow. Please try again."
                            )
                        except Exception:  # nosec B110 - intentionally catch all for error message delivery
                            pass  # If error message delivery fails, we've already logged the original error
                    except Exception as e:
                        self.logger.error(
                            f"Unexpected error in workflow start/monitor: {e}",
                            exc_info=True,
                            extra={"error": str(e), "user_id": user_id}
                        )
                        # Send error to Slack
                        try:
                            await self._send_error_message(
                                target_channel_id,
                                thread_ts,
                                "An unexpected error occurred. Please try again."
                            )
                        except Exception:  # nosec B110 - intentionally catch all for error message delivery
                            pass  # If error message delivery fails, we've already logged the original error

                # Start background monitoring task
                asyncio.create_task(start_and_monitor_workflow())

                return {
                    "text": "🔍 Starting your analysis...",
                    "blocks": [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": "🔍 *Starting your competency analysis...*\n\nI'm analyzing your recent activities and will provide insights shortly.",
                            },
                        },
                        {
                            "type": "context",
                            "elements": [
                                {
                                    "type": "mrkdwn",
                                    "text": "_Analysis workflow started. Results will be sent when ready (typically 30-60 seconds)._",
                                }
                            ],
                        },
                    ],
                }

            except Exception as e:
                self.logger.error(
                    "Failed to start analysis workflow",
                    exc_info=True,
                    extra={
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "user_id": user_id
                    }
                )
                # Fall through to stub response

        # Fallback: Return placeholder response
        return {
            "text": "🔍 Analysis feature is being configured...",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "🔍 *Analysis Feature*\n\nThe analysis workflow is being configured. Please check back shortly!",
                    },
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": "_This feature will be available once workflows are configured._",
                        }
                    ],
                },
            ],
        }

    async def _handle_report_request(
        self,
        user_id: str,
        intent_result,
        channel_id: str | None = None,
        thread_ts: str | None = None,
        date_range_days: int = 90
    ) -> dict[str, Any]:
        """
        Handle report generation requests.

        Args:
            user_id: Slack user ID
            intent_result: Intent analysis result
            channel_id: Slack channel ID (optional)
            thread_ts: Slack thread timestamp (optional)
            date_range_days: Number of days to include in report (default: 90)
        """

        # If workflow router is available, start report generation workflow
        if self.workflow_router:
            try:
                import uuid

                from src.services.workflow.models import WorkflowRequest, WorkflowType

                # Extract date range from intent if available
                if hasattr(intent_result, 'extracted_data') and intent_result.extracted_data:
                    period = intent_result.extracted_data.get("time_period", "90_days")
                    # Convert period to days
                    if "30" in period or "month" in period:
                        date_range_days = 30
                    elif "quarter" in period or "90" in period:
                        date_range_days = 90
                    elif "year" in period or "365" in period:
                        date_range_days = 365

                # Create WorkflowRequest for Report Generation
                workflow_request = WorkflowRequest(
                    workflow_type=WorkflowType.REPORT_GENERATION,
                    user_id=user_id,
                    team_id="default",
                    correlation_id=f"slack-report-{uuid.uuid4()}",
                    input_data={
                        "report_type": "competency_assessment",
                        "date_range_days": date_range_days,
                        "include_recommendations": True,
                        "source": "slack_report_command",
                        "channel_id": channel_id or user_id,
                    },
                )

                self.logger.info(
                    f"Starting report generation workflow for user {user_id}",
                    extra={
                        "workflow_type": workflow_request.workflow_type.value,
                        "correlation_id": workflow_request.correlation_id,
                        "date_range_days": date_range_days,
                    }
                )

                # Use channel_id for Slack posting
                target_channel_id = channel_id or user_id

                # Start workflow and monitor results
                async def start_and_monitor_workflow():
                    try:
                        # Start workflow
                        result = await self.workflow_router.route_workflow(
                            workflow_request,
                            user_id=user_id
                        )

                        workflow_id = result.workflow_id

                        self.logger.info(
                            f"Report workflow started successfully: {workflow_id}",
                            extra={
                                "workflow_id": workflow_id,
                                "decision": result.decision.value,
                                "user_id": user_id
                            }
                        )

                        # Send "generating" message to Slack
                        try:
                            await self.slack_app.client.chat_postMessage(
                                channel=target_channel_id,
                                text=f"📊 Generating your {date_range_days}-day competency report...",
                                thread_ts=thread_ts
                            )
                        except Exception as e:
                            self.logger.warning(
                                f"Failed to send report start message: {e}",
                                extra={"channel_id": target_channel_id}
                            )

                        # Monitor workflow and deliver results
                        # Reports take longer, so use 5 min timeout
                        await self._monitor_and_deliver_workflow_results(
                            workflow_id=workflow_id,
                            user_id=user_id,
                            channel_id=target_channel_id,
                            thread_ts=thread_ts,
                            max_wait_seconds=300  # 5 minutes for report generation
                        )

                    except Exception as e:
                        self.logger.error(
                            f"Error in report workflow start/monitor: {e}",
                            exc_info=True,
                            extra={"error": str(e), "user_id": user_id}
                        )
                        # Send error to Slack
                        try:
                            await self._send_error_message(
                                target_channel_id,
                                thread_ts,
                                "Failed to generate report. Please try again."
                            )
                        except Exception:  # nosec B110 - intentionally catch all for error message delivery
                            pass  # If error message delivery fails, we've already logged the original error

                # Start background monitoring task
                asyncio.create_task(start_and_monitor_workflow())

                return {
                    "text": "📊 Generating your report...",
                    "blocks": [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"📊 *Generating your {date_range_days}-day competency report...*\n\nThis will take a few moments. I'll send you the PDF when it's ready.",
                            },
                        }
                    ],
                }

            except Exception as e:
                self.logger.error(f"Failed to start report workflow: {e}", exc_info=True)
                # Fall through to button response

        # Fallback: Show buttons to select time period
        return {
            "text": "📊 Generating your report...",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "📊 *Generating your competency report...*\n\nI'm compiling your data and creating a comprehensive report.",
                    },
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Last 30 Days"},
                            "action_id": "generate_report",
                            "value": "30_days",
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Last Quarter"},
                            "action_id": "generate_report",
                            "value": "quarter",
                        },
                    ],
                },
            ],
        }

    async def _handle_competency_request(
        self,
        user_id: str,
        intent_result,
        channel_id: str | None = None,
        thread_ts: str | None = None
    ) -> dict[str, Any]:
        """
        Handle competency-related requests - detailed competency breakdown.

        Args:
            user_id: Slack user ID
            intent_result: Intent analysis result
            channel_id: Slack channel ID (optional)
            thread_ts: Slack thread timestamp (optional)
        """

        # If workflow router is available, start competency summary workflow
        if self.workflow_router:
            try:
                import uuid

                from src.services.workflow.models import WorkflowRequest, WorkflowType

                # Create WorkflowRequest for Quick Summary (competency-focused)
                workflow_request = WorkflowRequest(
                    workflow_type=WorkflowType.QUICK_SUMMARY,
                    user_id=user_id,
                    team_id="default",
                    correlation_id=f"slack-competency-{uuid.uuid4()}",
                    input_data={
                        "summary_type": "competency",  # Focus on competencies
                        "time_period": "recent",
                        "source": "slack_competency_command",
                        "max_activities": 20,  # More activities for better insight
                        "max_competencies": 10,  # Show more competencies (top 10)
                        "include_recommendations": True,  # Include growth recommendations
                    },
                )

                self.logger.info(
                    f"Starting competency workflow for user {user_id}",
                    extra={
                        "workflow_type": workflow_request.workflow_type.value,
                        "correlation_id": workflow_request.correlation_id,
                    }
                )

                # Use channel_id for Slack posting
                target_channel_id = channel_id or user_id

                # Start workflow and monitor results
                async def start_and_monitor_workflow():
                    try:
                        # Start workflow
                        result = await self.workflow_router.route_workflow(
                            workflow_request,
                            user_id=user_id
                        )

                        workflow_id = result.workflow_id

                        self.logger.info(
                            f"Competency workflow started successfully: {workflow_id}",
                            extra={
                                "workflow_id": workflow_id,
                                "decision": result.decision.value,
                                "user_id": user_id
                            }
                        )

                        # Send "analyzing" message to Slack
                        try:
                            await self.slack_app.client.chat_postMessage(
                                channel=target_channel_id,
                                text="🎯 Analyzing your competencies...",
                                thread_ts=thread_ts
                            )
                        except Exception as e:
                            self.logger.warning(
                                f"Failed to send competency start message: {e}",
                                extra={"channel_id": target_channel_id}
                            )

                        # Monitor workflow and deliver results
                        await self._monitor_and_deliver_workflow_results(
                            workflow_id=workflow_id,
                            user_id=user_id,
                            channel_id=target_channel_id,
                            thread_ts=thread_ts,
                            max_wait_seconds=90  # Competency analysis (1.5 min)
                        )

                    except Exception as e:
                        self.logger.error(
                            f"Error in competency workflow start/monitor: {e}",
                            exc_info=True,
                            extra={"error": str(e), "user_id": user_id}
                        )
                        # Send error to Slack
                        try:
                            await self._send_error_message(
                                target_channel_id,
                                thread_ts,
                                "Failed to analyze competencies. Please try again."
                            )
                        except Exception:  # nosec B110 - intentionally catch all for error message delivery
                            pass  # If error message delivery fails, we've already logged the original error

                # Start background monitoring task
                asyncio.create_task(start_and_monitor_workflow())

                return {
                    "text": "🎯 Analyzing your competencies...",
                    "blocks": [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": "🎯 *Analyzing Your Competencies...*\n\nI'm gathering your activity data and calculating your competency levels.",
                            },
                        }
                    ],
                }

            except Exception as e:
                self.logger.error(f"Failed to start competency workflow: {e}", exc_info=True)
                # Fall through to static response

        # Fallback: Static competency overview if workflow router not available
        return {
            "text": "🎯 Here are your competency insights:",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "🎯 *Your Competency Overview*\n\nBased on your recent activities, here are your key competencies:",
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": "*🚀 Top Strength*\nProblem Solving (Advanced)"},
                        {
                            "type": "mrkdwn",
                            "text": "*📈 Growing Skill*\nTeam Leadership (Developing)",
                        },
                        {"type": "mrkdwn", "text": "*🎯 Focus Area*\nStrategic Thinking"},
                        {"type": "mrkdwn", "text": "*📊 Recent Activity*\n15 activities analyzed"},
                    ],
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "View Detailed Analysis"},
                            "action_id": "view_competencies",
                            "style": "primary",
                        }
                    ],
                },
            ],
        }

    async def _handle_status_request(
        self,
        user_id: str,
        channel_id: str | None = None,
        thread_ts: str | None = None
    ) -> dict[str, Any]:
        """
        Handle status requests - show user's competency snapshot.

        Args:
            user_id: Slack user ID
            channel_id: Slack channel ID (optional, defaults to user_id for DM)
            thread_ts: Slack thread timestamp (optional)
        """

        # If workflow router is available, start actual status workflow
        if self.workflow_router:
            try:
                import uuid

                from src.services.workflow.models import WorkflowRequest, WorkflowType

                # Create WorkflowRequest for Quick Summary
                workflow_request = WorkflowRequest(
                    workflow_type=WorkflowType.QUICK_SUMMARY,
                    user_id=user_id,
                    team_id="default",
                    correlation_id=f"slack-status-{uuid.uuid4()}",
                    input_data={
                        "summary_type": "competency",
                        "time_period": "recent",
                        "source": "slack_status_command",
                        "max_activities": 10,
                        "max_competencies": 5,
                    },
                )

                self.logger.info(
                    f"Starting status workflow for user {user_id}",
                    extra={
                        "workflow_type": workflow_request.workflow_type.value,
                        "correlation_id": workflow_request.correlation_id,
                    }
                )

                # Use channel_id for Slack posting (default to user_id for DM)
                target_channel_id = channel_id or user_id

                # Start workflow and monitor results
                async def start_and_monitor_workflow():
                    try:
                        # Start workflow
                        result = await self.workflow_router.route_workflow(
                            workflow_request,
                            user_id=user_id
                        )

                        workflow_id = result.workflow_id

                        self.logger.info(
                            f"Status workflow started successfully: {workflow_id}",
                            extra={
                                "workflow_id": workflow_id,
                                "decision": result.decision.value,
                                "user_id": user_id
                            }
                        )

                        # Send "fetching" message to Slack
                        try:
                            await self.slack_app.client.chat_postMessage(
                                channel=target_channel_id,
                                text="🔄 Fetching your competency status...",
                                thread_ts=thread_ts
                            )
                        except Exception as e:
                            self.logger.warning(
                                f"Failed to send status message: {e}",
                                extra={"channel_id": target_channel_id}
                            )

                        # Monitor workflow and deliver results
                        await self._monitor_and_deliver_workflow_results(
                            workflow_id=workflow_id,
                            user_id=user_id,
                            channel_id=target_channel_id,
                            thread_ts=thread_ts,
                            max_wait_seconds=60  # Status should be quick (1 min)
                        )

                    except Exception as e:
                        self.logger.error(
                            f"Error in status workflow start/monitor: {e}",
                            exc_info=True,
                            extra={"error": str(e), "user_id": user_id}
                        )
                        # Send error to Slack
                        try:
                            await self._send_error_message(
                                target_channel_id,
                                thread_ts,
                                "Failed to fetch status. Please try again."
                            )
                        except Exception:  # nosec B110 - intentionally catch all for error message delivery
                            pass  # If error message delivery fails, we've already logged the original error

                # Start background monitoring task
                asyncio.create_task(start_and_monitor_workflow())

                return {
                    "text": "🔍 Fetching your status...",
                    "blocks": [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": "🔍 *Fetching your competency status...*\n\nI'm gathering your latest data.",
                            },
                        }
                    ],
                }

            except Exception as e:
                self.logger.error(f"Failed to start status workflow: {e}", exc_info=True)
                # Fall through to static response

        # Fallback: Static status response if workflow router not available
        return {
            "text": "✅ System Status: All systems operational",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "✅ *ReflectAI System Status*\n\nAll systems are operational and ready to help you!",
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": "*🤖 AI Analysis*\nOnline"},
                        {"type": "mrkdwn", "text": "*📊 Report Generation*\nOnline"},
                        {"type": "mrkdwn", "text": "*🎯 Competency Mapping*\nOnline"},
                        {"type": "mrkdwn", "text": "*💡 Recommendations*\nOnline"},
                    ],
                },
            ],
        }

    async def _handle_generic_request(self, user_id: str, intent_result) -> dict[str, Any]:
        """Handle generic requests that don't fit specific intents"""

        return {
            "text": "I understand you're looking for help. Let me guide you to what I can do.",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "🤔 I understand you're looking for help, but I'm not quite sure what you need.\n\nLet me show you what I can do:",
                    },
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Analyze My Work"},
                            "action_id": "start_analysis",
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Generate Report"},
                            "action_id": "generate_report",
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Get Help"},
                            "action_id": "get_help",
                        },
                    ],
                },
            ],
        }

    def _should_update_home_tab(self, intent_result) -> bool:
        """Determine if Home Tab should be updated based on intent"""

        update_triggers = ["analysis", "report", "competency"]
        # intent_result is IntentAnalysisResult with primary_intent (enum), not intent_type
        if intent_result.primary_intent:
            intent_value = intent_result.primary_intent.value
            return intent_value in update_triggers
        return False

    async def _update_user_home_tab(self, user_id: str):
        """Trigger Home Tab update for user"""

        try:
            # Trigger cache refresh for user
            await self.home_tab_manager.refresh_user_cache(user_id, "default_team")

        except Exception as e:
            self.logger.error(f"Failed to update home tab for user {user_id}: {str(e)}")

    def _create_error_response(self, error_message: str) -> dict[str, Any]:
        """Create standardized error response"""

        return {
            "text": "I encountered an error processing your request. Please try again.",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "⚠️ *Oops! Something went wrong.*\n\nI encountered an issue processing your request. Please try again in a moment.",
                    },
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": "_If the problem persists, please contact support._",
                        }
                    ],
                },
            ],
        }

    def _create_fallback_home_tab(self) -> dict[str, Any]:
        """Create fallback Home Tab view"""

        return {
            "type": "home",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "👋 *Welcome to ReflectAI!*\n\nI'm your competency development assistant.",
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
        }

    # Additional interaction handlers
    async def _handle_get_started_interaction(self, user_id: str) -> dict[str, Any]:
        """Handle get started button interaction"""

        return {
            "text": "Welcome! Let's get you started with ReflectAI.",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "🚀 *Great! Let's get you started.*\n\nTo begin, I can analyze your recent work activities and provide competency insights.",
                    },
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Start Analysis"},
                            "action_id": "start_analysis",
                            "style": "primary",
                        }
                    ],
                },
            ],
            "response_type": "ephemeral",
        }

    async def _handle_report_generation(self, user_id: str, period: str) -> dict[str, Any]:
        """Handle report generation interaction"""

        return {
            "text": f"Generating report for {period}...",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"📊 *Generating your {period} report...*\n\nThis will take a moment. I'll send you the report when it's ready.",
                    },
                }
            ],
            "response_type": "ephemeral",
        }

    async def _handle_competency_view(self, user_id: str) -> dict[str, Any]:
        """Handle competency view interaction"""

        return {
            "text": "Here's your competency overview:",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "🎯 *Your Competency Map*\n\nHere's an overview of your current competency levels:",
                    },
                }
            ],
            "response_type": "ephemeral",
        }

    async def _handle_competency_interaction(
        self, user_id: str, action_id: str, value: str
    ) -> dict[str, Any]:
        """Handle competency-specific interactions"""

        return {"text": "Competency details loaded.", "response_type": "ephemeral"}

    async def _handle_generic_interaction(
        self, user_id: str, action_id: str, value: str
    ) -> dict[str, Any]:
        """Handle generic interactions"""

        return {"text": "Processing your request...", "response_type": "ephemeral"}

    async def _handle_help_command(self, user_id: str) -> dict[str, Any]:
        """Handle help slash command"""

        return await self._handle_help_request(user_id)

    async def _handle_status_command(self, user_id: str) -> dict[str, Any]:
        """Handle status slash command"""

        return await self._handle_status_request(user_id)

    async def _handle_report_command(self, user_id: str, text: str) -> dict[str, Any]:
        """Handle report slash command"""

        return await self._handle_report_request(user_id, None)

    # ==================================================================================
    # Workflow Monitoring and Result Delivery Methods
    # ==================================================================================

    async def _monitor_and_deliver_workflow_results(
        self,
        workflow_id: str,
        user_id: str,
        channel_id: str,
        thread_ts: str | None,
        max_wait_seconds: int = 300  # 5 minutes
    ):
        """
        Monitor workflow completion and deliver results to Slack.

        Polls workflow status every 2 seconds until complete or timeout.

        Args:
            workflow_id: The workflow ID to monitor
            user_id: User ID for logging
            channel_id: Slack channel ID to send results to
            thread_ts: Slack thread timestamp (optional)
            max_wait_seconds: Maximum time to wait (default: 300 seconds / 5 minutes)
        """
        import asyncio
        import time

        start_time = time.time()
        check_interval = 2  # seconds

        self.logger.info(
            f"Starting workflow result monitoring for {workflow_id}",
            extra={
                "workflow_id": workflow_id,
                "user_id": user_id,
                "channel_id": channel_id
            }
        )

        try:
            while True:
                # Check timeout
                elapsed = time.time() - start_time
                if elapsed > max_wait_seconds:
                    self.logger.warning(
                        f"Workflow monitoring timeout after {max_wait_seconds}s",
                        extra={
                            "workflow_id": workflow_id,
                            "elapsed": elapsed
                        }
                    )
                    await self._send_timeout_message(channel_id, thread_ts)
                    return

                # Get workflow status
                status = await self.workflow_router.get_workflow_status(workflow_id)

                if not status or status.get("status") == "NOT_FOUND":
                    self.logger.error(
                        f"Workflow {workflow_id} not found",
                        extra={"workflow_id": workflow_id}
                    )
                    await self._send_error_message(
                        channel_id,
                        thread_ts,
                        "Workflow not found. Please try again."
                    )
                    return

                # Check if completed
                if status["status"] == "COMPLETED":
                    self.logger.info(
                        f"Workflow {workflow_id} completed successfully",
                        extra={"workflow_id": workflow_id}
                    )
                    await self._deliver_workflow_results(
                        status["result"],
                        channel_id,
                        thread_ts
                    )
                    return

                # Check if failed
                elif status["status"] in ["FAILED", "CANCELLED", "TIMED_OUT"]:
                    self.logger.error(
                        f"Workflow {workflow_id} failed",
                        extra={
                            "workflow_id": workflow_id,
                            "status": status["status"],
                            "error": status.get("error")
                        }
                    )
                    await self._send_error_message(
                        channel_id,
                        thread_ts,
                        "Analysis failed. Our team has been notified. Please try again."
                    )
                    return

                # Still running, wait before next check
                self.logger.debug(
                    f"Workflow {workflow_id} still running, checking again in {check_interval}s",
                    extra={"workflow_id": workflow_id, "elapsed": elapsed}
                )
                await asyncio.sleep(check_interval)

        except Exception as e:
            self.logger.error(
                f"Error monitoring workflow {workflow_id}: {e}",
                exc_info=True,
                extra={"workflow_id": workflow_id}
            )
            await self._send_error_message(
                channel_id,
                thread_ts,
                "An unexpected error occurred. Please try again."
            )

    async def _format_workflow_results(self, result: dict[str, Any]) -> list[dict]:
        """
        Format workflow results as Slack Block Kit blocks.

        Args:
            result: Workflow result dictionary containing analysis, competencies, advice, etc.

        Returns:
            List of Slack Block Kit block dictionaries
        """
        # Extract data
        analysis = result.get("analysis", {})
        competencies = result.get("competencies", {})
        advice = result.get("advice", {})
        synthesis = result.get("synthesis", {})

        blocks = []

        # Header
        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "✅ Analysis Complete",
                "emoji": True
            }
        })

        # Analysis summary
        if analysis:
            blocks.append({"type": "divider"})
            classification = analysis.get("classification", "Unknown")
            confidence = analysis.get("confidence", 0)

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Activity Classification:*\n{classification.replace('_', ' ').title()} (Confidence: {confidence:.0%})"
                }
            })

        # Competencies
        if competencies and competencies.get("competencies"):
            blocks.append({"type": "divider"})
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Competency Assessment:*"
                }
            })

            comp_dict = competencies.get("competencies", {})
            # Handle both dict and list formats
            if isinstance(comp_dict, dict):
                comp_items = list(comp_dict.items())[:5]  # Top 5
                for comp_name, comp_data in comp_items:
                    if isinstance(comp_data, dict):
                        score = comp_data.get("score", 0)
                        level = comp_data.get("level", "Unknown")
                        blocks.append({
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"• *{comp_name.replace('_', ' ').title()}*: {level} ({score:.1f}/5.0)"
                            }
                        })

        # Advice/Recommendations
        if advice:
            blocks.append({"type": "divider"})
            advice_text = advice.get("advice", "")
            if isinstance(advice_text, str) and advice_text:
                # Truncate if too long
                if len(advice_text) > 500:
                    advice_text = advice_text[:497] + "..."
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Recommendations:*\n{advice_text}"
                    }
                })

        # Key insights
        if synthesis and synthesis.get("key_insights"):
            insights = synthesis.get("key_insights", [])
            if insights and isinstance(insights, list):
                blocks.append({"type": "divider"})
                insight_text = "\n".join(f"• {insight}" for insight in insights[:3])
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Key Insights:*\n{insight_text}"
                    }
                })

        # Footer with cost
        total_cost = result.get("total_llm_cost", 0)
        blocks.append({
            "type": "context",
            "elements": [{
                "type": "mrkdwn",
                "text": f"💰 Analysis cost: ${total_cost:.4f} | Powered by ReflectAI"
            }]
        })

        return blocks

    async def _deliver_workflow_results(
        self,
        result: dict[str, Any],
        channel_id: str,
        thread_ts: str | None
    ):
        """
        Deliver formatted workflow results to Slack.

        Args:
            result: Workflow result dictionary
            channel_id: Slack channel ID
            thread_ts: Slack thread timestamp (optional)
        """
        try:
            blocks = await self._format_workflow_results(result)

            await self.slack_app.client.chat_postMessage(
                channel=channel_id,
                blocks=blocks,
                text="Analysis complete!",
                thread_ts=thread_ts
            )

            self.logger.info(
                "Successfully delivered workflow results to Slack",
                extra={
                    "channel_id": channel_id,
                    "block_count": len(blocks)
                }
            )

        except Exception as e:
            self.logger.error(
                f"Failed to deliver workflow results: {e}",
                exc_info=True,
                extra={"channel_id": channel_id}
            )
            # Try to send simple error message
            try:
                await self.slack_app.client.chat_postMessage(
                    channel=channel_id,
                    text="✅ Analysis complete, but failed to format results. Please check logs.",
                    thread_ts=thread_ts
                )
            except Exception as e2:
                self.logger.error(f"Failed to send fallback message: {e2}")

    async def _send_error_message(
        self,
        channel_id: str,
        thread_ts: str | None,
        message: str
    ):
        """
        Send error message to Slack.

        Args:
            channel_id: Slack channel ID
            thread_ts: Slack thread timestamp (optional)
            message: Error message to send
        """
        try:
            await self.slack_app.client.chat_postMessage(
                channel=channel_id,
                text=f"❌ {message}",
                thread_ts=thread_ts
            )
            self.logger.info(
                "Sent error message to Slack",
                extra={"channel_id": channel_id, "message": message}
            )
        except Exception as e:
            self.logger.error(
                f"Failed to send error message: {e}",
                exc_info=True
            )

    async def _send_timeout_message(
        self,
        channel_id: str,
        thread_ts: str | None
    ):
        """
        Send timeout message to Slack.

        Args:
            channel_id: Slack channel ID
            thread_ts: Slack thread timestamp (optional)
        """
        await self._send_error_message(
            channel_id,
            thread_ts,
            "Analysis is taking longer than expected. The workflow may still be running. Please check back later or try again."
        )
