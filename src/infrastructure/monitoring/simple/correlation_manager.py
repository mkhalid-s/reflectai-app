"""
Correlation ID Generation and Propagation for ReflectAI

Implements correlation ID strategy per Task 2b specification with
UUID4 generation, context propagation, and Slack thread mapping.
"""

import uuid
from datetime import UTC, datetime, timedelta

from src.shared.logging import LoggingContext, get_correlation_id, get_logger


class CorrelationIDManager:
    """
    Manages correlation IDs for request tracing and conversation continuity.

    Features:
    - Generate UUID4 correlation IDs for each user request
    - Map Slack thread_ts to correlation IDs
    - Propagate correlation IDs through system components
    - Handle conversation continuity across thread boundaries
    """

    def __init__(self):
        self.thread_to_correlation: dict[str, str] = {}
        self.correlation_to_thread: dict[str, str] = {}
        self.correlation_metadata: dict[str, dict] = {}
        self.logger = get_logger(__name__)

    def generate_correlation_id(self) -> str:
        """Generate a new UUID4 correlation ID."""
        return str(uuid.uuid4())

    def create_or_get_correlation_id(
        self,
        slack_thread_ts: str | None = None,
        user_id: str | None = None,
        team_id: str | None = None,
    ) -> str:
        """
        Create new correlation ID or get existing one for Slack thread.

        Args:
            slack_thread_ts: Slack thread timestamp
            user_id: User ID for context
            team_id: Team ID for context

        Returns:
            Correlation ID (new or existing)
        """
        # Check if we have existing correlation ID for this thread
        if slack_thread_ts and slack_thread_ts in self.thread_to_correlation:
            correlation_id = self.thread_to_correlation[slack_thread_ts]
            self.logger.debug(
                "Using existing correlation ID for thread",
                correlation_id=correlation_id,
                thread_ts=slack_thread_ts,
                user_id=user_id,
            )
            return correlation_id

        # Generate new correlation ID
        correlation_id = self.generate_correlation_id()

        # Map thread to correlation ID for continuity
        if slack_thread_ts:
            self.thread_to_correlation[slack_thread_ts] = correlation_id
            self.correlation_to_thread[correlation_id] = slack_thread_ts

        # Store metadata
        self.correlation_metadata[correlation_id] = {
            "created_at": datetime.now(UTC),
            "thread_ts": slack_thread_ts,
            "user_id": user_id,
            "team_id": team_id,
            "request_count": 0,
        }

        self.logger.info(
            "Generated new correlation ID",
            correlation_id=correlation_id,
            thread_ts=slack_thread_ts,
            user_id=user_id,
            team_id=team_id,
        )

        return correlation_id

    def get_correlation_for_thread(self, thread_ts: str) -> str | None:
        """Get correlation ID for Slack thread."""
        return self.thread_to_correlation.get(thread_ts)

    def get_thread_for_correlation(self, correlation_id: str) -> str | None:
        """Get Slack thread for correlation ID."""
        return self.correlation_to_thread.get(correlation_id)

    def increment_request_count(self, correlation_id: str):
        """Increment request count for correlation ID."""
        if correlation_id in self.correlation_metadata:
            self.correlation_metadata[correlation_id]["request_count"] += 1

    def update_context_for_correlation(
        self,
        correlation_id: str,
        user_id: str | None = None,
        team_id: str | None = None,
        additional_context: dict | None = None,
    ):
        """Update context information for correlation ID."""
        if correlation_id not in self.correlation_metadata:
            self.correlation_metadata[correlation_id] = {
                "created_at": datetime.now(UTC),
                "request_count": 0,
            }

        metadata = self.correlation_metadata[correlation_id]

        if user_id:
            metadata["user_id"] = user_id
        if team_id:
            metadata["team_id"] = team_id
        if additional_context:
            metadata.update(additional_context)

        metadata["last_updated"] = datetime.now(UTC)

    def cleanup_expired_correlations(self, max_age_hours: int = 24):
        """
        Clean up expired correlation ID mappings.

        Args:
            max_age_hours: Maximum age in hours before cleanup
        """
        cutoff_time = datetime.now(UTC) - timedelta(hours=max_age_hours)
        expired_correlations = []

        for correlation_id, metadata in self.correlation_metadata.items():
            if metadata.get("created_at", datetime.now(UTC)) < cutoff_time:
                expired_correlations.append(correlation_id)

        # Clean up expired correlations
        for correlation_id in expired_correlations:
            # Remove thread mapping
            thread_ts = self.correlation_to_thread.pop(correlation_id, None)
            if thread_ts:
                self.thread_to_correlation.pop(thread_ts, None)

            # Remove metadata
            self.correlation_metadata.pop(correlation_id, None)

        if expired_correlations:
            self.logger.info(
                "Cleaned up expired correlation IDs",
                count=len(expired_correlations),
                max_age_hours=max_age_hours,
            )

    def get_correlation_metadata(self, correlation_id: str) -> dict | None:
        """Get metadata for correlation ID."""
        return self.correlation_metadata.get(correlation_id)

    def get_active_correlations_count(self) -> int:
        """Get count of active correlation IDs."""
        return len(self.correlation_metadata)

    def get_thread_mappings_count(self) -> int:
        """Get count of active thread mappings."""
        return len(self.thread_to_correlation)


# Global correlation manager instance
correlation_manager = CorrelationIDManager()


class CorrelationContext:
    """
    Context manager for correlation ID propagation across async operations.

    Ensures correlation context is preserved across await boundaries and
    provides integration with logging context.

    Usage:
        async with CorrelationContext(correlation_id="abc123", user_id="U123456"):
            # All operations within this context will have correlation ID
            await some_async_operation()
    """

    def __init__(
        self,
        correlation_id: str | None = None,
        user_id: str | None = None,
        team_id: str | None = None,
        thread_ts: str | None = None,
        auto_generate: bool = True,
    ):
        self.correlation_id = correlation_id
        self.user_id = user_id
        self.team_id = team_id
        self.thread_ts = thread_ts
        self.auto_generate = auto_generate
        self.logging_context = None

    async def __aenter__(self):
        # Get or create correlation ID
        if not self.correlation_id and self.auto_generate:
            self.correlation_id = correlation_manager.create_or_get_correlation_id(
                slack_thread_ts=self.thread_ts, user_id=self.user_id, team_id=self.team_id
            )

        # Set up logging context
        self.logging_context = LoggingContext(
            correlation_id=self.correlation_id,
            user_id=self.user_id,
            team_id=self.team_id,
            auto_generate_correlation_id=False,
        )
        self.logging_context.__enter__()

        # Update correlation manager context
        if self.correlation_id:
            correlation_manager.update_context_for_correlation(
                self.correlation_id, user_id=self.user_id, team_id=self.team_id
            )
            correlation_manager.increment_request_count(self.correlation_id)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Clean up logging context
        if self.logging_context:
            self.logging_context.__exit__(exc_type, exc_val, exc_tb)


# Utility functions for correlation ID management


def get_or_create_correlation_id(
    thread_ts: str | None = None, user_id: str | None = None, team_id: str | None = None
) -> str:
    """
    Get existing or create new correlation ID for request context.

    Args:
        thread_ts: Slack thread timestamp
        user_id: User ID
        team_id: Team ID

    Returns:
        Correlation ID
    """
    # Check if we already have one in context
    existing_id = get_correlation_id()
    if existing_id:
        return existing_id

    # Create or get from thread mapping
    return correlation_manager.create_or_get_correlation_id(
        slack_thread_ts=thread_ts, user_id=user_id, team_id=team_id
    )


def propagate_correlation_headers() -> dict[str, str]:
    """
    Get HTTP headers for correlation ID propagation to external services.

    Returns:
        Dictionary of headers to include in HTTP requests
    """
    correlation_id = get_correlation_id()
    if correlation_id:
        return {
            "X-Correlation-ID": correlation_id,
            "X-Request-ID": correlation_id,  # Alternative header name
            "User-Agent": f"ReflectAI/2.0.0 (correlation-id: {correlation_id})",
        }
    return {}


def extract_correlation_from_headers(headers: dict[str, str]) -> str | None:
    """
    Extract correlation ID from HTTP headers.

    Args:
        headers: HTTP headers dictionary

    Returns:
        Correlation ID if found, None otherwise
    """
    # Try common correlation header names
    header_names = ["X-Correlation-ID", "X-Request-ID", "Correlation-ID", "Request-ID"]

    for header_name in header_names:
        # Check both exact case and lowercase
        correlation_id = headers.get(header_name) or headers.get(header_name.lower())
        if correlation_id:
            return correlation_id

    return None


# Health check and status functions


def get_correlation_health() -> dict[str, any]:
    """Get health status of correlation ID system."""
    return {
        "manager_ready": True,
        "active_correlations": correlation_manager.get_active_correlations_count(),
        "thread_mappings": correlation_manager.get_thread_mappings_count(),
        "current_correlation_id": get_correlation_id(),
        "context_active": get_correlation_id() is not None,
    }


def get_correlation_stats() -> dict[str, any]:
    """Get statistics about correlation ID usage."""
    active_count = correlation_manager.get_active_correlations_count()
    thread_mapping_count = correlation_manager.get_thread_mappings_count()

    return {
        "active_correlation_ids": active_count,
        "thread_mappings": thread_mapping_count,
        "mapping_efficiency": thread_mapping_count / max(active_count, 1),
        "current_context": {
            "correlation_id": get_correlation_id(),
            "has_context": get_correlation_id() is not None,
        },
    }
