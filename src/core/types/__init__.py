"""
Core Type Definitions

Centralized type definitions used across the ReflectAI platform.
"""

from .intents import (
    INTENT_HANDLER_MAP,
    IntentConfidence,
    IntentType,
    get_handler_for_intent,
    is_actionable_intent,
    is_high_confidence,
    is_informational_intent,
)

__all__ = [
    "IntentType",
    "IntentConfidence",
    "INTENT_HANDLER_MAP",
    "get_handler_for_intent",
    "is_high_confidence",
    "is_actionable_intent",
    "is_informational_intent",
]
