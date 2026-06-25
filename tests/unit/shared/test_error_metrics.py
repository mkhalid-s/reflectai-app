"""
Tests for ReflectAI Error Metrics Collection

Comprehensive tests for Prometheus metrics tracking, error monitoring,
and alerting functionality.
"""

from unittest.mock import Mock, patch

import pytest

from src.shared.error_metrics import (
    ErrorMetricsCollector,
    ErrorMetricsContext,
    MockMetric,
    create_metrics_collector,
    get_error_metrics_health,
    track_error,
)
from src.shared.exceptions import (
    DatabaseError,
    ErrorCategory,
    ErrorSeverity,
    LLMProviderError,
    ReflectAIError,
    SlackAPIError,
)


class TestMockMetric:
    """Test MockMetric fallback."""

    def test_mock_metric_labels(self):
        """Test MockMetric labels method returns self."""
        metric = MockMetric()

        result = metric.labels(category="test", severity="error")

        assert result is metric

    def test_mock_metric_inc(self):
        """Test MockMetric inc method is no-op."""
        metric = MockMetric()

        # Should not raise exception
        metric.inc()
        metric.inc(5)

    def test_mock_metric_observe(self):
        """Test MockMetric observe method is no-op."""
        metric = MockMetric()

        # Should not raise exception
        metric.observe(1.23)
        metric.observe(0.0)

    def test_mock_metric_set(self):
        """Test MockMetric set method is no-op."""
        metric = MockMetric()

        # Should not raise exception
        metric.set(10)
        metric.set(0)


class TestErrorMetricsCollector:
    """Test ErrorMetricsCollector class."""

    def test_collector_initialization(self):
        """Test collector initializes with component name."""
        collector = ErrorMetricsCollector(component="test_component")

        assert collector.component == "test_component"

    def test_collector_default_component(self):
        """Test collector with default component name."""
        collector = ErrorMetricsCollector()

        assert collector.component == "unknown"

    @patch("src.shared.error_metrics.PROMETHEUS_AVAILABLE", True)
    @patch("src.shared.error_metrics.error_counter")
    def test_track_error_basic(self, mock_counter):
        """Test basic error tracking."""
        mock_labels = Mock()
        mock_counter.labels.return_value = mock_labels

        collector = ErrorMetricsCollector(component="test")
        error = ReflectAIError(
            message="Test error",
            error_code="TEST_ERROR",
            category=ErrorCategory.VALIDATION_ERROR,
            severity=ErrorSeverity.ERROR,
        )

        collector.track_error(error)

        # Verify metric was incremented
        mock_counter.labels.assert_called_once()
        mock_labels.inc.assert_called_once()

    @patch("src.shared.error_metrics.PROMETHEUS_AVAILABLE", True)
    @patch("src.shared.error_metrics.error_counter")
    @patch("src.shared.error_metrics.error_duration")
    def test_track_error_with_duration(self, mock_duration, mock_counter):
        """Test error tracking with processing duration."""
        mock_counter_labels = Mock()
        mock_duration_labels = Mock()
        mock_counter.labels.return_value = mock_counter_labels
        mock_duration.labels.return_value = mock_duration_labels

        collector = ErrorMetricsCollector(component="test")
        error = ReflectAIError(
            message="Test error",
            error_code="TEST_ERROR",
            category=ErrorCategory.DATABASE_ERROR,
        )

        collector.track_error(error, handler_type="retry", processing_duration=1.5)

        # Verify both metrics were updated
        mock_counter_labels.inc.assert_called_once()
        mock_duration_labels.observe.assert_called_once_with(1.5)

    @patch("src.shared.error_metrics.PROMETHEUS_AVAILABLE", False)
    def test_track_error_without_prometheus(self):
        """Test error tracking when Prometheus not available."""
        collector = ErrorMetricsCollector(component="test")
        error = ReflectAIError(
            message="Test error",
            error_code="TEST_ERROR",
            category=ErrorCategory.NETWORK_ERROR,
        )

        # Should not raise exception
        collector.track_error(error)

    @patch("src.shared.error_metrics.PROMETHEUS_AVAILABLE", True)
    @patch("src.shared.error_metrics.error_recovery_attempts")
    def test_track_recovery_attempt(self, mock_recovery):
        """Test tracking recovery attempts."""
        mock_labels = Mock()
        mock_recovery.labels.return_value = mock_labels

        collector = ErrorMetricsCollector(component="test")

        collector.track_recovery_attempt(ErrorCategory.DATABASE_ERROR, "retry", "success")

        mock_recovery.labels.assert_called_once_with(
            category="database_error",
            recovery_type="retry",
            outcome="success",
            component="test",
        )
        mock_labels.inc.assert_called_once()

    @patch("src.shared.error_metrics.PROMETHEUS_AVAILABLE", True)
    @patch("src.shared.error_metrics.circuit_breaker_state")
    def test_track_circuit_breaker_state(self, mock_state):
        """Test tracking circuit breaker state."""
        mock_labels = Mock()
        mock_state.labels.return_value = mock_labels

        collector = ErrorMetricsCollector(component="test")

        # Test all states
        collector.track_circuit_breaker_state("slack_api", "closed")
        mock_labels.set.assert_called_with(0)

        collector.track_circuit_breaker_state("slack_api", "half_open")
        mock_labels.set.assert_called_with(1)

        collector.track_circuit_breaker_state("slack_api", "open")
        mock_labels.set.assert_called_with(2)

    @patch("src.shared.error_metrics.PROMETHEUS_AVAILABLE", True)
    @patch("src.shared.error_metrics.circuit_breaker_failures")
    def test_track_circuit_breaker_failure(self, mock_failures):
        """Test tracking circuit breaker failures."""
        mock_labels = Mock()
        mock_failures.labels.return_value = mock_labels

        collector = ErrorMetricsCollector(component="test")

        collector.track_circuit_breaker_failure("llm_provider")

        mock_failures.labels.assert_called_once_with(service="llm_provider", component="test")
        mock_labels.inc.assert_called_once()

    @patch("src.shared.error_metrics.PROMETHEUS_AVAILABLE", True)
    @patch("src.shared.error_metrics.retry_attempts")
    def test_track_retry_attempt(self, mock_retry):
        """Test tracking retry attempts."""
        mock_labels = Mock()
        mock_retry.labels.return_value = mock_labels

        collector = ErrorMetricsCollector(component="test")

        # Test different outcomes
        collector.track_retry_attempt("database_query", "success")
        collector.track_retry_attempt("api_call", "failure")
        collector.track_retry_attempt("network_request", "exhausted")

        assert mock_labels.inc.call_count == 3

    @patch("src.shared.error_metrics.PROMETHEUS_AVAILABLE", True)
    @patch("src.shared.error_metrics.timeout_errors")
    def test_track_timeout_error(self, mock_timeout):
        """Test tracking timeout errors."""
        mock_labels = Mock()
        mock_timeout.labels.return_value = mock_labels

        collector = ErrorMetricsCollector(component="test")

        collector.track_timeout_error("api_call", 30.0)

        mock_timeout.labels.assert_called_once_with(
            operation="api_call", timeout_seconds="30", component="test"
        )
        mock_labels.inc.assert_called_once()

    @patch("src.shared.error_metrics.PROMETHEUS_AVAILABLE", True)
    @patch("src.shared.error_metrics.user_facing_errors")
    def test_track_user_facing_error(self, mock_user_errors):
        """Test tracking user-facing errors."""
        mock_labels = Mock()
        mock_user_errors.labels.return_value = mock_labels

        collector = ErrorMetricsCollector(component="test")
        error = ReflectAIError(
            message="User error",
            error_code="USER_ERROR",
            category=ErrorCategory.VALIDATION_ERROR,
            severity=ErrorSeverity.WARNING,
        )

        collector.track_user_facing_error(error, "slack")

        mock_user_errors.labels.assert_called_once_with(
            category="validation_error",
            severity="warning",
            notification_method="slack",
        )
        mock_labels.inc.assert_called_once()


class TestErrorMetricsContext:
    """Test ErrorMetricsContext context manager."""

    @patch("src.shared.error_metrics.PROMETHEUS_AVAILABLE", True)
    def test_context_manager_basic(self):
        """Test basic context manager usage."""
        collector = ErrorMetricsCollector(component="test")

        with ErrorMetricsContext(collector, "retry", ErrorCategory.DATABASE_ERROR):
            pass

        # Should not raise exception

    @patch("src.shared.error_metrics.PROMETHEUS_AVAILABLE", True)
    @patch("src.shared.error_metrics.error_duration")
    def test_context_manager_timing(self, mock_duration):
        """Test context manager tracks timing."""
        import time

        mock_labels = Mock()
        mock_duration.labels.return_value = mock_labels

        collector = ErrorMetricsCollector(component="test")

        with ErrorMetricsContext(collector, "retry", ErrorCategory.DATABASE_ERROR):
            time.sleep(0.01)  # Small delay

        # Should have observed duration
        # Can't verify exact value due to timing, but should be called
        mock_labels.observe.assert_called()
        call_args = mock_labels.observe.call_args[0]
        assert call_args[0] > 0  # Duration should be positive

    @patch("src.shared.error_metrics.PROMETHEUS_AVAILABLE", True)
    def test_context_manager_with_exception(self):
        """Test context manager handles exceptions."""
        collector = ErrorMetricsCollector(component="test")

        with pytest.raises(ReflectAIError):
            with ErrorMetricsContext(collector, "retry"):
                raise ReflectAIError(
                    message="Test error",
                    error_code="TEST",
                    category=ErrorCategory.DATABASE_ERROR,
                )

    @patch("src.shared.error_metrics.PROMETHEUS_AVAILABLE", True)
    def test_context_manager_tracks_error_on_exception(self):
        """Test context manager tracks error when exception raised."""
        collector = ErrorMetricsCollector(component="test")
        collector.track_error = Mock()

        error = ReflectAIError(
            message="Test error",
            error_code="TEST",
            category=ErrorCategory.DATABASE_ERROR,
        )

        with pytest.raises(ReflectAIError):
            with ErrorMetricsContext(collector, "retry"):
                raise error

        # Verify error was tracked
        collector.track_error.assert_called_once()


class TestUtilityFunctions:
    """Test utility functions."""

    def test_create_metrics_collector(self):
        """Test creating metrics collector."""
        collector = create_metrics_collector("test_component")

        assert isinstance(collector, ErrorMetricsCollector)
        assert collector.component == "test_component"

    @patch("src.shared.error_metrics.ErrorMetricsCollector")
    def test_track_error_convenience_function(self, mock_collector_class):
        """Test track_error convenience function."""
        mock_instance = Mock()
        mock_collector_class.return_value = mock_instance

        error = ReflectAIError(
            message="Test",
            error_code="TEST",
            category=ErrorCategory.NETWORK_ERROR,
        )

        track_error(error, "test_component")

        mock_collector_class.assert_called_once_with("test_component")
        mock_instance.track_error.assert_called_once_with(error)


class TestHealthCheck:
    """Test health check functionality."""

    @patch("src.shared.error_metrics.PROMETHEUS_AVAILABLE", True)
    def test_get_error_metrics_health_with_prometheus(self):
        """Test health check when Prometheus available."""
        health = get_error_metrics_health()

        assert health["prometheus_available"] is True
        assert health["metrics_registered"] is True
        assert health["collector_ready"] is True

    @patch("src.shared.error_metrics.PROMETHEUS_AVAILABLE", False)
    def test_get_error_metrics_health_without_prometheus(self):
        """Test health check when Prometheus not available."""
        health = get_error_metrics_health()

        assert health["prometheus_available"] is False
        assert health["metrics_registered"] is True
        assert health["collector_ready"] is True


class TestMetricRegistration:
    """Test metric registration and deduplication."""

    @patch("src.shared.error_metrics.PROMETHEUS_AVAILABLE", True)
    def test_metrics_dont_duplicate(self):
        """Test that metrics handle duplicate registration."""
        # Creating multiple collectors should not cause issues
        collector1 = ErrorMetricsCollector("component1")
        collector2 = ErrorMetricsCollector("component2")

        error = ReflectAIError(
            message="Test",
            error_code="TEST",
            category=ErrorCategory.VALIDATION_ERROR,
        )

        # Should not raise exception about duplicate metrics
        collector1.track_error(error)
        collector2.track_error(error)


class TestDifferentErrorTypes:
    """Test tracking different error types."""

    @patch("src.shared.error_metrics.PROMETHEUS_AVAILABLE", True)
    @patch("src.shared.error_metrics.error_counter")
    def test_track_database_error(self, mock_counter):
        """Test tracking database error."""
        mock_labels = Mock()
        mock_counter.labels.return_value = mock_labels

        collector = ErrorMetricsCollector(component="test")
        error = DatabaseError(
            message="DB error",
            query="SELECT * FROM users",
        )

        collector.track_error(error)

        # Verify correct category used
        call_args = mock_counter.labels.call_args[1]
        assert call_args["category"] == "database_error"

    @patch("src.shared.error_metrics.PROMETHEUS_AVAILABLE", True)
    @patch("src.shared.error_metrics.error_counter")
    def test_track_llm_provider_error(self, mock_counter):
        """Test tracking LLM provider error."""
        mock_labels = Mock()
        mock_counter.labels.return_value = mock_labels

        collector = ErrorMetricsCollector(component="test")
        error = LLMProviderError(
            message="LLM error",
            provider="openai",
            model="gpt-4",
        )

        collector.track_error(error)

        call_args = mock_counter.labels.call_args[1]
        assert call_args["category"] == "llm_provider_error"

    @patch("src.shared.error_metrics.PROMETHEUS_AVAILABLE", True)
    @patch("src.shared.error_metrics.error_counter")
    def test_track_slack_api_error(self, mock_counter):
        """Test tracking Slack API error."""
        mock_labels = Mock()
        mock_counter.labels.return_value = mock_labels

        collector = ErrorMetricsCollector(component="test")
        error = SlackAPIError(
            message="Slack error",
            api_method="chat.postMessage",
            response_code=429,
        )

        collector.track_error(error)

        call_args = mock_counter.labels.call_args[1]
        assert call_args["category"] == "slack_api_error"


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_collector_with_empty_component_name(self):
        """Test collector with empty component name."""
        collector = ErrorMetricsCollector(component="")

        assert collector.component == ""

    @patch("src.shared.error_metrics.PROMETHEUS_AVAILABLE", True)
    def test_track_error_with_none_duration(self):
        """Test tracking error with None duration."""
        collector = ErrorMetricsCollector(component="test")
        error = ReflectAIError(
            message="Test",
            error_code="TEST",
            category=ErrorCategory.INFRASTRUCTURE_ERROR,
        )

        # Should not raise exception
        collector.track_error(error, handler_type="retry", processing_duration=None)

    @patch("src.shared.error_metrics.PROMETHEUS_AVAILABLE", True)
    def test_track_error_with_zero_duration(self):
        """Test tracking error with zero duration."""
        collector = ErrorMetricsCollector(component="test")
        error = ReflectAIError(
            message="Test",
            error_code="TEST",
            category=ErrorCategory.INFRASTRUCTURE_ERROR,
        )

        # Should not raise exception
        collector.track_error(error, handler_type="retry", processing_duration=0.0)

    @patch("src.shared.error_metrics.PROMETHEUS_AVAILABLE", True)
    def test_track_circuit_breaker_unknown_state(self):
        """Test tracking circuit breaker with unknown state."""
        collector = ErrorMetricsCollector(component="test")

        # Should default to 0 (closed)
        collector.track_circuit_breaker_state("service", "unknown_state")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
