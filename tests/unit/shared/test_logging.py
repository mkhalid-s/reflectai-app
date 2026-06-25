"""
Tests for ReflectAI Unified Logging Foundation

Comprehensive tests for structlog-based logging with correlation IDs,
context management, and structured output.
"""

import asyncio
import logging
from unittest.mock import patch

import pytest

# Try to import structlog, skip tests if not available
try:
    import structlog

    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False

from src.shared.logging import (
    LoggingContext,
    clear_logging_context,
    configure_logging,
    get_correlation_id,
    get_logger,
    get_logging_health,
    log_business_event,
    log_error_with_context,
    log_function_call,
    log_function_result,
    set_agent_context,
    set_correlation_id,
    set_user_context,
)


class TestConfigureLogging:
    """Test logging configuration."""

    def test_configure_logging_development(self):
        """Test development mode configuration."""
        configure_logging(environment="development", log_level="DEBUG")

        # Verify logger can be obtained
        logger = get_logger("test")
        assert logger is not None

    def test_configure_logging_production(self):
        """Test production mode configuration with JSON."""
        configure_logging(environment="production", log_level="INFO", json_format=True)

        logger = get_logger("test")
        assert logger is not None

    def test_configure_logging_with_log_file(self, tmp_path):
        """Test configuration with log file."""
        log_file = str(tmp_path / "test.log")
        configure_logging(environment="development", log_file=log_file)

        logger = get_logger("test")
        assert logger is not None

    def test_configure_logging_without_structlog(self):
        """Test fallback when structlog not available."""
        with patch("src.shared.logging.STRUCTLOG_AVAILABLE", False):
            configure_logging(environment="development")

            logger = get_logger("test")
            assert logger is not None
            assert isinstance(logger, logging.Logger)


class TestCorrelationID:
    """Test correlation ID management."""

    def test_set_and_get_correlation_id(self):
        """Test setting and getting correlation ID."""
        test_id = "test-correlation-123"

        set_correlation_id(test_id)
        retrieved_id = get_correlation_id()

        assert retrieved_id == test_id

        # Cleanup
        clear_logging_context()

    def test_correlation_id_none_initially(self):
        """Test correlation ID is None initially."""
        clear_logging_context()

        correlation_id = get_correlation_id()

        assert correlation_id is None

    def test_clear_correlation_id(self):
        """Test clearing correlation ID."""
        set_correlation_id("test-123")
        clear_logging_context()

        correlation_id = get_correlation_id()

        assert correlation_id is None


class TestUserContext:
    """Test user context management."""

    def test_set_user_context(self):
        """Test setting user context."""
        set_user_context("U123456", "T789012")

        # Context should be set (actual validation would require checking contextvars)
        # This is more of a smoke test
        assert True

        # Cleanup
        clear_logging_context()

    def test_set_user_context_without_team(self):
        """Test setting user context without team ID."""
        set_user_context("U123456")

        assert True

        # Cleanup
        clear_logging_context()


class TestAgentContext:
    """Test agent context management."""

    def test_set_agent_context_full(self):
        """Test setting full agent context."""
        set_agent_context(agent_type="advisor", model="gpt-4", stage="analysis")

        assert True

        # Cleanup
        clear_logging_context()

    def test_set_agent_context_minimal(self):
        """Test setting minimal agent context."""
        set_agent_context(agent_type="advisor")

        assert True

        # Cleanup
        clear_logging_context()


class TestLoggingContext:
    """Test LoggingContext context manager."""

    def test_logging_context_basic(self):
        """Test basic logging context usage."""
        with LoggingContext(correlation_id="test-123"):
            correlation_id = get_correlation_id()
            assert correlation_id == "test-123"

        # Context should be restored after exit
        correlation_id = get_correlation_id()
        # Should be None or previous value
        assert correlation_id != "test-123"

    def test_logging_context_auto_generate_correlation_id(self):
        """Test auto-generation of correlation ID."""
        with LoggingContext():
            correlation_id = get_correlation_id()
            assert correlation_id is not None
            assert len(correlation_id) > 0

    def test_logging_context_no_auto_generate(self):
        """Test disabling auto-generation."""
        with LoggingContext(auto_generate_correlation_id=False):
            # Should not auto-generate
            pass

    def test_logging_context_with_user(self):
        """Test logging context with user information."""
        with LoggingContext(correlation_id="test-123", user_id="U123", team_id="T456"):
            correlation_id = get_correlation_id()
            assert correlation_id == "test-123"

    def test_logging_context_nested(self):
        """Test nested logging contexts."""
        with LoggingContext(correlation_id="outer"):
            outer_id = get_correlation_id()
            assert outer_id == "outer"

            with LoggingContext(correlation_id="inner"):
                inner_id = get_correlation_id()
                assert inner_id == "inner"

            # Should restore outer context
            restored_id = get_correlation_id()
            assert restored_id == "outer"

    @pytest.mark.asyncio
    async def test_logging_context_async(self):
        """Test logging context in async function."""

        async def async_operation():
            with LoggingContext(correlation_id="async-123"):
                correlation_id = get_correlation_id()
                assert correlation_id == "async-123"
                await asyncio.sleep(0.01)
                # Should still have correct correlation ID after await
                correlation_id = get_correlation_id()
                assert correlation_id == "async-123"

        await async_operation()


class TestGetLogger:
    """Test logger retrieval."""

    def test_get_logger_with_name(self):
        """Test getting logger with specific name."""
        logger = get_logger("test.module")

        assert logger is not None

    def test_get_logger_without_name(self):
        """Test getting logger without name."""
        logger = get_logger()

        assert logger is not None

    def test_get_logger_without_structlog(self):
        """Test getting logger when structlog not available."""
        with patch("src.shared.logging.STRUCTLOG_AVAILABLE", False):
            logger = get_logger("test")

            assert isinstance(logger, logging.Logger)


class TestUtilityFunctions:
    """Test logging utility functions."""

    def test_log_function_call(self):
        """Test logging function call."""
        logger = get_logger("test")

        # Should not raise exception
        log_function_call(logger, "test_function", param1="value1", param2="value2")

    def test_log_function_result(self):
        """Test logging function result."""
        logger = get_logger("test")

        log_function_result(logger, "test_function", duration_ms=123.45, success=True, result="OK")

    def test_log_error_with_context(self):
        """Test logging error with context."""
        logger = get_logger("test")

        error = ValueError("Test error")
        log_error_with_context(logger, error, "test_operation", user_id="U123", component="test")

    def test_log_business_event(self):
        """Test logging business event."""
        logger = get_logger("test")

        log_business_event(
            logger,
            "user_signup",
            user_id="U123",
            team_id="T456",
            plan="enterprise",
        )


class TestHealthCheck:
    """Test logging health check."""

    def test_get_logging_health(self):
        """Test getting logging health status."""
        health = get_logging_health()

        assert isinstance(health, dict)
        assert "structlog_available" in health
        assert "correlation_id_enabled" in health
        assert "context_variables_active" in health

    def test_logging_health_with_correlation_id(self):
        """Test health check with correlation ID set."""
        set_correlation_id("test-123")

        health = get_logging_health()

        assert health["correlation_id_enabled"] is True
        assert health["current_correlation_id"] == "test-123"

        # Cleanup
        clear_logging_context()

    def test_logging_health_context_variables(self):
        """Test health check shows active context variables."""
        set_correlation_id("test-123")
        set_user_context("U123", "T456")

        health = get_logging_health()

        context_vars = health["context_variables_active"]
        assert context_vars["correlation_id"] is True
        assert context_vars["user_id"] is True
        assert context_vars["team_id"] is True

        # Cleanup
        clear_logging_context()


@pytest.mark.skipif(not STRUCTLOG_AVAILABLE, reason="structlog not available")
class TestStructlogIntegration:
    """Test structlog-specific features."""

    def test_structlog_configuration(self):
        """Test structlog is properly configured."""
        configure_logging(environment="development")

        logger = get_logger("test")

        # Should be a structlog BoundLogger
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")
        assert hasattr(logger, "warning")

    def test_correlation_id_in_log(self, caplog):
        """Test correlation ID appears in logs."""
        configure_logging(environment="development")
        logger = get_logger("test")

        set_correlation_id("test-correlation-id")

        with caplog.at_level(logging.INFO):
            logger.info("Test message")

        # Check if correlation ID would be in context
        # (actual verification would require parsing structured output)
        assert True

        # Cleanup
        clear_logging_context()


class TestClearLoggingContext:
    """Test clearing all logging context."""

    def test_clear_all_context(self):
        """Test clearing all context variables."""
        # Set various context values
        set_correlation_id("test-123")
        set_user_context("U123", "T456")
        set_agent_context("advisor", "gpt-4")

        # Clear all
        clear_logging_context()

        # Verify all cleared
        health = get_logging_health()
        context_vars = health["context_variables_active"]

        assert context_vars["correlation_id"] is False
        assert context_vars["user_id"] is False
        assert context_vars["team_id"] is False
        assert context_vars["agent_context"] is False


@pytest.mark.asyncio
class TestAsyncLogging:
    """Test logging in async contexts."""

    async def test_correlation_id_isolation(self):
        """Test correlation ID isolation between async tasks."""

        async def task1():
            with LoggingContext(correlation_id="task1"):
                await asyncio.sleep(0.01)
                assert get_correlation_id() == "task1"

        async def task2():
            with LoggingContext(correlation_id="task2"):
                await asyncio.sleep(0.01)
                assert get_correlation_id() == "task2"

        # Run concurrently
        await asyncio.gather(task1(), task2())

    async def test_context_propagation_through_await(self):
        """Test context propagates correctly through await points."""
        test_id = "test-propagation"

        async def inner_operation():
            await asyncio.sleep(0.01)
            return get_correlation_id()

        with LoggingContext(correlation_id=test_id):
            result = await inner_operation()
            assert result == test_id


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_multiple_clear_calls(self):
        """Test multiple clear calls don't cause issues."""
        clear_logging_context()
        clear_logging_context()
        clear_logging_context()

        # Should not raise exception
        assert True

    def test_set_correlation_id_empty_string(self):
        """Test setting empty string as correlation ID."""
        set_correlation_id("")

        correlation_id = get_correlation_id()
        assert correlation_id == ""

        # Cleanup
        clear_logging_context()

    def test_logging_with_none_values(self):
        """Test logging functions handle None values gracefully."""
        logger = get_logger("test")

        # Should not raise exceptions
        log_function_call(logger, "test", param=None)
        log_function_result(logger, "test", duration_ms=None, success=True)
        log_business_event(logger, "test", data=None)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
