"""
Greeting and Help System

Implements  Advanced greeting pattern recognition, contextual responses,
personalized onboarding, and interactive help system.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from src.shared import get_logger

from .types import ConversationContext

logger = get_logger(__name__)


class GreetingType(str, Enum):
    """Types of greetings detected"""

    FIRST_TIME = "first_time"
    RETURNING = "returning"
    CASUAL = "casual"
    FORMAL = "formal"
    HELP_REQUEST = "help_request"
    CONFUSED = "confused"


class UserExperienceLevel(str, Enum):
    """User experience levels for personalization"""

    NEW_USER = "new_user"
    OCCASIONAL = "occasional"
    REGULAR = "regular"
    POWER_USER = "power_user"


@dataclass
class GreetingContext:
    """Context for greeting responses"""

    greeting_type: GreetingType
    user_experience: UserExperienceLevel
    last_interaction: datetime | None
    interaction_count: int
    preferred_style: str  # casual, professional, concise, detailed
    user_role: str | None
    department: str | None


@dataclass
class HelpResponse:
    """Structured help response"""

    response_type: str
    blocks: list[dict[str, Any]]
    follow_up_actions: list[str]
    personalization_applied: bool


class GreetingAndHelpSystem:
    """
    Advanced greeting and help system with personalization.

    Implements Requirements:
    - 31.1: Advanced greeting pattern recognition
    - 31.2: Contextual responses based on user history
    - 31.3: Personalized onboarding for new users
    - 31.4: Interactive help system
    - 31.5: User capability overview personalized by role
    - 31.6: Greeting response effectiveness monitoring
    """

    def __init__(self):
        self.greeting_patterns = self._load_greeting_patterns()
        self.help_templates = self._load_help_templates()
        self.onboarding_flows = self._load_onboarding_flows()
        self.role_capabilities = self._load_role_capabilities()

    async def process_greeting(
        self, message: str, user_id: str, user_profile: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Process greeting message and generate contextual response.

        Args:
            message: User's greeting message
            user_id: Slack user ID
            user_profile: Optional user profile data

        Returns:
            Greeting response with Slack blocks
        """
        try:
            # Detect greeting type and context
            greeting_context = await self._analyze_greeting(message, user_id, user_profile)

            # Generate contextual response
            response = await self._generate_greeting_response(
                message, greeting_context, user_profile
            )

            # Log greeting metrics for optimization
            await self._log_greeting_metrics(user_id, greeting_context, response)

            return response

        except Exception as e:
            logger.error(
                "Failed to process greeting",
                extra={"user_id": user_id, "message_length": len(message), "error": str(e)},
            )
            # Return fallback greeting
            return self._get_fallback_greeting()

    async def generate_help_response(
        self,
        request: str,
        user_id: str,
        user_profile: dict[str, Any] | None = None,
        context: ConversationContext | None = None,
    ) -> HelpResponse:
        """
        Generate interactive help response.

        Args:
            request: Help request text
            user_id: Slack user ID
            user_profile: Optional user profile
            context: Optional conversation context

        Returns:
            Structured help response
        """
        try:
            # Analyze help request type
            help_category = await self._categorize_help_request(request, context)

            # Generate personalized help content
            help_content = await self._generate_help_content(help_category, user_profile, context)

            # Create interactive help blocks
            blocks = await self._build_help_blocks(help_content, help_category, user_profile)

            return HelpResponse(
                response_type=help_category,
                blocks=blocks,
                follow_up_actions=help_content.get("follow_up_actions", []),
                personalization_applied=bool(user_profile),
            )

        except Exception as e:
            logger.error(
                "Failed to generate help response",
                extra={"user_id": user_id, "request": request[:100], "error": str(e)},
            )
            return self._get_fallback_help()

    async def get_onboarding_flow(
        self, user_id: str, user_profile: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Get personalized onboarding flow for new users.

        Args:
            user_id: Slack user ID
            user_profile: User profile data

        Returns:
            Onboarding flow blocks
        """
        try:
            # Determine user's role and experience level
            role = user_profile.get("role", "individual_contributor")
            experience = self._determine_experience_level(user_profile)

            # Select appropriate onboarding flow
            flow_key = f"{role}_{experience}"
            onboarding_flow = self.onboarding_flows.get(flow_key, self.onboarding_flows["default"])

            # Personalize onboarding content
            personalized_flow = await self._personalize_onboarding(onboarding_flow, user_profile)

            logger.info(
                "Generated onboarding flow",
                extra={
                    "user_id": user_id,
                    "role": role,
                    "experience": experience,
                    "flow_steps": len(personalized_flow.get("steps", [])),
                },
            )

            return personalized_flow

        except Exception as e:
            logger.error(
                "Failed to get onboarding flow", extra={"user_id": user_id, "error": str(e)}
            )
            return self.onboarding_flows["default"]

    async def _analyze_greeting(
        self, message: str, user_id: str, user_profile: dict[str, Any] | None
    ) -> GreetingContext:
        """Analyze greeting message and user context."""

        # Detect greeting type using patterns
        greeting_type = self._detect_greeting_type(message)

        # Determine user experience level
        experience_level = self._determine_experience_level(user_profile or {})

        # Get user interaction history (would integrate with analytics)
        interaction_count = await self._get_interaction_count(user_id)
        last_interaction = await self._get_last_interaction(user_id)

        return GreetingContext(
            greeting_type=greeting_type,
            user_experience=experience_level,
            last_interaction=last_interaction,
            interaction_count=interaction_count,
            preferred_style=user_profile.get("communication_style", "casual")
            if user_profile
            else "casual",
            user_role=user_profile.get("role") if user_profile else None,
            department=user_profile.get("department") if user_profile else None,
        )

    def _detect_greeting_type(self, message: str) -> GreetingType:
        """Detect type of greeting from message patterns."""

        message_lower = message.lower().strip()

        # First time user patterns
        first_time_patterns = [
            r"new to this",
            r"first time",
            r"never used",
            r"getting started",
            r"how do i",
            r"what can you",
            r"what do you do",
        ]
        if any(re.search(pattern, message_lower) for pattern in first_time_patterns):
            return GreetingType.FIRST_TIME

        # Help request patterns
        help_patterns = [
            r"help",
            r"how to",
            r"can you",
            r"what",
            r"explain",
            r"show me",
            r"guide",
            r"tutorial",
            r"instructions",
        ]
        if any(re.search(pattern, message_lower) for pattern in help_patterns):
            return GreetingType.HELP_REQUEST

        # Confused/lost patterns
        confused_patterns = [
            r"confused",
            r"lost",
            r"don't understand",
            r"not sure",
            r"unclear",
            r"stuck",
            r"having trouble",
        ]
        if any(re.search(pattern, message_lower) for pattern in confused_patterns):
            return GreetingType.CONFUSED

        # Formal greetings
        formal_patterns = [
            r"good morning",
            r"good afternoon",
            r"good evening",
            r"greetings",
            r"salutations",
        ]
        if any(re.search(pattern, message_lower) for pattern in formal_patterns):
            return GreetingType.FORMAL

        # Casual greetings (default)
        casual_patterns = [r"hi", r"hello", r"hey", r"yo", r"sup", r"what's up", r"howdy", r"hiya"]
        if any(re.search(pattern, message_lower) for pattern in casual_patterns):
            return GreetingType.CASUAL

        # Default to returning if no clear greeting pattern
        return GreetingType.RETURNING

    def _determine_experience_level(self, user_profile: dict[str, Any]) -> UserExperienceLevel:
        """Determine user experience level from profile and usage."""

        interaction_count = user_profile.get("interaction_count", 0)
        user_profile.get("last_interaction")

        if interaction_count == 0:
            return UserExperienceLevel.NEW_USER
        elif interaction_count < 5:
            return UserExperienceLevel.OCCASIONAL
        elif interaction_count < 20:
            return UserExperienceLevel.REGULAR
        else:
            return UserExperienceLevel.POWER_USER

    async def _generate_greeting_response(
        self, message: str, context: GreetingContext, user_profile: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Generate contextual greeting response."""

        # Select response template based on greeting type and experience
        template_key = f"{context.greeting_type}_{context.user_experience}"
        response_template = self._get_greeting_template(template_key)

        # Personalize response
        personalized_response = await self._personalize_greeting(
            response_template, context, user_profile
        )

        # Add role-specific capabilities if available
        if context.user_role:
            capabilities = self.role_capabilities.get(context.user_role, [])
            personalized_response["role_capabilities"] = capabilities

        return personalized_response

    async def _categorize_help_request(
        self, request: str, context: ConversationContext | None
    ) -> str:
        """Categorize help request for appropriate response."""

        request_lower = request.lower()

        # Category patterns
        categories = {
            "getting_started": [
                "getting started",
                "how to start",
                "begin",
                "first time",
                "new user",
                "onboarding",
            ],
            "activity_analysis": [
                "analyze",
                "activity",
                "work",
                "classify",
                "competency",
                "skills",
                "what can you do with",
            ],
            "reports": ["report", "pdf", "generate", "create", "download", "summary", "overview"],
            "career_advice": [
                "career",
                "development",
                "growth",
                "advice",
                "guidance",
                "recommendations",
                "next steps",
            ],
            "features": [
                "features",
                "capabilities",
                "what can you do",
                "functions",
                "commands",
                "options",
            ],
            "troubleshooting": [
                "error",
                "problem",
                "issue",
                "not working",
                "broken",
                "failed",
                "trouble",
            ],
        }

        # Find best matching category
        for category, keywords in categories.items():
            if any(keyword in request_lower for keyword in keywords):
                return category

        return "general"

    def _get_greeting_template(self, template_key: str) -> dict[str, Any]:
        """Get greeting template for specific context."""

        templates = {
            "first_time_new_user": {
                "emoji": "👋",
                "title": "Welcome to ReflectAI!",
                "message": (
                    "Hi there! I'm your AI companion for professional development. "
                    "I help you understand and track your competencies by analyzing "
                    "your work activities.\n\n"
                    "Here's what I can do for you:\n"
                    "🔍 Analyze your work activities\n"
                    "💡 Provide career development insights\n"
                    "📊 Generate competency reports\n\n"
                    "Want to try it out? Just tell me about something you worked on recently!"
                ),
                "show_onboarding": True,
                "show_quick_actions": True,
            },
            "casual_regular": {
                "emoji": "👋",
                "title": "Hey there!",
                "message": "Good to see you again! What can I help you with today?",
                "show_recent_activities": True,
                "show_quick_actions": True,
            },
            "help_request_new_user": {
                "emoji": "💡",
                "title": "I'm here to help!",
                "message": (
                    "I'd be happy to show you around! I specialize in helping you "
                    "understand and develop your professional competencies.\n\n"
                    "What would you like to learn about first?"
                ),
                "show_help_menu": True,
                "show_examples": True,
            },
        }

        return templates.get(
            template_key,
            templates.get(
                "casual_regular",
                {
                    "emoji": "👋",
                    "title": "Hello!",
                    "message": "How can I assist you today?",
                    "show_quick_actions": True,
                },
            ),
        )

    async def _get_interaction_count(self, user_id: str) -> int:
        """Get user interaction count from analytics."""
        # This would integrate with analytics service
        return 0

    async def _get_last_interaction(self, user_id: str) -> datetime | None:
        """Get user's last interaction timestamp."""
        # This would integrate with analytics service
        return None

    def _get_fallback_greeting(self) -> dict[str, Any]:
        """Return fallback greeting when processing fails."""
        return {
            "emoji": "👋",
            "title": "Hello!",
            "message": (
                "Hi there! I'm ReflectAI, your professional development assistant. "
                "I can help you analyze your work activities, provide career insights, "
                "and generate competency reports.\n\n"
                "How can I help you today?"
            ),
            "blocks": [],
            "show_quick_actions": True,
        }

    def _load_greeting_patterns(self) -> dict[str, list[str]]:
        """Load greeting recognition patterns."""
        return {
            "casual": ["hi", "hello", "hey", "yo", "sup", "what's up"],
            "formal": ["good morning", "good afternoon", "greetings"],
            "first_time": ["new", "first time", "getting started", "how do i"],
            "help": ["help", "how to", "can you", "what", "explain"],
        }

    def _load_help_templates(self) -> dict[str, Any]:
        """Load help response templates."""
        return {}  # Would be loaded from configuration

    def _load_onboarding_flows(self) -> dict[str, Any]:
        """Load onboarding flows for different user types."""
        return {
            "default": {
                "steps": [
                    "Welcome and introduction",
                    "First activity analysis",
                    "Understanding competencies",
                    "Generating your first report",
                ]
            }
        }

    def _load_role_capabilities(self) -> dict[str, list[str]]:
        """Load role-specific capabilities."""
        return {
            "manager": [
                "Team competency analysis",
                "Development planning for reports",
                "Skill gap identification across team",
            ],
            "individual_contributor": [
                "Personal competency tracking",
                "Career development planning",
                "Skill gap analysis",
            ],
        }
