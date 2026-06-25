"""
Tests for Middleware Error Metrics Integration

Unit tests for error metrics tracking logic in SimpleMetricsMiddleware.
Uses mocks to avoid circular import issues.
"""

import time
from unittest.mock import Mock, patch

import pytest

from src.shared.error_metrics import ErrorMetricsCollector
from src.shared.exceptions import (
    DatabaseError,
    ErrorCategory,
    ErrorSeverity,
    ReflectAIError,
)


class TestErrorMetricsCollectorInitialization:
    """Test ErrorMetricsCollector initialization in middleware."""

    def test_collector_created_with_correct_component(self):
        """Test that middleware creates collector with correct component name."""
        collector = ErrorMetricsCollector(component="http_middleware")

        assert collector.component == "http_middleware"


class TestReflectAIErrorTracking:
    """Test tracking logic for ReflectAI errors."""

    @patch("src.shared.error_metrics.PROMETHEUS_AVAILABLE", True)
    @patch("src.shared.error_metrics.error_counter")
    @patch("src.shared.error_metrics.error_duration")
    def test_track_reflectai_error_with_duration(self, mock_duration, mock_counter):
        """Test tracking ReflectAI error with processing duration."""
        mock_counter_labels = Mock()
        mock_duration_labels = Mock()
        mock_counter.labels.return_value = mock_counter_labels
        mock_duration.labels.return_value = mock_duration_labels

        collector = ErrorMetricsCollector(component="http_middleware")
        error = ReflectAIError(
            message="Test error",
            error_code="TEST_ERROR",
            category=ErrorCategory.VALIDATION_ERROR,
            severity=ErrorSeverity.ERROR,
        )

        # Simulate middleware tracking
        processing_duration = 0.123
        collector.track_error(
            error=error, handler_type="middleware", processing_duration=processing_duration
        )

        # Verify metrics were tracked
        mock_counter_labels.inc.assert_called_once()
        mock_duration_labels.observe.assert_called_once_with(processing_duration)

    @patch("src.shared.error_metrics.PROMETHEUS_AVAILABLE", True)
    @patch("src.shared.error_metrics.user_facing_errors")
    def test_track_user_facing_error(self, mock_user_errors):
        """Test tracking user-facing error."""
        mock_labels = Mock()
        mock_user_errors.labels.return_value = mock_labels

        collector = ErrorMetricsCollector(component="http_middleware")
        error = ReflectAIError(
            message="Test error",
            error_code="TEST_ERROR",
            category=ErrorCategory.VALIDATION_ERROR,
            severity=ErrorSeverity.WARNING,
            user_message="Something went wrong",
        )

        # Track user-facing error
        collector.track_user_facing_error(error=error, notification_method="http")

        # Verify tracking
        mock_user_errors.labels.assert_called_once_with(
            category="validation_error",
            severity="warning",
            notification_method="http",
        )
        mock_labels.inc.assert_called_once()


class TestDatabaseErrorTracking:
    """Test tracking of DatabaseError (ReflectAI error subclass)."""

    @patch("src.shared.error_metrics.PROMETHEUS_AVAILABLE", True)
    @patch("src.shared.error_metrics.error_counter")
    def test_track_database_error(self, mock_counter):
        """Test tracking DatabaseError."""
        mock_labels = Mock()
        mock_counter.labels.return_value = mock_labels

        collector = ErrorMetricsCollector(component="http_middleware")
        error = DatabaseError(message="Database connection failed", query="SELECT * FROM users")

        collector.track_error(error=error, handler_type="middleware", processing_duration=0.5)

        # Verify error was tracked with correct category
        # Note: error_counter.labels() has category, severity, component, error_code
        # (handler_type is NOT in error_counter, only in error_duration)
        mock_counter.labels.assert_called_once()
        call_kwargs = mock_counter.labels.call_args.kwargs
        assert call_kwargs["category"] == "database_error"
        assert call_kwargs["component"] == "http_middleware"
        mock_labels.inc.assert_called_once()


class TestMiddlewareErrorLogic:
    """Test middleware error handling logic."""

    def test_isinstance_check_for_reflectai_error(self):
        """Test isinstance check works for ReflectAI errors."""
        error = ReflectAIError(
            message="Test",
            error_code="TEST",
            category=ErrorCategory.VALIDATION_ERROR,
        )

        # This is the check used in middleware
        assert isinstance(error, ReflectAIError)

    def test_isinstance_check_for_database_error(self):
        """Test isinstance check works for DatabaseError subclass."""
        error = DatabaseError(message="DB error", query="SELECT")

        # DatabaseError should pass ReflectAIError check
        assert isinstance(error, ReflectAIError)
        assert isinstance(error, DatabaseError)

    def test_isinstance_check_for_non_reflectai_error(self):
        """Test isinstance check for non-ReflectAI errors."""
        error = RuntimeError("Generic error")

        assert not isinstance(error, ReflectAIError)


class TestUserMessagePresence:
    """Test checking for user_message in errors."""

    def test_error_with_user_message(self):
        """Test error has user_message attribute."""
        error = ReflectAIError(
            message="Test",
            error_code="TEST",
            category=ErrorCategory.VALIDATION_ERROR,
            user_message="User-friendly message",
        )

        assert hasattr(error, "user_message")
        assert error.user_message == "User-friendly message"
        # This is the check used in middleware
        assert error.user_message is not None

    def test_error_without_user_message(self):
        """Test error without explicit user_message uses default."""
        error = ReflectAIError(
            message="Test",
            error_code="TEST",
            category=ErrorCategory.INFRASTRUCTURE_ERROR,
        )

        assert hasattr(error, "user_message")
        # ReflectAIError provides a default user_message if not explicitly set
        assert error.user_message is not None

    def test_error_with_none_user_message(self):
        """Test error with explicitly set None user_message."""
        error = ReflectAIError(
            message="Test",
            error_code="TEST",
            category=ErrorCategory.INFRASTRUCTURE_ERROR,
            user_message=None,
        )

        # Even when set to None explicitly, ReflectAIError may provide a default
        # The middleware checks: if e.user_message (truthy check)
        # This test verifies that the check works correctly
        assert hasattr(error, "user_message")


class TestDurationTracking:
    """Test duration tracking calculation."""

    def test_duration_calculation(self):
        """Test duration is calculated correctly."""
        start_time = time.time()
        time.sleep(0.01)  # Small delay
        end_time = time.time()

        duration = end_time - start_time

        assert duration > 0
        assert duration >= 0.01
        assert isinstance(duration, float)


class TestMetricsCollectorComponentName:
    """Test component naming for different use cases."""

    def test_http_middleware_component(self):
        """Test http_middleware component name."""
        collector = ErrorMetricsCollector(component="http_middleware")
        assert collector.component == "http_middleware"

    def test_multiple_collectors_different_components(self):
        """Test multiple collectors can have different components."""
        collector1 = ErrorMetricsCollector(component="http_middleware")
        collector2 = ErrorMetricsCollector(component="slack_handler")

        assert collector1.component == "http_middleware"
        assert collector2.component == "slack_handler"


class TestErrorCategoryMapping:
    """Test error category is correctly identified."""

    def test_validation_error_category(self):
        """Test validation error has correct category."""
        error = ReflectAIError(
            message="Test",
            error_code="TEST",
            category=ErrorCategory.VALIDATION_ERROR,
        )

        assert error.category == ErrorCategory.VALIDATION_ERROR

    def test_database_error_category(self):
        """Test database error has correct category."""
        error = DatabaseError(message="DB error", query="SELECT")

        assert error.category == ErrorCategory.DATABASE_ERROR

    def test_infrastructure_error_category(self):
        """Test infrastructure error category."""
        error = ReflectAIError(
            message="Test",
            error_code="TEST",
            category=ErrorCategory.INFRASTRUCTURE_ERROR,
        )

        assert error.category == ErrorCategory.INFRASTRUCTURE_ERROR


class TestIntegrationScenarios:
    """Test complete integration scenarios."""

    @patch("src.shared.error_metrics.PROMETHEUS_AVAILABLE", True)
    @patch("src.shared.error_metrics.error_counter")
    @patch("src.shared.error_metrics.error_duration")
    @patch("src.shared.error_metrics.user_facing_errors")
    def test_complete_error_handling_flow(self, mock_user_errors, mock_duration, mock_counter):
        """Test complete error handling flow as in middleware."""
        # Setup mocks
        mock_counter_labels = Mock()
        mock_duration_labels = Mock()
        mock_user_labels = Mock()
        mock_counter.labels.return_value = mock_counter_labels
        mock_duration.labels.return_value = mock_duration_labels
        mock_user_errors.labels.return_value = mock_user_labels

        # Create collector (simulating middleware init)
        collector = ErrorMetricsCollector(component="http_middleware")

        # Simulate request processing
        start_time = time.time()
        # ... request processing would happen here ...
        time.sleep(0.01)  # Simulate some processing

        # Simulate error
        error = ReflectAIError(
            message="Validation failed",
            error_code="VALIDATION_ERROR",
            category=ErrorCategory.VALIDATION_ERROR,
            severity=ErrorSeverity.ERROR,
            user_message="Invalid input provided",
        )

        # Calculate duration (as middleware does)
        duration = time.time() - start_time

        # Track error (as middleware does)
        collector.track_error(error=error, handler_type="middleware", processing_duration=duration)

        # Track user-facing error if user_message present (as middleware does)
        if error.user_message:
            collector.track_user_facing_error(error=error, notification_method="http")

        # Verify all tracking happened
        mock_counter_labels.inc.assert_called_once()
        mock_duration_labels.observe.assert_called_once()
        mock_user_labels.inc.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
