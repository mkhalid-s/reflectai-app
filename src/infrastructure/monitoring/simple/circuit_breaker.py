"""
Circuit Breaker Implementation for ReflectAI

Provides resilience patterns for service calls and external dependencies.
Production Basic circuit breaker with failure tracking.
"""

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.shared import get_logger

logger = get_logger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Blocking calls due to failures
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerStats:
    """Circuit breaker statistics."""

    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float | None = None
    state_change_time: float = field(default_factory=time.time)
    total_requests: int = 0


class CircuitBreaker:
    """
    Simple circuit breaker implementation.

    Protects against cascading failures by monitoring failure rates
    and temporarily blocking requests when failure threshold is exceeded.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before trying half-open
            expected_exception: Exception type that counts as failure
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.stats = CircuitBreakerStats()

        logger.info(
            "Circuit breaker initialized",
            extra={
                "failure_threshold": failure_threshold,
                "recovery_timeout": recovery_timeout,
                "expected_exception": expected_exception.__name__,
            },
        )

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker.

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerOpenError: When circuit is open
            Original exception: When function fails in closed/half-open state
        """
        self.stats.total_requests += 1

        # Check if circuit should transition states
        self._update_state()

        if self.stats.state == CircuitState.OPEN:
            logger.warning(
                "Circuit breaker is OPEN, blocking call",
                extra={
                    "failure_count": self.stats.failure_count,
                    "last_failure": self.stats.last_failure_time,
                },
            )
            raise CircuitBreakerOpenError(
                f"Circuit breaker is OPEN. Failure count: {self.stats.failure_count}"
            )

        try:
            # Execute the function
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            # Record success
            self._record_success()
            return result

        except self.expected_exception as e:
            # Record failure
            self._record_failure()

            logger.warning(
                "Circuit breaker recorded failure",
                extra={
                    "failure_count": self.stats.failure_count,
                    "circuit_state": self.stats.state.value,
                    "error": str(e),
                },
            )

            raise e

    def _update_state(self):
        """Update circuit breaker state based on current conditions."""
        current_time = time.time()

        if self.stats.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if (
                self.stats.last_failure_time
                and current_time - self.stats.last_failure_time >= self.recovery_timeout
            ):
                self._transition_to_half_open()

        elif self.stats.state == CircuitState.CLOSED:
            # Check if failure threshold exceeded
            if self.stats.failure_count >= self.failure_threshold:
                self._transition_to_open()

        # HALF_OPEN transitions are handled in record_success/failure methods

    def _record_success(self):
        """Record successful operation."""
        self.stats.success_count += 1

        if self.stats.state == CircuitState.HALF_OPEN:
            # Recovery successful, close circuit
            self._transition_to_closed()
        elif self.stats.state == CircuitState.CLOSED:
            # Reset failure count on success in closed state
            self.stats.failure_count = max(0, self.stats.failure_count - 1)

    def _record_failure(self):
        """Record failed operation."""
        self.stats.failure_count += 1
        self.stats.last_failure_time = time.time()

        if self.stats.state == CircuitState.HALF_OPEN:
            # Failure during recovery, go back to open
            self._transition_to_open()
        elif (
            self.stats.state == CircuitState.CLOSED
            and self.stats.failure_count >= self.failure_threshold
        ):
            # Failure threshold exceeded, open circuit
            self._transition_to_open()

    def _transition_to_open(self):
        """Transition to OPEN state."""
        old_state = self.stats.state
        self.stats.state = CircuitState.OPEN
        self.stats.state_change_time = time.time()

        logger.warning(
            f"Circuit breaker transitioned {old_state.value} -> OPEN",
            extra={
                "failure_count": self.stats.failure_count,
                "failure_threshold": self.failure_threshold,
            },
        )

    def _transition_to_half_open(self):
        """Transition to HALF_OPEN state."""
        old_state = self.stats.state
        self.stats.state = CircuitState.HALF_OPEN
        self.stats.state_change_time = time.time()

        logger.info(
            f"Circuit breaker transitioned {old_state.value} -> HALF_OPEN",
            extra={"recovery_timeout": self.recovery_timeout},
        )

    def _transition_to_closed(self):
        """Transition to CLOSED state."""
        old_state = self.stats.state
        self.stats.state = CircuitState.CLOSED
        self.stats.state_change_time = time.time()
        self.stats.failure_count = 0  # Reset failure count

        logger.info(
            f"Circuit breaker transitioned {old_state.value} -> CLOSED",
            extra={"success_count": self.stats.success_count},
        )

    def get_stats(self) -> dict[str, Any]:
        """Get circuit breaker statistics."""
        return {
            "state": self.stats.state.value,
            "failure_count": self.stats.failure_count,
            "success_count": self.stats.success_count,
            "total_requests": self.stats.total_requests,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "last_failure_time": self.stats.last_failure_time,
            "state_change_time": self.stats.state_change_time,
        }

    def reset(self):
        """Reset circuit breaker to initial state."""
        logger.info("Resetting circuit breaker")
        self.stats = CircuitBreakerStats()

    def force_open(self):
        """Force circuit breaker to OPEN state."""
        logger.warning("Forcing circuit breaker to OPEN state")
        self._transition_to_open()

    def force_closed(self):
        """Force circuit breaker to CLOSED state."""
        logger.info("Forcing circuit breaker to CLOSED state")
        self._transition_to_closed()


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is in OPEN state."""

    pass


# Global circuit breakers registry for shared instances
_circuit_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    expected_exception: type = Exception,
) -> CircuitBreaker:
    """
    Get or create a named circuit breaker.

    Args:
        name: Circuit breaker identifier
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds to wait before trying half-open
        expected_exception: Exception type that counts as failure

    Returns:
        CircuitBreaker instance
    """
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=expected_exception,
        )

        logger.info(
            f"Created circuit breaker '{name}'",
            extra={"failure_threshold": failure_threshold, "recovery_timeout": recovery_timeout},
        )

    return _circuit_breakers[name]


def get_all_circuit_breaker_stats() -> dict[str, dict[str, Any]]:
    """Get statistics for all registered circuit breakers."""
    return {name: breaker.get_stats() for name, breaker in _circuit_breakers.items()}
