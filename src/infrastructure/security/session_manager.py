"""
Session Management with Timeout Policies

Provides secure session management with configurable timeout policies,
automatic renewal, and Redis-backed persistence.
"""

import hashlib
import json
import secrets
import time
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

import redis.asyncio as redis
from fastapi import Depends, Header, HTTPException
from pydantic import BaseModel, Field

from src.infrastructure.cache.redis_manager import get_redis_manager
from src.shared.logging import get_logger

logger = get_logger(__name__)


class SessionType(str, Enum):
    """Types of sessions with different timeout policies"""

    USER = "user"
    API_KEY = "api_key"
    SLACK_BOT = "slack_bot"
    ADMIN = "admin"
    SERVICE = "service"


class SessionConfig(BaseModel):
    """Configuration for session management"""

    # Timeout policies by session type (in seconds)
    timeout_policies: dict[SessionType, int] = Field(
        default_factory=lambda: {
            SessionType.USER: 3600,  # 1 hour for regular users
            SessionType.API_KEY: 86400,  # 24 hours for API keys
            SessionType.SLACK_BOT: 7200,  # 2 hours for Slack sessions
            SessionType.ADMIN: 1800,  # 30 minutes for admin sessions
            SessionType.SERVICE: 0,  # No timeout for service accounts
        }
    )

    # Inactivity timeout (seconds) - session expires after this period of inactivity
    inactivity_timeout: int = Field(default=1800, ge=60)  # 30 minutes default

    # Maximum session duration (seconds) - absolute maximum lifetime
    max_session_duration: int = Field(default=86400, ge=3600)  # 24 hours default

    # Session renewal settings
    auto_renew: bool = Field(default=True)
    renewal_threshold: float = Field(default=0.75)  # Renew when 75% of timeout elapsed

    # Security settings
    secure_tokens: bool = Field(default=True)
    token_length: int = Field(default=32, ge=16)

    # Redis settings
    redis_prefix: str = Field(default="session:")
    use_redis: bool = Field(default=True)

    # Cleanup settings
    cleanup_interval: int = Field(default=3600)  # Run cleanup every hour


class Session(BaseModel):
    """Session data model"""

    session_id: str
    user_id: str
    session_type: SessionType
    created_at: datetime
    last_accessed: datetime
    expires_at: datetime
    data: dict[str, Any] = Field(default_factory=dict)
    ip_address: str | None = None
    user_agent: str | None = None
    renewed_count: int = 0
    active: bool = True


class SessionManager:
    """Manages user sessions with timeout policies"""

    def __init__(self, config: SessionConfig | None = None):
        self.config = config or SessionConfig()
        self.redis_client: redis.Redis | None = None

        # In-memory fallback storage
        self.memory_storage: dict[str, Session] = {}

        # Initialize Redis if configured
        if self.config.use_redis:
            try:
                self.redis_client = get_redis_manager()
                logger.info("Redis-based session management initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Redis for sessions: {e}")
                logger.info("Falling back to in-memory session storage")

    def _generate_session_id(self) -> str:
        """Generate a secure session ID"""
        if self.config.secure_tokens:
            return secrets.token_urlsafe(self.config.token_length)
        else:
            # Less secure but faster for development
            return hashlib.sha256(f"{time.time()}:{secrets.randbits(128)}".encode()).hexdigest()[
                : self.config.token_length
            ]

    def _get_timeout_for_type(self, session_type: SessionType) -> int:
        """Get timeout duration for session type"""
        return self.config.timeout_policies.get(session_type, self.config.inactivity_timeout)

    async def create_session(
        self,
        user_id: str,
        session_type: SessionType = SessionType.USER,
        data: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Session:
        """Create a new session with timeout policy"""

        session_id = self._generate_session_id()
        now = datetime.now(UTC)

        # Calculate expiration based on session type
        timeout_seconds = self._get_timeout_for_type(session_type)

        if timeout_seconds == 0:
            # No timeout for service accounts
            expires_at = now + timedelta(seconds=self.config.max_session_duration)
        else:
            expires_at = now + timedelta(seconds=timeout_seconds)

        session = Session(
            session_id=session_id,
            user_id=user_id,
            session_type=session_type,
            created_at=now,
            last_accessed=now,
            expires_at=expires_at,
            data=data or {},
            ip_address=ip_address,
            user_agent=user_agent,
            renewed_count=0,
            active=True,
        )

        # Store session
        await self._store_session(session)

        logger.info(
            f"Session created for user {user_id} (type: {session_type}, expires: {expires_at})"
        )

        return session

    async def get_session(self, session_id: str, touch: bool = True) -> Session | None:
        """Get session and optionally update last access time"""

        # Retrieve session
        session = await self._retrieve_session(session_id)

        if not session:
            return None

        # Check if session is expired
        now = datetime.now(UTC)

        if session.expires_at < now:
            logger.info(f"Session {session_id} has expired")
            await self.invalidate_session(session_id)
            return None

        # Check inactivity timeout
        if self.config.inactivity_timeout > 0:
            inactivity_limit = session.last_accessed + timedelta(
                seconds=self.config.inactivity_timeout
            )
            if inactivity_limit < now:
                logger.info(f"Session {session_id} expired due to inactivity")
                await self.invalidate_session(session_id)
                return None

        # Update last access time if requested
        if touch:
            session.last_accessed = now

            # Check if session should be renewed
            if self.config.auto_renew:
                await self._check_and_renew_session(session)

            # Store updated session
            await self._store_session(session)

        return session

    async def _check_and_renew_session(self, session: Session) -> bool:
        """Check if session should be renewed and renew if needed"""

        if session.session_type == SessionType.SERVICE:
            # Don't renew service sessions
            return False

        now = datetime.now(UTC)
        total_duration = (session.expires_at - session.created_at).total_seconds()
        elapsed = (now - session.created_at).total_seconds()

        # Renew if we've passed the threshold
        if elapsed / total_duration >= self.config.renewal_threshold:
            timeout_seconds = self._get_timeout_for_type(session.session_type)
            session.expires_at = now + timedelta(seconds=timeout_seconds)
            session.renewed_count += 1

            logger.info(f"Session {session.session_id} renewed (count: {session.renewed_count})")

            return True

        return False

    async def update_session_data(
        self, session_id: str, data: dict[str, Any], merge: bool = True
    ) -> bool:
        """Update session data"""

        session = await self.get_session(session_id, touch=True)

        if not session:
            return False

        if merge:
            session.data.update(data)
        else:
            session.data = data

        await self._store_session(session)
        return True

    async def invalidate_session(self, session_id: str) -> bool:
        """Invalidate a session"""

        session = await self._retrieve_session(session_id)

        if session:
            session.active = False
            await self._delete_session(session_id)

            logger.info(f"Session {session_id} invalidated")
            return True

        return False

    async def invalidate_user_sessions(
        self, user_id: str, session_type: SessionType | None = None
    ) -> int:
        """Invalidate all sessions for a user"""

        count = 0

        if self.redis_client:
            # Redis-based invalidation
            pattern = f"{self.config.redis_prefix}*"
            cursor = 0

            while True:
                cursor, keys = await self.redis_client.scan(cursor, match=pattern, count=100)

                for key in keys:
                    session_data = await self.redis_client.get(key)
                    if session_data:
                        session = Session.parse_raw(session_data)

                        if session.user_id == user_id:
                            if not session_type or session.session_type == session_type:
                                await self.redis_client.delete(key)
                                count += 1

                if cursor == 0:
                    break
        else:
            # Memory-based invalidation
            sessions_to_delete = []

            for session_id, session in self.memory_storage.items():
                if session.user_id == user_id:
                    if not session_type or session.session_type == session_type:
                        sessions_to_delete.append(session_id)

            for session_id in sessions_to_delete:
                del self.memory_storage[session_id]
                count += 1

        logger.info(f"Invalidated {count} sessions for user {user_id}")
        return count

    async def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions from storage"""

        count = 0
        now = datetime.now(UTC)

        if self.redis_client:
            # Redis-based cleanup
            pattern = f"{self.config.redis_prefix}*"
            cursor = 0

            while True:
                cursor, keys = await self.redis_client.scan(cursor, match=pattern, count=100)

                for key in keys:
                    session_data = await self.redis_client.get(key)
                    if session_data:
                        try:
                            session = Session.parse_raw(session_data)

                            if session.expires_at < now:
                                await self.redis_client.delete(key)
                                count += 1
                        except Exception as e:
                            logger.error(f"Error parsing session: {e}")
                            # Delete corrupted session
                            await self.redis_client.delete(key)
                            count += 1

                if cursor == 0:
                    break
        else:
            # Memory-based cleanup
            expired_sessions = []

            for session_id, session in self.memory_storage.items():
                if session.expires_at < now:
                    expired_sessions.append(session_id)

            for session_id in expired_sessions:
                del self.memory_storage[session_id]
                count += 1

        if count > 0:
            logger.info(f"Cleaned up {count} expired sessions")

        return count

    async def get_active_sessions_count(self, session_type: SessionType | None = None) -> int:
        """Get count of active sessions"""

        count = 0
        now = datetime.now(UTC)

        if self.redis_client:
            pattern = f"{self.config.redis_prefix}*"
            cursor = 0

            while True:
                cursor, keys = await self.redis_client.scan(cursor, match=pattern, count=100)

                for key in keys:
                    session_data = await self.redis_client.get(key)
                    if session_data:
                        try:
                            session = Session.parse_raw(session_data)

                            if session.active and session.expires_at > now:
                                if not session_type or session.session_type == session_type:
                                    count += 1
                        except (json.JSONDecodeError, ValueError, AttributeError):
                            pass

                if cursor == 0:
                    break
        else:
            for session in self.memory_storage.values():
                if session.active and session.expires_at > now:
                    if not session_type or session.session_type == session_type:
                        count += 1

        return count

    async def _store_session(self, session: Session):
        """Store session in backend"""

        key = f"{self.config.redis_prefix}{session.session_id}"
        ttl = int((session.expires_at - datetime.now(UTC)).total_seconds())

        if ttl <= 0:
            # Session already expired
            return

        session_data = session.json()

        if self.redis_client:
            await self.redis_client.setex(key, ttl, session_data)
        else:
            self.memory_storage[session.session_id] = session

    async def _retrieve_session(self, session_id: str) -> Session | None:
        """Retrieve session from backend"""

        if self.redis_client:
            key = f"{self.config.redis_prefix}{session_id}"
            session_data = await self.redis_client.get(key)

            if session_data:
                return Session.parse_raw(session_data)
        else:
            return self.memory_storage.get(session_id)

        return None

    async def _delete_session(self, session_id: str):
        """Delete session from backend"""

        if self.redis_client:
            key = f"{self.config.redis_prefix}{session_id}"
            await self.redis_client.delete(key)
        else:
            if session_id in self.memory_storage:
                del self.memory_storage[session_id]


# Singleton instance
_session_manager: SessionManager | None = None


def get_session_manager() -> SessionManager:
    """Get or create session manager instance"""
    global _session_manager

    if _session_manager is None:
        _session_manager = SessionManager()

    return _session_manager


# FastAPI dependency for session validation


async def get_current_session(
    session_token: str | None = Header(None, alias="X-Session-Token"),
) -> Session | None:
    """FastAPI dependency to get current session from header"""

    if not session_token:
        return None

    session_manager = get_session_manager()
    session = await session_manager.get_session(session_token)

    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    return session


async def require_session(session: Session | None = Depends(get_current_session)) -> Session:
    """FastAPI dependency to require valid session"""

    if not session:
        raise HTTPException(status_code=401, detail="Authentication required")

    return session


async def require_admin_session(session: Session = Depends(require_session)) -> Session:
    """FastAPI dependency to require admin session"""

    if session.session_type != SessionType.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")

    return session
