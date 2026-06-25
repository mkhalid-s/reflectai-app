"""
Unified Logging and Observability Foundation for ReflectAI

Implements Structlog-based logging with correlation IDs, context management,
and structured output following the Task 2 specification.
"""

import logging
import sys
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

try:
    import structlog

    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False
    # Will be available when structlog is installed

# Context variables for thread-safe correlation ID storage
correlation_id_ctx: ContextVar[str | None] = ContextVar("correlation_id", default=None)
user_id_ctx: ContextVar[str | None] = ContextVar("user_id", default=None)
team_id_ctx: ContextVar[str | None] = ContextVar("team_id", default=None)
request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
agent_context_ctx: ContextVar[dict[str, Any] | None] = ContextVar("agent_context", default=None)


def configure_logging(
    environment: str = "development",
    log_level: str = "INFO",
    json_format: bool = None,
    log_file: str | None = None,
) -> None:
    """
    Configure unified logging system with Structlog.

    Args:
        environment: Environment name (development, staging, production)
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Use JSON formatting (None = auto-detect based on environment)
        log_file: Optional log file path
    """
    if not STRUCTLOG_AVAILABLE:
        # Fallback to standard logging if structlog is not available
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.StreamHandler(sys.stdout)],
        )
        return

    # Auto-detect JSON formatting based on environment
    if json_format is None:
        json_format = environment in ("staging", "production")

    # Configure processors chain
    processors = [
        # Add correlation ID and context to all log entries
        add_correlation_context,
        add_user_context,
        add_request_context,
        add_agent_context,
        # Standard processors
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if json_format:
        # Production/Staging: JSON structured logs
        processors.append(structlog.processors.JSONRenderer())
    else:
        # Development: Human-readable console output
        processors.extend(
            [structlog.processors.add_log_level, structlog.dev.ConsoleRenderer(colors=True)]
        )

    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, log_level.upper()),
        handlers=_create_handlers(environment, log_file),
    )


def _create_handlers(environment: str, log_file: str | None) -> list:
    """Create logging handlers based on environment and configuration."""
    handlers = [logging.StreamHandler(sys.stdout)]

    if log_file:
        # Add file handler with rotation
        try:
            from logging.handlers import RotatingFileHandler

            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=100 * 1024 * 1024,  # 100MB
                backupCount=30,  # 30-day retention
            )
            handlers.append(file_handler)
        except ImportError:
            # Fallback to basic file handler
            handlers.append(logging.FileHandler(log_file))

    return handlers


# Context processors for Structlog


def add_correlation_context(_, __, event_dict):
    """Add correlation ID to log entries."""
    correlation_id = correlation_id_ctx.get()
    if correlation_id:
        event_dict["correlation_id"] = correlation_id
    return event_dict


def add_user_context(_, __, event_dict):
    """Add user context to log entries."""
    user_id = user_id_ctx.get()
    team_id = team_id_ctx.get()

    if user_id:
        event_dict["user_id"] = user_id
    if team_id:
        event_dict["team_id"] = team_id

    return event_dict


def add_request_context(_, __, event_dict):
    """Add request context to log entries."""
    request_id = request_id_ctx.get()
    if request_id:
        event_dict["request_id"] = request_id
    return event_dict


def add_agent_context(_, __, event_dict):
    """Add agent context to log entries."""
    agent_context = agent_context_ctx.get()
    if agent_context:
        event_dict.update(
            {
                "agent_type": agent_context.get("agent_type"),
                "model_used": agent_context.get("model"),
                "workflow_stage": agent_context.get("stage"),
            }
        )
    return event_dict


class LoggingContext:
    """
    Context manager for setting logging context variables.

    Usage:
        with LoggingContext(correlation_id="abc123", user_id="U123456"):
            logger.info("Processing user request")
    """

    def __init__(
        self,
        correlation_id: str | None = None,
        user_id: str | None = None,
        team_id: str | None = None,
        request_id: str | None = None,
        agent_context: dict[str, Any] | None = None,
        auto_generate_correlation_id: bool = True,
    ):
        self.correlation_id = correlation_id or (
            str(uuid.uuid4()) if auto_generate_correlation_id else None
        )
        self.user_id = user_id
        self.team_id = team_id
        self.request_id = request_id
        self.agent_context = agent_context

        # Store original values for restoration
        self._original_correlation_id = None
        self._original_user_id = None
        self._original_team_id = None
        self._original_request_id = None
        self._original_agent_context = None

    def __enter__(self):
        # Store original values
        self._original_correlation_id = correlation_id_ctx.get()
        self._original_user_id = user_id_ctx.get()
        self._original_team_id = team_id_ctx.get()
        self._original_request_id = request_id_ctx.get()
        self._original_agent_context = agent_context_ctx.get()

        # Set new values
        if self.correlation_id:
            correlation_id_ctx.set(self.correlation_id)
        if self.user_id:
            user_id_ctx.set(self.user_id)
        if self.team_id:
            team_id_ctx.set(self.team_id)
        if self.request_id:
            request_id_ctx.set(self.request_id)
        if self.agent_context:
            agent_context_ctx.set(self.agent_context)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore original values
        correlation_id_ctx.set(self._original_correlation_id)
        user_id_ctx.set(self._original_user_id)
        team_id_ctx.set(self._original_team_id)
        request_id_ctx.set(self._original_request_id)
        agent_context_ctx.set(self._original_agent_context)


def get_logger(name: str = None):
    """
    Get a configured logger instance.

    Args:
        name: Logger name (defaults to calling module name)

    Returns:
        Configured logger instance (Structlog or standard logger)
    """
    if STRUCTLOG_AVAILABLE:
        return structlog.get_logger(name)
    else:
        return logging.getLogger(name or __name__)


def set_correlation_id(correlation_id: str):
    """Set correlation ID for current context."""
    correlation_id_ctx.set(correlation_id)


def get_correlation_id() -> str | None:
    """Get correlation ID from current context."""
    return correlation_id_ctx.get()


def set_user_context(user_id: str, team_id: str | None = None):
    """Set user context for current request."""
    user_id_ctx.set(user_id)
    if team_id:
        team_id_ctx.set(team_id)


def set_agent_context(agent_type: str, model: str | None = None, stage: str | None = None):
    """Set agent context for current operation."""
    context = {
        "agent_type": agent_type,
        "model": model,
        "stage": stage,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    agent_context_ctx.set(context)


def clear_logging_context():
    """Clear all logging context variables."""
    correlation_id_ctx.set(None)
    user_id_ctx.set(None)
    team_id_ctx.set(None)
    request_id_ctx.set(None)
    agent_context_ctx.set(None)


# Utility functions for common logging patterns


def log_function_call(logger, func_name: str, **kwargs):
    """Log function call with parameters."""
    logger.debug(
        "Function called",
        function=func_name,
        parameters={k: str(v)[:100] for k, v in kwargs.items()},  # Truncate long values
    )


def log_function_result(logger, func_name: str, duration_ms: float, success: bool = True, **kwargs):
    """Log function completion with timing."""
    logger.info(
        "Function completed", function=func_name, duration_ms=duration_ms, success=success, **kwargs
    )


def log_error_with_context(logger, error: Exception, operation: str, **context):
    """Log error with full context information."""
    logger.error(
        "Operation failed",
        operation=operation,
        error_type=type(error).__name__,
        error_message=str(error),
        **context,
        exc_info=True,
    )


def log_business_event(logger, event_type: str, **event_data):
    """Log business event with structured data."""
    logger.info(
        "Business event occurred",
        event_type=event_type,
        timestamp=datetime.now(UTC).isoformat(),
        **event_data,
    )


# Health check for logging system
def get_logging_health() -> dict[str, Any]:
    """
    Get health status of logging system.

    Returns:
        Dictionary with health status information
    """
    return {
        "structlog_available": STRUCTLOG_AVAILABLE,
        "correlation_id_enabled": correlation_id_ctx.get() is not None,
        "current_correlation_id": correlation_id_ctx.get(),
        "context_variables_active": {
            "correlation_id": correlation_id_ctx.get() is not None,
            "user_id": user_id_ctx.get() is not None,
            "team_id": team_id_ctx.get() is not None,
            "agent_context": agent_context_ctx.get() is not None,
        },
    }
