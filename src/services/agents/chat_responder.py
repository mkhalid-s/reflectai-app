"""
Chat Responder Agent for ReflectAI

Specializes in conversational interactions and user engagement.
"""

import json
from datetime import UTC, datetime
from typing import Any

from src.shared import get_logger

from .base import AgentCapability, AgentRequest, BaseAgent

logger = get_logger(__name__)


class ChatResponderAgent(BaseAgent):
    """
    Agent specialized in conversational responses and user interaction.

    Capabilities:
    - Natural conversation
    - Context awareness
    - Empathetic responses
    - Question handling
    - Clarification requests
    """

    def __init__(self):
        super().__init__(
            name="ChatResponder",
            description="Conversational AI expert focused on helpful and engaging interactions",
            capabilities=[
                AgentCapability.CONVERSATION,
                AgentCapability.ADVICE,
                AgentCapability.SYNTHESIS,
            ],
        )

        # Conversation state
        self.conversation_context = {}
        self.interaction_style = "professional_friendly"

    async def _run(self, request: AgentRequest) -> dict[str, Any]:
        """
        Execute chat response task.

        Args:
            request: The chat request

        Returns:
            Chat response and metadata
        """
        message = request.task
        context = request.context
        conversation_history = request.conversation_history

        # Classify message intent
        intent = await self._classify_intent(message, request.user_id)

        # Generate appropriate response
        response = await self._generate_response(
            message, intent, context, conversation_history, request.user_id
        )

        # Extract follow-up questions if needed
        follow_ups = self._generate_follow_ups(intent, response)

        # Update conversation context
        await self._update_context(message, response, intent)

        return {
            "response": response,
            "intent": intent,
            "confidence": self._calculate_response_confidence(intent),
            "follow_up_questions": follow_ups,
            "requires_action": self._requires_user_action(intent),
            "sentiment": self._analyze_sentiment(message),
            "timestamp": datetime.now(UTC).isoformat(),
        }

    async def _classify_intent(self, message: str, user_id: str | None = None) -> dict[str, Any]:
        """Classify the intent of the user message."""

        prompt = f"""Classify the intent of this message:

Message: "{message}"

Determine:
1. Primary intent (greeting, question, request, feedback, complaint, clarification)
2. Topic area (career, skills, advice, analysis, general)
3. Urgency (low, medium, high)
4. Emotion (neutral, positive, negative, frustrated, excited)
5. Requires follow-up (yes/no)

Provide as JSON."""

        response = await self.think(prompt, require_json=True, user_id=user_id)

        try:
            intent = json.loads(response)
        except json.JSONDecodeError:
            intent = {
                "primary_intent": "question",
                "topic": "general",
                "urgency": "medium",
                "emotion": "neutral",
                "requires_followup": True,
            }

        return intent

    async def _generate_response(
        self,
        message: str,
        intent: dict[str, Any],
        context: dict[str, Any],
        history: list[dict[str, str]],
        user_id: str | None = None,
    ) -> str:
        """Generate contextual response."""

        # Build conversation context
        history_str = self._format_history(history[-5:])  # Last 5 messages

        # Adjust prompt based on intent
        style = self._get_response_style(intent)

        prompt = f"""Generate a helpful response:

User Message: "{message}"
Intent: {json.dumps(intent, indent=2)}
Context: {json.dumps(context, indent=2)}
Recent History:
{history_str}

Response Style: {style}

Guidelines:
1. Be {self.interaction_style}
2. Address the user's specific needs
3. Provide actionable information when relevant
4. Ask clarifying questions if needed
5. Show empathy and understanding
6. Keep response concise but complete

Generate the response:"""

        response = await self.think(prompt, user_id=user_id)

        # Post-process response
        response = self._post_process_response(response, intent)

        return response

    async def _update_context(self, message: str, response: str, intent: dict[str, Any]):
        """Update conversation context."""

        # Store in short-term memory
        context_update = {
            "last_message": message,
            "last_response": response,
            "last_intent": intent,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        await self.remember("last_interaction", context_update, ttl=3600)

        # Update conversation context
        self.conversation_context.update(context_update)

        # Track topics discussed
        if "topics" not in self.conversation_context:
            self.conversation_context["topics"] = []

        if topic := intent.get("topic"):
            if topic not in self.conversation_context["topics"]:
                self.conversation_context["topics"].append(topic)

    def _generate_follow_ups(self, intent: dict[str, Any], response: str) -> list[str]:
        """Generate follow-up questions."""
        follow_ups = []

        primary_intent = intent.get("primary_intent", "")
        topic = intent.get("topic", "")

        if primary_intent == "question":
            follow_ups.extend(
                [
                    "Would you like more details on this topic?",
                    "Is there a specific aspect you'd like to explore?",
                    "How does this apply to your current situation?",
                ]
            )
        elif primary_intent == "request":
            follow_ups.extend(
                [
                    "What timeline are you working with?",
                    "What are your main goals?",
                    "Would you like me to create a plan for this?",
                ]
            )
        elif topic == "career":
            follow_ups.extend(
                [
                    "What's your current role and experience level?",
                    "What are your long-term career goals?",
                    "Are there specific skills you want to develop?",
                ]
            )

        return follow_ups[:3]  # Return top 3 relevant follow-ups

    def _format_history(self, history: list[dict[str, str]]) -> str:
        """Format conversation history."""
        if not history:
            return "No previous conversation"

        formatted = []
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            formatted.append(f"{role.capitalize()}: {content}")

        return "\n".join(formatted)

    def _get_response_style(self, intent: dict[str, Any]) -> str:
        """Determine appropriate response style."""
        emotion = intent.get("emotion", "neutral")
        urgency = intent.get("urgency", "medium")

        if emotion == "frustrated":
            return "empathetic and solution-focused"
        elif emotion == "excited":
            return "enthusiastic and encouraging"
        elif urgency == "high":
            return "direct and action-oriented"
        else:
            return "professional and friendly"

    def _post_process_response(self, response: str, intent: dict[str, Any]) -> str:
        """Post-process the generated response."""

        # Remove any system-like tokens
        response = response.replace("Assistant:", "").strip()

        # Ensure appropriate ending
        if intent.get("requires_followup") and not response.endswith("?"):
            if not any(response.endswith(p) for p in [",", ".", "!", "?"]):
                response += "."

        # Limit length for chat context
        max_length = 500
        if len(response) > max_length:
            # Find last complete sentence within limit
            sentences = response[:max_length].split(". ")
            response = ". ".join(sentences[:-1]) + "."

        return response

    def _calculate_response_confidence(self, intent: dict[str, Any]) -> float:
        """Calculate confidence in response."""
        confidence = 0.7  # Base confidence

        # Adjust based on intent clarity
        if intent.get("primary_intent") in ["greeting", "question", "request"]:
            confidence += 0.1

        # Adjust based on topic familiarity
        if intent.get("topic") in ["career", "skills", "advice"]:
            confidence += 0.15

        return min(confidence, 0.95)

    def _requires_user_action(self, intent: dict[str, Any]) -> bool:
        """Determine if user action is required."""
        return (
            intent.get("requires_followup", False)
            or intent.get("primary_intent") == "clarification"
        )

    def _analyze_sentiment(self, message: str) -> str:
        """Analyze message sentiment."""
        # Simple sentiment analysis
        positive_words = ["great", "excellent", "happy", "love", "thank"]
        negative_words = ["bad", "terrible", "hate", "frustrated", "angry"]

        message_lower = message.lower()

        positive_count = sum(1 for word in positive_words if word in message_lower)
        negative_count = sum(1 for word in negative_words if word in message_lower)

        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"
