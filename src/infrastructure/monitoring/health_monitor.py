"""
Health Monitoring System for ReflectAI

Provides comprehensive health checks, status monitoring, and
system diagnostics with detailed component health tracking.
"""

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

# Optional structlog import
try:
    import structlog

    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False
    # Fallback logger
    structlog = None

# Optional psutil for system metrics
try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    import warnings

    warnings.warn("psutil not available. System metrics will be disabled.", ImportWarning, stacklevel=2)

from src.infrastructure.config import get_config_manager
from src.shared.logging import get_logger

# Use structlog if available, otherwise fall back to our logger
if STRUCTLOG_AVAILABLE:
    logger = structlog.get_logger(__name__)
else:
    logger = get_logger(__name__)


class HealthStatus(str, Enum):
    """Health status levels."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ComponentType(str, Enum):
    """Types of system components."""

    DATABASE = "database"
    CACHE = "cache"
    QUEUE = "queue"
    EXTERNAL_SERVICE = "external_service"
    INFRASTRUCTURE = "infrastructure"
    APPLICATION = "application"


@dataclass
class HealthCheck:
    """Individual health check configuration."""

    name: str
    component_type: ComponentType
    check_function: Callable[[], Awaitable[dict[str, Any]]]
    timeout: float = 5.0
    critical: bool = True
    enabled: bool = True
    description: str = ""

    # Health thresholds
    warning_threshold: float | None = None
    critical_threshold: float | None = None

    # Check frequency
    check_interval: float = 30.0  # seconds
    last_check: datetime | None = None
    last_result: dict[str, Any] | None = None


@dataclass
class HealthResult:
    """Result of a health check."""

    name: str
    status: HealthStatus
    response_time: float
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    error: str | None = None


@dataclass
class SystemHealth:
    """Overall system health status."""

    overall_status: HealthStatus
    response_time: float
    timestamp: datetime
    component_results: dict[str, HealthResult]
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    # System metrics
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    disk_percent: float = 0.0
    uptime_seconds: float = 0.0


class HealthMonitor:
    """
    Comprehensive health monitoring system.

    Features:
    - Component health checks
    - System resource monitoring
    - Dependency health tracking
    - Automated alerting thresholds
    - Historical health data
    """

    def __init__(self):
        self.logger = get_logger("infrastructure.monitoring.health")

        # Health checks registry
        self.health_checks: dict[str, HealthCheck] = {}
        self.check_results: dict[str, HealthResult] = {}

        # System monitoring
        self.start_time = datetime.now(UTC)
        self.monitoring_enabled = True
        self.check_interval = 30.0  # seconds

        # Background tasks
        self._monitor_task: asyncio.Task | None = None
        self._is_running = False

        # Health history
        self.health_history: list[SystemHealth] = []
        self.max_history_size = 100

    async def initialize(self) -> bool:
        """Initialize health monitoring system."""
        try:
            self.logger.info("Initializing health monitoring system")

            # Load configuration
            await self._load_health_config()

            # Register default health checks
            await self._register_default_checks()

            # Start background monitoring
            if self.monitoring_enabled:
                await self._start_monitoring()

            self.logger.info(
                "Health monitoring system initialized", checks_registered=len(self.health_checks)
            )
            return True

        except Exception as e:
            self.logger.error("Failed to initialize health monitor", error=str(e))
            return False

    async def _load_health_config(self):
        """Load health monitoring configuration."""
        try:
            config_manager = get_config_manager()

            # Load configuration
            self.monitoring_enabled = await config_manager.get("health.monitoring_enabled", True)
            self.check_interval = await config_manager.get("health.check_interval", 30.0)
            self.max_history_size = await config_manager.get("health.max_history_size", 100)

            self.logger.info(
                "Health monitoring configuration loaded",
                monitoring_enabled=self.monitoring_enabled,
                check_interval=self.check_interval,
            )

        except Exception as e:
            self.logger.warning("Failed to load health config, using defaults", error=str(e))

    async def _register_default_checks(self):
        """Register default system health checks."""

        # System resource health check
        await self.register_health_check(
            HealthCheck(
                name="system_resources",
                component_type=ComponentType.INFRASTRUCTURE,
                check_function=self._check_system_resources,
                description="System CPU, memory, and disk usage",
                critical=True,
                check_interval=15.0,
            )
        )

        # Application health check
        await self.register_health_check(
            HealthCheck(
                name="application_health",
                component_type=ComponentType.APPLICATION,
                check_function=self._check_application_health,
                description="Core application functionality",
                critical=True,
            )
        )

        # Configuration health check
        await self.register_health_check(
            HealthCheck(
                name="configuration",
                component_type=ComponentType.APPLICATION,
                check_function=self._check_configuration,
                description="Configuration manager health",
                critical=True,
            )
        )

    async def register_health_check(self, health_check: HealthCheck) -> bool:
        """Register a new health check."""
        try:
            if not health_check.enabled:
                return False

            self.health_checks[health_check.name] = health_check
            self.logger.debug(
                "Health check registered",
                name=health_check.name,
                component_type=health_check.component_type.value,
                critical=health_check.critical,
            )
            return True

        except Exception as e:
            self.logger.error(
                "Failed to register health check", name=health_check.name, error=str(e)
            )
            return False

    async def _check_system_resources(self) -> dict[str, Any]:
        """Check system resources health."""
        try:
            # Get system metrics if psutil is available
            if PSUTIL_AVAILABLE:
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)

                # Memory usage
                memory = psutil.virtual_memory()
                memory_percent = memory.percent
                memory_total_gb = memory.total / (1024**3)
                memory_used_gb = memory.used / (1024**3)

                # Disk usage (root partition)
                disk = psutil.disk_usage("/")
                disk_percent = (disk.used / disk.total) * 100
                disk_total_gb = disk.total / (1024**3)
                disk_used_gb = disk.used / (1024**3)
            else:
                # Default values when psutil is not available
                cpu_percent = 0.0
                memory_percent = 0.0
                disk_percent = 0.0
                memory_total_gb = 0.0
                memory_used_gb = 0.0
                disk_total_gb = 0.0
                disk_used_gb = 0.0

            # Determine status based on thresholds
            status = HealthStatus.HEALTHY
            warnings = []

            if cpu_percent > 80:
                status = HealthStatus.DEGRADED
                warnings.append(f"High CPU usage: {cpu_percent:.1f}%")

            if memory_percent > 85:
                status = HealthStatus.DEGRADED
                warnings.append(f"High memory usage: {memory_percent:.1f}%")

            if disk_percent > 90:
                status = HealthStatus.UNHEALTHY
                warnings.append(f"High disk usage: {disk_percent:.1f}%")

            return {
                "status": status.value,
                "message": "System resources check completed",
                "details": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory_percent,
                    "disk_percent": disk_percent,
                    "memory_total_gb": memory_total_gb,
                    "memory_used_gb": memory_used_gb,
                    "disk_total_gb": disk_total_gb,
                    "disk_used_gb": disk_used_gb,
                },
                "warnings": warnings,
            }

        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY.value,
                "message": f"System resources check failed: {str(e)}",
                "details": {},
                "error": str(e),
            }

    async def _check_application_health(self) -> dict[str, Any]:
        """Check core application health."""
        try:
            # Basic application checks
            uptime = (datetime.now(UTC) - self.start_time).total_seconds()

            # Check if basic services are responsive
            checks = {
                "uptime_seconds": uptime,
                "health_checks_registered": len(self.health_checks),
                "monitoring_active": self._is_running,
            }

            return {
                "status": HealthStatus.HEALTHY.value,
                "message": "Application is running normally",
                "details": checks,
            }

        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY.value,
                "message": f"Application health check failed: {str(e)}",
                "details": {},
                "error": str(e),
            }

    async def _check_configuration(self) -> dict[str, Any]:
        """Check configuration system health."""
        try:
            config_manager = get_config_manager()

            # Test configuration access
            test_key = "health.monitoring_enabled"
            test_value = await config_manager.get(test_key, True)

            return {
                "status": HealthStatus.HEALTHY.value,
                "message": "Configuration system is accessible",
                "details": {
                    "test_key": test_key,
                    "test_value": test_value,
                    "config_manager_type": type(config_manager).__name__,
                },
            }

        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY.value,
                "message": f"Configuration check failed: {str(e)}",
                "details": {},
                "error": str(e),
            }

    async def run_health_check(self, check_name: str) -> HealthResult:
        """Run a specific health check."""
        if check_name not in self.health_checks:
            return HealthResult(
                name=check_name,
                status=HealthStatus.UNKNOWN,
                response_time=0.0,
                message="Health check not found",
                error=f"No health check named '{check_name}'",
            )

        health_check = self.health_checks[check_name]
        start_time = time.time()

        try:
            # Run the check with timeout
            result = await asyncio.wait_for(
                health_check.check_function(), timeout=health_check.timeout
            )

            response_time = time.time() - start_time

            # Parse result
            status = HealthStatus(result.get("status", HealthStatus.UNKNOWN.value))
            message = result.get("message", "Health check completed")
            details = result.get("details", {})
            error = result.get("error")

            health_result = HealthResult(
                name=check_name,
                status=status,
                response_time=response_time,
                message=message,
                details=details,
                error=error,
            )

            # Update check record
            health_check.last_check = datetime.now(UTC)
            health_check.last_result = result
            self.check_results[check_name] = health_result

            return health_result

        except TimeoutError:
            response_time = time.time() - start_time
            return HealthResult(
                name=check_name,
                status=HealthStatus.UNHEALTHY,
                response_time=response_time,
                message=f"Health check timed out after {health_check.timeout}s",
                error="timeout",
            )

        except Exception as e:
            response_time = time.time() - start_time
            return HealthResult(
                name=check_name,
                status=HealthStatus.UNHEALTHY,
                response_time=response_time,
                message=f"Health check failed: {str(e)}",
                error=str(e),
            )

    async def run_all_health_checks(self) -> SystemHealth:
        """Run all registered health checks."""
        start_time = time.time()

        # Run all health checks
        check_tasks = []
        for check_name in self.health_checks:
            task = asyncio.create_task(self.run_health_check(check_name))
            check_tasks.append((check_name, task))

        # Wait for all checks to complete
        component_results = {}
        for check_name, task in check_tasks:
            try:
                result = await task
                component_results[check_name] = result
            except Exception as e:
                component_results[check_name] = HealthResult(
                    name=check_name,
                    status=HealthStatus.UNHEALTHY,
                    response_time=0.0,
                    message=f"Health check failed: {str(e)}",
                    error=str(e),
                )

        # Determine overall health
        overall_status = self._calculate_overall_health(component_results)
        response_time = time.time() - start_time

        # Collect warnings and errors
        warnings = []
        errors = []
        for result in component_results.values():
            if result.status == HealthStatus.DEGRADED:
                warnings.append(f"{result.name}: {result.message}")
            elif result.status == HealthStatus.UNHEALTHY:
                errors.append(f"{result.name}: {result.message}")

        # Get system metrics
        try:
            if PSUTIL_AVAILABLE:
                cpu_percent = psutil.cpu_percent()
                memory_percent = psutil.virtual_memory().percent
                disk_percent = (lambda d: (d.used / d.total) * 100)(psutil.disk_usage("/"))
            else:
                cpu_percent = memory_percent = disk_percent = 0.0
            uptime_seconds = (datetime.now(UTC) - self.start_time).total_seconds()
        except Exception:
            cpu_percent = memory_percent = disk_percent = uptime_seconds = 0.0

        # Create system health status
        system_health = SystemHealth(
            overall_status=overall_status,
            response_time=response_time,
            timestamp=datetime.now(UTC),
            component_results=component_results,
            warnings=warnings,
            errors=errors,
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            disk_percent=disk_percent,
            uptime_seconds=uptime_seconds,
        )

        # Add to history
        self._add_to_history(system_health)

        return system_health

    def _calculate_overall_health(self, component_results: dict[str, HealthResult]) -> HealthStatus:
        """Calculate overall system health from component results."""
        if not component_results:
            return HealthStatus.UNKNOWN

        # Get critical and non-critical results
        critical_results = []
        non_critical_results = []

        for name, result in component_results.items():
            health_check = self.health_checks.get(name)
            if health_check and health_check.critical:
                critical_results.append(result)
            else:
                non_critical_results.append(result)

        # Check critical components
        critical_unhealthy = any(r.status == HealthStatus.UNHEALTHY for r in critical_results)
        critical_degraded = any(r.status == HealthStatus.DEGRADED for r in critical_results)

        if critical_unhealthy:
            return HealthStatus.UNHEALTHY
        elif critical_degraded:
            return HealthStatus.DEGRADED

        # Check non-critical components
        non_critical_unhealthy = any(
            r.status == HealthStatus.UNHEALTHY for r in non_critical_results
        )

        if non_critical_unhealthy:
            return HealthStatus.DEGRADED

        return HealthStatus.HEALTHY

    def _add_to_history(self, system_health: SystemHealth):
        """Add system health to history."""
        self.health_history.append(system_health)

        # Limit history size
        if len(self.health_history) > self.max_history_size:
            self.health_history = self.health_history[-self.max_history_size :]

    async def _start_monitoring(self):
        """Start background health monitoring."""
        if self._monitor_task is not None:
            return

        self._is_running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        self.logger.info("Health monitoring started", interval=self.check_interval)

    async def _monitor_loop(self):
        """Background monitoring loop."""
        while self._is_running:
            try:
                # Run health checks
                system_health = await self.run_all_health_checks()

                # Log health status
                if system_health.overall_status == HealthStatus.UNHEALTHY:
                    self.logger.error(
                        "System health check failed",
                        status=system_health.overall_status.value,
                        errors=system_health.errors,
                    )
                elif system_health.overall_status == HealthStatus.DEGRADED:
                    self.logger.warning(
                        "System health degraded",
                        status=system_health.overall_status.value,
                        warnings=system_health.warnings,
                    )
                else:
                    self.logger.debug(
                        "System health check completed",
                        status=system_health.overall_status.value,
                        response_time=system_health.response_time,
                    )

            except Exception as e:
                self.logger.error("Health monitoring error", error=str(e))

            await asyncio.sleep(self.check_interval)

    async def get_health_summary(self) -> dict[str, Any]:
        """Get comprehensive health summary."""
        try:
            # Run current health check
            current_health = await self.run_all_health_checks()

            # Calculate health trends
            recent_health = self.health_history[-10:] if self.health_history else []
            health_trend = "stable"

            if len(recent_health) > 1:
                recent_statuses = [h.overall_status for h in recent_health]
                if recent_statuses[-1] != recent_statuses[0]:
                    health_trend = "changing"

            return {
                "overall_status": current_health.overall_status.value,
                "response_time": current_health.response_time,
                "timestamp": current_health.timestamp.isoformat(),
                "uptime_seconds": current_health.uptime_seconds,
                "health_trend": health_trend,
                # System metrics
                "system_metrics": {
                    "cpu_percent": current_health.cpu_percent,
                    "memory_percent": current_health.memory_percent,
                    "disk_percent": current_health.disk_percent,
                },
                # Component health
                "components": {
                    name: {
                        "status": result.status.value,
                        "message": result.message,
                        "response_time": result.response_time,
                        "last_check": result.timestamp.isoformat(),
                    }
                    for name, result in current_health.component_results.items()
                },
                # Issues
                "warnings": current_health.warnings,
                "errors": current_health.errors,
                # Monitoring info
                "monitoring": {
                    "enabled": self.monitoring_enabled,
                    "running": self._is_running,
                    "check_interval": self.check_interval,
                    "checks_registered": len(self.health_checks),
                    "history_size": len(self.health_history),
                },
            }

        except Exception as e:
            self.logger.error("Failed to get health summary", error=str(e))
            return {
                "overall_status": HealthStatus.UNKNOWN.value,
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
            }

    async def close(self):
        """Shutdown health monitoring."""
        try:
            self._is_running = False

            if self._monitor_task:
                self._monitor_task.cancel()
                try:
                    await self._monitor_task
                except asyncio.CancelledError:
                    pass

            self.logger.info("Health monitoring system closed")

        except Exception as e:
            self.logger.error("Error closing health monitor", error=str(e))


# Global health monitor instance
_global_monitor: HealthMonitor | None = None


async def get_health_monitor() -> HealthMonitor:
    """Get global health monitor instance."""
    global _global_monitor

    if not _global_monitor:
        _global_monitor = HealthMonitor()
        await _global_monitor.initialize()

    return _global_monitor


# Convenience functions
async def get_system_health() -> SystemHealth:
    """Get current system health."""
    monitor = await get_health_monitor()
    return await monitor.run_all_health_checks()


async def register_health_check(health_check: HealthCheck) -> bool:
    """Register a custom health check."""
    monitor = await get_health_monitor()
    return await monitor.register_health_check(health_check)
