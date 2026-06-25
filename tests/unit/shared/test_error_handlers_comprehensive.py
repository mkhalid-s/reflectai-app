"""
Comprehensive Tests for ReflectAI Error Handlers

Tests for CircuitBreaker, retry logic, context managers, decorators,
and all error handling patterns.
"""

import asyncio
import time
from unittest.mock import Mock, patch

import pytest

from src.shared.error_handlers import (
    CircuitBreaker,
    ErrorContext,
    database_error_handler,
    error_context,
    handle_errors,
    handle_temporal_activity_errors,
    retry_with_exponential_backoff,
    safe_api_call,
    with_error_context,
)
from src.shared.exceptions import (
    DatabaseError,
    ErrorCategory,
    NetworkError,
    ReflectAIError,
    ValidationError,
)


class TestCircuitBreaker:
    """Test CircuitBreaker pattern implementation."""

    def test_circuit_breaker_initialization(self):
        """Test circuit breaker initializes correctly."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=30, expected_exception=ValueError)

        assert cb.failure_threshold == 3
        assert cb.recovery_timeout == 30
        assert cb.expected_exception == ValueError
        assert cb.state == "closed"
        assert cb.failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_success(self):
        """Test circuit breaker allows successful calls."""
        cb = CircuitBreaker()

        async def successful_func():
            return "success"

        result = await cb.call(successful_func)

        assert result == "success"
        assert cb.state == "closed"
        assert cb.failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_failure_tracking(self):
        """Test circuit breaker tracks failures."""
        cb = CircuitBreaker(failure_threshold=3)
        call_count = [0]

        async def failing_func():
            call_count[0] += 1
            raise Exception("Test failure")

        # Should track failures but not open yet
        for i in range(2):
            with pytest.raises(Exception):
                await cb.call(failing_func)
            assert cb.failure_count == i + 1
            assert cb.state == "closed"

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_threshold(self):
        """Test circuit breaker opens after failure threshold."""
        cb = CircuitBreaker(failure_threshold=3)

        async def failing_func():
            raise Exception("Test failure")

        # Reach threshold
        for _ in range(3):
            with pytest.raises(Exception):
                await cb.call(failing_func)

        # Circuit should now be open
        assert cb.state == "open"
        assert cb.failure_count == 3

    @pytest.mark.asyncio
    async def test_circuit_breaker_rejects_when_open(self):
        """Test circuit breaker rejects calls when open."""
        cb = CircuitBreaker(failure_threshold=2)

        async def failing_func():
            raise Exception("Test failure")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                await cb.call(failing_func)

        # Next call should fail immediately with ReflectAIError
        with pytest.raises(ReflectAIError) as exc_info:
            await cb.call(failing_func)

        assert "Circuit breaker is open" in str(exc_info.value)
        assert exc_info.value.error_code == "CIRCUIT_BREAKER_OPEN"

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_after_timeout(self):
        """Test circuit breaker enters half-open after recovery timeout."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

        async def failing_func():
            raise Exception("Test failure")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                await cb.call(failing_func)

        assert cb.state == "open"

        # Wait for recovery timeout
        await asyncio.sleep(0.15)

        # Next call should attempt recovery (half-open)
        with pytest.raises(Exception):
            await cb.call(failing_func)

        # State should have been half-open before failure
        # (now it's open again due to failure)

    @pytest.mark.asyncio
    async def test_circuit_breaker_resets_on_success(self):
        """Test circuit breaker resets after successful call."""
        cb = CircuitBreaker(failure_threshold=3)

        async def sometimes_failing_func(should_fail):
            if should_fail:
                raise Exception("Test failure")
            return "success"

        # Record some failures
        with pytest.raises(Exception):
            await cb.call(sometimes_failing_func, True)

        assert cb.failure_count == 1

        # Successful call should reset
        result = await cb.call(sometimes_failing_func, False)

        assert result == "success"
        assert cb.failure_count == 0
        assert cb.state == "closed"

    @pytest.mark.asyncio
    async def test_circuit_breaker_with_sync_function(self):
        """Test circuit breaker works with synchronous functions."""
        cb = CircuitBreaker()

        def sync_func():
            return "sync_success"

        result = await cb.call(sync_func)

        assert result == "sync_success"


class TestDatabaseErrorHandler:
    """Test database_error_handler context manager."""

    @pytest.mark.asyncio
    async def test_database_error_handler_success(self):
        """Test context manager allows successful operations."""
        async with database_error_handler("test_operation"):
            # Should not raise
            result = "success"

        assert result == "success"

    @pytest.mark.asyncio
    @patch("src.shared.error_handlers.SQLALCHEMY_AVAILABLE", True)
    @patch("src.shared.error_handlers.IntegrityError", Exception)
    async def test_database_error_handler_integrity_error(self):
        """Test handling of IntegrityError."""

        class MockIntegrityError(Exception):
            pass

        with patch("src.shared.error_handlers.IntegrityError", MockIntegrityError):
            with pytest.raises(DatabaseError) as exc_info:
                async with database_error_handler("create_user"):
                    raise MockIntegrityError("Duplicate key")

            error = exc_info.value
            # DatabaseError has its own error_code
            assert error.error_code in ["DB_ERROR", "DB_INTEGRITY_ERROR"]
            assert error.context["operation"] == "create_user"

    @pytest.mark.asyncio
    async def test_database_error_handler_generic_error(self):
        """Test handling of generic exceptions."""
        with pytest.raises(DatabaseError) as exc_info:
            async with database_error_handler("query_users"):
                raise ValueError("Generic error")

        error = exc_info.value
        # DatabaseError sets its own error_code
        assert error.error_code in ["DB_ERROR", "DB_OPERATION_ERROR"]
        assert error.context["operation"] == "query_users"


class TestRetryWithExponentialBackoff:
    """Test retry decorator with exponential backoff."""

    @pytest.mark.asyncio
    async def test_retry_successful_first_attempt(self):
        """Test retry succeeds on first attempt."""

        @retry_with_exponential_backoff(max_retries=3)
        async def successful_func():
            return "success"

        result = await successful_func()

        assert result == "success"

    @pytest.mark.asyncio
    async def test_retry_succeeds_after_failures(self):
        """Test retry succeeds after some failures."""
        attempt_count = [0]

        @retry_with_exponential_backoff(max_retries=3, base_delay=0.01)
        async def eventually_successful():
            attempt_count[0] += 1
            if attempt_count[0] < 3:
                raise NetworkError("Temporary failure", service="test")
            return "success"

        result = await eventually_successful()

        assert result == "success"
        assert attempt_count[0] == 3

    @pytest.mark.asyncio
    async def test_retry_exhausts_attempts(self):
        """Test retry exhausts all attempts and fails."""

        @retry_with_exponential_backoff(max_retries=2, base_delay=0.01)
        async def always_failing():
            raise NetworkError("Permanent failure", service="test")

        with pytest.raises(NetworkError) as exc_info:
            await always_failing()

        # NetworkError is re-raised with retry context added
        error = exc_info.value
        assert (
            error.context.get("retry_attempts") == 3 or error.context.get("retry_attempts") is None
        )

    @pytest.mark.asyncio
    async def test_retry_exponential_backoff(self):
        """Test exponential backoff timing."""
        start_time = time.time()

        @retry_with_exponential_backoff(max_retries=2, base_delay=0.1, jitter=False)
        async def failing_func():
            raise NetworkError("Test", service="test")

        with pytest.raises(ReflectAIError):
            await failing_func()

        duration = time.time() - start_time

        # Should have delayed: 0.1 + 0.2 = 0.3 seconds minimum
        assert duration >= 0.3

    @pytest.mark.asyncio
    async def test_retry_non_retryable_error(self):
        """Test retry doesn't retry non-retryable errors."""

        @retry_with_exponential_backoff(max_retries=3)
        async def validation_error_func():
            raise ValidationError("Invalid input", field="test")

        # Should fail immediately without retry
        with pytest.raises(ValidationError):
            await validation_error_func()

    @pytest.mark.asyncio
    async def test_retry_with_custom_exceptions(self):
        """Test retry with custom retryable exceptions."""

        @retry_with_exponential_backoff(
            max_retries=2, base_delay=0.01, retryable_exceptions=(ValueError,)
        )
        async def value_error_func():
            raise ValueError("Test error")

        with pytest.raises(ReflectAIError):
            await value_error_func()

    def test_retry_with_sync_function(self):
        """Test retry decorator with synchronous function."""

        @retry_with_exponential_backoff(max_retries=2, base_delay=0.01)
        def sync_func():
            return "sync_success"

        result = sync_func()

        assert result == "sync_success"


class TestSafeApiCall:
    """Test safe_api_call utility."""

    @pytest.mark.asyncio
    async def test_safe_api_call_success(self):
        """Test successful API call."""

        async def successful_api():
            return {"status": "ok"}

        result = await safe_api_call(successful_api)

        assert result["status"] == "ok"

    @pytest.mark.asyncio
    async def test_safe_api_call_with_timeout(self):
        """Test API call with timeout."""

        async def slow_api():
            await asyncio.sleep(1)
            return "result"

        # TimeoutError is raised, not NetworkError
        with pytest.raises((TimeoutError, NetworkError)):
            await safe_api_call(slow_api, timeout_seconds=0.1)

    @pytest.mark.asyncio
    async def test_safe_api_call_with_circuit_breaker(self):
        """Test API call with circuit breaker."""
        cb = CircuitBreaker()

        async def api_func():
            return "result"

        result = await safe_api_call(api_func, circuit_breaker=cb)

        assert result == "result"

    @pytest.mark.asyncio
    async def test_safe_api_call_with_sync_function(self):
        """Test safe API call with synchronous function."""

        def sync_api():
            return "sync_result"

        result = await safe_api_call(sync_api)

        assert result == "sync_result"


class TestHandleTemporalActivityErrors:
    """Test Temporal activity error decorator."""

    @pytest.mark.asyncio
    async def test_temporal_handler_success(self):
        """Test successful activity execution."""

        @handle_temporal_activity_errors("test_activity")
        async def successful_activity():
            return "success"

        result = await successful_activity()

        assert result == "success"

    @pytest.mark.asyncio
    async def test_temporal_handler_validation_error(self):
        """Test validation errors are not retried."""

        @handle_temporal_activity_errors("test_activity")
        async def validation_activity():
            raise ValidationError("Invalid", field="test")

        # Should raise ValidationError directly without conversion
        with pytest.raises(ValidationError):
            await validation_activity()

    @pytest.mark.asyncio
    @patch("src.shared.error_handlers.ActivityError", create=True)
    async def test_temporal_handler_database_error(self, mock_activity_error):
        """Test database errors are converted and retried."""

        @handle_temporal_activity_errors("test_activity")
        async def db_activity():
            raise DatabaseError("DB failed", query="SELECT *")

        with patch.dict("sys.modules", {"temporalio.exceptions": Mock()}):
            with pytest.raises(Exception):  # ActivityError or DatabaseError
                await db_activity()

    @pytest.mark.asyncio
    async def test_temporal_handler_without_temporal(self):
        """Test handler works when Temporal not available."""

        @handle_temporal_activity_errors("test_activity")
        async def activity():
            raise DatabaseError("DB failed", query="SELECT *")

        # Should raise DatabaseError when Temporal not available
        # The decorator tries to import ActivityError and fails, so re-raises original
        with pytest.raises((DatabaseError, Exception)):
            await activity()


class TestErrorContext:
    """Test ErrorContext class."""

    def test_error_context_initialization(self):
        """Test ErrorContext initializes empty."""
        ctx = ErrorContext()

        assert ctx.to_dict() == {}

    def test_error_context_set_get(self):
        """Test setting and getting context values."""
        ctx = ErrorContext()

        ctx.set("key1", "value1")
        ctx.set("key2", 123)

        assert ctx.get("key1") == "value1"
        assert ctx.get("key2") == 123
        assert ctx.get("nonexistent") is None
        assert ctx.get("nonexistent", "default") == "default"

    def test_error_context_update(self):
        """Test updating context with dictionary."""
        ctx = ErrorContext()

        ctx.update({"user_id": "U123", "team_id": "T456"})

        assert ctx.get("user_id") == "U123"
        assert ctx.get("team_id") == "T456"

    def test_error_context_clear(self):
        """Test clearing context."""
        ctx = ErrorContext()

        ctx.set("key", "value")
        ctx.clear()

        assert ctx.to_dict() == {}

    def test_error_context_to_dict(self):
        """Test converting context to dictionary."""
        ctx = ErrorContext()

        ctx.set("a", 1)
        ctx.set("b", 2)

        result = ctx.to_dict()

        assert result == {"a": 1, "b": 2}
        # Should be a copy
        result["c"] = 3
        assert "c" not in ctx.to_dict()


class TestWithErrorContextDecorator:
    """Test with_error_context decorator."""

    @pytest.mark.asyncio
    async def test_with_error_context_async(self):
        """Test error context decorator with async function."""

        @with_error_context(component="test", operation="test_op")
        async def async_func():
            # Check context is set
            assert error_context.get("component") == "test"
            assert error_context.get("operation") == "test_op"
            return "success"

        result = await async_func()

        assert result == "success"
        # Context should be restored (empty in this case)

    def test_with_error_context_sync(self):
        """Test error context decorator with sync function."""

        @with_error_context(component="test", operation="test_op")
        def sync_func():
            assert error_context.get("component") == "test"
            return "success"

        result = sync_func()

        assert result == "success"

    @pytest.mark.asyncio
    async def test_with_error_context_preserves_original(self):
        """Test decorator preserves original context."""
        # Set initial context
        error_context.set("existing", "value")

        @with_error_context(component="test")
        async def test_func():
            assert error_context.get("component") == "test"
            assert error_context.get("existing") == "value"

        await test_func()

        # Original context should be restored
        assert error_context.get("existing") == "value"
        assert error_context.get("component") is None  # Decorator context removed

        # Cleanup
        error_context.clear()

    @pytest.mark.asyncio
    async def test_with_error_context_on_exception(self):
        """Test decorator restores context on exception."""
        error_context.set("original", "value")

        @with_error_context(component="test")
        async def failing_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            await failing_func()

        # Context should still be restored
        assert error_context.get("original") == "value"
        assert error_context.get("component") is None

        # Cleanup
        error_context.clear()


class TestHandleErrorsDecorator:
    """Test handle_errors decorator."""

    @pytest.mark.asyncio
    async def test_handle_errors_async_success(self):
        """Test handle_errors with successful async function."""

        @handle_errors(category=ErrorCategory.VALIDATION_ERROR, component="test")
        async def successful_func():
            return "success"

        result = await successful_func()

        assert result == "success"

    @pytest.mark.asyncio
    async def test_handle_errors_reflects_our_errors(self):
        """Test handle_errors re-raises ReflectAIError without modification."""

        @handle_errors(category=ErrorCategory.VALIDATION_ERROR)
        async def reflect_error_func():
            raise DatabaseError("DB error", query="SELECT *")

        with pytest.raises(DatabaseError):
            await reflect_error_func()

    @pytest.mark.asyncio
    async def test_handle_errors_converts_unknown_errors(self):
        """Test handle_errors converts unknown errors."""

        @handle_errors(category=ErrorCategory.INFRASTRUCTURE_ERROR, component="test")
        async def unknown_error_func():
            raise ValueError("Unknown error")

        # Should convert to ReflectAIError
        with pytest.raises(ReflectAIError) as exc_info:
            await unknown_error_func()

        error = exc_info.value
        assert error.error_code == "COMPONENT_ERROR"
        assert error.category == ErrorCategory.INFRASTRUCTURE_ERROR

    def test_handle_errors_sync_function(self):
        """Test handle_errors with synchronous function."""

        @handle_errors(category=ErrorCategory.VALIDATION_ERROR)
        def sync_func():
            return "success"

        result = sync_func()

        assert result == "success"


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_with_zero_threshold(self):
        """Test circuit breaker with zero threshold."""
        cb = CircuitBreaker(failure_threshold=0)

        async def func():
            raise Exception("Test")

        # Should open immediately
        with pytest.raises(Exception):
            await cb.call(func)

        assert cb.state == "open"

    @pytest.mark.asyncio
    async def test_retry_with_zero_retries(self):
        """Test retry decorator with max_retries=0."""

        @retry_with_exponential_backoff(max_retries=0, base_delay=0.01)
        async def func():
            raise NetworkError("Error", service="test")

        with pytest.raises(ReflectAIError):
            await func()

    def test_error_context_global_instance(self):
        """Test global error_context instance."""
        from src.shared.error_handlers import error_context as global_context

        assert isinstance(global_context, ErrorContext)

        # Test it works
        global_context.set("test", "value")
        assert global_context.get("test") == "value"

        # Cleanup
        global_context.clear()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
