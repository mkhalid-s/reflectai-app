"""
Proactive DM Intelligent Detection System for ReflectAI

Implements  Intelligent Clarification System with:
- IntentAnalyzer with confidence threshold of 0.7
- ClarificationGenerator with contextual response templates
- ConversationContextManager with Redis-based state storage (5min TTL)
- Smart follow-up questions per intent category
- Proactive assistance and conversation intelligence
"""

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from src.core.llm import LLMRequest, ModelTier, get_llm_gateway
from src.infrastructure.cache.redis_manager import get_redis_manager
from src.infrastructure.monitoring import get_or_create_correlation_id
from src.shared import get_logger

logger = get_logger(__name__)


class IntentCategory(str, Enum):
    """Intent categories for conversation classification."""

    COMPETENCY_ANALYSIS = "competency_analysis"
    REPORT_REQUEST = "report_request"
    HELP_SEEKING = "help_seeking"
    GREETING = "greeting"
    FEEDBACK = "feedback"
    STATUS_INQUIRY = "status_inquiry"
    CLARIFICATION = "clarification"
    SMALL_TALK = "small_talk"
    UNKNOWN = "unknown"


class ConversationPhase(str, Enum):
    """Phases of conversation flow."""

    INITIAL_CONTACT = "initial_contact"
    INTENT_GATHERING = "intent_gathering"
    PARAMETER_COLLECTION = "parameter_collection"
    PROCESSING = "processing"
    FOLLOW_UP = "follow_up"
    COMPLETE = "complete"


@dataclass
class IntentAnalysisResult:
    """Result of intent analysis."""

    intent: IntentCategory
    confidence: float
    extracted_entities: dict[str, Any] = field(default_factory=dict)
    suggested_actions: list[str] = field(default_factory=list)
    clarification_needed: bool = False
    reasoning: str = ""


@dataclass
class ConversationContext:
    """Context for ongoing conversation."""

    user_id: str
    conversation_id: str
    phase: ConversationPhase
    primary_intent: IntentCategory | None = None
    collected_parameters: dict[str, Any] = field(default_factory=dict)
    message_history: list[dict[str, Any]] = field(default_factory=list)
    last_interaction: datetime = field(default_factory=datetime.utcnow)
    clarification_attempts: int = 0
    max_clarification_attempts: int = 3
    metadata: dict[str, Any] = field(default_factory=dict)


class IntentAnalyzer:
    """
    LLM-powered intent analyzer with confidence threshold.

    Features:
    - Confidence threshold of 0.7 for reliable classification
    - Entity extraction from user messages
    - Context-aware intent detection
    - Multi-turn conversation understanding
    """

    def __init__(self, confidence_threshold: float = 0.7):
        self.confidence_threshold = confidence_threshold
        self.llm_gateway = get_llm_gateway()

        # Intent patterns for quick classification
        self.intent_patterns = {
            IntentCategory.COMPETENCY_ANALYSIS: [
                r"\b(analy[sz]e|competenc|skill|assessment|evaluation)\b",
                r"\b(how.*doing|performance|strength|weakness)\b",
                r"\b(improve|develop|grow|learning)\b",
            ],
            IntentCategory.REPORT_REQUEST: [
                r"\b(report|summary|overview|document)\b",
                r"\b(generate|create|make|give.*report)\b",
                r"\b(download|export|send.*report)\b",
            ],
            IntentCategory.HELP_SEEKING: [
                r"\b(help|support|assist|guide|how.*to)\b",
                r"\b(explain|understand|learn|tutorial)\b",
                r"\b(stuck|confused|lost|don't.*know)\b",
            ],
            IntentCategory.GREETING: [
                r"\b(hello|hi|hey|good.*morning|good.*afternoon)\b",
                r"\b(start|begin|let's.*get.*started)\b",
            ],
            IntentCategory.STATUS_INQUIRY: [
                r"\b(status|progress|update|how.*going)\b",
                r"\b(ready|complete|finished|done)\b",
            ],
        }

        logger.info(
            "Intent analyzer initialized", extra={"confidence_threshold": self.confidence_threshold}
        )

    async def analyze_intent(
        self, message: str, conversation_context: ConversationContext | None = None
    ) -> IntentAnalysisResult:
        """
        Analyze user message intent with confidence scoring.

        Args:
            message: User message text
            conversation_context: Optional conversation context

        Returns:
            Intent analysis result with confidence and suggestions
        """
        try:
            # Quick pattern-based classification first
            pattern_intent = self._classify_with_patterns(message)

            # Use LLM for sophisticated analysis
            llm_result = await self._analyze_with_llm(message, conversation_context, pattern_intent)

            # Combine results with confidence weighting
            final_result = self._combine_analysis_results(pattern_intent, llm_result)

            logger.debug(
                "Intent analysis completed",
                extra={
                    "intent": final_result.intent.value,
                    "confidence": final_result.confidence,
                    "clarification_needed": final_result.clarification_needed,
                },
            )

            return final_result

        except Exception as e:
            logger.error(f"Intent analysis failed: {e}", exc_info=True)

            # Fallback to pattern-based classification
            return IntentAnalysisResult(
                intent=pattern_intent or IntentCategory.UNKNOWN,
                confidence=0.3,
                reasoning="Fallback to pattern analysis due to LLM error",
            )

    def _classify_with_patterns(self, message: str) -> IntentCategory | None:
        """Quick pattern-based classification."""
        message_lower = message.lower()

        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    return intent

        return None

    async def _analyze_with_llm(
        self,
        message: str,
        conversation_context: ConversationContext | None,
        pattern_hint: IntentCategory | None,
    ) -> IntentAnalysisResult:
        """Sophisticated LLM-based intent analysis."""

        # Build context for LLM
        context_info = ""
        if conversation_context:
            context_info = f"""
Conversation Context:
- Phase: {conversation_context.phase.value}
- Primary Intent: {conversation_context.primary_intent.value if conversation_context.primary_intent else "None"}
- Previous Messages: {len(conversation_context.message_history)} messages
- Last Interaction: {conversation_context.last_interaction.strftime("%Y-%m-%d %H:%M")}
"""

        pattern_info = f"Pattern Hint: {pattern_hint.value}" if pattern_hint else "No pattern match"

        # Craft LLM prompt for intent analysis
        analysis_prompt = f"""
You are ReflectAI, an AI-powered competency analysis assistant. Analyze the user's message to determine their intent and provide helpful insights.

User Message: "{message}"

{context_info}
{pattern_info}

Intent Categories:
1. competency_analysis - User wants analysis of their skills, performance, or competencies
2. report_request - User wants to generate, download, or receive a report
3. help_seeking - User needs help, guidance, or explanation of features
4. greeting - User is greeting or starting a conversation
5. feedback - User is providing feedback or opinions
6. status_inquiry - User is asking about progress or status of something
7. clarification - User is asking for clarification or more details
8. small_talk - Casual conversation not related to main functionality
9. unknown - Intent is unclear or doesn't fit other categories

Respond with JSON format:
{{
    "intent": "<intent_category>",
    "confidence": <0.0-1.0>,
    "entities": {{
        "time_period": "<if mentioned>",
        "competency_area": "<if mentioned>",
        "report_type": "<if mentioned>",
        "specific_request": "<main request>"
    }},
    "reasoning": "<brief explanation>",
    "clarification_needed": <true/false>,
    "suggested_actions": ["<action1>", "<action2>"]
}}
"""

        try:
            llm_request = LLMRequest(
                messages=[{"role": "user", "content": analysis_prompt}],
                model_tier=ModelTier.TIER_2,  # Use competency specialist tier
                user_id="system_intent_analysis",
                temperature=0.3,  # Lower temperature for consistency
                max_tokens=500,
            )

            llm_response = await self.llm_gateway.process_request(llm_request)

            # Parse LLM response
            try:
                result_json = json.loads(llm_response.content)

                return IntentAnalysisResult(
                    intent=IntentCategory(result_json.get("intent", "unknown")),
                    confidence=float(result_json.get("confidence", 0.5)),
                    extracted_entities=result_json.get("entities", {}),
                    suggested_actions=result_json.get("suggested_actions", []),
                    clarification_needed=result_json.get("clarification_needed", False),
                    reasoning=result_json.get("reasoning", ""),
                )

            except (json.JSONDecodeError, ValueError, KeyError) as e:
                logger.warning(f"Failed to parse LLM intent analysis response: {e}")

                # Fallback to basic analysis
                return IntentAnalysisResult(
                    intent=pattern_hint or IntentCategory.UNKNOWN,
                    confidence=0.4,
                    reasoning="LLM response parsing failed",
                )

        except Exception as e:
            logger.error(f"LLM intent analysis failed: {e}")
            raise

    def _combine_analysis_results(
        self, pattern_intent: IntentCategory | None, llm_result: IntentAnalysisResult
    ) -> IntentAnalysisResult:
        """Combine pattern and LLM analysis results."""

        # If LLM confidence is high, trust it
        if llm_result.confidence >= self.confidence_threshold:
            return llm_result

        # If pattern and LLM agree, boost confidence
        if pattern_intent and pattern_intent == llm_result.intent:
            llm_result.confidence = min(llm_result.confidence + 0.2, 1.0)
            return llm_result

        # If confidence is low, mark for clarification
        if llm_result.confidence < self.confidence_threshold:
            llm_result.clarification_needed = True

        return llm_result


class ConversationContextManager:
    """
    Redis-based conversation context manager with 5-minute TTL.

    Features:
    - Redis-based state storage for scalability
    - 5-minute TTL for conversation contexts
    - Context persistence across interactions
    - Conversation history tracking
    """

    def __init__(self, context_ttl_seconds: int = 300):  # 5 minutes
        self.context_ttl = context_ttl_seconds
        self.redis_manager = get_redis_manager()

    async def get_context(self, user_id: str) -> ConversationContext | None:
        """Get conversation context for user."""
        try:
            context_data = await self.redis_manager.get("user", f"dm_context:{user_id}")

            if context_data:
                # Reconstruct ConversationContext from cached data
                return ConversationContext(
                    user_id=context_data["user_id"],
                    conversation_id=context_data["conversation_id"],
                    phase=ConversationPhase(context_data["phase"]),
                    primary_intent=IntentCategory(context_data["primary_intent"])
                    if context_data.get("primary_intent")
                    else None,
                    collected_parameters=context_data.get("collected_parameters", {}),
                    message_history=context_data.get("message_history", []),
                    last_interaction=datetime.fromisoformat(context_data["last_interaction"]),
                    clarification_attempts=context_data.get("clarification_attempts", 0),
                    max_clarification_attempts=context_data.get("max_clarification_attempts", 3),
                    metadata=context_data.get("metadata", {}),
                )

            return None

        except Exception as e:
            logger.error(f"Failed to get conversation context for {user_id}: {e}")
            return None

    async def save_context(self, context: ConversationContext) -> bool:
        """Save conversation context to Redis."""
        try:
            context_data = {
                "user_id": context.user_id,
                "conversation_id": context.conversation_id,
                "phase": context.phase.value,
                "primary_intent": context.primary_intent.value if context.primary_intent else None,
                "collected_parameters": context.collected_parameters,
                "message_history": context.message_history,
                "last_interaction": context.last_interaction.isoformat(),
                "clarification_attempts": context.clarification_attempts,
                "max_clarification_attempts": context.max_clarification_attempts,
                "metadata": context.metadata,
            }

            success = await self.redis_manager.set(
                "user", f"dm_context:{context.user_id}", context_data, ttl_override=self.context_ttl
            )

            if success:
                logger.debug(f"Conversation context saved for {context.user_id}")

            return success

        except Exception as e:
            logger.error(f"Failed to save conversation context for {context.user_id}: {e}")
            return False

    async def update_context(
        self, user_id: str, message: str, intent_result: IntentAnalysisResult
    ) -> ConversationContext:
        """Update conversation context with new message and intent."""
        context = await self.get_context(user_id)

        if context is None:
            # Create new conversation context
            context = ConversationContext(
                user_id=user_id,
                conversation_id=f"{user_id}_{int(datetime.now(UTC).timestamp())}",
                phase=ConversationPhase.INITIAL_CONTACT,
            )

        # Update context
        context.last_interaction = datetime.now(UTC)

        # Add message to history (keep last 10 messages)
        context.message_history.append(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "message": message,
                "intent": intent_result.intent.value,
                "confidence": intent_result.confidence,
            }
        )

        if len(context.message_history) > 10:
            context.message_history = context.message_history[-10:]

        # Update primary intent if confidence is high
        if intent_result.confidence >= 0.7:
            if context.primary_intent is None:
                context.primary_intent = intent_result.intent
                context.phase = ConversationPhase.INTENT_GATHERING

        # Extract and merge parameters
        if intent_result.extracted_entities:
            context.collected_parameters.update(intent_result.extracted_entities)

        # Save updated context
        await self.save_context(context)

        return context

    async def clear_context(self, user_id: str) -> bool:
        """Clear conversation context for user."""
        try:
            return await self.redis_manager.delete("user", f"dm_context:{user_id}")
        except Exception as e:
            logger.error(f"Failed to clear context for {user_id}: {e}")
            return False


class ClarificationGenerator:
    """
    Contextual clarification and response generator.

    Features:
    - Smart follow-up questions per intent category
    - Contextual response templates
    - Progressive clarification approach
    - Conversation flow management
    """

    def __init__(self):
        self.llm_gateway = get_llm_gateway()

        # Clarification templates by intent
        self.clarification_templates = {
            IntentCategory.COMPETENCY_ANALYSIS: [
                "I'd be happy to analyze your competencies! Which specific area would you like me to focus on?",
                "What time period should I analyze - the last week, month, or a custom timeframe?",
                "Are you looking for overall performance or specific skills like leadership, communication, or technical abilities?",
            ],
            IntentCategory.REPORT_REQUEST: [
                "I can generate a report for you! What type would you prefer - PDF, summary, or detailed analysis?",
                "Which time period should the report cover?",
                "Would you like a focus on specific competencies or a comprehensive overview?",
            ],
            IntentCategory.HELP_SEEKING: [
                "I'm here to help! What specific aspect of ReflectAI would you like to learn about?",
                "Are you looking for help with commands, understanding your analysis, or something else?",
                "Would you like a quick overview or detailed guidance on a particular feature?",
            ],
        }

        # Follow-up suggestions by intent
        self.follow_up_suggestions = {
            IntentCategory.COMPETENCY_ANALYSIS: [
                "Start basic analysis with `/reflect`",
                "Try detailed analysis with `/analyze 7 days`",
                "Focus on specific area: communication, leadership, technical",
            ],
            IntentCategory.REPORT_REQUEST: [
                "Generate PDF report with `/report pdf`",
                "Get quick summary with `/report summary`",
                "Choose time period: week, month, quarter",
            ],
            IntentCategory.HELP_SEEKING: [
                "Use `/help` for general information",
                "Try `/help commands` for available commands",
                "Ask specific questions about features",
            ],
        }

        logger.info("Clarification generator initialized")

    async def generate_response(
        self,
        intent_result: IntentAnalysisResult,
        context: ConversationContext,
        original_message: str,
    ) -> dict[str, Any]:
        """
        Generate appropriate response based on intent and context.

        Args:
            intent_result: Result of intent analysis
            context: Current conversation context
            original_message: Original user message

        Returns:
            Response dictionary with text and optional blocks
        """
        try:
            if intent_result.clarification_needed or intent_result.confidence < 0.7:
                return await self._generate_clarification_response(intent_result, context)

            elif intent_result.intent == IntentCategory.GREETING:
                return self._generate_greeting_response(context)

            elif intent_result.intent == IntentCategory.COMPETENCY_ANALYSIS:
                return await self._generate_analysis_response(intent_result, context)

            elif intent_result.intent == IntentCategory.REPORT_REQUEST:
                return await self._generate_report_response(intent_result, context)

            elif intent_result.intent == IntentCategory.HELP_SEEKING:
                return self._generate_help_response(intent_result, context)

            elif intent_result.intent == IntentCategory.SMALL_TALK:
                return self._generate_small_talk_response(original_message)

            else:
                return await self._generate_clarification_response(intent_result, context)

        except Exception as e:
            logger.error(f"Response generation failed: {e}", exc_info=True)
            return {
                "text": "I'm here to help with competency analysis and career development. How can I assist you today?"
            }

    async def _generate_clarification_response(
        self, intent_result: IntentAnalysisResult, context: ConversationContext
    ) -> dict[str, Any]:
        """Generate clarification questions to better understand user intent."""

        # Avoid too many clarification attempts
        if context.clarification_attempts >= context.max_clarification_attempts:
            return {
                "text": "Let me help you get started! Try using `/reflect` for competency analysis or `/help` for available commands.",
                "blocks": self._create_quick_action_blocks(),
            }

        # Get appropriate clarification based on best-guess intent
        if intent_result.intent in self.clarification_templates:
            templates = self.clarification_templates[intent_result.intent]
            clarification_text = templates[context.clarification_attempts % len(templates)]
        else:
            clarification_text = (
                "I want to help you! Could you tell me more about what you're looking for?"
            )

        suggestions = self.follow_up_suggestions.get(intent_result.intent, [])

        blocks = []
        if suggestions:
            blocks = [
                {"type": "section", "text": {"type": "mrkdwn", "text": clarification_text}},
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Suggestions:*\n"
                        + "\n".join(f"• {suggestion}" for suggestion in suggestions[:3]),
                    },
                },
            ]

        return {"text": clarification_text, "blocks": blocks}

    def _generate_greeting_response(self, context: ConversationContext) -> dict[str, Any]:
        """Generate friendly greeting response."""
        greeting_messages = [
            "Hello! I'm ReflectAI, your AI-powered competency analysis assistant. How can I help you grow professionally today?",
            "Hi there! I'm here to help you understand and develop your professional competencies. What would you like to explore?",
            "Hey! Ready to gain some insights into your professional development? I can analyze your competencies, generate reports, or answer questions.",
        ]

        greeting = greeting_messages[0]  # Use first for consistency

        blocks = [
            {"type": "section", "text": {"type": "mrkdwn", "text": greeting}},
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "🔍 Start Analysis"},
                        "value": "start_analysis",
                        "action_id": "quick_reflect",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "📄 Get Report"},
                        "value": "get_report",
                        "action_id": "quick_report",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "❓ Learn More"},
                        "value": "learn_more",
                        "action_id": "quick_help",
                    },
                ],
            },
        ]

        return {"text": greeting, "blocks": blocks}

    async def _generate_analysis_response(
        self, intent_result: IntentAnalysisResult, context: ConversationContext
    ) -> dict[str, Any]:
        """Generate response for competency analysis requests."""

        entities = intent_result.extracted_entities
        time_period = entities.get("time_period", "last week")
        competency_area = entities.get("competency_area", "overall competencies")

        response_text = (
            f"I'll analyze your {competency_area} from {time_period}. Let me start that for you!"
        )

        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🔍 *Starting Competency Analysis*\n*Focus:* {competency_area}\n*Period:* {time_period}",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "I'll analyze your activities and provide insights on your professional development.",
                },
            },
        ]

        return {"text": response_text, "blocks": blocks}

    async def _generate_report_response(
        self, intent_result: IntentAnalysisResult, context: ConversationContext
    ) -> dict[str, Any]:
        """Generate response for report requests."""

        entities = intent_result.extracted_entities
        report_type = entities.get("report_type", "PDF")
        time_period = entities.get("time_period", "last month")

        response_text = f"I'll generate a {report_type} report covering {time_period} for you!"

        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"📄 *Generating Report*\n*Type:* {report_type}\n*Period:* {time_period}",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Your personalized competency report will be ready shortly. I'll notify you when it's available for download.",
                },
            },
        ]

        return {"text": response_text, "blocks": blocks}

    def _generate_help_response(
        self, intent_result: IntentAnalysisResult, context: ConversationContext
    ) -> dict[str, Any]:
        """Generate response for help-seeking requests."""

        help_text = "I'm happy to help! Here are some things I can assist you with:"

        blocks = [
            {"type": "section", "text": {"type": "mrkdwn", "text": help_text}},
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": "*🔍 Analysis*\nUnderstand your competencies and skills",
                    },
                    {
                        "type": "mrkdwn",
                        "text": "*📊 Reports*\nGenerate detailed development reports",
                    },
                    {"type": "mrkdwn", "text": "*💡 Insights*\nGet personalized recommendations"},
                    {"type": "mrkdwn", "text": "*📈 Tracking*\nMonitor your progress over time"},
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Try `/help commands` for a full list of available commands, or just tell me what you'd like to do!",
                },
            },
        ]

        return {"text": help_text, "blocks": blocks}

    def _generate_small_talk_response(self, original_message: str) -> dict[str, Any]:
        """Generate friendly response to small talk while redirecting to functionality."""

        small_talk_responses = {
            "how are you": "I'm doing great and ready to help you with your professional development!",
            "thank you": "You're very welcome! I'm always here to help you grow professionally.",
            "good job": "Thank you! I'm glad I could help with your competency development.",
        }

        message_lower = original_message.lower()
        response = None

        for phrase, reply in small_talk_responses.items():
            if phrase in message_lower:
                response = reply
                break

        if not response:
            response = "I appreciate the conversation! I'm here whenever you need help with competency analysis or career development."

        response += " What would you like to work on today?"

        return {"text": response, "blocks": self._create_quick_action_blocks()}

    def _create_quick_action_blocks(self) -> list[dict[str, Any]]:
        """Create quick action buttons for common tasks."""
        return [
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "🔍 Analyze"},
                        "value": "quick_analyze",
                        "action_id": "quick_analyze",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "📄 Report"},
                        "value": "quick_report",
                        "action_id": "quick_report",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "❓ Help"},
                        "value": "quick_help",
                        "action_id": "quick_help",
                    },
                ],
            }
        ]


class IntelligentDMSystem:
    """
    Complete intelligent DM system integrating all components.

    Features:
    - Intent analysis with 0.7 confidence threshold
    - Redis-based conversation context management
    - Intelligent clarification and response generation
    - Proactive assistance and follow-up
    """

    def __init__(self):
        self.intent_analyzer = IntentAnalyzer(confidence_threshold=0.7)
        self.context_manager = ConversationContextManager(context_ttl_seconds=300)  # 5 minutes
        self.clarification_generator = ClarificationGenerator()

        logger.info("Intelligent DM system initialized")

    async def process_dm_message(
        self, user_id: str, message: str, metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Process incoming DM message with intelligent analysis and response.

        Args:
            user_id: User ID
            message: User message content
            metadata: Optional metadata (channel info, etc.)

        Returns:
            Response dictionary for Slack
        """
        correlation_id = get_or_create_correlation_id()

        logger.info(
            "Processing intelligent DM",
            extra={
                "correlation_id": correlation_id,
                "user_id": user_id,
                "message_length": len(message),
            },
        )

        try:
            # Get conversation context
            context = await self.context_manager.get_context(user_id)

            # Analyze message intent
            intent_result = await self.intent_analyzer.analyze_intent(message, context)

            # Update conversation context
            updated_context = await self.context_manager.update_context(
                user_id, message, intent_result
            )

            # Track clarification attempts
            if intent_result.clarification_needed:
                updated_context.clarification_attempts += 1
                await self.context_manager.save_context(updated_context)

            # Generate appropriate response
            response = await self.clarification_generator.generate_response(
                intent_result, updated_context, message
            )

            logger.info(
                "Intelligent DM processed successfully",
                extra={
                    "correlation_id": correlation_id,
                    "intent": intent_result.intent.value,
                    "confidence": intent_result.confidence,
                    "clarification_needed": intent_result.clarification_needed,
                },
            )

            return response

        except Exception as e:
            logger.error(
                f"Intelligent DM processing failed: {e}",
                extra={"correlation_id": correlation_id, "user_id": user_id},
                exc_info=True,
            )

            # Fallback response
            return {
                "text": "I'm here to help with your professional development! Try `/help` to see what I can do for you."
            }

    async def get_conversation_analytics(self, user_id: str) -> dict[str, Any]:
        """Get analytics for user's conversation patterns."""
        context = await self.context_manager.get_context(user_id)

        if not context:
            return {"status": "no_conversation_data"}

        return {
            "conversation_id": context.conversation_id,
            "phase": context.phase.value,
            "primary_intent": context.primary_intent.value if context.primary_intent else None,
            "message_count": len(context.message_history),
            "clarification_attempts": context.clarification_attempts,
            "last_interaction": context.last_interaction.isoformat(),
            "collected_parameters": context.collected_parameters,
        }


# Global instance
_intelligent_dm_system: IntelligentDMSystem | None = None


async def get_intelligent_dm_system() -> IntelligentDMSystem:
    """Get or create global intelligent DM system instance."""
    global _intelligent_dm_system
    if _intelligent_dm_system is None:
        _intelligent_dm_system = IntelligentDMSystem()
    return _intelligent_dm_system
