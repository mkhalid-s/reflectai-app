"""
Canonical Intent Type System

This module defines the single source of truth for user intent types across
the ReflectAI platform. All intent classification, routing, and handling should
use these types.

This replaces the previous fragmented intent type systems:
- IntentType (was in intent_analyzer.py)
- UserIntent (was in conversation/types.py)
- String literal mappings (was in conversation_manager.py)
"""

from enum import Enum


class IntentType(str, Enum):
    """
    Canonical user intent types for the ReflectAI platform.

    These represent the user's underlying goal or request type, not workflow
    execution modes. Each intent maps to specific handler logic in the
    conversation manager.

    Usage:
        intent = IntentType.ACTIVITY_CLASSIFICATION
        if intent == IntentType.HELP_REQUEST:
            # Handle help request
    """

    # Core Activity Intents
    ACTIVITY_CLASSIFICATION = "activity_classification"
    """User wants to classify or log work activities"""

    COMPETENCY_ANALYSIS = "competency_analysis"
    """User wants competency assessment or gap analysis"""

    # Career & Development Intents
    CAREER_ADVICE = "career_advice"
    """User wants career guidance or development recommendations"""

    GOAL_MANAGEMENT = "goal_management"
    """User wants to manage goals or track progress"""

    # Information & Help Intents
    HELP_REQUEST = "help_request"
    """User needs help understanding the system or features"""

    RESOURCE_DISCOVERY = "resource_discovery"
    """User wants to find learning resources or materials"""

    STATUS_INQUIRY = "status_inquiry"
    """User wants to check status of requests or workflows"""

    # Reporting Intents
    REPORT_REQUEST = "report_request"
    """User wants to generate or view reports (competency, activity, etc.)"""

    # Conversational Intents
    GENERAL_CHAT = "general_chat"
    """Greeting, small talk, or general conversation (hello, hi, thanks)"""

    # Fallback Intent
    UNKNOWN = "unknown"
    """Intent could not be determined with confidence"""


class IntentConfidence(str, Enum):
    """
    Intent classification confidence levels.

    These determine routing behavior and whether clarification is needed.
    """

    HIGH = "high"
    """Confidence >0.7 - direct routing to handler"""

    MEDIUM = "medium"
    """Confidence 0.5-0.7 - route with confirmation"""

    LOW = "low"
    """Confidence 0.3-0.5 - request clarification"""

    VERY_LOW = "very_low"
    """Confidence <0.3 - require detailed clarification"""


# Intent to Handler Mapping
# This defines which conversation handlers should be used for each intent type
INTENT_HANDLER_MAP = {
    IntentType.GENERAL_CHAT: "greeting",
    IntentType.HELP_REQUEST: "help",
    IntentType.ACTIVITY_CLASSIFICATION: "analysis",
    IntentType.COMPETENCY_ANALYSIS: "competency",
    IntentType.CAREER_ADVICE: "career",
    IntentType.GOAL_MANAGEMENT: "goals",
    IntentType.REPORT_REQUEST: "report",
    IntentType.RESOURCE_DISCOVERY: "resources",
    IntentType.STATUS_INQUIRY: "status",
    IntentType.UNKNOWN: "generic",
}


def get_handler_for_intent(intent: IntentType) -> str:
    """
    Get the conversation handler name for a given intent type.

    Args:
        intent: The classified intent type

    Returns:
        Handler name (e.g., "greeting", "analysis", "report")

    Example:
        >>> get_handler_for_intent(IntentType.GENERAL_CHAT)
        'greeting'
        >>> get_handler_for_intent(IntentType.ACTIVITY_CLASSIFICATION)
        'analysis'
    """
    return INTENT_HANDLER_MAP.get(intent, "generic")


def is_high_confidence(confidence: float) -> bool:
    """Check if confidence score is high (>0.7)"""
    return confidence > 0.7


def is_actionable_intent(intent: IntentType) -> bool:
    """
    Check if intent requires immediate action/workflow execution.

    Args:
        intent: The intent type to check

    Returns:
        True if intent typically triggers workflow execution
    """
    actionable_intents = {
        IntentType.ACTIVITY_CLASSIFICATION,
        IntentType.COMPETENCY_ANALYSIS,
        IntentType.REPORT_REQUEST,
        IntentType.CAREER_ADVICE,
    }
    return intent in actionable_intents


def is_informational_intent(intent: IntentType) -> bool:
    """
    Check if intent is primarily informational (no workflow needed).

    Args:
        intent: The intent type to check

    Returns:
        True if intent is informational only
    """
    informational_intents = {
        IntentType.GENERAL_CHAT,
        IntentType.HELP_REQUEST,
        IntentType.STATUS_INQUIRY,
    }
    return intent in informational_intents


__all__ = [
    "IntentType",
    "IntentConfidence",
    "INTENT_HANDLER_MAP",
    "get_handler_for_intent",
    "is_high_confidence",
    "is_actionable_intent",
    "is_informational_intent",
]
