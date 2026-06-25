"""
Infrastructure Monitoring Module for ReflectAI

Comprehensive observability stack with advanced metrics collection,
health monitoring, and production-grade monitoring capabilities.
"""

# Production Simple monitoring exports
# NOTE: audit.py was removed as dead code (not integrated into app lifecycle)
# If audit functionality is needed, re-implement with proper integration
from .health_monitor import (
    ComponentType,
    HealthCheck,
    HealthMonitor,
    HealthResult,
    HealthStatus,
    SystemHealth,
    get_health_monitor,
    get_system_health,
    register_health_check,
)
from .simple.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitState,
    get_all_circuit_breaker_stats,
    get_circuit_breaker,
)
from .simple.correlation_manager import (
    CorrelationContext,
    CorrelationIDManager,
    correlation_manager,
    extract_correlation_from_headers,
    get_correlation_health,
    get_correlation_stats,
    get_or_create_correlation_id,
    propagate_correlation_headers,
)
from .simple.metrics_collector import (
    MetricsCollector,
    RequestMetricsMiddleware,
    create_metrics_collector,
    get_metrics_collector,
    get_metrics_health,
    start_metrics_server,
)

__all__ = [
    # Metrics collection
    "MetricsCollector",
    "RequestMetricsMiddleware",
    "start_metrics_server",
    "create_metrics_collector",
    "get_metrics_collector",
    "get_metrics_health",
    # Correlation management
    "CorrelationIDManager",
    "CorrelationContext",
    "correlation_manager",
    "get_or_create_correlation_id",
    "propagate_correlation_headers",
    "extract_correlation_from_headers",
    "get_correlation_health",
    "get_correlation_stats",
    # Circuit breaker
    "CircuitBreaker",
    "CircuitBreakerOpenError",
    "CircuitState",
    "get_circuit_breaker",
    "get_all_circuit_breaker_stats",
    # NOTE: Audit logging exports removed - audit.py deleted as dead code
    # Advanced health monitoring
    "HealthMonitor",
    "HealthStatus",
    "ComponentType",
    "HealthCheck",
    "HealthResult",
    "SystemHealth",
    "get_health_monitor",
    "get_system_health",
    "register_health_check",
]
