"""
Conversation Context Manager

Implements Redis-based context storage for conversation state persistence
and cross-session continuity (Task 30.2, 30.4).
"""

import json
from datetime import UTC, datetime, timedelta

try:
    import redis.asyncio as redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

from src.core.types import IntentType
from src.shared import ErrorCategory, ErrorSeverity, ReflectAIError, get_logger

from .types import ConversationContext, ConversationStage

logger = get_logger(__name__)


class ConversationContextManager:
    """
    Manages conversation context with Redis-based persistence.

    Implements Requirements:
    - 29.2: Redis context storage
    - 29.7: Context state management
    - 29.8: Context expiration handling
    - 30.2: Conversation context management
    - 30.4: State persistence
    """

    def __init__(self, redis_client=None):
        self.redis_client = redis_client
        self.context_ttl = 24 * 3600  # 24 hours (Task 27c requirement)
        self.context_namespace = "conversation"

    async def get_context(self, user_id: str, thread_id: str | None = None) -> ConversationContext:
        """
        Get or create conversation context.

        Args:
            user_id: Slack user ID
            thread_id: Slack thread timestamp (optional)

        Returns:
            Conversation context object
        """
        try:
            context_key = self._build_context_key(user_id, thread_id)

            if self.redis_client and REDIS_AVAILABLE:
                # Try to load from Redis
                context_data = await self.redis_client.hgetall(context_key)
                if context_data:
                    # Decode bytes to strings if needed
                    decoded_data = {
                        k.decode() if isinstance(k, bytes) else k:
                        v.decode() if isinstance(v, bytes) else v
                        for k, v in context_data.items()
                    }
                    return self._deserialize_context(decoded_data)

            # Create new context if not found
            return self._create_new_context(user_id, thread_id)

        except Exception as e:
            logger.error(
                "Failed to get conversation context",
                extra={"user_id": user_id, "thread_id": thread_id, "error": str(e)},
            )
            # Return new context as fallback
            return self._create_new_context(user_id, thread_id)

    async def update_context(self, context: ConversationContext):
        """Update conversation context in storage."""
        try:
            context_key = self._build_context_key(context.user_id, context.thread_id)

            if self.redis_client and REDIS_AVAILABLE:
                # Serialize and store in Redis
                context_data = self._serialize_context(context)

                async with self.redis_client.pipeline() as pipe:
                    await pipe.hset(context_key, mapping=context_data)
                    await pipe.expire(context_key, self.context_ttl)
                    await pipe.execute()

                logger.debug(
                    "Updated conversation context",
                    extra={
                        "user_id": context.user_id,
                        "thread_id": context.thread_id,
                        "stage": context.stage,
                    },
                )
            else:
                # In-memory fallback (for testing/development)
                logger.warning(
                    "Redis not available, context not persisted", extra={"user_id": context.user_id}
                )

        except Exception as e:
            logger.error(
                "Failed to update conversation context",
                extra={"user_id": context.user_id, "thread_id": context.thread_id, "error": str(e)},
            )
            raise ReflectAIError(
                message="Failed to update conversation context",
                error_code="CONTEXT_UPDATE_FAILED",
                category=ErrorCategory.INFRASTRUCTURE_ERROR,
                severity=ErrorSeverity.ERROR,
                context={"user_id": context.user_id, "error": str(e)},
            ) from e

    async def cleanup_expired(self) -> int:
        """Clean up expired conversation contexts."""
        try:
            if not (self.redis_client and REDIS_AVAILABLE):
                return 0

            # Find all conversation context keys
            pattern = f"{self.context_namespace}:*"
            keys = await self.redis_client.keys(pattern)

            # Check each key for expiration
            expired_keys = []
            for key in keys:
                ttl = await self.redis_client.ttl(key)
                if ttl <= 0:  # Key has expired or will expire soon
                    expired_keys.append(key)

            # Delete expired keys
            if expired_keys:
                await self.redis_client.delete(*expired_keys)

            logger.info(
                "Cleaned up expired conversation contexts",
                extra={"cleaned_count": len(expired_keys)},
            )

            return len(expired_keys)

        except Exception as e:
            logger.error("Failed to cleanup expired contexts", extra={"error": str(e)})
            return 0

    async def get_user_contexts(self, user_id: str) -> list[ConversationContext]:
        """Get all conversation contexts for a user."""
        try:
            if not (self.redis_client and REDIS_AVAILABLE):
                return []

            # Find all contexts for this user
            pattern = f"{self.context_namespace}:{user_id}:*"
            keys = await self.redis_client.keys(pattern)

            contexts = []
            for key in keys:
                try:
                    context_data = await self.redis_client.hgetall(key)
                    if context_data:
                        contexts.append(self._deserialize_context(context_data))
                except Exception as e:
                    logger.error(
                        "Failed to deserialize context", extra={"key": key, "error": str(e)}
                    )
                    continue

            return contexts

        except Exception as e:
            logger.error("Failed to get user contexts", extra={"user_id": user_id, "error": str(e)})
            return []

    def _build_context_key(self, user_id: str, thread_id: str | None) -> str:
        """Build Redis key for conversation context."""
        if thread_id:
            return f"{self.context_namespace}:{user_id}:{thread_id}"
        else:
            return f"{self.context_namespace}:{user_id}:dm"

    def _create_new_context(self, user_id: str, thread_id: str | None) -> ConversationContext:
        """Create new conversation context."""
        now = datetime.now(UTC)
        return ConversationContext(
            user_id=user_id,
            thread_id=thread_id,
            stage=ConversationStage.GREETING,
            intent=None,
            intent_confidence=0.0,
            message_history=[],
            context_summary="",
            mentioned_activities=[],
            pending_actions=[],
            last_updated=now,
            expires_at=now + timedelta(seconds=self.context_ttl),
        )

    def _serialize_context(self, context: ConversationContext) -> dict[str, str]:
        """Serialize conversation context for Redis storage."""
        return {
            "user_id": context.user_id,
            "thread_id": context.thread_id or "",
            "stage": context.stage.value if context.stage else "",
            "intent": context.intent.value if context.intent else "",
            "intent_confidence": str(context.intent_confidence),
            "message_history": json.dumps(context.message_history),
            "context_summary": context.context_summary,
            "mentioned_activities": json.dumps(context.mentioned_activities),
            "pending_actions": json.dumps(context.pending_actions),
            "last_updated": context.last_updated.isoformat(),
            "expires_at": context.expires_at.isoformat(),
        }

    def _deserialize_context(self, context_data: dict[str, str]) -> ConversationContext:
        """Deserialize conversation context from Redis storage."""
        try:
            # Try to parse intent, fallback to None if not valid
            intent = None
            if context_data.get("intent"):
                try:
                    intent = IntentType(context_data["intent"])
                except ValueError:
                    # Intent value doesn't match IntentType enum, keep as None
                    logger.debug(f"Invalid intent value in context: {context_data['intent']}")

            return ConversationContext(
                user_id=context_data["user_id"],
                thread_id=context_data["thread_id"] or None,
                stage=ConversationStage(context_data["stage"]),
                intent=intent,
                intent_confidence=float(context_data["intent_confidence"]),
                message_history=json.loads(context_data["message_history"]),
                context_summary=context_data["context_summary"],
                mentioned_activities=json.loads(context_data["mentioned_activities"]),
                pending_actions=json.loads(context_data["pending_actions"]),
                last_updated=datetime.fromisoformat(context_data["last_updated"]),
                expires_at=datetime.fromisoformat(context_data["expires_at"]),
            )
        except (KeyError, ValueError, TypeError) as e:
            logger.error(
                "Failed to deserialize context data",
                extra={"error": str(e), "context_data_keys": list(context_data.keys())},
            )
            # Return new context as fallback
            user_id = context_data.get("user_id", "unknown")
            thread_id = context_data.get("thread_id")
            return self._create_new_context(user_id, thread_id)
