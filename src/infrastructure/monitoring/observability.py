"""
Simple Observability Module for ReflectAI

Provides basic metrics collection and health monitoring
without complex registry management issues.
"""

from contextvars import ContextVar
from datetime import UTC, datetime

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, Info

from src.shared.logging import get_logger

logger = get_logger(__name__)

# Use a custom registry to avoid conflicts
custom_registry = CollectorRegistry()

logger.info("Using custom Prometheus registry for clean metrics")


# Context variable for correlation ID
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


# System Performance Metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
    registry=custom_registry,
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["method", "endpoint"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=custom_registry,
)

http_requests_active = Gauge(
    "http_requests_active", "Active HTTP requests", ["endpoint"], registry=custom_registry
)

# System Health
system_health_status = Gauge(
    "system_health_status",
    "System health status (1=healthy, 0=unhealthy)",
    ["component"],
    registry=custom_registry,
)

# Business Metrics
user_activities_total = Counter(
    "user_activities_total", "Total user activities", ["activity_type"], registry=custom_registry
)

events_processed_total = Counter(
    "events_processed_total",
    "Total events processed",
    ["event_type", "status"],
    registry=custom_registry,
)

# Database Metrics
database_operations_total = Counter(
    "database_operations_total",
    "Database operations",
    ["operation", "status"],
    registry=custom_registry,
)

database_query_duration_seconds = Histogram(
    "database_query_duration_seconds",
    "Database query duration",
    ["operation"],
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0),
    registry=custom_registry,
)

# Cache Metrics
cache_operations_total = Counter(
    "cache_operations_total", "Cache operations", ["operation", "result"], registry=custom_registry
)

# Application Info
app_info = Info("reflectai_application_info", "Application information", registry=custom_registry)

# Error Tracking
errors_total = Counter(
    "errors_total", "Total errors", ["component", "error_type"], registry=custom_registry
)


# Helper functions
def get_correlation_id() -> str:
    """Get current correlation ID."""
    return correlation_id_var.get()


def set_correlation_id(correlation_id: str):
    """Set correlation ID in context."""
    correlation_id_var.set(correlation_id)


def track_request(method: str, endpoint: str, status_code: int, duration: float):
    """Track HTTP request metrics."""
    http_requests_total.labels(method=method, endpoint=endpoint, status=str(status_code)).inc()

    http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)


def track_error(component: str, error_type: str):
    """Track error metrics."""
    errors_total.labels(component=component, error_type=error_type).inc()


def update_component_health(component: str, is_healthy: bool):
    """Update component health status."""
    system_health_status.labels(component=component).set(1 if is_healthy else 0)


def set_application_info(version: str, environment: str, phase: str):
    """Set application information."""
    app_info.info(
        {
            "version": version,
            "environment": environment,
            "phase": phase,
            "startup_time": datetime.now(UTC).isoformat(),
        }
    )


def track_user_activity(activity_type: str):
    """Track user activity."""
    user_activities_total.labels(activity_type=activity_type).inc()


def track_event_processing(event_type: str, success: bool):
    """Track event processing."""
    status = "success" if success else "failure"
    events_processed_total.labels(event_type=event_type, status=status).inc()


def track_database_operation(operation: str, duration: float, success: bool = True):
    """Track database operations."""
    status = "success" if success else "failure"
    database_operations_total.labels(operation=operation, status=status).inc()
    database_query_duration_seconds.labels(operation=operation).observe(duration)


def track_cache_operation(operation: str, hit: bool = None):
    """Track cache operations."""
    if hit is None:
        result = "operation"
    else:
        result = "hit" if hit else "miss"
    cache_operations_total.labels(operation=operation, result=result).inc()


# Context manager for active requests
class ActiveRequestTracker:
    """Context manager for tracking active requests."""

    def __init__(self, endpoint: str):
        self.endpoint = endpoint

    def __enter__(self):
        http_requests_active.labels(endpoint=self.endpoint).inc()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        http_requests_active.labels(endpoint=self.endpoint).dec()


logger.info("Observability module initialized with clean metrics registry")
