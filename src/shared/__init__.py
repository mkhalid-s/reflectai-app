"""
Shared Utilities Module for ReflectAI

This module contains shared utilities, error handling, and common components
used across the ReflectAI application.
"""

# Error handling foundation (Task 1)
from .error_handlers import (
    CircuitBreaker,
    ErrorContext,
    database_error_handler,
    error_context,
    handle_errors,
    handle_temporal_activity_errors,
    retry_with_exponential_backoff,
    safe_api_call,
    with_error_context,
)
from .error_metrics import (
    ErrorMetricsCollector,
    ErrorMetricsContext,
    create_metrics_collector,
    get_error_metrics_health,
    track_error,
)
from .exceptions import (
    ConfigurationError,
    # Specialized error classes
    DatabaseError,
    ErrorCategory,
    ErrorSeverity,
    LLMProviderError,
    NetworkError,
    # Base classes
    ReflectAIError,
    SlackAPIError,
    TemporalWorkflowError,
    ValidationError,
    get_error_recovery_actions,
    # Utility functions
    is_retryable_error,
)

# Unified logging foundation (Task 2)
from .logging import (
    LoggingContext,
    clear_logging_context,
    configure_logging,
    get_correlation_id,
    get_logger,
    get_logging_health,
    log_business_event,
    log_error_with_context,
    log_function_call,
    log_function_result,
    set_agent_context,
    set_correlation_id,
    set_user_context,
)


# Configuration - delegate to infrastructure layer
def get_config():
    """
    Get configuration settings.

    This is a compatibility shim that delegates to the infrastructure layer.
    Imports lazily to avoid circular dependencies.
    """
    try:
        from src.infrastructure.config.config_manager import get_config_manager

        manager = get_config_manager()
        return manager.get_config()
    except ImportError:
        # Fallback for testing or when config manager not available
        import os

        class SimpleConfig:
            def get(self, key, default=None):
                return os.environ.get(key, default)

        return SimpleConfig()


__all__ = [
    # Base error classes and enums
    "ReflectAIError",
    "ErrorCategory",
    "ErrorSeverity",
    # Specialized error classes
    "DatabaseError",
    "SlackAPIError",
    "LLMProviderError",
    "ValidationError",
    "TemporalWorkflowError",
    "ConfigurationError",
    "NetworkError",
    # Error handling utilities
    "is_retryable_error",
    "get_error_recovery_actions",
    "CircuitBreaker",
    "database_error_handler",
    "handle_errors",
    "retry_with_exponential_backoff",
    "safe_api_call",
    "handle_temporal_activity_errors",
    "ErrorContext",
    "error_context",
    "with_error_context",
    # Metrics and monitoring
    "ErrorMetricsCollector",
    "ErrorMetricsContext",
    "create_metrics_collector",
    "track_error",
    "get_error_metrics_health",
    # Unified logging foundation
    "configure_logging",
    "get_logger",
    "LoggingContext",
    "set_correlation_id",
    "get_correlation_id",
    "set_user_context",
    "set_agent_context",
    "clear_logging_context",
    "log_function_call",
    "log_function_result",
    "log_error_with_context",
    "log_business_event",
    "get_logging_health",
    # Configuration
    "get_config",
]
