"""
Prometheus Metrics Collection for ReflectAI production

Direct Prometheus integration without OpenTelemetry complexity,
following the Task 2d specification for essential metrics.
"""

import time
from typing import Any

try:
    from prometheus_client import Counter, Gauge, Histogram, Info, start_http_server

    PROMETHEUS_AVAILABLE = True
except ImportError:
    # Mock metrics if prometheus_client is not available
    PROMETHEUS_AVAILABLE = False

    class MockMetric:
        def labels(self, **labels: Any) -> "MockMetric":
            return self

        def inc(self, amount: int = 1) -> None:
            pass

        def observe(self, amount: float) -> None:
            pass

        def set(self, value: float) -> None:
            pass

        def info(self, value: dict[str, Any]) -> None:
            pass

    Counter = Histogram = Gauge = Info = lambda *args, **kwargs: MockMetric()
    def start_http_server(port):
        return None


# Core Application Metrics (Task 2d specification)

# System Performance Metrics
request_duration = Histogram(
    "reflectai_request_duration_seconds",
    "Request duration in seconds",
    ["method", "endpoint", "status"],
)

request_count = Counter(
    "reflectai_requests_total", "Total number of requests", ["endpoint", "status_code"]
)

active_requests = Gauge("reflectai_active_requests", "Number of active requests", ["endpoint"])

# Database Metrics
db_query_duration = Histogram(
    "reflectai_db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation", "table"],
)

db_connections_active = Gauge(
    "reflectai_db_connections_active", "Number of active database connections"
)

# Cache Metrics
cache_hit_rate = Gauge(
    "reflectai_cache_hit_rate", "Cache hit rate percentage", ["cache_type", "key_pattern"]
)

cache_operations = Counter(
    "reflectai_cache_operations_total",
    "Total cache operations",
    ["operation", "cache_type", "result"],
)

# Business and Agent Metrics
agent_execution_duration = Histogram(
    "reflectai_agent_execution_duration_seconds",
    "Agent execution duration in seconds",
    ["agent_type", "model"],
)

agent_requests = Counter(
    "reflectai_agent_requests_total", "Total agent requests", ["agent_type", "status"]
)

llm_cost_usd = Counter(
    "reflectai_llm_cost_usd_total", "Total LLM costs in USD", ["model", "agent_type"]
)

llm_tokens_consumed = Counter(
    "reflectai_llm_tokens_consumed_total",
    "Total LLM tokens consumed",
    ["model", "agent_type", "token_type"],
)

user_activities_processed = Counter(
    "reflectai_user_activities_processed_total",
    "Total user activities processed",
    ["activity_type", "status"],
)

active_users = Gauge("reflectai_active_users_total", "Number of active users", ["time_window"])

# Event Processing Metrics
events_processed = Counter(
    "reflectai_events_processed_total", "Total events processed", ["event_type", "status"]
)

events_deduplicated = Counter("reflectai_events_deduplicated_total", "Total events deduplicated")

event_processing_duration = Histogram(
    "reflectai_event_processing_duration_seconds",
    "Event processing duration in seconds",
    ["event_type"],
)

# Application Info
app_info = Info("reflectai_app_info", "Application information")


class MetricsCollector:
    """
    Centralized metrics collection with contextual information.

    Provides high-level interface for recording metrics with
    automatic context injection and correlation with logging.
    """

    def __init__(self, component: str = "unknown") -> None:
        self.component = component
        self._request_start_times: dict[str, float] = {}

    def start_request_timer(self, request_id: str, endpoint: str) -> None:
        """Start timing a request."""
        self._request_start_times[request_id] = time.time()
        active_requests.labels(endpoint=endpoint).inc()

    def end_request_timer(
        self, request_id: str, method: str, endpoint: str, status_code: int
    ) -> None:
        """End timing a request and record metrics."""
        start_time = self._request_start_times.pop(request_id, None)
        if start_time and PROMETHEUS_AVAILABLE:
            duration = time.time() - start_time

            # Record duration
            request_duration.labels(
                method=method, endpoint=endpoint, status=str(status_code)
            ).observe(duration)

            # Record count
            request_count.labels(endpoint=endpoint, status_code=str(status_code)).inc()

            # Decrement active requests
            active_requests.labels(endpoint=endpoint).dec()

    def record_db_operation(self, operation: str, table: str, duration: float) -> None:
        """Record database operation metrics."""
        if PROMETHEUS_AVAILABLE:
            db_query_duration.labels(operation=operation, table=table).observe(duration)

    def update_db_connections(self, count: int) -> None:
        """Update database connection count."""
        if PROMETHEUS_AVAILABLE:
            db_connections_active.set(count)

    def record_cache_operation(self, operation: str, cache_type: str, result: str) -> None:
        """Record cache operation."""
        if PROMETHEUS_AVAILABLE:
            cache_operations.labels(operation=operation, cache_type=cache_type, result=result).inc()

    def update_cache_hit_rate(self, cache_type: str, key_pattern: str, hit_rate: float) -> None:
        """Update cache hit rate percentage."""
        if PROMETHEUS_AVAILABLE:
            cache_hit_rate.labels(cache_type=cache_type, key_pattern=key_pattern).set(
                hit_rate * 100
            )  # Convert to percentage

    def record_agent_execution(
        self, agent_type: str, model: str, duration: float, status: str
    ) -> None:
        """Record agent execution metrics."""
        if PROMETHEUS_AVAILABLE:
            agent_execution_duration.labels(agent_type=agent_type, model=model).observe(duration)

            agent_requests.labels(agent_type=agent_type, status=status).inc()

    def record_llm_usage(
        self, model: str, agent_type: str, cost_usd: float, tokens: int, token_type: str = "total"
    ) -> None:
        """Record LLM usage and costs."""
        if PROMETHEUS_AVAILABLE:
            llm_cost_usd.labels(model=model, agent_type=agent_type).inc(cost_usd)

            llm_tokens_consumed.labels(
                model=model, agent_type=agent_type, token_type=token_type
            ).inc(tokens)

    def record_activity_processed(self, activity_type: str, status: str) -> None:
        """Record user activity processing."""
        if PROMETHEUS_AVAILABLE:
            user_activities_processed.labels(activity_type=activity_type, status=status).inc()

    def update_active_users(self, count: int, time_window: str = "24h") -> None:
        """Update active users count."""
        if PROMETHEUS_AVAILABLE:
            active_users.labels(time_window=time_window).set(count)

    def record_event_processing(self, event_type: str, duration: float, status: str) -> None:
        """Record event processing metrics."""
        if PROMETHEUS_AVAILABLE:
            events_processed.labels(event_type=event_type, status=status).inc()

            event_processing_duration.labels(event_type=event_type).observe(duration)

    def record_event_deduplication(self) -> None:
        """Record event deduplication."""
        if PROMETHEUS_AVAILABLE:
            events_deduplicated.inc()

    def set_app_info(self, version: str, phase: str, build: str | None = None) -> None:
        """Set application information."""
        if PROMETHEUS_AVAILABLE:
            info_data = {"version": version, "phase": phase, "component": self.component}
            if build:
                info_data["build"] = build

            app_info.info(info_data)


class RequestMetricsMiddleware:
    """
    Middleware for automatic request metrics collection.

    Usage with FastAPI:
        @app.middleware("http")
        async def metrics_middleware(request, call_next):
            middleware = RequestMetricsMiddleware("api")
            return await middleware(request, call_next)
    """

    def __init__(self, component: str = "api"):
        self.collector = MetricsCollector(component)

    async def __call__(self, request, call_next):
        """Process request with metrics collection."""
        from shared.logging import get_correlation_id

        # Generate request ID and get correlation context
        request_id = get_correlation_id() or f"req_{int(time.time())}"
        method = request.method
        endpoint = request.url.path

        # Start timer
        self.collector.start_request_timer(request_id, endpoint)

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            status_code = 500
            raise
        finally:
            # End timer regardless of outcome
            self.collector.end_request_timer(request_id, method, endpoint, status_code)

        return response


# Metrics server management


def start_metrics_server(port: int = 8001, host: str = "127.0.0.1"):
    """
    Start Prometheus metrics HTTP server.

    Args:
        port: Port to serve metrics on
        host: Host to bind to (default: 127.0.0.1 for security)
    """
    if PROMETHEUS_AVAILABLE:
        try:
            start_http_server(port, addr=host)
            from shared.logging import get_logger

            logger = get_logger(__name__)
            logger.info(
                f"Prometheus metrics server started on {host}:{port} - endpoint: http://{host}:{port}/metrics"
            )
        except Exception as e:
            from shared.logging import get_logger

            logger = get_logger(__name__)
            logger.error(f"Failed to start metrics server on {host}:{port} - error: {str(e)}")
    else:
        from shared.logging import get_logger

        logger = get_logger(__name__)
        logger.warning("Prometheus client not available, metrics server not started")


# Convenience functions


def create_metrics_collector(component: str) -> MetricsCollector:
    """Create a metrics collector for a specific component."""
    return MetricsCollector(component)


# Global collector instance
_global_metrics_collector: MetricsCollector | None = None


def get_metrics_collector(component: str = "default") -> MetricsCollector:
    """Get or create a global metrics collector instance."""
    global _global_metrics_collector
    if _global_metrics_collector is None:
        _global_metrics_collector = MetricsCollector(component)
    return _global_metrics_collector


def get_metrics_health() -> dict[str, any]:
    """Get health status of metrics system."""
    return {
        "prometheus_available": PROMETHEUS_AVAILABLE,
        "metrics_registered": True,
        "collectors_ready": True,
        "metrics_count": len(
            [
                request_duration,
                request_count,
                active_requests,
                db_query_duration,
                db_connections_active,
                cache_hit_rate,
                cache_operations,
                agent_execution_duration,
                agent_requests,
                llm_cost_usd,
                llm_tokens_consumed,
                user_activities_processed,
                active_users,
                events_processed,
                events_deduplicated,
                event_processing_duration,
            ]
        ),
    }
