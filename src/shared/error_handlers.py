"""
Error Handling Patterns and Utilities

Context managers, decorators, and utilities for consistent error handling
across all ReflectAI components following the error-handling-standards.md.
"""

import asyncio
import functools
import time
from collections.abc import Callable
from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import Any, TypeVar

# Optional database imports - available when packages are installed
try:
    from sqlalchemy.exc import IntegrityError, SQLAlchemyError

    SQLALCHEMY_AVAILABLE = True
except ImportError:
    IntegrityError = SQLAlchemyError = None
    SQLALCHEMY_AVAILABLE = False

try:
    from asyncpg.exceptions import PostgreSQLError

    ASYNCPG_AVAILABLE = True
except ImportError:
    PostgreSQLError = None
    ASYNCPG_AVAILABLE = False

from .exceptions import (
    DatabaseError,
    ErrorCategory,
    ErrorSeverity,
    LLMProviderError,
    NetworkError,
    ReflectAIError,
    SlackAPIError,
    ValidationError,
)

T = TypeVar("T")


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for preventing cascade failures.

    States:
    - CLOSED: Normal operation, calls pass through
    - OPEN: Failure threshold exceeded, calls fail immediately
    - HALF_OPEN: Testing if service has recovered
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type[Exception] = Exception,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time: float | None = None
        self.state = "closed"  # closed, open, half_open

    async def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function with circuit breaker protection."""
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half_open"
            else:
                raise ReflectAIError(
                    message="Circuit breaker is open - service unavailable",
                    error_code="CIRCUIT_BREAKER_OPEN",
                    category=ErrorCategory.INFRASTRUCTURE_ERROR,
                    severity=ErrorSeverity.WARNING,
                    context={
                        "failure_count": self.failure_count,
                        "last_failure": self.last_failure_time,
                    },
                    user_message="Service is temporarily unavailable. Please try again later.",
                    recovery_suggestions=["Wait a few minutes and try again"],
                )

        try:
            result = (
                await func(*args, **kwargs)
                if asyncio.iscoroutinefunction(func)
                else func(*args, **kwargs)
            )
            self._on_success()
            return result
        except self.expected_exception:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        return (
            self.last_failure_time
            and (time.time() - self.last_failure_time) >= self.recovery_timeout
        )

    def _on_success(self):
        """Reset circuit breaker on successful call."""
        self.failure_count = 0
        self.state = "closed"

    def _on_failure(self):
        """Record failure and potentially open circuit."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "open"


@asynccontextmanager
async def database_error_handler(operation_name: str):
    """
    Context manager for database operations with standardized error handling.

    Usage:
        async with database_error_handler("create_user_activity"):
            # database operations
            pass
    """
    try:
        yield
    except Exception as e:
        # Handle SQLAlchemy IntegrityError if available
        if SQLALCHEMY_AVAILABLE and IntegrityError and isinstance(e, IntegrityError):
            raise DatabaseError(
                message=f"Data integrity error in {operation_name}",
                context={"operation": operation_name, "constraint": str(e)},
                user_message="There was a conflict with existing data. Please check your input.",
                recovery_suggestions=[
                    "Verify the data doesn't already exist",
                    "Check for required fields",
                ],
                cause=e,
            ) from e
        # Handle PostgreSQL errors if asyncpg is available
        elif ASYNCPG_AVAILABLE and PostgreSQLError and isinstance(e, PostgreSQLError):
            raise DatabaseError(
                message=f"PostgreSQL error in {operation_name}",
                context={"operation": operation_name, "sqlstate": getattr(e, "sqlstate", None)},
                recovery_suggestions=["Retry the operation", "Check database connectivity"],
                cause=e,
            ) from e
        # Handle other SQLAlchemy errors if available
        elif SQLALCHEMY_AVAILABLE and SQLAlchemyError and isinstance(e, SQLAlchemyError):
            raise DatabaseError(
                message=f"Database operation failed: {operation_name}",
                context={"operation": operation_name},
                cause=e,
            ) from e
        # Handle any other exceptions as generic database errors
        else:
            raise DatabaseError(
                message=f"Database operation failed: {operation_name}",
                context={"operation": operation_name},
                cause=e,
            ) from e


def retry_with_exponential_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: tuple | None = None,
):
    """
    Decorator for retrying functions with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay between retries
        exponential_base: Multiplier for exponential backoff
        jitter: Add random jitter to delay
        retryable_exceptions: Tuple of exception types to retry
    """
    if retryable_exceptions is None:
        retryable_exceptions = (NetworkError, SlackAPIError, DatabaseError)

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    else:
                        return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e

                    if attempt == max_retries:
                        # Final attempt failed
                        if isinstance(e, ReflectAIError):
                            e.context["retry_attempts"] = attempt + 1
                            raise
                        else:
                            raise ReflectAIError(
                                message=f"Operation failed after {attempt + 1} attempts: {str(e)}",
                                error_code="RETRY_EXHAUSTED",
                                category=ErrorCategory.INFRASTRUCTURE_ERROR,
                                context={"retry_attempts": attempt + 1, "original_error": str(e)},
                                cause=e,
                            ) from e

                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (exponential_base**attempt), max_delay)
                    if jitter:
                        import random

                        delay *= 0.5 + random.random() * 0.5  # 50-100% of calculated delay

                    await asyncio.sleep(delay)
                except Exception:
                    # Non-retryable exception
                    raise

            # Should not reach here
            raise last_exception

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            # For sync functions, run in async context
            return asyncio.run(async_wrapper(*args, **kwargs))

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


async def safe_api_call(
    func: Callable[..., T],
    *args,
    circuit_breaker: CircuitBreaker | None = None,
    timeout_seconds: float | None = None,
    **kwargs,
) -> T:
    """
    Make a safe API call with optional circuit breaker and timeout.

    Args:
        func: The function to call
        *args: Positional arguments for the function
        circuit_breaker: Optional circuit breaker instance
        timeout_seconds: Optional timeout in seconds
        **kwargs: Keyword arguments for the function

    Returns:
        The result of the function call

    Raises:
        ReflectAIError: On failure with appropriate error details
    """

    async def _call():
        if circuit_breaker:
            return await circuit_breaker.call(func, *args, **kwargs)
        elif asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            return func(*args, **kwargs)

    try:
        if timeout_seconds:
            return await asyncio.wait_for(_call(), timeout=timeout_seconds)
        else:
            return await _call()
    except TimeoutError as e:
        # NetworkError handles context and recovery_suggestions internally
        error = NetworkError(
            message=f"API call timed out after {timeout_seconds} seconds",
            service=func.__name__,
        )
        # Add timeout info to context
        error.context["timeout_seconds"] = timeout_seconds
        error.context["function"] = func.__name__
        raise error from e


def handle_temporal_activity_errors(activity_name: str):
    """
    Decorator for Temporal activity error handling.

    Converts ReflectAI errors to appropriate Temporal ActivityError instances
    while preserving error information for logging.

    Note: This decorator requires temporalio to be installed.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            try:
                return await func(*args, **kwargs)
            except ValidationError:
                # Don't retry validation errors
                raise
            except DatabaseError as e:
                # Log and convert for Temporal if available
                try:
                    from temporalio.exceptions import ActivityError

                    raise ActivityError(
                        message=f"Database error in {activity_name}: {e.message}",
                        cause=e,
                        retry=True,
                    )
                except ImportError:
                    # Temporal not available, re-raise original error
                    raise
            except LLMProviderError as e:
                # Log and decide on retry based on severity
                try:
                    from temporalio.exceptions import ActivityError

                    raise ActivityError(
                        message=f"LLM provider error in {activity_name}: {e.message}",
                        cause=e,
                        retry=e.severity != ErrorSeverity.CRITICAL,
                    )
                except ImportError:
                    raise
            except SlackAPIError as e:
                # Slack errors are usually retryable
                try:
                    from temporalio.exceptions import ActivityError

                    raise ActivityError(
                        message=f"Slack API error in {activity_name}: {e.message}",
                        cause=e,
                        retry=True,
                    )
                except ImportError:
                    raise
            except ReflectAIError as e:
                # Generic ReflectAI error
                try:
                    from temporalio.exceptions import ActivityError

                    raise ActivityError(
                        message=f"ReflectAI error in {activity_name}: {e.message}",
                        cause=e,
                        retry=e.severity in [ErrorSeverity.WARNING, ErrorSeverity.INFO],
                    )
                except ImportError:
                    raise
            except Exception as e:
                # Unexpected error - don't retry
                try:
                    from temporalio.exceptions import ActivityError

                    raise ActivityError(
                        message=f"Unexpected error in {activity_name}: {str(e)}",
                        cause=e,
                        retry=False,
                    )
                except ImportError:
                    raise

        return wrapper

    return decorator


# Context variables for async-safe error context storage
_error_context_var: ContextVar[dict[str, Any]] = ContextVar("error_context", default=None)


class ErrorContext:
    """Async-safe error context for correlation and debugging using contextvars."""

    def set(self, key: str, value: Any):
        """Set a context value."""
        current = _error_context_var.get()
        if current is None:
            current = {}
        current[key] = value
        _error_context_var.set(current)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a context value."""
        current = _error_context_var.get()
        if current is None:
            return default
        return current.get(key, default)

    def clear(self):
        """Clear all context."""
        _error_context_var.set({})

    def to_dict(self) -> dict[str, Any]:
        """Get context as dictionary."""
        current = _error_context_var.get()
        if current is None:
            return {}
        return current.copy()

    def update(self, context: dict[str, Any]):
        """Update context with dictionary."""
        current = _error_context_var.get()
        if current is None:
            current = {}
        else:
            current = current.copy()  # Don't mutate the contextvar dict
        current.update(context)
        _error_context_var.set(current)


# Global error context instance
error_context = ErrorContext()


def with_error_context(**context_vars):
    """
    Decorator to add error context to a function.

    Usage:
        @with_error_context(component="slack_handler", operation="process_message")
        async def process_slack_message(...):
            pass
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            # Set context
            original_context = error_context.to_dict()
            error_context.update(context_vars)

            try:
                return await func(*args, **kwargs)
            finally:
                # Restore original context
                error_context.clear()
                error_context.update(original_context)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            # Set context
            original_context = error_context.to_dict()
            error_context.update(context_vars)

            try:
                return func(*args, **kwargs)
            finally:
                # Restore original context
                error_context.clear()
                error_context.update(original_context)

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


def handle_errors(
    category: ErrorCategory = ErrorCategory.INFRASTRUCTURE_ERROR,
    component: str | None = None,
    log_errors: bool = True,
):
    """
    Decorator for consistent error handling across components.

    Args:
        category: Error category for classification
        component: Component name for logging context
        log_errors: Whether to log errors (default: True)
    """

    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except ReflectAIError:
                # Re-raise our own errors without modification
                raise
            except Exception as e:
                # Convert unknown errors to ReflectAI errors
                error = ReflectAIError(
                    message=str(e),
                    error_code="COMPONENT_ERROR",
                    category=category,
                    context={"component": component or func.__name__},
                )
                if log_errors:
                    # Import logger here to avoid circular import
                    from src.shared.logging import get_logger

                    logger = get_logger(func.__module__)
                    logger.error(f"Error in {func.__name__}: {error}")
                raise error from e

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ReflectAIError:
                # Re-raise our own errors without modification
                raise
            except Exception as e:
                # Convert unknown errors to ReflectAI errors
                error = ReflectAIError(
                    message=str(e),
                    error_code="COMPONENT_ERROR",
                    category=category,
                    context={"component": component or func.__name__},
                )
                if log_errors:
                    # Import logger here to avoid circular import
                    from src.shared.logging import get_logger

                    logger = get_logger(func.__module__)
                    logger.error(f"Error in {func.__name__}: {error}")
                raise error from e

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator
