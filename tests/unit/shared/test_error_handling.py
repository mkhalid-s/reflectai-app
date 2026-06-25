"""
Tests for ReflectAI Error Handling Foundation

Basic tests to verify error handling components work correctly
following the error-handling-standards.md specification.
"""

from datetime import datetime

from src.shared import (
    DatabaseError,
    ErrorCategory,
    ErrorSeverity,
    ReflectAIError,
    ValidationError,
    get_error_recovery_actions,
    is_retryable_error,
)


class TestReflectAIError:
    """Test base ReflectAI error class."""

    def test_basic_error_creation(self):
        """Test basic error creation with required fields."""
        error = ReflectAIError(
            message="Test error message",
            error_code="TEST_ERROR",
            category=ErrorCategory.VALIDATION_ERROR,
            severity=ErrorSeverity.ERROR,
        )

        assert error.message == "Test error message"
        assert error.error_code == "TEST_ERROR"
        assert error.category == ErrorCategory.VALIDATION_ERROR
        assert error.severity == ErrorSeverity.ERROR
        assert error.error_id is not None
        assert isinstance(error.timestamp, datetime)
        assert error.user_message is not None
        assert isinstance(error.context, dict)
        assert isinstance(error.recovery_suggestions, list)

    def test_error_with_context(self):
        """Test error creation with context information."""
        context = {"user_id": "U123456", "operation": "test_operation"}

        error = ReflectAIError(
            message="Test error with context",
            error_code="TEST_ERROR_CONTEXT",
            category=ErrorCategory.DATABASE_ERROR,
            context=context,
        )

        assert error.context == context
        assert error.context["user_id"] == "U123456"
        assert error.context["operation"] == "test_operation"

    def test_error_to_dict(self):
        """Test error serialization to dictionary."""
        error = ReflectAIError(
            message="Test serialization",
            error_code="TEST_SERIALIZE",
            category=ErrorCategory.NETWORK_ERROR,
            severity=ErrorSeverity.WARNING,
            context={"test": "value"},
            recovery_suggestions=["Try again", "Contact support"],
        )

        error_dict = error.to_dict()

        assert error_dict["message"] == "Test serialization"
        assert error_dict["error_code"] == "TEST_SERIALIZE"
        assert error_dict["category"] == "network_error"
        assert error_dict["severity"] == "warning"
        assert error_dict["context"]["test"] == "value"
        assert len(error_dict["recovery_suggestions"]) == 2
        assert error_dict["error_id"] == error.error_id


class TestSpecializedErrors:
    """Test specialized error classes."""

    def test_database_error(self):
        """Test DatabaseError with query context."""
        error = DatabaseError(message="Connection failed", query="SELECT * FROM users")

        assert error.category == ErrorCategory.DATABASE_ERROR
        assert error.error_code == "DB_ERROR"
        assert error.context["query"] == "SELECT * FROM users"
        assert "database" in error.user_message.lower()

    def test_validation_error(self):
        """Test ValidationError with field context."""
        error = ValidationError(
            message="Invalid email format", field="email", value="invalid-email"
        )

        assert error.category == ErrorCategory.VALIDATION_ERROR
        assert error.severity == ErrorSeverity.INFO
        assert error.context["field"] == "email"
        assert error.context["invalid_value"] == "invalid-email"
        assert "Invalid email" in error.user_message


class TestErrorUtilities:
    """Test error utility functions."""

    def test_is_retryable_error(self):
        """Test retryable error detection."""
        # Retryable error
        network_error = ReflectAIError(
            message="Network timeout",
            error_code="NETWORK_TIMEOUT",
            category=ErrorCategory.NETWORK_ERROR,
            severity=ErrorSeverity.WARNING,
        )
        assert is_retryable_error(network_error) is True

        # Non-retryable error (critical)
        critical_error = ReflectAIError(
            message="Critical system failure",
            error_code="SYSTEM_FAILURE",
            category=ErrorCategory.NETWORK_ERROR,
            severity=ErrorSeverity.CRITICAL,
        )
        assert is_retryable_error(critical_error) is False

        # Non-retryable category
        validation_error = ValidationError(message="Invalid input", field="test")
        assert is_retryable_error(validation_error) is False

    def test_get_error_recovery_actions(self):
        """Test recovery actions generation."""
        error = ReflectAIError(
            message="Database connection failed",
            error_code="DB_CONNECTION_FAILED",
            category=ErrorCategory.DATABASE_ERROR,
        )

        actions = get_error_recovery_actions(error)
        assert isinstance(actions, list)
        assert len(actions) > 0
        assert any("try again" in action.lower() for action in actions)
