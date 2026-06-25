"""
Error Metrics Collection for ReflectAI

Prometheus metrics for error tracking, monitoring, and alerting
following the error-handling-standards.md specification.
"""

import time
from typing import Any

from .exceptions import ErrorCategory, ReflectAIError


class MockMetric:
    """Mock metric for when Prometheus is unavailable or duplicates exist."""

    def labels(self, **labels: Any) -> "MockMetric":
        return self

    def inc(self, amount: int = 1) -> None:
        pass

    def observe(self, amount: float) -> None:
        pass

    def set(self, amount: float) -> None:
        pass


try:
    from prometheus_client import REGISTRY, Counter, Gauge, Histogram

    PROMETHEUS_AVAILABLE = True
except ImportError:
    # Metrics will be no-ops if prometheus_client is not available
    PROMETHEUS_AVAILABLE = False
    Counter = Histogram = Gauge = lambda *args, **kwargs: MockMetric()

# Error Metrics Definitions - Use singleton pattern to avoid duplicates
_metrics_initialized = False
_metrics: dict[str, Any] = {}


def _get_or_create_metric(name: str, metric_type: Any, description: str, labels: list[str]) -> Any:
    """Get or create a metric, avoiding duplicates."""
    global _metrics_initialized, _metrics

    if name in _metrics:
        return _metrics[name]

    if PROMETHEUS_AVAILABLE:
        # Check if metric already exists in registry
        for collector in list(REGISTRY._collector_to_names):
            if hasattr(collector, "_name") and collector._name == name:
                _metrics[name] = collector
                return collector

    # Create new metric with error handling
    try:
        metric = metric_type(name, description, labels)
        _metrics[name] = metric
        return metric
    except ValueError as e:
        # If duplicate exists, find and return it
        if "Duplicated timeseries" in str(e):
            for collector in list(REGISTRY._collector_to_names):
                if hasattr(collector, "_name") and collector._name == name:
                    _metrics[name] = collector
                    return collector
        # If not found or other error, return mock metric
        return MockMetric()


error_counter = _get_or_create_metric(
    "reflectai_errors_total",
    Counter,
    "Total number of errors by category, severity, and component",
    ["category", "severity", "component", "error_code"],
)

error_duration = _get_or_create_metric(
    "reflectai_error_handling_duration_seconds",
    Histogram,
    "Time spent handling errors by category and handler type",
    ["category", "handler_type", "component"],
)

error_recovery_attempts = _get_or_create_metric(
    "reflectai_error_recovery_attempts_total",
    Counter,
    "Error recovery attempts and outcomes",
    ["category", "recovery_type", "outcome", "component"],
)

circuit_breaker_state = _get_or_create_metric(
    "reflectai_circuit_breaker_state",
    Gauge,
    "Circuit breaker state (0=closed, 1=half_open, 2=open)",
    ["service", "component"],
)

circuit_breaker_failures = _get_or_create_metric(
    "reflectai_circuit_breaker_failures_total",
    Counter,
    "Circuit breaker failure count by service",
    ["service", "component"],
)

retry_attempts = _get_or_create_metric(
    "reflectai_retry_attempts_total",
    Counter,
    "Retry attempts by operation and outcome",
    ["operation", "outcome", "component"],
)

timeout_errors = _get_or_create_metric(
    "reflectai_timeout_errors_total",
    Counter,
    "Timeout errors by operation and timeout duration",
    ["operation", "timeout_seconds", "component"],
)

user_facing_errors = _get_or_create_metric(
    "reflectai_user_facing_errors_total",
    Counter,
    "Errors that resulted in user notifications",
    ["category", "severity", "notification_method"],
)


class ErrorMetricsCollector:
    """
    Centralized error metrics collection with contextual information.
    """

    def __init__(self, component: str = "unknown") -> None:
        self.component = component

    def track_error(
        self,
        error: ReflectAIError,
        handler_type: str | None = None,
        processing_duration: float | None = None,
    ) -> None:
        """
        Track error occurrence with comprehensive metrics.

        Args:
            error: The ReflectAI error instance
            handler_type: Type of error handler (e.g., "circuit_breaker", "retry")
            processing_duration: Time spent processing the error
        """
        if not PROMETHEUS_AVAILABLE:
            return

        # Basic error count
        error_counter.labels(
            category=error.category.value,
            severity=error.severity.value,
            component=self.component,
            error_code=error.error_code,
        ).inc()

        # Error handling duration
        if processing_duration is not None and handler_type:
            error_duration.labels(
                category=error.category.value, handler_type=handler_type, component=self.component
            ).observe(processing_duration)

    def track_recovery_attempt(
        self, error_category: ErrorCategory, recovery_type: str, outcome: str
    ) -> None:
        """
        Track error recovery attempts.

        Args:
            error_category: Category of the error being recovered
            recovery_type: Type of recovery (e.g., "retry", "fallback", "circuit_breaker")
            outcome: Outcome of recovery ("success" or "failure")
        """
        if not PROMETHEUS_AVAILABLE:
            return

        error_recovery_attempts.labels(
            category=error_category.value,
            recovery_type=recovery_type,
            outcome=outcome,
            component=self.component,
        ).inc()

    def track_circuit_breaker_state(self, service: str, state: str) -> None:
        """
        Track circuit breaker state changes.

        Args:
            service: Service name (e.g., "slack_api", "llm_provider")
            state: Circuit breaker state ("closed", "half_open", "open")
        """
        if not PROMETHEUS_AVAILABLE:
            return

        state_values = {"closed": 0, "half_open": 1, "open": 2}
        circuit_breaker_state.labels(service=service, component=self.component).set(
            state_values.get(state, 0)
        )

    def track_circuit_breaker_failure(self, service: str) -> None:
        """Track circuit breaker failures."""
        if not PROMETHEUS_AVAILABLE:
            return

        circuit_breaker_failures.labels(service=service, component=self.component).inc()

    def track_retry_attempt(self, operation: str, outcome: str) -> None:
        """
        Track retry attempts.

        Args:
            operation: Operation being retried
            outcome: Outcome ("success", "failure", "exhausted")
        """
        if not PROMETHEUS_AVAILABLE:
            return

        retry_attempts.labels(operation=operation, outcome=outcome, component=self.component).inc()

    def track_timeout_error(self, operation: str, timeout_seconds: float) -> None:
        """
        Track timeout errors.

        Args:
            operation: Operation that timed out
            timeout_seconds: Timeout duration
        """
        if not PROMETHEUS_AVAILABLE:
            return

        timeout_errors.labels(
            operation=operation, timeout_seconds=str(int(timeout_seconds)), component=self.component
        ).inc()

    def track_user_facing_error(
        self, error: ReflectAIError, notification_method: str = "slack"
    ) -> None:
        """
        Track errors that resulted in user notifications.

        Args:
            error: The error that was shown to the user
            notification_method: How the user was notified ("slack", "email", "api")
        """
        if not PROMETHEUS_AVAILABLE:
            return

        user_facing_errors.labels(
            category=error.category.value,
            severity=error.severity.value,
            notification_method=notification_method,
        ).inc()


class ErrorMetricsContext:
    """
    Context manager for timing error handling operations.

    Usage:
        with ErrorMetricsContext(metrics_collector, "retry", error_category):
            # error handling code
            pass
    """

    def __init__(
        self,
        collector: ErrorMetricsCollector,
        handler_type: str,
        error_category: ErrorCategory | None = None,
    ):
        self.collector = collector
        self.handler_type = handler_type
        self.error_category = error_category
        self.start_time: float | None = None

    def __enter__(self) -> "ErrorMetricsContext":
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.start_time is not None:
            duration = time.time() - self.start_time

            if exc_val and isinstance(exc_val, ReflectAIError):
                self.collector.track_error(
                    error=exc_val, handler_type=self.handler_type, processing_duration=duration
                )
            elif self.error_category:
                # Track processing time even without exception
                if PROMETHEUS_AVAILABLE:
                    error_duration.labels(
                        category=self.error_category.value,
                        handler_type=self.handler_type,
                        component=self.collector.component,
                    ).observe(duration)


def create_metrics_collector(component: str) -> ErrorMetricsCollector:
    """
    Create an error metrics collector for a specific component.

    Args:
        component: Component name (e.g., "slack_handler", "llm_gateway")

    Returns:
        ErrorMetricsCollector instance
    """
    return ErrorMetricsCollector(component)


# Convenience function for quick error tracking
def track_error(error: ReflectAIError, component: str = "unknown") -> None:
    """
    Quick function to track an error occurrence.

    Args:
        error: The ReflectAI error instance
        component: Component where the error occurred
    """
    collector = ErrorMetricsCollector(component)
    collector.track_error(error)


# Health check for metrics system
def get_error_metrics_health() -> dict[str, Any]:
    """
    Get health status of error metrics system.

    Returns:
        Dictionary with health status information
    """
    return {
        "prometheus_available": PROMETHEUS_AVAILABLE,
        "metrics_registered": True,
        "collector_ready": True,
    }
