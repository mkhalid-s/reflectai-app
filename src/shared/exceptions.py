"""
ReflectAI Error Handling Foundation

Comprehensive error handling patterns and standards following the
error-handling-standards.md specification for consistent error management
across all components.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class ErrorSeverity(str, Enum):
    """Error severity levels for proper handling and alerting."""

    CRITICAL = "critical"  # System-wide failure, immediate attention required
    ERROR = "error"  # Feature failure, affects user experience
    WARNING = "warning"  # Degraded performance, fallback used
    INFO = "info"  # Expected errors (rate limits, user input)
    DEBUG = "debug"  # Development/troubleshooting information


class ErrorCategory(str, Enum):
    """Error categories for classification and routing."""

    # System Errors
    DATABASE_ERROR = "database_error"
    NETWORK_ERROR = "network_error"
    CONFIGURATION_ERROR = "configuration_error"
    INFRASTRUCTURE_ERROR = "infrastructure_error"

    # Integration Errors
    SLACK_API_ERROR = "slack_api_error"
    LLM_PROVIDER_ERROR = "llm_provider_error"
    TEMPORAL_ERROR = "temporal_error"
    EXTERNAL_API_ERROR = "external_api_error"
    EXTERNAL_SERVICE_ERROR = "external_service_error"

    # Business Logic Errors
    VALIDATION_ERROR = "validation_error"
    AUTHORIZATION_ERROR = "authorization_error"
    AUTHENTICATION_ERROR = "authentication_error"
    BUSINESS_RULE_ERROR = "business_rule_error"
    DATA_INTEGRITY_ERROR = "data_integrity_error"

    # User Errors
    INPUT_ERROR = "input_error"
    PERMISSION_ERROR = "permission_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    RESOURCE_NOT_FOUND = "resource_not_found"


class ReflectAIError(Exception):
    """
    Base exception class for all ReflectAI errors.

    Provides structured error information, user-friendly messages,
    recovery suggestions, and comprehensive logging context.
    """

    def __init__(
        self,
        message: str,
        error_code: str,
        category: ErrorCategory,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: dict[str, Any] | None = None,
        user_message: str | None = None,
        recovery_suggestions: list[str] | None = None,
        cause: Exception | None = None,
    ):
        super().__init__(message)
        self.error_id = str(uuid.uuid4())
        self.timestamp = datetime.now(UTC)
        self.message = message
        self.error_code = error_code
        self.category = category
        self.severity = severity
        self.context = context or {}
        self.user_message = user_message or self._generate_user_message()
        self.recovery_suggestions = recovery_suggestions or []
        self.cause = cause

    def _generate_user_message(self) -> str:
        """Generate user-friendly error message based on category."""
        user_messages = {
            ErrorCategory.DATABASE_ERROR: "We're experiencing database issues. Please try again in a few moments.",
            ErrorCategory.SLACK_API_ERROR: "There's an issue connecting to Slack. Your request will be retried automatically.",
            ErrorCategory.LLM_PROVIDER_ERROR: "Our AI analysis service is temporarily unavailable. Please try again shortly.",
            ErrorCategory.VALIDATION_ERROR: "There was an issue with your request. Please check your input and try again.",
            ErrorCategory.RATE_LIMIT_ERROR: "You're sending requests too quickly. Please wait a moment before trying again.",
            ErrorCategory.AUTHORIZATION_ERROR: "You don't have permission to perform this action.",
            ErrorCategory.RESOURCE_NOT_FOUND: "The requested information couldn't be found.",
        }
        return user_messages.get(self.category, "An unexpected error occurred. Please try again.")

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary for logging and serialization."""
        return {
            "error_id": self.error_id,
            "timestamp": self.timestamp.isoformat(),
            "message": self.message,
            "error_code": self.error_code,
            "category": self.category.value,
            "severity": self.severity.value,
            "context": self.context,
            "user_message": self.user_message,
            "recovery_suggestions": self.recovery_suggestions,
            "cause": str(self.cause) if self.cause else None,
        }

    def __str__(self) -> str:
        return f"{self.error_code}: {self.message}"

    def __repr__(self) -> str:
        return f"ReflectAIError(error_id='{self.error_id}', code='{self.error_code}', category='{self.category.value}')"

    def to_response(self) -> dict[str, Any]:
        """Convert error to response format compatible with error middleware."""
        return {
            "error_id": self.error_id,
            "error_code": self.error_code,
            "severity": self.severity.value,
            "category": self.category.value,
            "message": self.message,
            "user_message": self.user_message,
            "recovery_suggestions": self.recovery_suggestions,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context,
        }


# Specialized Error Classes


class DatabaseError(ReflectAIError):
    """Database-related errors with query context."""

    def __init__(self, message: str, query: str | None = None, **kwargs) -> None:
        context = kwargs.get("context", {})
        if query:
            context["query"] = query
        kwargs["context"] = context
        super().__init__(
            message=message,
            error_code="DB_ERROR",
            category=ErrorCategory.DATABASE_ERROR,
            severity=ErrorSeverity.ERROR,
            **kwargs,
        )


class SlackAPIError(ReflectAIError):
    """Slack API integration errors with response context."""

    def __init__(
        self, message: str, api_method: str, response_code: int | None = None, **kwargs
    ) -> None:
        context = kwargs.get("context", {})
        context.update({"api_method": api_method, "response_code": response_code})
        kwargs["context"] = context
        super().__init__(
            message=message,
            error_code="SLACK_API_ERROR",
            category=ErrorCategory.SLACK_API_ERROR,
            severity=ErrorSeverity.WARNING,
            **kwargs,
        )


class LLMProviderError(ReflectAIError):
    """LLM provider errors with model and provider context."""

    def __init__(self, message: str, provider: str, model: str | None = None, **kwargs) -> None:
        context = kwargs.get("context", {})
        context.update({"provider": provider, "model": model})
        kwargs["context"] = context
        super().__init__(
            message=message,
            error_code="LLM_PROVIDER_ERROR",
            category=ErrorCategory.LLM_PROVIDER_ERROR,
            severity=ErrorSeverity.ERROR,
            **kwargs,
        )


class ValidationError(ReflectAIError):
    """Input validation errors with field context."""

    def __init__(self, message: str, field: str | None = None, value: Any = None, **kwargs) -> None:
        context = kwargs.get("context", {})
        context.update({"field": field, "invalid_value": str(value) if value is not None else None})
        kwargs["context"] = context
        user_message = f"Invalid {field}: {message}" if field else message
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            category=ErrorCategory.VALIDATION_ERROR,
            severity=ErrorSeverity.INFO,
            user_message=user_message,
            **kwargs,
        )


class TemporalWorkflowError(ReflectAIError):
    """Temporal workflow execution errors with workflow context."""

    def __init__(
        self,
        message: str,
        workflow_id: str | None = None,
        activity: str | None = None,
        **kwargs,
    ) -> None:
        context = kwargs.get("context", {})
        context.update({"workflow_id": workflow_id, "activity": activity})
        kwargs["context"] = context
        super().__init__(
            message=message,
            error_code="TEMPORAL_WORKFLOW_ERROR",
            category=ErrorCategory.TEMPORAL_ERROR,
            severity=ErrorSeverity.ERROR,
            **kwargs,
        )


class ConfigurationError(ReflectAIError):
    """Configuration and secrets management errors."""

    def __init__(self, message: str, config_key: str | None = None, **kwargs) -> None:
        context = kwargs.get("context", {})
        if config_key:
            context["config_key"] = config_key
        kwargs["context"] = context
        super().__init__(
            message=message,
            error_code="CONFIG_ERROR",
            category=ErrorCategory.CONFIGURATION_ERROR,
            severity=ErrorSeverity.CRITICAL,
            user_message="System configuration issue. Please contact support.",
            recovery_suggestions=["Contact system administrator"],
            **kwargs,
        )


class NetworkError(ReflectAIError):
    """Network connectivity and communication errors."""

    def __init__(self, message: str, service: str | None = None, **kwargs) -> None:
        context = kwargs.get("context", {})
        if service:
            context["service"] = service
        kwargs["context"] = context
        super().__init__(
            message=message,
            error_code="NETWORK_ERROR",
            category=ErrorCategory.NETWORK_ERROR,
            severity=ErrorSeverity.WARNING,
            user_message="Network connectivity issue. Please try again shortly.",
            recovery_suggestions=["Check network connection", "Try again in a few moments"],
            **kwargs,
        )


# Error Helper Functions


def is_retryable_error(error: Exception) -> bool:
    """
    Determine if an error is retryable based on its type and properties.

    Args:
        error: The exception to check

    Returns:
        True if the error should be retried, False otherwise
    """
    if isinstance(error, ReflectAIError):
        retryable_categories = {
            ErrorCategory.NETWORK_ERROR,
            ErrorCategory.LLM_PROVIDER_ERROR,
            ErrorCategory.SLACK_API_ERROR,
            ErrorCategory.INFRASTRUCTURE_ERROR,
        }
        return error.category in retryable_categories and error.severity != ErrorSeverity.CRITICAL

    # Common retryable standard exceptions
    retryable_types = {"ConnectionError", "TimeoutError", "TemporaryFailure", "ServiceUnavailable"}
    return type(error).__name__ in retryable_types


def get_error_recovery_actions(error: ReflectAIError) -> list[str]:
    """
    Get recovery actions for an error based on its category and context.

    Args:
        error: The ReflectAI error instance

    Returns:
        List of recovery actions for the user
    """
    if error.recovery_suggestions:
        return error.recovery_suggestions

    # Default recovery actions by category
    recovery_map = {
        ErrorCategory.DATABASE_ERROR: [
            "Try again in a few moments",
            "Contact support if issue persists",
        ],
        ErrorCategory.LLM_PROVIDER_ERROR: ["Wait a moment and try again", "Try a simpler request"],
        ErrorCategory.SLACK_API_ERROR: ["Check Slack connection", "Try again in a few moments"],
        ErrorCategory.VALIDATION_ERROR: ["Check your input format", "Refer to help documentation"],
        ErrorCategory.RATE_LIMIT_ERROR: ["Wait before trying again", "Reduce request frequency"],
        ErrorCategory.AUTHORIZATION_ERROR: ["Contact your administrator", "Check your permissions"],
        ErrorCategory.RESOURCE_NOT_FOUND: [
            "Check the request details",
            "Verify the resource exists",
        ],
    }

    return recovery_map.get(error.category, ["Try again", "Contact support if issue persists"])


class ExternalServiceError(ReflectAIError):
    """
    Raised when external service integration fails.

    This covers API failures, timeout issues, and
    service unavailability scenarios.
    """

    def __init__(self, message: str, service_name: str | None = None, **kwargs) -> None:
        context = kwargs.get("context", {})
        if service_name:
            context["service_name"] = service_name

        super().__init__(
            message=message,
            error_code=kwargs.get("error_code", "EXTERNAL_SERVICE_ERROR"),
            category=ErrorCategory.EXTERNAL_SERVICE_ERROR,
            severity=kwargs.get("severity", ErrorSeverity.ERROR),
            context=context,
            **{k: v for k, v in kwargs.items() if k not in ["error_code", "severity", "context"]},
        )


class AuthenticationError(ReflectAIError):
    """
    Raised when authentication fails.

    This covers OAuth2 failures, token validation issues,
    and permission denied scenarios.
    """

    def __init__(self, message: str, **kwargs) -> None:
        super().__init__(
            message=message,
            error_code=kwargs.get("error_code", "AUTHENTICATION_FAILED"),
            category=ErrorCategory.AUTHENTICATION_ERROR,
            severity=kwargs.get("severity", ErrorSeverity.WARNING),
            **{k: v for k, v in kwargs.items() if k not in ["error_code", "severity"]},
        )
