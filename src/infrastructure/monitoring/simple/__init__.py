"""
Simple Monitoring Components - production

Simplified observability stack with direct Prometheus integration
and basic correlation management (no OpenTelemetry complexity).
"""

from .correlation_manager import (
    CorrelationContext,
    CorrelationIDManager,
    correlation_manager,
    extract_correlation_from_headers,
    get_correlation_health,
    get_correlation_stats,
    get_or_create_correlation_id,
    propagate_correlation_headers,
)
from .metrics_collector import (
    MetricsCollector,
    RequestMetricsMiddleware,
    create_metrics_collector,
    get_metrics_health,
    start_metrics_server,
)

__all__ = [
    "MetricsCollector",
    "RequestMetricsMiddleware",
    "start_metrics_server",
    "create_metrics_collector",
    "get_metrics_health",
    "CorrelationIDManager",
    "CorrelationContext",
    "correlation_manager",
    "get_or_create_correlation_id",
    "propagate_correlation_headers",
    "extract_correlation_from_headers",
    "get_correlation_health",
    "get_correlation_stats",
]
