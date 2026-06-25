"""
Example unit tests demonstrating the testing framework.
Task 5: Testing framework foundation - Example usage

This module shows how to use the testing framework components:
- Fixtures from conftest.py
- Factory classes for test data generation
- Mocking infrastructure
- Performance testing utilities
"""

import pytest

from tests.factories import ActivityFactory, UserFactory


class TestUserFactoryExample:
    """Example tests using UserFactory."""

    def test_user_factory_basic_creation(self):
        """Test basic user creation with UserFactory."""
        user = UserFactory()

        assert "id" in user
        assert "name" in user
        assert "email" in user
        assert "role" in user
        assert user["is_active"] is not None

    def test_user_factory_junior_engineer(self):
        """Test creating a junior engineer."""
        user = UserFactory.create_junior_engineer()

        assert user["role"] == "software_engineer"
        assert user["level"] == "junior"
        assert user["years_of_experience"] <= 2
        assert "python" in user["skills"]

    def test_user_factory_team_creation(self):
        """Test creating a team with manager and members."""
        team = UserFactory.create_team(team_size=3)

        assert "manager" in team
        assert "members" in team
        assert len(team["members"]) == 3
        assert team["team_size"] == 4  # 3 members + 1 manager

        # All team members should be in same organization
        org_id = team["manager"]["organization_id"]
        for member in team["members"]:
            assert member["organization_id"] == org_id


class TestActivityFactoryExample:
    """Example tests using ActivityFactory."""

    def test_activity_factory_basic_creation(self):
        """Test basic activity creation."""
        activity = ActivityFactory()

        assert "id" in activity
        assert "user_id" in activity
        assert "content" in activity
        assert "category" in activity
        assert "confidence" in activity

    def test_activity_factory_code_review(self):
        """Test creating a code review activity."""
        activity = ActivityFactory.create_code_review()

        assert activity["category"] == "code_review"
        assert activity["subcategory"] == "pull_request_review"
        assert activity["confidence"] >= 0.8
        assert any(
            keyword in ["code", "review", "pull", "request"] for keyword in activity["keywords"]
        )

    def test_activity_factory_sequence(self):
        """Test creating activity sequence for a user."""
        user_id = "test_user_123"
        activities = ActivityFactory.create_activity_sequence(user_id, days=7)

        assert len(activities) >= 20  # Should create multiple activities

        # All activities should belong to the user
        for activity in activities:
            assert activity["user_id"] == user_id

        # Activities should be chronologically ordered
        timestamps = [activity["timestamp"] for activity in activities]
        assert timestamps == sorted(timestamps)


class TestMockInfrastructureExample:
    """Example tests using mock infrastructure fixtures."""

    def test_mock_openai_client(self, mock_openai_client):
        """Test using mocked OpenAI client."""
        # Use the mock client
        response = mock_openai_client.chat.completions.create(
            model="gpt-4", messages=[{"role": "user", "content": "Test message"}]
        )

        assert response.choices[0].message.content == "Test response from OpenAI"
        assert response.usage.total_tokens == 100

        # Verify the mock was called
        mock_openai_client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_mock_slack_client(self, mock_slack_client):
        """Test using mocked Slack client."""
        response = await mock_slack_client.chat_postMessage(channel="#test", text="Test message")

        assert response["ok"] is True
        assert "ts" in response

        mock_slack_client.chat_postMessage.assert_called_once_with(
            channel="#test", text="Test message"
        )


class TestPerformanceExample:
    """Example performance tests using performance fixtures."""

    def test_activity_creation_performance(self, performance_timer):
        """Test performance of activity creation."""
        performance_timer.start()

        # Create 100 activities
        activities = [ActivityFactory() for _ in range(100)]

        performance_timer.stop()

        assert len(activities) == 100
        assert performance_timer.duration < 1.0  # Should complete in under 1 second


@pytest.mark.asyncio
class TestAsyncExample:
    """Example async tests using async fixtures."""

    async def test_config_manager_fixture(self, config_manager):
        """Test using config manager fixture."""
        config = config_manager.get_config()

        assert config is not None
        assert config.app.name == "reflectai"
        assert config.app.version == "2.0.0"

    async def test_secrets_manager_fixture(self, secrets_manager):
        """Test using secrets manager fixture."""
        # Test secrets should be available
        db_url = secrets_manager.get_secret("DATABASE_URL")
        assert db_url is not None
        assert "postgresql://" in db_url

        # Test required secret
        api_key = secrets_manager.get_secret("OPENAI_API_KEY", required=True)
        assert api_key == "sk-test-openai-key"


class TestDataValidationExample:
    """Example tests for data validation."""

    def test_user_data_validation(self, sample_user_data):
        """Test user data fixture provides valid data."""
        assert "id" in sample_user_data
        assert "slack_user_id" in sample_user_data
        assert "email" in sample_user_data
        assert "@" in sample_user_data["email"]

    def test_activity_data_validation(self, sample_activity_data):
        """Test activity data fixture provides valid data."""
        assert "id" in sample_activity_data
        assert "user_id" in sample_activity_data
        assert "content" in sample_activity_data
        assert "timestamp" in sample_activity_data
        assert "confidence" in sample_activity_data

    def test_competency_data_validation(self, sample_competency_data):
        """Test competency data fixture provides valid data."""
        assert "id" in sample_competency_data
        assert "user_id" in sample_competency_data
        assert "category" in sample_competency_data
        assert "score" in sample_competency_data
        assert 1.0 <= sample_competency_data["score"] <= 5.0


class TestErrorHandlingExample:
    """Example tests for error handling."""

    def test_factory_with_invalid_params(self):
        """Test factory behavior with invalid parameters."""
        # This should not raise an exception but should handle gracefully
        user = UserFactory(years_of_experience=-5)  # Invalid experience

        # Factory should create user despite invalid input
        assert "id" in user
        assert "name" in user

    def test_low_confidence_activity(self):
        """Test creating activities with low confidence."""
        activity = ActivityFactory.create_low_confidence_activity()

        assert activity["confidence"] < 0.5
        assert activity["category"] == "other"
        assert activity["subcategory"] == "unclear"


@pytest.mark.integration
class TestIntegrationExample:
    """Example integration tests using testcontainers."""

    async def test_database_connection(self, db_session):
        """Test database connection using testcontainer."""
        # This would test actual database operations
        # For now, we have a mock session
        assert db_session is not None

    async def test_redis_connection(self, redis_client):
        """Test Redis connection using testcontainer."""
        # This would test actual Redis operations
        # For now, we have a mock client
        assert redis_client is not None


@pytest.mark.slow
class TestLongRunningExample:
    """Example of tests marked as slow."""

    def test_large_dataset_processing(self):
        """Test processing large dataset (marked as slow)."""
        # Create large dataset
        activities = ActivityFactory.create_golden_dataset(size=500)

        assert len(activities) == 500

        # Process dataset (simulated)
        processed_count = 0
        for activity in activities:
            if activity["confidence"] > 0.8:
                processed_count += 1

        assert processed_count > 0


# Test markers demonstration
@pytest.mark.unit
def test_marked_as_unit():
    """Example test marked as unit test."""
    user = UserFactory()
    assert user["name"] is not None


@pytest.mark.llm
def test_marked_as_llm(mock_anthropic_client):
    """Example test marked as requiring LLM mocks."""
    response = mock_anthropic_client.messages.create(
        model="claude-3-haiku", messages=[{"role": "user", "content": "Test"}]
    )

    assert response.content[0].text == "Test response from Claude"


@pytest.mark.database
async def test_marked_as_database(db_session):
    """Example test marked as requiring database."""
    # Database operations would go here
    assert db_session is not None


if __name__ == "__main__":
    # Run tests when executed directly
    pytest.main([__file__, "-v"])
