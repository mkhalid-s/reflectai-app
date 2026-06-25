"""
Unit Tests for InlineAnalysisReportWorkflow

Tests the inline analysis workflow for instant competency assessment
from user-provided activity descriptions.
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.services.workflow.models import WorkflowRequest, WorkflowType
from src.services.workflow.workflows import InlineAnalysisReportWorkflow


class TestInlineAnalysisWorkflowExecution:
    """Test inline analysis workflow execution flow"""

    @pytest.fixture
    def mock_workflow_info(self):
        """Mock workflow.info() for testing"""
        mock_info = Mock()
        mock_info.workflow_id = f"inline_analysis_{uuid.uuid4().hex[:8]}"
        return mock_info

    @pytest.fixture
    def sample_request(self):
        """Sample workflow request for testing"""
        return WorkflowRequest(
            workflow_type=WorkflowType.INLINE_ANALYSIS,
            user_id="U123",
            team_id="T123",
            correlation_id="test-corr-123",
            input_data={
                "inline_content": "I implemented OAuth2 authentication with JWT tokens",
                "content_metadata": {
                    "extraction_method": "pattern",
                    "confidence": 0.95,
                    "intent": "activity_classification",
                },
                "output_format": "slack_blocks",
                "channel_id": "C123",
                "include_gap_analysis": True,
                "context": {"source": "slack_message"},
            },
            conversation_id="conv-123",
            thread_ts="1234567890.123456",
            priority=0,
        )

    @pytest.mark.asyncio
    async def test_successful_workflow_execution(self, mock_workflow_info, sample_request):
        """Test successful inline analysis workflow execution"""
        workflow = InlineAnalysisReportWorkflow()

        # Mock workflow.info()
        with patch("temporalio.workflow.info", return_value=mock_workflow_info):
            # Mock workflow.execute_activity to return expected results
            mock_execute = AsyncMock()

            # Mock activity results
            mock_execute.side_effect = [
                # analyze_inline_content result
                {
                    "activity_title": "OAuth2 Authentication Implementation",
                    "activity_description": "Implemented OAuth2 with JWT tokens",
                    "technical_skills": ["OAuth2", "JWT", "Authentication"],
                    "impact": "high",
                    "llm_cost": 0.002,
                },
                # assess_content_competencies result
                {
                    "competencies": [
                        {"name": "Security Engineering", "level": "advanced", "confidence": 0.9},
                        {
                            "name": "Backend Development",
                            "level": "intermediate",
                            "confidence": 0.85,
                        },
                    ],
                    "gaps": ["DevSecOps practices"],
                    "llm_cost": 0.003,
                },
                # format_inline_report result
                {
                    "format": "slack_blocks",
                    "blocks": [{"type": "section", "text": "Analysis complete"}],
                    "text": "Competency Analysis Results",
                },
                # deliver_report result
                {
                    "success": True,
                    "delivered_at": datetime.now().isoformat(),
                    "processing_time": 2.5,
                    "channel_id": "C123",
                    "thread_ts": "1234567890.123456",
                },
            ]

            with patch("temporalio.workflow.execute_activity", mock_execute):
                result = await workflow.run(sample_request)

        # Verify result structure
        assert result["success"] is True
        assert result["workflow_type"] == "inline_analysis"
        assert "I implemented OAuth2" in result["content_analyzed"]
        assert "analysis" in result
        assert len(result["competencies"]) == 2
        assert result["competency_count"] == 2
        assert len(result["gaps_identified"]) == 1
        assert result["total_llm_cost"] == 0.005  # 0.002 + 0.003
        assert result["processing_time"] == 2.5

    @pytest.mark.asyncio
    async def test_workflow_with_pdf_output(self, mock_workflow_info):
        """Test workflow with PDF output format"""
        request = WorkflowRequest(
            workflow_type=WorkflowType.INLINE_ANALYSIS,
            user_id="U123",
            team_id="T123",
            correlation_id="test-corr-123",
            input_data={
                "inline_content": "Led migration to microservices architecture",
                "content_metadata": {"extraction_method": "llm", "confidence": 0.88},
                "output_format": "pdf",  # PDF output
                "channel_id": "C123",
                "include_gap_analysis": False,
            },
            thread_ts="1234567890.123456",
        )

        workflow = InlineAnalysisReportWorkflow()

        with patch("temporalio.workflow.info", return_value=mock_workflow_info):
            mock_execute = AsyncMock()
            mock_execute.side_effect = [
                {"activity_title": "Microservices Migration", "llm_cost": 0.001},
                {"competencies": [], "llm_cost": 0.002},
                {"format": "pdf", "pdf_url": "https://example.com/report.pdf"},
                {
                    "success": True,
                    "delivered_at": datetime.now().isoformat(),
                    "processing_time": 3.0,
                },
            ]

            with patch("temporalio.workflow.execute_activity", mock_execute):
                result = await workflow.run(request)

        assert result["success"] is True
        assert result["formatted_report"]["format"] == "pdf"

    @pytest.mark.asyncio
    async def test_workflow_without_gap_analysis(self, mock_workflow_info):
        """Test workflow without gap analysis"""
        request = WorkflowRequest(
            workflow_type=WorkflowType.INLINE_ANALYSIS,
            user_id="U123",
            team_id="T123",
            correlation_id="test-corr-123",
            input_data={
                "inline_content": "Fixed critical bug in payment processing",
                "content_metadata": {},
                "include_gap_analysis": False,  # No gap analysis
            },
        )

        workflow = InlineAnalysisReportWorkflow()

        with patch("temporalio.workflow.info", return_value=mock_workflow_info):
            mock_execute = AsyncMock()
            mock_execute.side_effect = [
                {"activity_title": "Bug Fix", "llm_cost": 0.001},
                {
                    "competencies": [{"name": "Problem Solving", "level": "advanced"}],
                    "gaps": [],
                    "llm_cost": 0.001,
                },
                {"blocks": []},
                {
                    "success": True,
                    "delivered_at": datetime.now().isoformat(),
                    "processing_time": 1.5,
                },
            ]

            with patch("temporalio.workflow.execute_activity", mock_execute):
                await workflow.run(request)

        # Verify assess_content_competencies was called with include_gaps=False
        calls = mock_execute.call_args_list
        assess_call = calls[1]
        assert assess_call[0][1]["include_gaps"] is False


class TestInlineAnalysisActivities:
    """Test individual activity invocations"""

    @pytest.fixture
    def mock_workflow_info(self):
        """Mock workflow.info()"""
        mock_info = Mock()
        mock_info.workflow_id = "test-workflow-123"
        return mock_info

    @pytest.mark.asyncio
    async def test_analyze_inline_content_activity(self, mock_workflow_info):
        """Test analyze_inline_content activity is called correctly"""
        request = WorkflowRequest(
            workflow_type=WorkflowType.INLINE_ANALYSIS,
            user_id="U123",
            team_id="T123",
            correlation_id="test-corr-123",
            input_data={
                "inline_content": "Refactored legacy codebase",
                "content_metadata": {"extraction_method": "pattern", "confidence": 0.9},
                "context": {"source": "slack"},
            },
        )

        workflow = InlineAnalysisReportWorkflow()

        with patch("temporalio.workflow.info", return_value=mock_workflow_info):
            mock_execute = AsyncMock()
            mock_execute.side_effect = [
                {"activity_title": "Refactoring", "llm_cost": 0.001},
                {"competencies": [], "llm_cost": 0.001},
                {"blocks": []},
                {
                    "success": True,
                    "delivered_at": datetime.now().isoformat(),
                    "processing_time": 1.0,
                },
            ]

            with patch("temporalio.workflow.execute_activity", mock_execute):
                await workflow.run(request)

        # Verify analyze_inline_content was called with correct parameters
        first_call = mock_execute.call_args_list[0]
        activity_params = first_call[0][1]

        assert activity_params["content"] == "Refactored legacy codebase"
        assert activity_params["content_metadata"]["extraction_method"] == "pattern"
        assert activity_params["user_id"] == "U123"
        assert activity_params["context"]["source"] == "slack"

    @pytest.mark.asyncio
    async def test_assess_content_competencies_activity(self, mock_workflow_info):
        """Test assess_content_competencies activity is called correctly"""
        request = WorkflowRequest(
            workflow_type=WorkflowType.INLINE_ANALYSIS,
            user_id="U456",
            team_id="T123",
            correlation_id="test-corr-456",
            input_data={"inline_content": "Test content", "include_gap_analysis": True},
        )

        workflow = InlineAnalysisReportWorkflow()

        with patch("temporalio.workflow.info", return_value=mock_workflow_info):
            mock_execute = AsyncMock()
            mock_analysis = {"activity_title": "Test", "llm_cost": 0.001}
            mock_execute.side_effect = [
                mock_analysis,
                {"competencies": [], "gaps": [], "llm_cost": 0.001},
                {"blocks": []},
                {
                    "success": True,
                    "delivered_at": datetime.now().isoformat(),
                    "processing_time": 1.0,
                },
            ]

            with patch("temporalio.workflow.execute_activity", mock_execute):
                await workflow.run(request)

        # Verify assess_content_competencies was called correctly
        second_call = mock_execute.call_args_list[1]
        activity_params = second_call[0][1]

        assert activity_params["analysis"] == mock_analysis
        assert activity_params["content"] == "Test content"
        assert activity_params["user_id"] == "U456"
        assert activity_params["include_gaps"] is True

    @pytest.mark.asyncio
    async def test_format_inline_report_activity(self, mock_workflow_info):
        """Test format_inline_report activity is called with correct parameters"""
        request = WorkflowRequest(
            workflow_type=WorkflowType.INLINE_ANALYSIS,
            user_id="U789",
            team_id="T123",
            correlation_id="test-corr-789",
            input_data={
                "inline_content": "Sample activity description for formatting test",
                "content_metadata": {"extraction_method": "llm", "confidence": 0.87},
                "output_format": "slack_blocks",
            },
        )

        workflow = InlineAnalysisReportWorkflow()

        with patch("temporalio.workflow.info", return_value=mock_workflow_info):
            mock_execute = AsyncMock()
            mock_analysis = {"activity_title": "Sample", "llm_cost": 0.001}
            mock_competencies = {"competencies": [{"name": "Test"}], "llm_cost": 0.001}

            mock_execute.side_effect = [
                mock_analysis,
                mock_competencies,
                {"blocks": [], "text": "Report"},
                {
                    "success": True,
                    "delivered_at": datetime.now().isoformat(),
                    "processing_time": 1.0,
                },
            ]

            with patch("temporalio.workflow.execute_activity", mock_execute):
                await workflow.run(request)

        # Verify format_inline_report was called correctly
        third_call = mock_execute.call_args_list[2]
        activity_params = third_call[0][1]

        assert activity_params["analysis"] == mock_analysis
        assert activity_params["competencies"] == mock_competencies
        assert activity_params["output_format"] == "slack_blocks"
        assert activity_params["user_id"] == "U789"
        assert activity_params["report_metadata"]["extraction_method"] == "llm"
        assert activity_params["report_metadata"]["confidence"] == 0.87
        assert (
            "Sample activity description" in activity_params["report_metadata"]["content_preview"]
        )

    @pytest.mark.asyncio
    async def test_deliver_report_activity(self, mock_workflow_info):
        """Test deliver_report activity is called with correct parameters"""
        request = WorkflowRequest(
            workflow_type=WorkflowType.INLINE_ANALYSIS,
            user_id="U999",
            team_id="T123",
            correlation_id="test-corr-999",
            input_data={
                "inline_content": "Delivery test content",
                "channel_id": "C999",
                "output_format": "pdf",
            },
            thread_ts="9999999999.999999",
        )

        workflow = InlineAnalysisReportWorkflow()

        with patch("temporalio.workflow.info", return_value=mock_workflow_info):
            mock_execute = AsyncMock()
            mock_format_result = {"format": "pdf", "pdf_url": "https://example.com/report.pdf"}

            mock_execute.side_effect = [
                {"activity_title": "Delivery test", "llm_cost": 0.001},
                {"competencies": [], "llm_cost": 0.001},
                mock_format_result,
                {
                    "success": True,
                    "delivered_at": datetime.now().isoformat(),
                    "processing_time": 2.0,
                },
            ]

            with patch("temporalio.workflow.execute_activity", mock_execute):
                await workflow.run(request)

        # Verify deliver_report was called correctly
        fourth_call = mock_execute.call_args_list[3]
        activity_params = fourth_call[0][1]

        assert activity_params["formatted_report"] == mock_format_result
        assert activity_params["user_id"] == "U999"
        assert activity_params["channel_id"] == "C999"
        assert activity_params["thread_ts"] == "9999999999.999999"
        assert activity_params["delivery_method"] == "file"  # pdf -> file
        assert activity_params["report_type"] == "inline_analysis"


class TestInlineAnalysisErrorHandling:
    """Test error handling in inline analysis workflow"""

    @pytest.fixture
    def mock_workflow_info(self):
        """Mock workflow.info()"""
        mock_info = Mock()
        mock_info.workflow_id = "error-test-workflow"
        return mock_info

    @pytest.mark.asyncio
    async def test_analysis_activity_failure(self, mock_workflow_info):
        """Test handling of analyze_inline_content activity failure"""
        request = WorkflowRequest(
            workflow_type=WorkflowType.INLINE_ANALYSIS,
            user_id="U111",
            team_id="T123",
            correlation_id="error-test",
            input_data={"inline_content": "Error test"},
        )

        workflow = InlineAnalysisReportWorkflow()

        with patch("temporalio.workflow.info", return_value=mock_workflow_info):
            mock_execute = AsyncMock()
            mock_execute.side_effect = Exception("LLM service unavailable")

            with patch("temporalio.workflow.execute_activity", mock_execute):
                with pytest.raises(Exception, match="LLM service unavailable"):
                    await workflow.run(request)

    @pytest.mark.asyncio
    async def test_delivery_activity_failure(self, mock_workflow_info):
        """Test handling of deliver_report activity failure"""
        request = WorkflowRequest(
            workflow_type=WorkflowType.INLINE_ANALYSIS,
            user_id="U222",
            team_id="T123",
            correlation_id="delivery-error-test",
            input_data={"inline_content": "Delivery error test", "channel_id": "C222"},
        )

        workflow = InlineAnalysisReportWorkflow()

        with patch("temporalio.workflow.info", return_value=mock_workflow_info):
            mock_execute = AsyncMock()
            mock_execute.side_effect = [
                {"activity_title": "Test", "llm_cost": 0.001},
                {"competencies": [], "llm_cost": 0.001},
                {"blocks": []},
                Exception("Slack API error"),  # Delivery fails
            ]

            with patch("temporalio.workflow.execute_activity", mock_execute):
                with pytest.raises(Exception, match="Slack API error"):
                    await workflow.run(request)


class TestInlineAnalysisDataFlow:
    """Test data flow through workflow steps"""

    @pytest.fixture
    def mock_workflow_info(self):
        """Mock workflow.info()"""
        mock_info = Mock()
        mock_info.workflow_id = "dataflow-test-workflow"
        return mock_info

    @pytest.mark.asyncio
    async def test_metadata_propagation(self, mock_workflow_info):
        """Test that metadata is correctly propagated through workflow"""
        request = WorkflowRequest(
            workflow_type=WorkflowType.INLINE_ANALYSIS,
            user_id="U333",
            team_id="T123",
            correlation_id="metadata-test",
            input_data={
                "inline_content": "Built CI/CD pipeline with GitHub Actions",
                "content_metadata": {
                    "extraction_method": "hybrid",
                    "confidence": 0.92,
                    "source": "slack_thread",
                    "timestamp": "2025-10-05T10:00:00Z",
                },
            },
        )

        workflow = InlineAnalysisReportWorkflow()

        with patch("temporalio.workflow.info", return_value=mock_workflow_info):
            mock_execute = AsyncMock()
            mock_execute.side_effect = [
                {"activity_title": "CI/CD Pipeline", "llm_cost": 0.002},
                {"competencies": [], "llm_cost": 0.002},
                {"blocks": []},
                {
                    "success": True,
                    "delivered_at": datetime.now().isoformat(),
                    "processing_time": 2.5,
                },
            ]

            with patch("temporalio.workflow.execute_activity", mock_execute):
                await workflow.run(request)

        # Verify metadata was passed to format activity
        format_call = mock_execute.call_args_list[2]
        report_metadata = format_call[0][1]["report_metadata"]

        assert report_metadata["extraction_method"] == "hybrid"
        assert report_metadata["confidence"] == 0.92

    @pytest.mark.asyncio
    async def test_cost_aggregation(self, mock_workflow_info):
        """Test that LLM costs are correctly aggregated"""
        request = WorkflowRequest(
            workflow_type=WorkflowType.INLINE_ANALYSIS,
            user_id="U444",
            team_id="T123",
            correlation_id="cost-test",
            input_data={"inline_content": "Cost tracking test"},
        )

        workflow = InlineAnalysisReportWorkflow()

        with patch("temporalio.workflow.info", return_value=mock_workflow_info):
            mock_execute = AsyncMock()
            mock_execute.side_effect = [
                {"activity_title": "Test", "llm_cost": 0.015},  # High cost analysis
                {"competencies": [], "llm_cost": 0.012},  # High cost competency assessment
                {"blocks": []},
                {
                    "success": True,
                    "delivered_at": datetime.now().isoformat(),
                    "processing_time": 3.0,
                },
            ]

            with patch("temporalio.workflow.execute_activity", mock_execute):
                result = await workflow.run(request)

        # Verify total LLM cost is correctly calculated
        assert result["total_llm_cost"] == 0.027  # 0.015 + 0.012

    @pytest.mark.asyncio
    async def test_content_preview_truncation(self, mock_workflow_info):
        """Test that long content is properly truncated in result"""
        long_content = "A" * 500  # 500 character content

        request = WorkflowRequest(
            workflow_type=WorkflowType.INLINE_ANALYSIS,
            user_id="U555",
            team_id="T123",
            correlation_id="truncation-test",
            input_data={"inline_content": long_content},
        )

        workflow = InlineAnalysisReportWorkflow()

        with patch("temporalio.workflow.info", return_value=mock_workflow_info):
            mock_execute = AsyncMock()
            mock_execute.side_effect = [
                {"activity_title": "Long content", "llm_cost": 0.001},
                {"competencies": [], "llm_cost": 0.001},
                {"blocks": []},
                {
                    "success": True,
                    "delivered_at": datetime.now().isoformat(),
                    "processing_time": 1.5,
                },
            ]

            with patch("temporalio.workflow.execute_activity", mock_execute):
                result = await workflow.run(request)

        # Verify content is truncated to 200 characters in result
        assert len(result["content_analyzed"]) == 200

        # Verify content_preview in metadata is also truncated
        format_call = mock_execute.call_args_list[2]
        content_preview = format_call[0][1]["report_metadata"]["content_preview"]
        assert len(content_preview) == 200
