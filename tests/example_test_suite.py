#!/usr/bin/env python3
"""
Example Test Suite Demonstrating New Mock Infrastructure

This test suite demonstrates how to use the comprehensive mock infrastructure
for testing ReflectAI components with realistic scenarios.
"""

import time
from unittest.mock import patch

import pytest

from tests.factories import ActivityFactory, UserFactory
from tests.mocks import (
    create_test_event,
    get_external_service_mock,
    get_llm_mock,
    get_slack_client_mock,
    get_temporal_client_mock,
)
from tests.performance import record_test_timing
from tests.testcontainers import get_container_manager


class TestLLMMockInfrastructure:
    """Test suite demonstrating LLM mock usage."""

    @pytest.mark.asyncio
    async def test_activity_classification_with_mock(self):
        """Test activity classification using LLM mock."""
        # Get a mock LLM client
        mock_llm = get_llm_mock()

        # Create test data
        test_prompt = """
        Classify the following activity:
        User completed a Python programming course and received a certificate.
        This is part of their professional development.
        """

        # Mock the external LLM service
        with patch("src.core.llm.client.LLMClient") as mock_client_class:
            mock_client_class.return_value = mock_llm

            # Import and use the actual service
            from src.core.llm.client import LLMClient

            client = LLMClient()

            # Execute classification
            result = await client.classify_activity(test_prompt)

            # Verify the result matches our expected pattern
            assert result is not None
            assert "activity_type" in result
            assert result["activity_type"] == "professional_development"

    @pytest.mark.asyncio
    async def test_competency_assessment_with_different_models(self):
        """Test competency assessment with different LLM models."""
        # Test with different model types
        for model in ["gpt-4", "claude-3-sonnet-20240229", "amazon.nova-lite-v1:0"]:
            mock_llm = get_llm_mock(model=model)

            test_prompt = (
                "Assess the competency level of a user with 5 years of experience in data science."
            )

            with patch("src.core.llm.client.LLMClient") as mock_client_class:
                mock_client_class.return_value = mock_llm

                from src.core.llm.client import LLMClient

                client = LLMClient()

                result = await client.assess_competency(test_prompt)

                assert result is not None
                assert "competency_level" in result
                assert result["score"] > 0

    @pytest.mark.asyncio
    async def test_llm_error_scenarios(self):
        """Test LLM error handling scenarios."""
        mock_llm = get_llm_mock()

        # Test rate limiting
        test_prompt = "This is a test prompt that should trigger rate limiting."

        with patch("src.core.llm.client.LLMClient") as mock_client_class:
            mock_client_class.return_value = mock_llm

            from src.core.llm.client import LLMClient

            client = LLMClient()

            # The mock will handle different prompt patterns
            result = await client.process_request(test_prompt)

            # Verify error handling
            assert result is not None


class TestSlackMockInfrastructure:
    """Test suite demonstrating Slack API mock usage."""

    @pytest.mark.asyncio
    async def test_slack_message_handling(self):
        """Test Slack message event handling."""
        # Create a mock Slack client
        mock_client = get_slack_client_mock()

        # Create test event
        test_event = create_test_event(
            "message", text="Help me with my project", user="U1234567890", channel="C1234567890"
        )

        with patch("src.bot.client.SlackClient") as mock_client_class:
            mock_client_class.return_value = mock_client

            from src.bot.client import SlackClient

            client = SlackClient()

            # Test message sending
            response = await client.send_message(
                channel=test_event.channel, text="I'll help you with your project!"
            )

            assert response["ok"] is True
            assert response["channel"] == test_event.channel

    @pytest.mark.asyncio
    async def test_slack_app_mention_handling(self):
        """Test app mention event handling."""
        mock_client = get_slack_client_mock()

        test_event = create_test_event("app_mention", text="<@BOT123> help me", user="U1234567890")

        with patch("src.bot.client.SlackClient") as mock_client_class:
            mock_client_class.return_value = mock_client

            from src.bot.client import SlackClient

            client = SlackClient()

            # Test app mention response
            response = await client.handle_app_mention(test_event)

            assert response["ok"] is True

    @pytest.mark.asyncio
    async def test_slack_home_tab(self):
        """Test Slack home tab publishing."""
        mock_client = get_slack_client_mock()

        with patch("src.bot.client.SlackClient") as mock_client_class:
            mock_client_class.return_value = mock_client

            from src.bot.client import SlackClient

            client = SlackClient()

            # Test home tab publishing
            response = await client.publish_home_tab(user="U1234567890")

            assert response["ok"] is True
            assert "view" in response


class TestTemporalMockInfrastructure:
    """Test suite demonstrating Temporal workflow mock usage."""

    @pytest.mark.asyncio
    async def test_workflow_execution(self):
        """Test workflow execution with mock."""
        mock_client = get_temporal_client_mock()

        with patch("src.workflows.client.TemporalClient") as mock_client_class:
            mock_client_class.return_value = mock_client

            from src.workflows.client import TemporalClient

            client = TemporalClient()

            # Start a workflow
            workflow_id = "test-workflow-123"
            execution = client.start_workflow(
                "ActivityProcessingWorkflow",
                workflow_id=workflow_id,
                activity_data={"user_id": "U123", "activity": "completed_course"},
            )

            assert execution.workflow_id == workflow_id
            assert execution.state.value == "Running"

    @pytest.mark.asyncio
    async def test_batch_processing_workflow(self):
        """Test batch processing workflow."""
        mock_client = get_temporal_client_mock()

        with patch("src.workflows.client.TemporalClient") as mock_client_class:
            mock_client_class.return_value = mock_client

            from src.workflows.client import TemporalClient

            client = TemporalClient()

            # Execute batch processing
            workflow_id = "batch-workflow-456"
            result = await client.execute_workflow(
                workflow_id,
                batch_size=10,
                items=[{"id": i, "data": f"item_{i}"} for i in range(10)],
            )

            assert result["status"] == "completed"
            assert result["batch_size"] == 10

    @pytest.mark.asyncio
    async def test_workflow_error_handling(self):
        """Test workflow error handling."""
        mock_client = get_temporal_client_mock()

        with patch("src.workflows.client.TemporalClient") as mock_client_class:
            mock_client_class.return_value = mock_client

            from src.workflows.client import TemporalClient

            client = TemporalClient()

            # Test error scenario
            workflow_id = "error-workflow-789"

            with pytest.raises(Exception, match="Simulated activity failure"):
                await client.execute_workflow(workflow_id, fail_activity=True)


class TestExternalServicesMock:
    """Test suite demonstrating external services mock usage."""

    @pytest.mark.asyncio
    async def test_oauth_authentication(self):
        """Test OAuth authentication flow."""
        mock_service = get_external_service_mock()

        # Test Google OAuth
        oauth_mock = mock_service.create_oauth_mock("google")

        with patch("src.auth.oauth.OAuthService") as mock_oauth_class:
            mock_oauth_class.return_value = oauth_mock

            from src.auth.oauth import OAuthService

            service = OAuthService()

            # Exchange authorization code
            result = await service.exchange_code(
                code="test_code_123", client_id="test_client", client_secret="test_secret"
            )

            assert "access_token" in result
            assert result["token_type"] == "Bearer"

    @pytest.mark.asyncio
    async def test_email_sending(self):
        """Test email service functionality."""
        mock_service = get_external_service_mock()
        email_mock = mock_service.create_email_mock("smtp")

        with patch("src.services.email.EmailService") as mock_email_class:
            mock_email_class.return_value = email_mock

            from src.services.email import EmailService

            service = EmailService()

            # Send test email
            result = await service.send_email(
                to=["test@example.com"],
                subject="Test Email",
                body="This is a test email from ReflectAI",
            )

            assert result["status"] == "sent"
            assert result["message_id"].startswith("msg_")

    @pytest.mark.asyncio
    async def test_webhook_delivery(self):
        """Test webhook delivery functionality."""
        mock_service = get_external_service_mock()
        webhook_mock = mock_service.create_webhook_mock("slack")

        with patch("src.services.webhook.WebhookService") as mock_webhook_class:
            mock_webhook_class.return_value = webhook_mock

            from src.services.webhook import WebhookService

            service = WebhookService()

            # Deliver test webhook
            result = await service.deliver_webhook(
                url="https://hooks.slack.com/test", payload={"text": "Test message"}
            )

            assert result["status_code"] == 200
            assert result["response"] == "OK"


class TestIntegrationWithFactories:
    """Test suite demonstrating integration with test factories."""

    def test_user_factory_integration(self):
        """Test user factory with mock services."""
        # Create test user
        user = UserFactory.create(
            name="Test User", email="test@example.com", slack_id="U1234567890"
        )

        assert user.name == "Test User"
        assert user.email == "test@example.com"
        assert user.slack_id == "U1234567890"

    def test_activity_factory_integration(self):
        """Test activity factory with mock services."""
        activity = ActivityFactory.create(
            user_id="U1234567890",
            activity_type="professional_development",
            description="Completed Python course",
            metadata={"duration": "40 hours", "certificate": True},
        )

        assert activity.activity_type == "professional_development"
        assert activity.description == "Completed Python course"
        assert activity.metadata["certificate"] is True

    @pytest.mark.asyncio
    async def test_full_integration_scenario(self):
        """Test full integration scenario with all mocks and factories."""
        # Setup all mocks
        llm_mock = get_llm_mock()
        slack_mock = get_slack_client_mock()
        temporal_mock = get_temporal_client_mock()
        external_mock = get_external_service_mock()

        # Create test data
        user = UserFactory.create(name="Integration Test User", email="integration@example.com")

        activity = ActivityFactory.create(
            user_id=user.id,
            activity_type="learning",
            description="Completed comprehensive integration test",
        )

        # Test the complete flow
        with (
            patch.multiple("src.core.llm.client", LLMClient=lambda: llm_mock),
            patch.multiple("src.bot.client", SlackClient=lambda: slack_mock),
            patch.multiple("src.workflows.client", TemporalClient=lambda: temporal_mock),
            patch.multiple("src.services.external", ExternalService=lambda: external_mock),
        ):
            # Import services
            from src.bot.client import SlackClient
            from src.core.llm.client import LLMClient
            from src.services.external import ExternalService
            from src.workflows.client import TemporalClient

            # Execute integration test
            llm_client = LLMClient()
            slack_client = SlackClient()
            temporal_client = TemporalClient()
            external_service = ExternalService()

            # Process activity
            classification = await llm_client.classify_activity(activity.description)
            assert classification["activity_type"] == "professional_development"

            # Send notification
            notification = await slack_client.send_message(
                channel="C1234567890", text=f"Activity processed for {user.name}"
            )
            assert notification["ok"] is True

            # Start workflow
            workflow = temporal_client.start_workflow(
                "ActivityProcessingWorkflow", workflow_id="integration-test-workflow"
            )
            assert workflow.state.value == "Running"

            # Send email confirmation
            email_result = await external_service.send_email(
                to=[user.email],
                subject="Activity Processed",
                body="Your activity has been successfully processed.",
            )
            assert email_result["status"] == "sent"


class TestPerformanceValidation:
    """Test suite demonstrating performance validation."""

    @pytest.mark.performance
    def test_fast_unit_test(self):
        """A fast unit test that should complete quickly."""
        start_time = time.time()

        # Simulate some work
        result = sum(i**2 for i in range(1000))

        end_time = time.time()
        duration = end_time - start_time

        # Record timing for performance validation
        record_test_timing("test_fast_unit_test", duration)

        assert result == 333833500  # Expected result

    @pytest.mark.slow
    @pytest.mark.integration
    def test_integration_test_performance(self):
        """An integration test that takes longer."""
        start_time = time.time()

        # Simulate integration work
        for i in range(100):
            _ = i * i  # Some computation

        time.sleep(0.1)  # Simulate I/O delay

        end_time = time.time()
        duration = end_time - start_time

        # Record timing
        record_test_timing("test_integration_test_performance", duration)

        assert duration < 1.0  # Should complete within 1 second


class TestContainerIntegration:
    """Test suite demonstrating testcontainers usage."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_database_integration(self):
        """Test database integration with testcontainers."""
        container_manager = get_container_manager()

        if not container_manager.is_available():
            pytest.skip("testcontainers not available")

        async with container_manager.create_postgres_container() as env:
            # Use the test database

            # This would be the actual test implementation
            assert env.postgres_url.startswith("postgresql+asyncpg://")
            assert "testuser" in env.postgres_url
            assert "testpass" in env.postgres_url

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_redis_integration(self):
        """Test Redis integration with testcontainers."""
        container_manager = get_container_manager()

        if not container_manager.is_available():
            pytest.skip("testcontainers not available")

        async with container_manager.create_redis_container() as env:
            # Use the test Redis instance
            import redis.asyncio as redis

            client = redis.from_url(env.redis_url)

            # Test basic operations
            await client.set("test_key", "test_value")
            value = await client.get("test_key")

            assert value == "test_value"
            await client.close()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_environment_integration(self):
        """Test full environment with all services."""
        container_manager = get_container_manager()

        if not container_manager.is_available():
            pytest.skip("testcontainers not available")

        async with container_manager.create_full_environment() as env:
            # Test all services are available
            assert env.postgres_url
            assert env.redis_url
            assert env.nats_url

            # Verify connectivity to all services
            import asyncpg
            import redis.asyncio as redis_client

            # Test PostgreSQL
            conn = await asyncpg.connect(env.postgres_url)
            await conn.close()

            # Test Redis
            redis_conn = redis_client.from_url(env.redis_url)
            await redis_conn.ping()
            await redis_conn.close()

            # Test NATS
            import nats

            nc = await nats.connect(env.nats_url)
            await nc.close()


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
