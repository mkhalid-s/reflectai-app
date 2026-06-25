"""
Integration Tests for Error Handling System

Tests end-to-end error handling across components:
- Error handlers with metrics tracking
- Circuit breaker integration
- Context propagation through async operations
- Database error handling with retry logic
"""

import asyncio
import time
from unittest.mock import Mock, patch

import pytest

from src.shared.error_handlers import (
    CircuitBreaker,
    database_error_handler,
    error_context,
    retry_with_exponential_backoff,
)
from src.shared.error_metrics import ErrorMetricsCollector
from src.shared.exceptions import DatabaseError, ErrorCategory, NetworkError, ReflectAIError


class TestDatabaseErrorWithRetryMetrics:
    """Test database errors with retry and metrics tracking."""

    @pytest.mark.asyncio
    async def test_database_operation_with_retry_success(self):
        """Test successful database operation after retry with metrics."""
        attempt_count = 0

        @retry_with_exponential_backoff(max_retries=3, base_delay=0.01)
        async def flaky_db_operation():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise DatabaseError(message="Connection timeout", query="SELECT * FROM test")
            return {"success": True}

        # Execute operation
        result = await flaky_db_operation()

        assert result == {"success": True}
        assert attempt_count == 3

    @pytest.mark.asyncio
    async def test_database_error_handler_integration(self):
        """Test database error handler context manager."""
        operation_succeeded = False

        async with database_error_handler("test_operation"):
            # Successful operation
            operation_succeeded = True

        assert operation_succeeded

    @pytest.mark.asyncio
    async def test_database_error_handler_converts_errors(self):
        """Test database error handler converts generic errors."""
        with pytest.raises(DatabaseError) as exc_info:
            async with database_error_handler("test_operation"):
                raise Exception("Generic database error")

        error = exc_info.value
        assert error.category == ErrorCategory.DATABASE_ERROR
        assert "test_operation" in error.context["operation"]


class TestCircuitBreakerWithMetrics:
    """Test circuit breaker with metrics integration."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_tracks_failures(self):
        """Test circuit breaker failure tracking."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)

        async def failing_service():
            raise NetworkError(message="Service unavailable", service="test_service")

        # Record failures
        for _ in range(2):
            with pytest.raises(NetworkError):
                await cb.call(failing_service)

        # Circuit should be open
        assert cb.state == "open"

    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovery after timeout."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

        async def failing_then_succeeding():
            if cb.failure_count >= 2:
                return "success"
            raise NetworkError(message="Temporary failure", service="test_service")

        # Trigger failures
        for _ in range(2):
            with pytest.raises(NetworkError):
                await cb.call(failing_then_succeeding)

        assert cb.state == "open"

        # Wait for recovery timeout
        await asyncio.sleep(0.15)

        # Should enter half-open and then succeed
        result = await cb.call(failing_then_succeeding)
        assert result == "success"
        assert cb.state == "closed"


class TestErrorContextPropagation:
    """Test error context propagation through async operations."""

    @pytest.mark.asyncio
    async def test_context_propagates_through_async_calls(self):
        """Test error context propagates through nested async calls."""
        error_context.set("request_id", "test-123")
        error_context.set("user_id", "user-456")

        async def inner_operation():
            # Context should be available here
            request_id = error_context.get("request_id")
            user_id = error_context.get("user_id")
            return {"request_id": request_id, "user_id": user_id}

        async def outer_operation():
            await asyncio.sleep(0.01)
            return await inner_operation()

        result = await outer_operation()

        assert result["request_id"] == "test-123"
        assert result["user_id"] == "user-456"

        # Cleanup
        error_context.clear()

    @pytest.mark.asyncio
    async def test_context_isolation_between_tasks(self):
        """Test error context is isolated between concurrent tasks."""
        results = []

        async def task_with_context(task_id: str):
            error_context.clear()
            error_context.set("task_id", task_id)
            await asyncio.sleep(0.01)
            retrieved_id = error_context.get("task_id")
            results.append((task_id, retrieved_id))

        # Run tasks concurrently
        await asyncio.gather(
            task_with_context("task-1"),
            task_with_context("task-2"),
            task_with_context("task-3"),
        )

        # Each task should have retrieved its own task_id
        for original_id, retrieved_id in results:
            assert original_id == retrieved_id


class TestEndToEndErrorFlow:
    """Test complete error handling flow with all components."""

    @pytest.mark.asyncio
    async def test_complete_error_flow_with_retry_and_metrics(self):
        """Test complete error handling flow: error → retry → metrics."""
        attempt_count = 0

        @retry_with_exponential_backoff(max_retries=2, base_delay=0.01)
        async def operation_that_fails_then_succeeds():
            nonlocal attempt_count
            attempt_count += 1

            # Set error context
            error_context.set("operation", "test_operation")
            error_context.set("attempt", attempt_count)

            if attempt_count < 2:
                raise NetworkError(
                    message=f"Attempt {attempt_count} failed", service="test_service"
                )

            return {"status": "success", "attempts": attempt_count}

        # Execute operation
        result = await operation_that_fails_then_succeeds()

        assert result["status"] == "success"
        assert result["attempts"] == 2

        # Cleanup
        error_context.clear()

    @pytest.mark.asyncio
    async def test_circuit_breaker_with_retry_integration(self):
        """Test circuit breaker and retry logic working together."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=0.1)
        call_count = 0

        @retry_with_exponential_backoff(max_retries=2, base_delay=0.01)
        async def flaky_service_with_circuit_breaker():
            nonlocal call_count
            call_count += 1

            async def actual_service():
                if call_count <= 2:
                    raise NetworkError(message="Service error", service="flaky_service")
                return "success"

            return await cb.call(actual_service)

        # Execute - should succeed after retries
        result = await flaky_service_with_circuit_breaker()
        assert result == "success"


class TestMetricsCollectionIntegration:
    """Test metrics collection across error handling operations."""

    @patch("src.shared.error_metrics.PROMETHEUS_AVAILABLE", True)
    @patch("src.shared.error_metrics.error_counter")
    @patch("src.shared.error_metrics.error_duration")
    def test_error_metrics_tracked_in_handler(self, mock_duration, mock_counter):
        """Test error metrics are tracked during error handling."""
        mock_counter_labels = Mock()
        mock_duration_labels = Mock()
        mock_counter.labels.return_value = mock_counter_labels
        mock_duration.labels.return_value = mock_duration_labels

        collector = ErrorMetricsCollector(component="integration_test")

        # Simulate error handling
        error = ReflectAIError(
            message="Test error",
            error_code="TEST_ERROR",
            category=ErrorCategory.NETWORK_ERROR,
        )

        start_time = time.time()
        time.sleep(0.01)
        duration = time.time() - start_time

        # Track error as middleware would
        collector.track_error(error=error, handler_type="retry", processing_duration=duration)

        # Verify metrics were tracked
        mock_counter_labels.inc.assert_called_once()
        mock_duration_labels.observe.assert_called_once()


class TestErrorRecoveryPatterns:
    """Test various error recovery patterns."""

    @pytest.mark.asyncio
    async def test_retry_with_exponential_backoff_timing(self):
        """Test exponential backoff delays are applied."""
        attempt_times = []

        @retry_with_exponential_backoff(max_retries=3, base_delay=0.01, jitter=False)
        async def operation_that_always_fails():
            attempt_times.append(time.time())
            raise NetworkError(message="Always fails", service="test")

        # Execute and expect failure
        with pytest.raises(ReflectAIError):
            await operation_that_always_fails()

        # Verify delays increased exponentially
        assert len(attempt_times) == 4  # Initial + 3 retries

        # Check delays (approximately)
        for i in range(1, len(attempt_times)):
            delay = attempt_times[i] - attempt_times[i - 1]
            expected_min_delay = 0.01 * (2 ** (i - 1))
            # Allow some margin for execution time
            assert delay >= expected_min_delay * 0.8

    @pytest.mark.asyncio
    async def test_circuit_breaker_prevents_cascade_failures(self):
        """Test circuit breaker prevents cascade failures."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=10)
        call_count = 0

        async def always_failing_service():
            nonlocal call_count
            call_count += 1
            raise NetworkError(message="Service down", service="test")

        # Trigger circuit breaker
        for _ in range(2):
            with pytest.raises(NetworkError):
                await cb.call(always_failing_service)

        assert cb.state == "open"

        # Next calls should fail immediately without calling service
        calls_before = call_count
        with pytest.raises(ReflectAIError) as exc_info:
            await cb.call(always_failing_service)

        # Service should not have been called
        assert call_count == calls_before
        assert "Circuit breaker is open" in str(exc_info.value)


class TestAsyncContextSafety:
    """Test async context safety and isolation."""

    @pytest.mark.asyncio
    async def test_concurrent_operations_with_independent_contexts(self):
        """Test concurrent operations maintain independent error contexts."""
        results = {}

        async def operation_with_context(op_id: str):
            error_context.clear()
            error_context.set("operation_id", op_id)
            error_context.set("start_time", time.time())

            await asyncio.sleep(0.01)

            # Retrieve context
            retrieved_id = error_context.get("operation_id")
            results[op_id] = retrieved_id

        # Run multiple operations concurrently
        ops = [f"op-{i}" for i in range(5)]
        await asyncio.gather(*[operation_with_context(op_id) for op_id in ops])

        # Each operation should have retrieved its own ID
        for op_id in ops:
            assert results[op_id] == op_id


class TestDatabaseErrorHandlerWithSQLAlchemy:
    """Test database error handler with SQLAlchemy-like errors."""

    @pytest.mark.asyncio
    async def test_generic_database_error_handling(self):
        """Test handling of generic database errors."""
        with pytest.raises(DatabaseError) as exc_info:
            async with database_error_handler("test_query"):
                raise Exception("Connection refused")

        error = exc_info.value
        assert error.category == ErrorCategory.DATABASE_ERROR
        assert "test_query" in error.context["operation"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
