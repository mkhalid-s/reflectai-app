"""
Conversation Types and Data Models

Shared data structures for the conversation system to prevent circular imports.

Note: IntentType is now imported from src.core.types (canonical location).
The old UserIntent enum has been removed - use IntentType instead.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from src.core.types import IntentType


class ConversationStage(str, Enum):
    """Conversation stages for context tracking"""

    GREETING = "greeting"
    INTENT_CLARIFICATION = "intent_clarification"
    ANALYSIS_IN_PROGRESS = "analysis_in_progress"
    FOLLOW_UP = "follow_up"
    CLOSING = "closing"


@dataclass
class ConversationContext:
    """Conversation context data structure"""

    user_id: str
    thread_id: str | None
    stage: ConversationStage
    intent: IntentType | None
    intent_confidence: float
    message_history: list[dict[str, Any]]
    context_summary: str
    mentioned_activities: list[str]
    pending_actions: list[str]
    last_updated: datetime
    expires_at: datetime
