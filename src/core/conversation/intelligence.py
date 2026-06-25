"""
Conversation Intelligence System

Implements  Sophisticated LLM-powered intent analysis, conversation
context management, and intelligent clarification system.
"""

from datetime import UTC, datetime
from typing import Any

from src.core.classification.intent_analyzer import IntentAnalyzer, IntentClassificationResult
from src.core.types import is_informational_intent
from src.shared import ErrorCategory, ErrorSeverity, ReflectAIError, get_logger

from .clarification_generator import ClarificationGenerator
from .context_manager import ConversationContextManager
from .types import ConversationContext, ConversationStage

logger = get_logger(__name__)


class ConversationIntelligence:
    """
    Main conversation intelligence system coordinating all components.

    Implements Requirements:
    - 30.1: LLM-powered intent analysis
    - 30.2: Conversation context management
    - 30.3: Intelligent clarification system
    - 30.4: Conversation state persistence
    - 30.5: Conversation analytics
    """

    def __init__(self, redis_client=None):
        self.intent_analyzer = IntentAnalyzer()
        self.context_manager = ConversationContextManager(redis_client)
        self.clarification_generator = ClarificationGenerator()
        # Tiered confidence thresholds
        self.actionable_confidence_threshold = 0.7  # For actions that trigger workflows
        self.informational_confidence_threshold = 0.15  # For greetings, help, status (matches pattern threshold)

    async def analyze_message(
        self,
        message: str,
        user_id: str,
        thread_id: str | None = None,
        channel_id: str | None = None,
    ) -> IntentClassificationResult:
        """
        Analyze user message with conversation context.

        Args:
            message: User's message text
            user_id: Slack user ID
            thread_id: Slack thread timestamp (if threaded conversation)
            channel_id: Slack channel ID

        Returns:
            Intent analysis result with routing decision
        """
        try:
            # Get or create conversation context
            context = await self.context_manager.get_context(user_id=user_id, thread_id=thread_id)

            # Analyze intent with conversation context
            intent_result = await self.intent_analyzer.analyze_intent(
                user_input=message,
                user_context={"user_id": user_id, "profile": await self._get_user_profile(user_id), "stage": context.stage},
                conversation_history=context.message_history,
                agent_context=None,  # TODO: Pass agent context for LLM-based classification
            )

            # Update conversation context
            await self._update_conversation_context(context, message, intent_result)

            # Generate clarification if needed (use tiered thresholds)
            threshold = (
                self.informational_confidence_threshold
                if is_informational_intent(intent_result.primary_intent)
                else self.actionable_confidence_threshold
            )

            if intent_result.confidence < threshold:
                clarification = await self.clarification_generator.generate_clarification(
                    message=message, context=context, partial_intent=intent_result.primary_intent
                )
                # Append to existing clarification questions list
                intent_result.clarification_questions.append(clarification)
                intent_result.needs_clarification = True
            else:
                # Confidence is sufficient, don't request clarification
                intent_result.needs_clarification = False

            # Log conversation analytics
            await self._log_conversation_metrics(user_id, intent_result, context)

            return intent_result

        except Exception as e:
            logger.error(
                "Conversation intelligence analysis failed",
                extra={"user_id": user_id, "thread_id": thread_id, "error": str(e)},
            )
            raise ReflectAIError(
                message="Failed to analyze conversation",
                error_code="CONVERSATION_ANALYSIS_FAILED",
                category=ErrorCategory.BUSINESS_RULE_ERROR,
                severity=ErrorSeverity.ERROR,
                context={"user_id": user_id, "error": str(e)},
            ) from e

    async def update_conversation_stage(
        self,
        user_id: str,
        thread_id: str | None,
        new_stage: ConversationStage,
        additional_context: dict[str, Any] | None = None,
    ):
        """Update conversation stage and context."""
        try:
            context = await self.context_manager.get_context(user_id, thread_id)
            context.stage = new_stage
            context.last_updated = datetime.now(UTC)

            if additional_context:
                context.pending_actions.extend(additional_context.get("actions", []))
                context.mentioned_activities.extend(additional_context.get("activities", []))

            await self.context_manager.update_context(context)

        except Exception as e:
            logger.error(
                "Failed to update conversation stage",
                extra={
                    "user_id": user_id,
                    "thread_id": thread_id,
                    "new_stage": new_stage,
                    "error": str(e),
                },
            )

    async def get_conversation_summary(self, user_id: str, thread_id: str | None) -> dict[str, Any]:
        """Get conversation summary for handoff to agents."""
        try:
            context = await self.context_manager.get_context(user_id, thread_id)

            return {
                "stage": context.stage,
                "intent": context.intent,
                "confidence": context.intent_confidence,
                "context_summary": context.context_summary,
                "mentioned_activities": context.mentioned_activities,
                "pending_actions": context.pending_actions,
                "message_count": len(context.message_history),
            }

        except Exception as e:
            logger.error(
                "Failed to get conversation summary",
                extra={"user_id": user_id, "thread_id": thread_id, "error": str(e)},
            )
            return {}

    async def cleanup_expired_conversations(self):
        """Clean up expired conversation contexts."""
        try:
            cleaned_count = await self.context_manager.cleanup_expired()
            logger.info("Cleaned up expired conversations", extra={"cleaned_count": cleaned_count})
            return cleaned_count

        except Exception as e:
            logger.error("Failed to cleanup expired conversations", extra={"error": str(e)})
            return 0

    async def _update_conversation_context(
        self, context: ConversationContext, message: str, intent_result
    ):
        """Update conversation context with new message and analysis."""
        # Add message to history
        context.message_history.append(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "message": message,
                "intent": intent_result.primary_intent.value if intent_result.primary_intent else None,
                "confidence": intent_result.confidence,
            }
        )

        # Limit message history to last 20 messages (Task 27d requirement)
        if len(context.message_history) > 20:
            # Keep last 5 messages + create summary of earlier messages
            recent_messages = context.message_history[-5:]
            older_messages = context.message_history[:-5]

            # Create summary of older messages
            summary = await self._summarize_conversation_history(older_messages)
            context.context_summary = summary
            context.message_history = recent_messages

        # Update context metadata
        context.intent = intent_result.primary_intent
        context.intent_confidence = intent_result.confidence
        context.last_updated = datetime.now(UTC)

        # Extract mentioned activities and actions
        extracted = intent_result.extracted_content or {}
        context.mentioned_activities.extend(extracted.get("activities", []))
        context.pending_actions.extend(extracted.get("actions", []))

        # Update context in storage
        await self.context_manager.update_context(context)

    async def _summarize_conversation_history(self, messages: list[dict[str, Any]]) -> str:
        """Summarize conversation history using Analysis Agent."""
        try:
            # Use claude-3-5-haiku for cost-effective summarization
            from src.core.agents.analysis_agent import AnalysisAgent

            analysis_agent = AnalysisAgent()

            # Format messages for summarization
            conversation_text = "\n".join([f"User: {msg['message']}" for msg in messages])

            summary_prompt = f"""
            Summarize this conversation history, preserving key context:
            - Work activities mentioned
            - Competency areas discussed
            - User goals and preferences
            - Action items or requests

            Conversation:
            {conversation_text}

            Provide a concise summary (max 200 words):
            """

            result = await analysis_agent.process_simple_request(summary_prompt)
            return result.get("summary", "Previous conversation about work activities")

        except Exception as e:
            logger.error("Failed to summarize conversation history", extra={"error": str(e)})
            return "Previous conversation context (summarization failed)"

    async def _get_user_profile(self, user_id: str) -> dict[str, Any]:
        """Get user profile for intent analysis context."""
        try:
            # This would integrate with user profile service
            # For now, return basic profile structure
            return {
                "user_id": user_id,
                "role": "unknown",
                "department": "unknown",
                "experience_level": "unknown",
                "preferences": {},
            }
        except Exception as e:
            logger.error("Failed to get user profile", extra={"user_id": user_id, "error": str(e)})
            return {"user_id": user_id}

    async def _log_conversation_metrics(
        self, user_id: str, intent_result: IntentClassificationResult, context: ConversationContext
    ):
        """Log conversation analytics metrics."""
        try:
            metrics = {
                "user_id": user_id,
                "intent": intent_result.primary_intent.value if intent_result.primary_intent else None,
                "confidence": intent_result.confidence,
                "needs_clarification": intent_result.needs_clarification,
                "conversation_stage": context.stage.value if context.stage else None,
                "message_count": len(context.message_history),
                "timestamp": datetime.now(UTC).isoformat(),
            }

            logger.info("Conversation analytics", extra=metrics)

            # This would integrate with metrics collection
            # await self.metrics_collector.record_conversation_event(metrics)

        except Exception as e:
            logger.error(
                "Failed to log conversation metrics", extra={"user_id": user_id, "error": str(e)}
            )
