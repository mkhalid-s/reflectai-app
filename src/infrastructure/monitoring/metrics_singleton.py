"""
Singleton Metrics Registry for ReflectAI

Ensures metrics are only registered once across module reloads.
"""

import threading
from typing import Any

from prometheus_client import Counter, Gauge, Histogram, Info, Summary

from src.shared.logging import get_logger

logger = get_logger(__name__)


class MetricsRegistry:
    """Singleton registry for Prometheus metrics."""

    _instance = None
    _lock = threading.Lock()
    _metrics: dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._init_metrics()
        logger.info("Metrics registry initialized")

    def _init_metrics(self):
        """Initialize all metrics once."""
        # System Performance Metrics
        self._metrics["request_duration"] = Histogram(
            "reflectai_request_duration_seconds",
            "HTTP request duration in seconds",
            ["method", "endpoint", "status"],
            buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
        )

        self._metrics["request_count"] = Counter(
            "reflectai_requests_total",
            "Total number of HTTP requests",
            ["method", "endpoint", "status_code"],
        )

        self._metrics["active_requests"] = Gauge(
            "reflectai_active_requests", "Number of active requests", ["endpoint"]
        )

        self._metrics["error_count"] = Counter(
            "reflectai_errors_total",
            "Total number of errors",
            ["error_type", "component", "severity"],
        )

        # Database Metrics
        self._metrics["db_query_duration"] = Histogram(
            "reflectai_db_query_duration_seconds",
            "Database query duration in seconds",
            ["operation", "table"],
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
        )

        self._metrics["db_connections_active"] = Gauge(
            "reflectai_db_connections_active", "Number of active database connections"
        )

        self._metrics["db_operations_total"] = Counter(
            "reflectai_db_operations_total",
            "Total database operations",
            ["operation", "table", "status"],
        )

        # Cache Metrics
        self._metrics["cache_operations"] = Counter(
            "reflectai_cache_operations_total", "Total cache operations", ["operation", "status"]
        )

        self._metrics["cache_hit_rate"] = Summary(
            "reflectai_cache_hit_rate", "Cache hit rate percentage"
        )

        self._metrics["cache_size"] = Gauge(
            "reflectai_cache_size_bytes", "Current cache size in bytes", ["cache_type"]
        )

        # Event System Metrics
        self._metrics["events_published"] = Counter(
            "reflectai_events_published_total", "Total events published", ["event_type", "source"]
        )

        self._metrics["events_processed"] = Counter(
            "reflectai_events_processed_total",
            "Total events processed",
            ["event_type", "handler", "status"],
        )

        self._metrics["event_processing_duration"] = Histogram(
            "reflectai_event_processing_duration_seconds",
            "Event processing duration",
            ["event_type", "handler"],
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
        )

        # Business Metrics
        self._metrics["user_activities"] = Counter(
            "reflectai_user_activities_total",
            "Total user activities tracked",
            ["activity_type", "user_id", "team_id"],
        )

        self._metrics["competency_calculations"] = Counter(
            "reflectai_competency_calculations_total",
            "Total competency calculations performed",
            ["competency_type", "calculation_trigger"],
        )

        self._metrics["reports_generated"] = Counter(
            "reflectai_reports_generated_total",
            "Total reports generated",
            ["report_type", "format"],
        )

        # Agent Metrics
        self._metrics["agent_execution_duration"] = Histogram(
            "reflectai_agent_execution_duration_seconds",
            "Agent execution duration",
            ["agent_type", "workflow_type"],
            buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
        )

        self._metrics["agent_requests"] = Counter(
            "reflectai_agent_requests_total", "Total agent requests", ["agent_type", "status"]
        )

        # LLM Metrics
        self._metrics["llm_cost"] = Counter(
            "reflectai_llm_cost_usd_total",
            "Total LLM costs in USD",
            ["model", "agent_type", "provider"],
        )

        self._metrics["llm_tokens"] = Counter(
            "reflectai_llm_tokens_total",
            "Total LLM tokens used",
            ["model", "token_type", "agent_type"],
        )

        self._metrics["llm_request_duration"] = Histogram(
            "reflectai_llm_request_duration_seconds",
            "LLM request duration",
            ["model", "provider"],
            buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
        )

        self._metrics["llm_rate_limit_hits"] = Counter(
            "reflectai_llm_rate_limits_total", "LLM rate limit hits", ["provider", "model"]
        )

        # Slack Metrics
        self._metrics["slack_messages"] = Counter(
            "reflectai_slack_messages_total",
            "Total Slack messages processed",
            ["message_type", "team_id"],
        )

        self._metrics["slack_response_time"] = Histogram(
            "reflectai_slack_response_time_seconds",
            "Time to respond to Slack messages",
            ["message_type"],
            buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
        )

        self._metrics["slack_home_tab_updates"] = Counter(
            "reflectai_slack_home_tab_updates_total",
            "Total Slack home tab updates",
            ["team_id", "trigger_type"],
        )

        # System Health Metrics
        self._metrics["system_health"] = Gauge(
            "reflectai_system_health",
            "System health status (1=healthy, 0=unhealthy)",
            ["component"],
        )

        self._metrics["component_uptime"] = Gauge(
            "reflectai_component_uptime_seconds", "Component uptime in seconds", ["component"]
        )

        # Application Info
        self._metrics["app_info"] = Info("reflectai_app", "Application information")

    def get(self, name: str):
        """Get a metric by name."""
        return self._metrics.get(name)

    def __getattr__(self, name: str):
        """Allow attribute-style access to metrics."""
        if name in self._metrics:
            return self._metrics[name]
        raise AttributeError(f"Metric '{name}' not found")


# Global metrics instance
metrics = MetricsRegistry()
