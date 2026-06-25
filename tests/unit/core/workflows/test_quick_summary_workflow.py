"""
Unit Tests for QuickSummaryWorkflow

Tests the quick summary workflow for instant Slack-native competency summaries.
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.services.workflow.models import WorkflowRequest, WorkflowType
from src.services.workflow.workflows import QuickSummaryWorkflow


class TestQuickSummaryWorkflowExecution:
    """Test quick summary workflow execution flow"""

    @pytest.fixture
    def mock_workflow_info(self):
        """Mock workflow.info() for testing"""
        mock_info = Mock()
        mock_info.workflow_id = f"quick_summary_{uuid.uuid4().hex[:8]}"
        return mock_info

    @pytest.fixture
    def sample_request(self):
        """Sample workflow request for testing"""
        return WorkflowRequest(
            workflow_type=WorkflowType.QUICK_SUMMARY,
            user_id="U123",
            team_id="T123",
            correlation_id="test-corr-123",
            input_data={
                "summary_type": "competency",
                "time_period": "recent",
                "include_recommendations": False,
                "channel_id": "C123",
            },
            conversation_id="conv-123",
            thread_ts="1234567890.123456",
            priority=0,
        )

    @pytest.mark.asyncio
    async def test_successful_workflow_execution(self, mock_workflow_info, sample_request):
        """Test successful quick summary workflow execution"""
        workflow = QuickSummaryWorkflow()

        with patch("temporalio.workflow.info", return_value=mock_workflow_info):
            mock_execute = AsyncMock()

            # Mock activity results
            mock_execute.side_effect = [
                # fetch_summary_data result
                {
                    "competencies": [
                        {"name": "Python", "level": "advanced", "score": 0.92},
                        {"name": "System Design", "level": "intermediate", "score": 0.78},
                    ],
                    "activities": [
                        {"title": "Microservices Implementation", "date": "2025-10-01"},
                        {"title": "API Gateway Design", "date": "2025-09-28"},
                    ],
                    "competency_count": 2,
                    "activity_count": 2,
                    "processing_time": 0.5,
                },
                # format_slack_summary result
                {
                    "blocks": [
                        {
                            "type": "header",
                            "text": {"type": "plain_text", "text": "Competency Summary"},
                        },
                        {
                            "type": "section",
                            "text": {"type": "mrkdwn", "text": "*Top Competencies*"},
                        },
                    ],
                    "text": "Competency Summary",
                    "processing_time": 0.3,
                },
                # post_slack_message result
                {
                    "success": True,
                    "message_ts": "1234567890.123457",
                    "channel_id": "C123",
                    "delivered_at": datetime.now().isoformat(),
                    "processing_time": 0.2,
                },
            ]

            with patch("temporalio.workflow.execute_activity", mock_execute):
                result = await workflow.run(sample_request)

        # Verify result structure
        assert result["success"] is True
        assert result["workflow_type"] == "quick_summary"
        assert result["summary_type"] == "competency"
        assert result["time_period"] == "recent"
        assert result["competency_count"] == 2
        assert result["activity_count"] == 2
        assert result["message_ts"] == "1234567890.123457"
        assert result["channel_id"] == "C123"
        assert result["total_processing_time"] == 1.0  # 0.5 + 0.3 + 0.2

    @pytest.mark.asyncio
    async def test_workflow_with_recommendations(self, mock_workflow_info):
        """Test workflow with recommendations enabled"""
        request = WorkflowRequest(
            workflow_type=WorkflowType.QUICK_SUMMARY,
            user_id="U456",
            team_id="T123",
            correlation_id="test-corr-456",
            input_data={
                "summary_type": "competency",
                "time_period": "this_week",
                "include_recommendations": True,  # Enable recommendations
                "channel_id": "C456",
            },
        )

        workflow = QuickSummaryWorkflow()

        with patch("temporalio.workflow.info", return_value=mock_workflow_info):
            mock_execute = AsyncMock()
            mock_execute.side_effect = [
                {
                    "competencies": [],
                    "activities": [],
                    "competency_count": 0,
                    "activity_count": 0,
                    "processing_time": 0.5,
                },
                {"blocks": [], "text": "Summary", "processing_time": 0.3},
                {
                    "success": True,
                    "message_ts": "123.456",
                    "channel_id": "C456",
                    "delivered_at": datetime.now().isoformat(),
                    "processing_time": 0.2,
                },
            ]

            with patch("temporalio.workflow.execute_activity", mock_execute):
                await workflow.run(request)

        # Verify include_recommendations was passed to format activity
        format_call = mock_execute.call_args_list[1]
        assert format_call[0][1]["include_recommendations"] is True

    @pytest.mark.asyncio
    async def test_workflow_with_different_time_periods(self, mock_workflow_info):
        """Test workflow with different time periods"""
        for time_period in ["recent", "this_week", "this_month"]:
            request = WorkflowRequest(
                workflow_type=WorkflowType.QUICK_SUMMARY,
                user_id="U789",
                team_id="T123",
                correlation_id=f"test-{time_period}",
                input_data={
                    "summary_type": "competency",
                    "time_period": time_period,
                    "channel_id": "C789",
                },
            )

            workflow = QuickSummaryWorkflow()

            with patch("temporalio.workflow.info", return_value=mock_workflow_info):
                mock_execute = AsyncMock()
                mock_execute.side_effect = [
                    {
                        "competencies": [],
                        "activities": [],
                        "competency_count": 0,
                        "activity_count": 0,
                        "processing_time": 0.5,
                    },
                    {"blocks": [], "text": "Summary", "processing_time": 0.3},
                    {
                        "success": True,
                        "message_ts": "123.456",
                        "channel_id": "C789",
                        "delivered_at": datetime.now().isoformat(),
                        "processing_time": 0.2,
                    },
                ]

                with patch("temporalio.workflow.execute_activity", mock_execute):
                    result = await workflow.run(request)

            assert result["time_period"] == time_period


class TestQuickSummaryActivities:
    """Test individual activity invocations"""

    @pytest.fixture
    def mock_workflow_info(self):
        """Mock workflow.info()"""
        mock_info = Mock()
        mock_info.workflow_id = "test-workflow-123"
        return mock_info

    @pytest.mark.asyncio
    async def test_fetch_summary_data_activity(self, mock_workflow_info):
        """Test fetch_summary_data activity is called correctly"""
        request = WorkflowRequest(
            workflow_type=WorkflowType.QUICK_SUMMARY,
            user_id="U111",
            team_id="T123",
            correlation_id="test-111",
            input_data={
                "summary_type": "competency",
                "time_period": "this_week",
                "channel_id": "C111",
            },
        )

        workflow = QuickSummaryWorkflow()

        with patch("temporalio.workflow.info", return_value=mock_workflow_info):
            mock_execute = AsyncMock()
            mock_execute.side_effect = [
                {
                    "competencies": [],
                    "activities": [],
                    "competency_count": 5,
                    "activity_count": 10,
                    "processing_time": 0.5,
                },
                {"blocks": [], "text": "Summary", "processing_time": 0.3},
                {
                    "success": True,
                    "message_ts": "123.456",
                    "channel_id": "C111",
                    "delivered_at": datetime.now().isoformat(),
                    "processing_time": 0.2,
                },
            ]

            with patch("temporalio.workflow.execute_activity", mock_execute):
                await workflow.run(request)

        # Verify fetch_summary_data was called with correct parameters
        first_call = mock_execute.call_args_list[0]
        activity_params = first_call[0][1]

        assert activity_params["user_id"] == "U111"
        assert activity_params["summary_type"] == "competency"
        assert activity_params["time_period"] == "this_week"
        assert activity_params["max_activities"] == 10
        assert activity_params["max_competencies"] == 5

    @pytest.mark.asyncio
    async def test_format_slack_summary_activity(self, mock_workflow_info):
        """Test format_slack_summary activity is called correctly"""
        request = WorkflowRequest(
            workflow_type=WorkflowType.QUICK_SUMMARY,
            user_id="U222",
            team_id="T123",
            correlation_id="test-222",
            input_data={
                "summary_type": "activity",
                "time_period": "recent",
                "include_recommendations": True,
                "channel_id": "C222",
            },
        )

        workflow = QuickSummaryWorkflow()

        with patch("temporalio.workflow.info", return_value=mock_workflow_info):
            mock_execute = AsyncMock()
            mock_summary_data = {
                "competencies": [{"name": "Test"}],
                "activities": [{"title": "Test Activity"}],
                "competency_count": 1,
                "activity_count": 1,
                "processing_time": 0.5,
            }

            mock_execute.side_effect = [
                mock_summary_data,
                {"blocks": [{"type": "section"}], "text": "Summary", "processing_time": 0.3},
                {
                    "success": True,
                    "message_ts": "123.456",
                    "channel_id": "C222",
                    "delivered_at": datetime.now().isoformat(),
                    "processing_time": 0.2,
                },
            ]

            with patch("temporalio.workflow.execute_activity", mock_execute):
                await workflow.run(request)

        # Verify format_slack_summary was called correctly
        second_call = mock_execute.call_args_list[1]
        activity_params = second_call[0][1]

        assert activity_params["summary_data"] == mock_summary_data
        assert activity_params["summary_type"] == "activity"
        assert activity_params["include_recommendations"] is True
        assert activity_params["user_id"] == "U222"

    @pytest.mark.asyncio
    async def test_post_slack_message_activity(self, mock_workflow_info):
        """Test post_slack_message activity is called with correct parameters"""
        request = WorkflowRequest(
            workflow_type=WorkflowType.QUICK_SUMMARY,
            user_id="U333",
            team_id="T123",
            correlation_id="test-333",
            input_data={
                "summary_type": "competency",
                "time_period": "recent",
                "channel_id": "C333",
            },
            thread_ts="9999999999.999999",
        )

        workflow = QuickSummaryWorkflow()

        with patch("temporalio.workflow.info", return_value=mock_workflow_info):
            mock_execute = AsyncMock()
            mock_formatted_blocks = {
                "blocks": [
                    {"type": "header", "text": "Summary"},
                    {"type": "section", "text": "Content"},
                ],
                "text": "Competency Summary Text",
                "processing_time": 0.3,
            }

            mock_execute.side_effect = [
                {
                    "competencies": [],
                    "activities": [],
                    "competency_count": 0,
                    "activity_count": 0,
                    "processing_time": 0.5,
                },
                mock_formatted_blocks,
                {
                    "success": True,
                    "message_ts": "123.456",
                    "channel_id": "C333",
                    "delivered_at": datetime.now().isoformat(),
                    "processing_time": 0.2,
                },
            ]

            with patch("temporalio.workflow.execute_activity", mock_execute):
                await workflow.run(request)

        # Verify post_slack_message was called correctly
        third_call = mock_execute.call_args_list[2]
        activity_params = third_call[0][1]

        assert activity_params["blocks"] == mock_formatted_blocks["blocks"]
        assert activity_params["text"] == "Competency Summary Text"
        assert activity_params["channel_id"] == "C333"
        assert activity_params["thread_ts"] == "9999999999.999999"
        assert activity_params["user_id"] == "U333"


class TestQuickSummaryErrorHandling:
    """Test error handling in quick summary workflow"""

    @pytest.fixture
    def mock_workflow_info(self):
        """Mock workflow.info()"""
        mock_info = Mock()
        mock_info.workflow_id = "error-test-workflow"
        return mock_info

    @pytest.mark.asyncio
    async def test_fetch_data_activity_failure(self, mock_workflow_info):
        """Test handling of fetch_summary_data activity failure"""
        request = WorkflowRequest(
            workflow_type=WorkflowType.QUICK_SUMMARY,
            user_id="U444",
            team_id="T123",
            correlation_id="error-test",
            input_data={"channel_id": "C444"},
        )

        workflow = QuickSummaryWorkflow()

        with patch("temporalio.workflow.info", return_value=mock_workflow_info):
            mock_execute = AsyncMock()
            mock_execute.side_effect = Exception("Database connection failed")

            with patch("temporalio.workflow.execute_activity", mock_execute):
                with pytest.raises(Exception, match="Database connection failed"):
                    await workflow.run(request)

    @pytest.mark.asyncio
    async def test_slack_post_activity_failure(self, mock_workflow_info):
        """Test handling of post_slack_message activity failure"""
        request = WorkflowRequest(
            workflow_type=WorkflowType.QUICK_SUMMARY,
            user_id="U555",
            team_id="T123",
            correlation_id="slack-error-test",
            input_data={"channel_id": "C555"},
        )

        workflow = QuickSummaryWorkflow()

        with patch("temporalio.workflow.info", return_value=mock_workflow_info):
            mock_execute = AsyncMock()
            mock_execute.side_effect = [
                {
                    "competencies": [],
                    "activities": [],
                    "competency_count": 0,
                    "activity_count": 0,
                    "processing_time": 0.5,
                },
                {"blocks": [], "text": "Summary", "processing_time": 0.3},
                Exception("Slack API rate limit exceeded"),  # Slack post fails
            ]

            with patch("temporalio.workflow.execute_activity", mock_execute):
                with pytest.raises(Exception, match="Slack API rate limit exceeded"):
                    await workflow.run(request)


class TestQuickSummaryDataFlow:
    """Test data flow through workflow steps"""

    @pytest.fixture
    def mock_workflow_info(self):
        """Mock workflow.info()"""
        mock_info = Mock()
        mock_info.workflow_id = "dataflow-test-workflow"
        return mock_info

    @pytest.mark.asyncio
    async def test_processing_time_aggregation(self, mock_workflow_info):
        """Test that processing times are correctly aggregated"""
        request = WorkflowRequest(
            workflow_type=WorkflowType.QUICK_SUMMARY,
            user_id="U666",
            team_id="T123",
            correlation_id="time-test",
            input_data={"channel_id": "C666"},
        )

        workflow = QuickSummaryWorkflow()

        with patch("temporalio.workflow.info", return_value=mock_workflow_info):
            mock_execute = AsyncMock()
            mock_execute.side_effect = [
                {
                    "competencies": [],
                    "activities": [],
                    "competency_count": 0,
                    "activity_count": 0,
                    "processing_time": 1.5,
                },
                {"blocks": [], "text": "Summary", "processing_time": 0.8},
                {
                    "success": True,
                    "message_ts": "123.456",
                    "channel_id": "C666",
                    "delivered_at": datetime.now().isoformat(),
                    "processing_time": 0.7,
                },
            ]

            with patch("temporalio.workflow.execute_activity", mock_execute):
                result = await workflow.run(request)

        # Verify total processing time is correctly calculated
        assert result["total_processing_time"] == 3.0  # 1.5 + 0.8 + 0.7

    @pytest.mark.asyncio
    async def test_defaults_applied_correctly(self, mock_workflow_info):
        """Test that default values are applied when not specified"""
        request = WorkflowRequest(
            workflow_type=WorkflowType.QUICK_SUMMARY,
            user_id="U777",
            team_id="T123",
            correlation_id="defaults-test",
            input_data={},  # No parameters specified
        )

        workflow = QuickSummaryWorkflow()

        with patch("temporalio.workflow.info", return_value=mock_workflow_info):
            mock_execute = AsyncMock()
            mock_execute.side_effect = [
                {
                    "competencies": [],
                    "activities": [],
                    "competency_count": 0,
                    "activity_count": 0,
                    "processing_time": 0.5,
                },
                {"blocks": [], "text": "Summary", "processing_time": 0.3},
                {
                    "success": True,
                    "message_ts": "123.456",
                    "channel_id": None,
                    "delivered_at": datetime.now().isoformat(),
                    "processing_time": 0.2,
                },
            ]

            with patch("temporalio.workflow.execute_activity", mock_execute):
                result = await workflow.run(request)

        # Verify defaults were applied
        assert result["summary_type"] == "competency"  # Default
        assert result["time_period"] == "recent"  # Default

        # Verify fetch_summary_data was called with defaults
        first_call = mock_execute.call_args_list[0]
        fetch_params = first_call[0][1]
        assert fetch_params["summary_type"] == "competency"
        assert fetch_params["time_period"] == "recent"

    @pytest.mark.asyncio
    async def test_summary_counts_propagated(self, mock_workflow_info):
        """Test that summary counts from fetch activity are propagated to result"""
        request = WorkflowRequest(
            workflow_type=WorkflowType.QUICK_SUMMARY,
            user_id="U888",
            team_id="T123",
            correlation_id="counts-test",
            input_data={"channel_id": "C888"},
        )

        workflow = QuickSummaryWorkflow()

        with patch("temporalio.workflow.info", return_value=mock_workflow_info):
            mock_execute = AsyncMock()
            mock_execute.side_effect = [
                {
                    "competencies": [{}, {}, {}],  # 3 competencies
                    "activities": [{}, {}, {}, {}, {}],  # 5 activities
                    "competency_count": 3,
                    "activity_count": 5,
                    "processing_time": 0.5,
                },
                {"blocks": [], "text": "Summary", "processing_time": 0.3},
                {
                    "success": True,
                    "message_ts": "123.456",
                    "channel_id": "C888",
                    "delivered_at": datetime.now().isoformat(),
                    "processing_time": 0.2,
                },
            ]

            with patch("temporalio.workflow.execute_activity", mock_execute):
                result = await workflow.run(request)

        # Verify counts are propagated to final result
        assert result["competency_count"] == 3
        assert result["activity_count"] == 5
