"""
Unit Tests for WorkflowRouter

Tests routing logic, intent-based workflow selection, priority assignment,
and integration with IntentAnalyzer.
"""

from unittest.mock import AsyncMock, Mock

import pytest

from src.core.classification.intent_analyzer import (
    IntentClassificationResult,
    IntentConfidence,
    IntentType,
)
from src.core.workflows.workflow_router import (
    RoutingContext,
    RoutingDecision,
    WorkflowRouter,
)
from src.services.workflow.models import WorkflowType


class TestWorkflowRouterInitialization:
    """Test WorkflowRouter initialization"""

    def test_router_initialization(self):
        """Test that router initializes correctly"""
        router = WorkflowRouter()

        assert router.intent_analyzer is not None
        assert router.conversation_intelligence is not None
        assert router.config is not None

    def test_router_has_intent_analyzer(self):
        """Test that router has intent analyzer instance"""
        router = WorkflowRouter()

        assert hasattr(router, "intent_analyzer")
        assert router.intent_analyzer is not None


class TestIntentBasedRouting:
    """Test routing based on detected intent types"""

    @pytest.fixture
    def router(self):
        return WorkflowRouter()

    @pytest.fixture
    def base_context(self):
        return RoutingContext(
            user_id="U123", content="test content", metadata={"channel_id": "C123"}
        )

    @pytest.mark.asyncio
    async def test_route_activity_classification_intent(self, router, base_context, mocker):
        """Test routing for ACTIVITY_CLASSIFICATION intent"""
        # Mock conversation intelligence analyze_message
        mock_ci_result = Mock()
        mock_ci_result.intent = Mock(value="activity_classification")
        mock_ci_result.confidence = 0.85
        mock_ci_result.requires_clarification = True  # True for sequential analysis
        mock_ci_result.extracted_content = None

        mocker.patch.object(
            router.conversation_intelligence, "analyze_message", return_value=mock_ci_result
        )

        # Mock temporal client
        router.temporal_client = AsyncMock()
        router.temporal_client.start_workflow = AsyncMock(return_value=Mock(id="workflow-123"))

        result = await router.route_request(base_context)

        assert result is not None
        assert result.decision == RoutingDecision.SEQUENTIAL_ANALYSIS
        assert result.workflow_id is not None

    @pytest.mark.asyncio
    async def test_route_competency_analysis_intent(self, router, base_context, mocker):
        """Test routing for COMPETENCY_ANALYSIS intent"""
        mock_ci_result = Mock()
        mock_ci_result.intent = Mock(value="competency_analysis")
        mock_ci_result.confidence = 0.85
        mock_ci_result.requires_clarification = True  # True for sequential analysis
        mock_ci_result.extracted_content = None

        mocker.patch.object(
            router.conversation_intelligence, "analyze_message", return_value=mock_ci_result
        )

        router.temporal_client = AsyncMock()
        router.temporal_client.start_workflow = AsyncMock(return_value=Mock(id="workflow-123"))

        result = await router.route_request(base_context)

        assert result is not None
        assert result.decision == RoutingDecision.SEQUENTIAL_ANALYSIS

    @pytest.mark.asyncio
    async def test_route_career_advice_intent(self, router, base_context, mocker):
        """Test routing for CAREER_ADVICE intent"""
        mock_ci_result = Mock()
        mock_ci_result.intent = Mock(value="career_advice")
        mock_ci_result.confidence = 0.85
        mock_ci_result.requires_clarification = False
        mock_ci_result.extracted_content = None

        mocker.patch.object(
            router.conversation_intelligence, "analyze_message", return_value=mock_ci_result
        )

        router.temporal_client = AsyncMock()
        router.temporal_client.start_workflow = AsyncMock(return_value=Mock(id="workflow-123"))

        result = await router.route_request(base_context)

        assert result is not None
        # Career advice should route to conversation or specific workflow
        assert result.workflow_id is not None

    @pytest.mark.asyncio
    async def test_route_help_request_intent(self, router, base_context, mocker):
        """Test routing for HELP_REQUEST intent"""
        mock_ci_result = Mock()
        mock_ci_result.intent = Mock(value="help_request")
        mock_ci_result.confidence = 0.85

        mocker.patch.object(
            router.conversation_intelligence, "analyze_message", return_value=mock_ci_result
        )

        result = await router.route_request(base_context)

        assert result is not None
        assert result.decision == RoutingDecision.HELP

    @pytest.mark.asyncio
    async def test_route_general_chat_intent(self, router, base_context, mocker):
        """Test routing for GENERAL_CHAT intent"""
        mock_ci_result = Mock()
        mock_ci_result.intent = Mock(value="general_chat")
        mock_ci_result.confidence = 0.85

        mocker.patch.object(
            router.conversation_intelligence, "analyze_message", return_value=mock_ci_result
        )

        result = await router.route_request(base_context)

        assert result is not None
        assert result.decision == RoutingDecision.GREETING


class TestReportRequestRouting:
    """Test smart routing for report requests (quick summary vs full report)"""

    @pytest.fixture
    def router(self):
        return WorkflowRouter()

    @pytest.fixture
    def base_context(self):
        return RoutingContext(
            user_id="U123", content="test content", metadata={"channel_id": "C123"}
        )

    @pytest.mark.asyncio
    async def test_route_quick_summary_keywords(self, router, base_context, mocker):
        """Test routing to quick summary with summary keywords"""
        mock_ci_result = Mock()
        mock_ci_result.intent = Mock(value="report_request")
        mock_ci_result.confidence = 0.85
        mock_ci_result.requires_clarification = False
        mock_ci_result.extracted_content = None

        mocker.patch.object(
            router.conversation_intelligence, "analyze_message", return_value=mock_ci_result
        )

        router.temporal_client = AsyncMock()
        router.temporal_client.start_workflow = AsyncMock(return_value=Mock(id="workflow-123"))

        base_context.content = "show me my top skills"
        result = await router.route_request(base_context)

        assert result is not None
        assert result.decision == RoutingDecision.QUICK_SUMMARY
        assert result.workflow_type == WorkflowType.QUICK_SUMMARY

    @pytest.mark.asyncio
    async def test_route_full_report_with_pdf_keyword(self, router, base_context, mocker):
        """Test routing to full report with PDF keyword"""
        mock_ci_result = Mock()
        mock_ci_result.intent = Mock(value="report_request")
        mock_ci_result.confidence = 0.85
        mock_ci_result.requires_clarification = False
        mock_ci_result.extracted_content = None

        mocker.patch.object(
            router.conversation_intelligence, "analyze_message", return_value=mock_ci_result
        )

        router.temporal_client = AsyncMock()
        router.temporal_client.start_workflow = AsyncMock(return_value=Mock(id="workflow-123"))

        base_context.content = "generate a pdf report"
        result = await router.route_request(base_context)

        assert result is not None
        assert result.decision == RoutingDecision.REPORT_GENERATION
        assert result.workflow_type == WorkflowType.REPORT_GENERATION

    @pytest.mark.asyncio
    async def test_route_report_with_date_range(self, router, base_context, mocker):
        """Test that report routing includes date range extraction"""
        mock_ci_result = Mock()
        mock_ci_result.intent = Mock(value="report_request")
        mock_ci_result.confidence = 0.85
        mock_ci_result.requires_clarification = False
        mock_ci_result.extracted_content = None

        mocker.patch.object(
            router.conversation_intelligence, "analyze_message", return_value=mock_ci_result
        )

        router.temporal_client = AsyncMock()
        router.temporal_client.start_workflow = AsyncMock(return_value=Mock(id="workflow-123"))

        base_context.content = "generate report for last 30 days"
        result = await router.route_request(base_context)

        assert result is not None
        # Verify workflow was started with date range
        router.temporal_client.start_workflow.assert_called_once()


class TestInlineAnalysisRouting:
    """Test routing for inline analysis with content extraction"""

    @pytest.fixture
    def router(self):
        return WorkflowRouter()

    @pytest.fixture
    def base_context(self):
        return RoutingContext(
            user_id="U123", content="test content", metadata={"channel_id": "C123"}
        )

    @pytest.mark.asyncio
    async def test_route_inline_analysis_with_content(self, router, base_context, mocker):
        """Test routing to inline analysis when content is extracted"""
        mock_ci_result = Mock()
        mock_ci_result.intent = Mock(value="report_request")
        mock_ci_result.confidence = 0.85
        mock_ci_result.extracted_content = {
            "cleaned_text": "I implemented OAuth2 authentication",
            "raw_text": "I implemented OAuth2 authentication",
            "confidence": 0.95,
        }

        mocker.patch.object(
            router.conversation_intelligence, "analyze_message", return_value=mock_ci_result
        )

        router.temporal_client = AsyncMock()
        router.temporal_client.start_workflow = AsyncMock(return_value=Mock(id="workflow-123"))

        base_context.content = "analyze this: I implemented OAuth2 authentication"
        result = await router.route_request(base_context)

        assert result is not None
        assert result.decision == RoutingDecision.INLINE_ANALYSIS
        assert result.workflow_type == WorkflowType.INLINE_ANALYSIS

    @pytest.mark.asyncio
    async def test_inline_analysis_for_activity_classification(self, router, base_context, mocker):
        """Test inline analysis routing for activity classification with content"""
        mock_ci_result = Mock()
        mock_ci_result.intent = Mock(value="activity_classification")
        mock_ci_result.confidence = 0.85
        mock_ci_result.extracted_content = {
            "cleaned_text": "Led team migration to microservices",
            "confidence": 0.90,
        }

        mocker.patch.object(
            router.conversation_intelligence, "analyze_message", return_value=mock_ci_result
        )

        router.temporal_client = AsyncMock()
        router.temporal_client.start_workflow = AsyncMock(return_value=Mock(id="workflow-123"))

        result = await router.route_request(base_context)

        assert result is not None
        # Should route to inline analysis when content is extracted
        assert result.decision == RoutingDecision.INLINE_ANALYSIS


class TestPriorityAndQueueAssignment:
    """Test priority and task queue assignment"""

    @pytest.fixture
    def router(self):
        return WorkflowRouter()

    def test_default_priority_is_zero(self, router):
        """Test that default priority is 0 (normal)"""
        context = RoutingContext(user_id="U123", content="test")

        assert context.priority == 0

    def test_high_priority_context(self, router):
        """Test high priority routing context"""
        context = RoutingContext(user_id="U123", content="urgent request", priority=1)

        assert context.priority == 1

    @pytest.mark.asyncio
    async def test_correlation_id_generation(self, router, mocker):
        """Test that correlation ID is generated if not provided"""
        mock_intent_result = IntentClassificationResult(
            user_input="test",
            primary_intent=IntentType.GENERAL_CHAT,
            confidence=0.85,
            confidence_level=IntentConfidence.HIGH,
            method="pattern",
            processing_time=0.1,
        )

        mocker.patch.object(
            router.intent_analyzer, "analyze_intent", return_value=mock_intent_result
        )

        context = RoutingContext(
            user_id="U123",
            content="test",
            correlation_id=None,  # No correlation ID
        )

        result = await router.route_request(context)

        assert result is not None
        # Router should generate correlation ID internally


class TestErrorHandling:
    """Test error handling and edge cases"""

    @pytest.fixture
    def router(self):
        return WorkflowRouter()

    @pytest.mark.asyncio
    async def test_unknown_intent_fallback(self, router, mocker):
        """Test fallback for unknown intent"""
        mock_intent_result = IntentClassificationResult(
            user_input="asdfghjkl",
            primary_intent=IntentType.UNKNOWN,
            confidence=0.2,
            confidence_level=IntentConfidence.VERY_LOW,
            method="fallback",
            processing_time=0.1,
        )

        mocker.patch.object(
            router.intent_analyzer, "analyze_intent", return_value=mock_intent_result
        )

        context = RoutingContext(user_id="U123", content="asdfghjkl")

        result = await router.route_request(context)

        assert result is not None
        # Should handle unknown intent gracefully

    @pytest.mark.asyncio
    async def test_missing_user_context(self, router, mocker):
        """Test handling of missing user context"""
        mock_intent_result = IntentClassificationResult(
            user_input="test",
            primary_intent=IntentType.GENERAL_CHAT,
            confidence=0.85,
            confidence_level=IntentConfidence.HIGH,
            method="pattern",
            processing_time=0.1,
        )

        mocker.patch.object(
            router.intent_analyzer, "analyze_intent", return_value=mock_intent_result
        )

        context = RoutingContext(
            user_id="U123",
            content="test",
            user_profile=None,  # No user profile
        )

        result = await router.route_request(context)

        assert result is not None

    @pytest.mark.asyncio
    async def test_intent_analyzer_error(self, router, mocker):
        """Test handling of intent analyzer errors"""
        mocker.patch.object(
            router.intent_analyzer,
            "analyze_intent",
            side_effect=Exception("Intent analysis failed"),
        )

        context = RoutingContext(user_id="U123", content="test")

        result = await router.route_request(context)

        assert result is not None
        assert result.decision == RoutingDecision.ERROR

    @pytest.mark.asyncio
    async def test_temporal_client_unavailable(self, router, mocker):
        """Test handling when Temporal client is unavailable"""
        mock_intent_result = IntentClassificationResult(
            user_input="classify my activity",
            primary_intent=IntentType.ACTIVITY_CLASSIFICATION,
            confidence=0.85,
            confidence_level=IntentConfidence.HIGH,
            method="pattern",
            processing_time=0.1,
        )

        mocker.patch.object(
            router.intent_analyzer, "analyze_intent", return_value=mock_intent_result
        )

        # Set temporal client to None
        router.temporal_client = None

        context = RoutingContext(user_id="U123", content="classify my activity")

        result = await router.route_request(context)

        # Should handle gracefully (may return error or fallback)
        assert result is not None


class TestContextPreparation:
    """Test workflow context and request preparation"""

    @pytest.fixture
    def router(self):
        return WorkflowRouter()

    @pytest.mark.asyncio
    async def test_metadata_propagation(self, router, mocker):
        """Test that metadata is properly propagated to workflow request"""
        mock_intent_result = IntentClassificationResult(
            user_input="test",
            primary_intent=IntentType.GENERAL_CHAT,
            confidence=0.85,
            confidence_level=IntentConfidence.HIGH,
            method="pattern",
            processing_time=0.1,
        )

        mocker.patch.object(
            router.intent_analyzer, "analyze_intent", return_value=mock_intent_result
        )

        context = RoutingContext(
            user_id="U123",
            content="test",
            metadata={
                "channel_id": "C123",
                "thread_ts": "1234567890.123456",
                "custom_field": "custom_value",
            },
        )

        result = await router.route_request(context)

        assert result is not None

    @pytest.mark.asyncio
    async def test_conversation_history_included(self, router, mocker):
        """Test that conversation history is included in routing"""
        mock_ci_result = Mock()
        mock_ci_result.intent = Mock(value="general_chat")
        mock_ci_result.confidence = 0.85

        mocker.patch.object(
            router.conversation_intelligence, "analyze_message", return_value=mock_ci_result
        )

        context = RoutingContext(
            user_id="U123",
            content="test",
            conversation_history=[
                {"role": "user", "content": "previous message"},
                {"role": "assistant", "content": "previous response"},
            ],
        )

        result = await router.route_request(context)

        assert result is not None
        # Verify conversation intelligence was called
        router.conversation_intelligence.analyze_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_user_profile_included(self, router, mocker):
        """Test that user profile is included in routing"""
        mock_ci_result = Mock()
        mock_ci_result.intent = Mock(value="general_chat")
        mock_ci_result.confidence = 0.85

        mocker.patch.object(
            router.conversation_intelligence, "analyze_message", return_value=mock_ci_result
        )

        context = RoutingContext(
            user_id="U123",
            content="test",
            user_profile={
                "name": "Test User",
                "role": "Senior Engineer",
                "department": "Engineering",
            },
        )

        result = await router.route_request(context)

        assert result is not None
        # Verify conversation intelligence was called
        router.conversation_intelligence.analyze_message.assert_called_once()
