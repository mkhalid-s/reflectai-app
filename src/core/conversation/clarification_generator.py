"""
Clarification Generator

Implements intelligent clarification system to reduce user friction
when intent analysis confidence is below threshold (Task 30a).

Note: Now uses IntentType (canonical enum) instead of UserIntent.
"""

from src.core.types import IntentType
from src.shared import get_logger

from .types import ConversationContext

logger = get_logger(__name__)


class ClarificationGenerator:
    """
    Generates contextual clarification questions when intent is unclear.

    Implements Requirements:
    - 30.1: Intelligent clarification system
    - 30.1: Target <20% requests need clarification
    - 30.1: 95% resolution after clarification
    """

    def __init__(self):
        self.clarification_templates = self._load_clarification_templates()
        self.context_patterns = self._load_context_patterns()

    async def generate_clarification(
        self, message: str, context: ConversationContext, partial_intent: IntentType
    ) -> str:
        """
        Generate contextual clarification question.

        Args:
            message: User's original message
            context: Conversation context
            partial_intent: Best-guess intent with low confidence

        Returns:
            Clarification question string
        """
        try:
            # Choose clarification strategy based on context
            strategy = self._select_clarification_strategy(message, context, partial_intent)

            # Generate clarification using selected strategy
            clarification = await self._generate_by_strategy(
                strategy, message, context, partial_intent
            )

            logger.debug(
                "Generated clarification question",
                extra={
                    "user_id": context.user_id,
                    "strategy": strategy,
                    "partial_intent": partial_intent,
                    "clarification_length": len(clarification),
                },
            )

            return clarification

        except Exception as e:
            logger.error(
                "Failed to generate clarification",
                extra={
                    "user_id": context.user_id,
                    "partial_intent": partial_intent,
                    "error": str(e),
                },
            )
            # Return fallback clarification
            return self._get_fallback_clarification(partial_intent)

    def _select_clarification_strategy(
        self, message: str, context: ConversationContext, partial_intent: IntentType
    ) -> str:
        """Select appropriate clarification strategy."""

        # If user has conversation history, use context-aware strategy
        if len(context.message_history) > 0:
            return "context_aware"

        # If message contains work-related keywords, use activity-focused
        work_keywords = ["work", "project", "task", "meeting", "code", "review"]
        if any(keyword in message.lower() for keyword in work_keywords):
            return "activity_focused"

        # If partial intent suggests specific action
        if partial_intent == IntentType.REPORT_REQUEST:
            return "report_focused"

        # Default strategy for unclear messages
        return "general_help"

    async def _generate_by_strategy(
        self, strategy: str, message: str, context: ConversationContext, partial_intent: IntentType
    ) -> str:
        """Generate clarification using specific strategy."""

        if strategy == "context_aware":
            return self._generate_context_aware_clarification(message, context)

        elif strategy == "activity_focused":
            return self._generate_activity_clarification(message, partial_intent)

        elif strategy == "report_focused":
            return self._generate_report_clarification(message, context)

        else:  # general_help
            return self._generate_general_clarification(message)

    def _generate_context_aware_clarification(
        self, message: str, context: ConversationContext
    ) -> str:
        """Generate clarification based on conversation context."""

        # Reference previous conversation
        if context.mentioned_activities:
            recent_activity = context.mentioned_activities[-1]
            return (
                f"I see you mentioned '{recent_activity}' earlier. "
                f"Are you asking me to:\n"
                f"• Analyze this activity for competency insights?\n"
                f"• Get career advice based on your work?\n"
                f"• Generate a competency report?\n\n"
                f"Or something else? Please let me know!"
            )

        elif context.pending_actions:
            return (
                "Based on our conversation, I can help you with:\n"
                "• Analyzing your work activities\n"
                "• Providing career development advice\n"
                "• Generating competency reports\n\n"
                "What would you like to focus on?"
            )

        else:
            return (
                "I want to make sure I understand correctly. "
                "Could you tell me more about what you'd like me to help with?"
            )

    def _generate_activity_clarification(self, message: str, partial_intent: IntentType) -> str:
        """Generate clarification for activity-related requests."""

        return (
            "I can see you're mentioning work activities! "
            "I can help you with:\n\n"
            "🔍 **Analyze a specific activity** - I'll classify it and identify "
            "the competencies it demonstrates\n\n"
            "📊 **Comprehensive analysis** - Share multiple activities and "
            "I'll provide detailed competency insights\n\n"
            "📋 **Generate a report** - Create a PDF report of your "
            "competency development\n\n"
            "Which of these sounds most like what you're looking for?"
        )

    def _generate_report_clarification(self, message: str, context: ConversationContext) -> str:
        """Generate clarification for report-related requests."""

        return (
            "I'd be happy to generate a competency report for you! "
            "To create the most helpful report, could you tell me:\n\n"
            "📅 **Time period**: Last month? Quarter? Year? Or specific dates?\n\n"
            "📋 **Format**: Quick Slack summary or detailed PDF report?\n\n"
            "🎯 **Focus**: General competency overview or specific area "
            "(like technical skills, leadership, etc.)?\n\n"
            "Just let me know your preferences and I'll create it for you!"
        )

    def _generate_general_clarification(self, message: str) -> str:
        """Generate general clarification for unclear messages."""

        return (
            "I'm here to help with your professional development! "
            "I can assist you with:\n\n"
            "🔍 **Activity Analysis** - Tell me about your recent work and "
            "I'll identify the competencies you're developing\n\n"
            "💡 **Career Advice** - Get personalized recommendations for "
            "your professional growth\n\n"
            "📊 **Competency Reports** - Generate detailed reports showing "
            "your skills and development areas\n\n"
            "❓ **Help & Support** - Learn about all my capabilities\n\n"
            "What would you like to explore?"
        )

    def _get_fallback_clarification(self, partial_intent: IntentType) -> str:
        """Return fallback clarification when generation fails."""

        fallback_map = {
            IntentType.ACTIVITY_CLASSIFICATION: (
                "Could you tell me more about the specific work activity you'd like me to analyze?"
            ),
            IntentType.REPORT_REQUEST: (
                "I'd be happy to create a report for you! "
                "What time period would you like it to cover?"
            ),
            IntentType.CAREER_ADVICE: (
                "I can provide career guidance! What specific area would you like advice on?"
            ),
        }

        return fallback_map.get(
            partial_intent,
            "I want to make sure I help you with exactly what you need. "
            "Could you tell me a bit more about what you're looking for?",
        )

    def _load_clarification_templates(self) -> dict[str, str]:
        """Load clarification templates for different scenarios."""

        return {
            "activity_analysis": (
                "To analyze your activity, I need a bit more detail. "
                "Could you describe: {activity_prompt}"
            ),
            "competency_focus": (
                "Which competency area interests you most? I can focus on: {competency_options}"
            ),
            "time_period": ("What time period should I analyze? Options: {period_options}"),
            "report_format": ("How would you like your results? I can provide: {format_options}"),
        }

    def _load_context_patterns(self) -> dict[str, list[str]]:
        """Load patterns for context-aware clarifications."""

        return {
            "activity_keywords": [
                "meeting",
                "project",
                "code",
                "review",
                "presentation",
                "planning",
                "analysis",
                "development",
                "testing",
                "deployment",
            ],
            "competency_keywords": [
                "skill",
                "competency",
                "ability",
                "strength",
                "development",
                "improvement",
                "growth",
                "learning",
                "training",
            ],
            "report_keywords": [
                "report",
                "summary",
                "overview",
                "analysis",
                "assessment",
                "review",
                "evaluation",
                "progress",
                "status",
            ],
        }
