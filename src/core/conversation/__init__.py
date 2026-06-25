"""
Conversation Intelligence Module

Implements sophisticated conversation context management, intent analysis,
and intelligent clarification system for natural user interactions.

Note: IntentType (previously UserIntent) is now in src.core.types.
IntentAnalysisResult is in src.core.classification.intent_analyzer.
"""

from src.core.types import IntentType

from .clarification_generator import ClarificationGenerator
from .context_manager import ConversationContextManager
from .intelligence import ConversationIntelligence
from .types import ConversationContext, ConversationStage

__all__ = [
    "ConversationIntelligence",
    "ConversationContextManager",
    "ClarificationGenerator",
    "ConversationContext",
    "ConversationStage",
    "IntentType",  # Re-export canonical intent type
]
