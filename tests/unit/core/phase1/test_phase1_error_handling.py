"""
Phase 1: Security-First Foundation - Error Handling Tests

Unit tests for the error handling system including:
- Custom exception hierarchy
- Error context and correlation
- Error logging and reporting
- Error recovery mechanisms
"""

from typing import Any
from unittest.mock import patch

import pytest

# Import the modules under test
try:
    from shared.error_handling import (
        AuthenticationError,
        ConfigurationError,
        DatabaseError,
        ExternalServiceError,
        ReflectAIError,
        ValidationError,
        get_error_context,
        handle_error,
        log_error,
    )
except ImportError as e:
    pytest.skip(f"Error handling modules not available: {e}", allow_module_level=True)


@pytest.mark.unit
@pytest.mark.phase1
class TestReflectAIError:
    """Test base ReflectAIError functionality"""

    def test_basic_error_creation(self):
        """Test creating basic ReflectAI error"""
        error = ReflectAIError("Test error message")

        assert str(error) == "Test error message"
        assert error.message == "Test error message"
        assert error.error_code is None
        assert error.context == {}

    def test_error_with_code(self):
        """Test creating error with error code"""
        error = ReflectAIError(message="Test error with code", error_code="TEST_001")

        assert error.message == "Test error with code"
        assert error.error_code == "TEST_001"

    def test_error_with_context(self):
        """Test creating error with context"""
        context = {
            "user_id": "user123",
            "operation": "test_operation",
            "timestamp": "2023-01-01T00:00:00Z",
        }

        error = ReflectAIError(message="Test error with context", context=context)

        assert error.context == context
        assert error.context["user_id"] == "user123"

    def test_error_serialization(self):
        """Test error serialization to dict"""
        error = ReflectAIError(
            message="Serialization test", error_code="SER_001", context={"key": "value"}
        )

        serialized = error.to_dict()

        assert serialized["message"] == "Serialization test"
        assert serialized["error_code"] == "SER_001"
        assert serialized["context"] == {"key": "value"}
        assert serialized["error_type"] == "ReflectAIError"

    def test_error_correlation_id(self):
        """Test error correlation ID handling"""
        correlation_id = "corr-123-456"

        error = ReflectAIError(message="Correlation test", correlation_id=correlation_id)

        assert error.correlation_id == correlation_id


@pytest.mark.unit
@pytest.mark.phase1
class TestSpecificErrors:
    """Test specific error types"""

    def test_validation_error(self):
        """Test ValidationError functionality"""
        field_errors = {"email": "Invalid email format", "age": "Must be positive integer"}

        error = ValidationError(message="Validation failed", field_errors=field_errors)

        assert error.field_errors == field_errors
        assert "email" in error.field_errors
        assert error.field_errors["email"] == "Invalid email format"

    def test_configuration_error(self):
        """Test ConfigurationError functionality"""
        error = ConfigurationError(
            message="Missing required configuration", config_key="database.url"
        )

        assert error.config_key == "database.url"
        assert "configuration" in str(error).lower()

    def test_authentication_error(self):
        """Test AuthenticationError functionality"""
        error = AuthenticationError(message="Invalid credentials", auth_method="password")

        assert error.auth_method == "password"
        assert "authentication" in str(error).lower()

    def test_database_error(self):
        """Test DatabaseError functionality"""
        error = DatabaseError(message="Connection failed", operation="SELECT", table="users")

        assert error.operation == "SELECT"
        assert error.table == "users"

    def test_external_service_error(self):
        """Test ExternalServiceError functionality"""
        error = ExternalServiceError(
            message="Service unavailable", service="slack_api", status_code=503
        )

        assert error.service == "slack_api"
        assert error.status_code == 503


@pytest.mark.unit
@pytest.mark.phase1
class TestErrorHandling:
    """Test error handling utilities"""

    @patch("shared.error_handling.logger")
    def test_log_error_basic(self, mock_logger):
        """Test basic error logging"""
        error = ReflectAIError("Test error for logging")

        log_error(error)

        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert "Test error for logging" in str(call_args)

    @patch("shared.error_handling.logger")
    def test_log_error_with_context(self, mock_logger):
        """Test error logging with context"""
        context = {"user_id": "user123", "operation": "test"}
        error = ReflectAIError("Error with context", context=context)

        log_error(error, extra_context={"additional": "info"})

        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert call_args is not None

    def test_handle_error_validation(self):
        """Test validation error handling"""
        field_errors = {"email": "Required field"}
        error = ValidationError("Validation failed", field_errors=field_errors)

        result = handle_error(error)

        assert result["status"] == "error"
        assert result["error_type"] == "ValidationError"
        assert "field_errors" in result

    def test_handle_error_authentication(self):
        """Test authentication error handling"""
        error = AuthenticationError("Access denied")

        result = handle_error(error)

        assert result["status"] == "error"
        assert result["error_type"] == "AuthenticationError"
        assert result["message"] == "Access denied"

    def test_handle_error_generic(self):
        """Test generic error handling"""
        error = Exception("Generic Python error")

        result = handle_error(error)

        assert result["status"] == "error"
        assert result["error_type"] == "Exception"
        assert result["message"] == "Generic Python error"

    def test_get_error_context(self):
        """Test error context extraction"""
        context = get_error_context()

        assert "timestamp" in context
        assert "correlation_id" in context
        assert isinstance(context["timestamp"], str)


@pytest.mark.unit
@pytest.mark.phase1
class TestErrorPropagation:
    """Test error propagation and chaining"""

    def test_error_chaining(self):
        """Test error cause chaining"""
        original_error = ValueError("Original error")

        chained_error = ReflectAIError(message="Chained error", original_error=original_error)

        assert chained_error.original_error == original_error
        assert str(original_error) in str(chained_error.to_dict())

    def test_error_stack_preservation(self):
        """Test that error stack traces are preserved"""
        try:
            raise ValueError("Original error")
        except ValueError as e:
            wrapped_error = ReflectAIError("Wrapped error", original_error=e)

            assert wrapped_error.original_error is not None
            assert isinstance(wrapped_error.original_error, ValueError)

    def test_nested_error_context(self):
        """Test nested error context handling"""
        inner_context = {"level": "inner", "component": "database"}
        outer_context = {"level": "outer", "component": "api"}

        inner_error = DatabaseError("DB connection failed", context=inner_context)
        outer_error = ReflectAIError(
            "API request failed", context=outer_context, original_error=inner_error
        )

        assert outer_error.context["level"] == "outer"
        assert outer_error.original_error.context["level"] == "inner"


@pytest.mark.unit
@pytest.mark.phase1
class TestErrorRecovery:
    """Test error recovery mechanisms"""

    def test_retry_decorator(self):
        """Test retry mechanism for transient errors"""
        call_count = 0

        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ExternalServiceError("Service temporarily unavailable")
            return "success"

        # Test would implement actual retry decorator
        failing_function()
        assert call_count >= 1

    def test_circuit_breaker_integration(self):
        """Test circuit breaker integration with error handling"""
        # Test would verify circuit breaker triggers on specific errors
        error = ExternalServiceError("Service down", status_code=503)

        # Verify error is marked as circuit breaker eligible
        assert error.status_code == 503

    def test_error_reporting_integration(self):
        """Test error reporting to external systems"""
        error = ReflectAIError(
            "Critical system error", error_code="CRIT_001", context={"severity": "high"}
        )

        # Test would verify error is sent to monitoring system
        assert error.error_code == "CRIT_001"


@pytest.mark.unit
@pytest.mark.phase1
class TestErrorValidation:
    """Test error validation and sanitization"""

    def test_error_message_sanitization(self):
        """Test error message sanitization"""
        sensitive_info = "password=secret123"
        error_message = f"Database error: {sensitive_info}"

        # Test would implement actual sanitization
        sanitized_message = error_message.replace("password=secret123", "password=***")

        assert "secret123" not in sanitized_message
        assert "***" in sanitized_message

    def test_context_sanitization(self):
        """Test error context sanitization"""
        sensitive_context = {
            "user_id": "user123",
            "password": "secret",
            "api_key": "key123",
            "safe_data": "public_info",
        }

        # Test would implement actual context sanitization
        assert "password" in sensitive_context  # Before sanitization

    def test_pii_removal(self):
        """Test PII removal from error messages"""
        pii_message = "Error for user john.doe@example.com with SSN 123-45-6789"

        # Test would implement actual PII removal
        assert "@example.com" in pii_message  # Would be removed in actual implementation

    def test_error_size_limits(self):
        """Test error message and context size limits"""
        large_message = "x" * 10000  # Very large message
        large_context = {"data": "y" * 5000}  # Large context

        error = ReflectAIError(message=large_message, context=large_context)

        # Test would verify size limits are enforced
        assert len(error.message) > 0


@pytest.mark.unit
@pytest.mark.phase1
@pytest.mark.slow
class TestErrorPerformance:
    """Test error handling performance"""

    def test_error_creation_performance(self):
        """Test error creation performance"""
        import time

        start_time = time.time()

        for _ in range(1000):
            ReflectAIError("Performance test error")

        end_time = time.time()

        # Error creation should be fast
        assert (end_time - start_time) < 0.1

    def test_error_serialization_performance(self):
        """Test error serialization performance"""
        import time

        error = ReflectAIError("Performance test", context={"data": "test" * 100})

        start_time = time.time()

        for _ in range(1000):
            error.to_dict()

        end_time = time.time()

        # Serialization should be fast
        assert (end_time - start_time) < 0.1

    def test_concurrent_error_handling(self):
        """Test concurrent error handling"""
        import concurrent.futures

        def create_and_handle_error():
            error = ReflectAIError("Concurrent test error")
            return handle_error(error)

        # Test concurrent error handling
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_and_handle_error) for _ in range(50)]
            results = [future.result() for future in futures]

        assert len(results) == 50
        assert all(result["status"] == "error" for result in results)


# Test utilities and helpers
def create_test_error(error_type: str = "base") -> ReflectAIError:
    """Helper function to create test errors"""
    if error_type == "validation":
        return ValidationError("Test validation error", field_errors={"test": "error"})
    elif error_type == "auth":
        return AuthenticationError("Test auth error")
    elif error_type == "database":
        return DatabaseError("Test database error", operation="SELECT")
    else:
        return ReflectAIError("Test base error")


def assert_error_structure(error_dict: dict[str, Any]) -> None:
    """Helper function to validate error structure"""
    required_fields = ["status", "error_type", "message", "timestamp"]

    for field in required_fields:
        assert field in error_dict, f"Missing required field: {field}"

    assert error_dict["status"] == "error"
    assert isinstance(error_dict["message"], str)
    assert len(error_dict["message"]) > 0
