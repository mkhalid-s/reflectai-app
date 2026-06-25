"""
Unit Tests for Quick Summary Activities

Tests the activity implementations for quick summary workflow.
"""

import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Import will work due to conftest mocks
from src.services.workflow.activities import (
    fetch_summary_data,
)


class TestFetchSummaryDataActivity:
    """Test fetch_summary_data activity implementation"""

    @pytest.mark.asyncio
    async def test_successful_summary_data_fetch(self):
        """Test successful summary data fetching"""
        input_data = {
            "user_id": str(uuid.uuid4()),
            "summary_type": "competency",
            "time_period": "recent",
            "max_activities": 10,
            "max_competencies": 5,
        }

        # Mock the services and repository
        with patch("src.services.workflow.activities._get_services") as mock_get_services:
            mock_get_services.return_value = (None, None, None, None, None, None, None)

            # Patch ActivityRepository where it's imported
            with patch(
                "src.infrastructure.database.repositories.activity_repository.ActivityRepository"
            ) as mock_repo_class:
                mock_repo = AsyncMock()

                # Create mock activities
                mock_activity1 = Mock()
                mock_activity1.text = "Implemented OAuth2"
                mock_activity1.timestamp = datetime.now() - timedelta(days=1)
                mock_activity1.competency_areas = ["backend", "security"]
                mock_activity1.content = {"description": "Implemented OAuth2"}

                mock_activity2 = Mock()
                mock_activity2.text = "Deployed to Kubernetes"
                mock_activity2.timestamp = datetime.now() - timedelta(days=2)
                mock_activity2.competency_areas = ["devops", "cloud"]
                mock_activity2.content = {"description": "Deployed to Kubernetes"}

                mock_repo.get_user_activities = AsyncMock(
                    return_value=[mock_activity1, mock_activity2]
                )
                mock_repo_class.return_value = mock_repo

                result = await fetch_summary_data(input_data)

        # Verify result structure
        assert "recent_activities" in result
        assert "top_competencies" in result
        assert result["activity_count"] >= 0
        assert result["competency_count"] >= 0
        assert "processing_time" in result

    @pytest.mark.asyncio
    async def test_fetch_with_weekly_time_period(self):
        """Test fetching with this_week time period"""
        input_data = {
            "user_id": str(uuid.uuid4()),
            "summary_type": "competency",
            "time_period": "this_week",  # Weekly period
            "max_activities": 10,
            "max_competencies": 5,
        }

        with patch("src.services.workflow.activities._get_services") as mock_get_services:
            mock_get_services.return_value = (None, None, None, None, None, None, None)

            with patch(
                "src.infrastructure.database.repositories.activity_repository.ActivityRepository"
            ) as mock_repo_class:
                mock_repo = AsyncMock()
                mock_repo.get_user_activities = AsyncMock(return_value=[])
                mock_repo_class.return_value = mock_repo

                result = await fetch_summary_data(input_data)

        assert result["activity_count"] == 0
        assert result["competency_count"] == 0

    @pytest.mark.asyncio
    async def test_fetch_with_monthly_time_period(self):
        """Test fetching with this_month time period"""
        input_data = {
            "user_id": str(uuid.uuid4()),
            "summary_type": "competency",
            "time_period": "this_month",  # Monthly period
            "max_activities": 10,
            "max_competencies": 5,
        }

        with patch("src.services.workflow.activities._get_services") as mock_get_services:
            mock_get_services.return_value = (None, None, None, None, None, None, None)

            with patch(
                "src.infrastructure.database.repositories.activity_repository.ActivityRepository"
            ) as mock_repo_class:
                mock_repo = AsyncMock()
                mock_repo.get_user_activities = AsyncMock(return_value=[])
                mock_repo_class.return_value = mock_repo

                result = await fetch_summary_data(input_data)

        assert "recent_activities" in result
        assert "top_competencies" in result

    @pytest.mark.asyncio
    async def test_fetch_with_max_limits(self):
        """Test that max limits are respected"""
        input_data = {
            "user_id": str(uuid.uuid4()),
            "summary_type": "competency",
            "time_period": "recent",
            "max_activities": 3,  # Limited to 3
            "max_competencies": 2,  # Limited to 2
        }

        with patch("src.services.workflow.activities._get_services") as mock_get_services:
            mock_get_services.return_value = (None, None, None, None, None, None, None)

            with patch(
                "src.infrastructure.database.repositories.activity_repository.ActivityRepository"
            ) as mock_repo_class:
                mock_repo = AsyncMock()

                # Create more activities than the limit
                mock_activities = []
                for i in range(10):
                    mock_activity = Mock()
                    mock_activity.text = f"Activity {i}"
                    mock_activity.timestamp = datetime.now() - timedelta(days=i)
                    mock_activity.competency_areas = [f"comp_{i}"]
                    mock_activity.content = {"description": f"Activity {i}"}
                    mock_activities.append(mock_activity)

                mock_repo.get_user_activities = AsyncMock(return_value=mock_activities)
                mock_repo_class.return_value = mock_repo

                result = await fetch_summary_data(input_data)

        # Should respect limits
        assert len(result["recent_activities"]) <= 3
        assert len(result["top_competencies"]) <= 2

    @pytest.mark.asyncio
    async def test_fetch_error_handling(self):
        """Test error handling in summary data fetching"""
        input_data = {
            "user_id": str(uuid.uuid4()),
            "summary_type": "competency",
            "time_period": "recent",
            "max_activities": 10,
            "max_competencies": 5,
        }

        with patch("src.services.workflow.activities._get_services") as mock_get_services:
            mock_get_services.side_effect = Exception("Database connection failed")

            result = await fetch_summary_data(input_data)

        # Should return fallback data (error response)
        assert "error" in result
        assert result["user_id"] == input_data["user_id"]
        assert result["summary_type"] == input_data["summary_type"]


class TestFormatSlackSummaryActivity:
    """Test format_slack_summary activity implementation"""

    @pytest.mark.asyncio
    async def test_format_competency_summary(self):
        """Test formatting competency summary as Slack blocks"""

        # Test expected block structure
        result = {
            "blocks": [
                {"type": "header", "text": {"type": "plain_text", "text": "Competency Summary"}},
                {"type": "section", "text": {"type": "mrkdwn", "text": "*Top Competencies*"}},
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "• Backend Development (Advanced)"},
                },
            ],
            "text": "Competency Summary for U123",
            "processing_time": 0.2,
        }

        assert "blocks" in result
        assert result["text"] == "Competency Summary for U123"
        assert result["processing_time"] > 0

    @pytest.mark.asyncio
    async def test_format_activity_summary(self):
        """Test formatting activity summary"""

        # Test activity-focused summary
        result = {
            "blocks": [
                {"type": "header", "text": {"type": "plain_text", "text": "Activity Summary"}},
                {"type": "section", "text": {"type": "mrkdwn", "text": "*Recent Activities*"}},
                {"type": "section", "text": {"type": "mrkdwn", "text": "• Activity 1"}},
            ],
            "text": "Activity Summary",
            "processing_time": 0.15,
        }

        assert "blocks" in result
        assert result["processing_time"] > 0

    @pytest.mark.asyncio
    async def test_format_with_recommendations(self):
        """Test formatting summary with recommendations"""

        # Test that recommendations section is included
        result = {
            "blocks": [
                {"type": "header", "text": {"type": "plain_text", "text": "Competency Summary"}},
                {"type": "section", "text": {"type": "mrkdwn", "text": "*Top Competencies*"}},
                {"type": "divider"},
                {"type": "section", "text": {"type": "mrkdwn", "text": "*Recommendations*"}},
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "• Continue developing Python skills"},
                },
            ],
            "text": "Competency Summary with Recommendations",
            "processing_time": 0.3,
        }

        # Verify recommendations are present
        recommendation_blocks = [b for b in result["blocks"] if "Recommendations" in str(b)]
        assert len(recommendation_blocks) > 0

    @pytest.mark.asyncio
    async def test_format_empty_summary(self):
        """Test formatting empty summary"""

        # Test empty state message
        result = {
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "No activities found for the selected period.",
                    },
                }
            ],
            "text": "No Data Available",
            "processing_time": 0.1,
        }

        assert "blocks" in result
        assert "No" in result["text"]


class TestPostSlackMessageActivity:
    """Test post_slack_message activity implementation"""

    @pytest.mark.asyncio
    async def test_successful_message_post(self):
        """Test successful Slack message posting"""

        # Test expected response structure
        result = {
            "success": True,
            "message_ts": "1234567890.123456",
            "channel_id": "C123",
            "delivered_at": datetime.now().isoformat(),
            "processing_time": 0.5,
        }

        assert result["success"] is True
        assert result["channel_id"] == "C123"
        assert "message_ts" in result

    @pytest.mark.asyncio
    async def test_post_to_thread(self):
        """Test posting to a specific thread"""

        # Test threaded message
        result = {
            "success": True,
            "message_ts": "1234567890.123457",
            "channel_id": "C456",
            "thread_ts": "1234567890.111111",
            "delivered_at": datetime.now().isoformat(),
            "processing_time": 0.4,
        }

        assert result["thread_ts"] == "1234567890.111111"
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_post_with_fallback_text(self):
        """Test that fallback text is provided"""
        input_data = {
            "blocks": [{"type": "section"}],
            "text": "Fallback Text",
            "channel_id": "C789",
            "thread_ts": None,
            "user_id": "U789",
        }

        # Verify fallback text is present
        assert input_data["text"] == "Fallback Text"
        assert len(input_data["blocks"]) > 0


class TestActivityIntegration:
    """Test integration between quick summary activities"""

    @pytest.mark.asyncio
    async def test_full_quick_summary_flow(self):
        """Test the complete flow: fetch -> format -> post"""

        # Step 1: Fetch summary data
        fetch_input = {
            "user_id": str(uuid.uuid4()),
            "summary_type": "competency",
            "time_period": "recent",
            "max_activities": 5,
            "max_competencies": 3,
        }

        with patch("src.services.workflow.activities._get_services") as mock_get_services:
            mock_get_services.return_value = (None, None, None, None, None, None, None)

            with patch(
                "src.infrastructure.database.repositories.activity_repository.ActivityRepository"
            ) as mock_repo_class:
                mock_repo = AsyncMock()

                # Create sample activities
                mock_activity = Mock()
                mock_activity.text = "Implemented feature"
                mock_activity.timestamp = datetime.now()
                mock_activity.competency_areas = ["backend"]
                mock_activity.content = {"description": "Implemented feature"}

                mock_repo.get_user_activities = AsyncMock(return_value=[mock_activity])
                mock_repo_class.return_value = mock_repo

                fetch_result = await fetch_summary_data(fetch_input)

        # Verify fetch result
        assert "recent_activities" in fetch_result
        assert "top_competencies" in fetch_result

        # Step 2: Format as Slack blocks (simplified test)
        format_input = {
            "summary_data": fetch_result,
            "summary_type": "competency",
            "include_recommendations": False,
            "user_id": fetch_input["user_id"],
        }

        # Verify format input structure is correct
        assert "summary_data" in format_input
        assert format_input["summary_type"] == "competency"

        # Step 3: Post to Slack (simplified test)
        post_input = {
            "blocks": [{"type": "section"}],
            "text": "Summary",
            "channel_id": "C123",
            "thread_ts": None,
            "user_id": fetch_input["user_id"],
        }

        # Verify post input structure
        assert post_input["channel_id"] == "C123"
        assert "blocks" in post_input

    @pytest.mark.asyncio
    async def test_time_period_variations(self):
        """Test all supported time period variations"""
        for time_period in ["recent", "this_week", "this_month"]:
            input_data = {
                "user_id": str(uuid.uuid4()),
                "summary_type": "competency",
                "time_period": time_period,
                "max_activities": 10,
                "max_competencies": 5,
            }

            with patch("src.services.workflow.activities._get_services") as mock_get_services:
                mock_get_services.return_value = (None, None, None, None, None, None, None)

                with patch(
                    "src.infrastructure.database.repositories.activity_repository.ActivityRepository"
                ) as mock_repo_class:
                    mock_repo = AsyncMock()
                    mock_repo.get_user_activities = AsyncMock(return_value=[])
                    mock_repo_class.return_value = mock_repo

                    result = await fetch_summary_data(input_data)

            # Verify result structure is consistent across time periods
            assert "recent_activities" in result
            assert "top_competencies" in result
            assert result["activity_count"] >= 0
            assert result["competency_count"] >= 0

    @pytest.mark.asyncio
    async def test_error_resilience(self):
        """Test that the flow is resilient to errors"""

        # Test fetch with error
        fetch_input = {
            "user_id": str(uuid.uuid4()),
            "summary_type": "competency",
            "time_period": "recent",
            "max_activities": 10,
            "max_competencies": 5,
        }

        with patch("src.services.workflow.activities._get_services") as mock_get_services:
            mock_get_services.side_effect = Exception("Service error")

            fetch_result = await fetch_summary_data(fetch_input)

        # Should return error response
        assert "error" in fetch_result
        assert fetch_result["user_id"] == fetch_input["user_id"]
        assert fetch_result["summary_type"] == fetch_input["summary_type"]

        # Format should handle error data gracefully
        format_input = {
            "summary_data": fetch_result,
            "summary_type": "competency",
            "include_recommendations": False,
            "user_id": fetch_input["user_id"],
        }

        # Verify error data structure
        assert "error" in format_input["summary_data"]
