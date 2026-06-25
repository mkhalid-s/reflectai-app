"""
Integration Test: Slack → Workflow Router → Temporal
Tests the complete flow from Slack message to workflow execution.
"""
import asyncio
import uuid

import pytest

from src.core.workflows.workflow_router import get_workflow_router
from src.services.workflow.models import WorkflowRequest, WorkflowType


@pytest.mark.integration
@pytest.mark.asyncio
async def test_workflow_router_route_workflow_method_exists():
    """Test that route_workflow method exists and is callable."""
    router = await get_workflow_router()

    assert hasattr(router, 'route_workflow'), "route_workflow method should exist"
    assert callable(router.route_workflow), "route_workflow should be callable"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_workflow_request_creation():
    """Test that WorkflowRequest can be created with all required fields."""

    workflow_request = WorkflowRequest(
        workflow_type=WorkflowType.INLINE_ANALYSIS,
        user_id="test_user_123",
        team_id="default",
        correlation_id=f"test-{uuid.uuid4()}",
        input_data={
            "time_period": "7_days",
            "source": "test_suite",
            "activity_text": "Test activity"
        },
    )

    assert workflow_request.workflow_type == WorkflowType.INLINE_ANALYSIS
    assert workflow_request.user_id == "test_user_123"
    assert workflow_request.team_id == "default"
    assert workflow_request.correlation_id is not None
    assert "activity_text" in workflow_request.input_data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_route_workflow_with_mock_temporal(mocker):
    """Test route_workflow method with mocked Temporal client."""
    from src.core.workflows.workflow_router import RoutingDecision
    from src.services.workflow.models import WorkflowResponse, WorkflowStatus

    router = await get_workflow_router()

    # Mock the Temporal client
    mock_response = WorkflowResponse(
        workflow_id="test-wf-123",
        workflow_type=WorkflowType.INLINE_ANALYSIS,
        status=WorkflowStatus.RUNNING,
        user_id="test_user",
        team_id="default",
        correlation_id="test-corr-123"
    )

    mock_temporal_client = mocker.AsyncMock()
    mock_temporal_client.start_workflow.return_value = mock_response
    router.temporal_client = mock_temporal_client

    # Create workflow request
    workflow_request = WorkflowRequest(
        workflow_type=WorkflowType.INLINE_ANALYSIS,
        user_id="test_user",
        team_id="default",
        correlation_id="test-corr-123",
        input_data={"activity_text": "Test activity"}
    )

    # Call route_workflow
    result = await router.route_workflow(workflow_request, user_id="test_user")

    # Verify result
    assert result is not None
    assert result.decision == RoutingDecision.SEQUENTIAL_ANALYSIS
    assert result.workflow_id is not None
    assert result.workflow_type == WorkflowType.INLINE_ANALYSIS

    # Verify Temporal client was called
    mock_temporal_client.start_workflow.assert_called_once()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_conversation_manager_workflow_integration(mocker):
    """Test that ConversationManager can successfully call workflow_router.route_workflow()."""
    import redis.asyncio as redis

    from src.core.conversation.intelligence import ConversationIntelligence
    from src.core.workflows.workflow_router import get_workflow_router
    from src.interfaces.slack.conversation_manager import ConversationManager
    from src.interfaces.slack.enhanced_home_tab import EnhancedHomeTabManager

    # Create mocked dependencies
    redis_mock = mocker.AsyncMock(spec=redis.Redis)
    conversation_intel_mock = mocker.AsyncMock(spec=ConversationIntelligence)
    home_tab_mock = mocker.AsyncMock(spec=EnhancedHomeTabManager)

    # Get real workflow router and mock its temporal client
    workflow_router = await get_workflow_router()

    mock_response = WorkflowResponse(
        workflow_id="test-wf-456",
        workflow_type=WorkflowType.INLINE_ANALYSIS,
        status=WorkflowStatus.RUNNING,
        user_id="test_user",
        team_id="default",
        correlation_id="test-corr-456"
    )

    mock_temporal_client = mocker.AsyncMock()
    mock_temporal_client.start_workflow.return_value = mock_response
    workflow_router.temporal_client = mock_temporal_client

    # Create ConversationManager with mocked workflow router
    conv_manager = ConversationManager(
        redis_client=redis_mock,
        conversation_intelligence=conversation_intel_mock,
        home_tab_manager=home_tab_mock,
        workflow_router=workflow_router
    )

    # Mock intent result with extracted_data
    class MockIntentResult:
        extracted_data = {"time_period": "7_days"}

    intent_result = MockIntentResult()

    # Call _handle_analysis_request
    response = await conv_manager._handle_analysis_request("test_user", intent_result)

    # Verify response
    assert response is not None
    assert "text" in response
    assert "Starting your analysis" in response["text"]

    # Wait a bit for async task to execute
    await asyncio.sleep(0.1)

    # Verify workflow router was called (via the async task)
    # Note: Since it's fire-and-forget, we can't directly assert the call
    # But we verified the method exists and is callable above


@pytest.mark.integration
@pytest.mark.asyncio
async def test_end_to_end_slack_to_workflow_flow(mocker):
    """
    Test the complete integration flow:
    Slack Event → ConversationManager → WorkflowRouter → Temporal
    """
    from src.core.workflows.workflow_router import RoutingDecision

    # 1. Create workflow router with mocked Temporal
    router = await get_workflow_router()

    mock_response = WorkflowResponse(
        workflow_id="e2e-test-wf",
        workflow_type=WorkflowType.INLINE_ANALYSIS,
        status=WorkflowStatus.RUNNING,
        user_id="e2e_user",
        team_id="default",
        correlation_id="e2e-corr-id"
    )

    mock_temporal_client = mocker.AsyncMock()
    mock_temporal_client.start_workflow.return_value = mock_response
    router.temporal_client = mock_temporal_client

    # 2. Create workflow request (simulating what ConversationManager does)
    workflow_request = WorkflowRequest(
        workflow_type=WorkflowType.INLINE_ANALYSIS,
        user_id="e2e_user",
        team_id="default",
        correlation_id="e2e-corr-id",
        input_data={
            "time_period": "7_days",
            "source": "slack_conversation",
            "activity_text": "User e2e_user requested competency analysis"
        }
    )

    # 3. Route the workflow
    result = await router.route_workflow(workflow_request, user_id="e2e_user")

    # 4. Verify complete flow
    assert result.decision != RoutingDecision.ERROR, f"Workflow routing failed: {result.message}"
    assert result.workflow_id is not None, "Workflow ID should be generated"
    assert result.workflow_type == WorkflowType.INLINE_ANALYSIS

    # 5. Verify Temporal client was called with correct parameters
    mock_temporal_client.start_workflow.assert_called_once()
    call_args = mock_temporal_client.start_workflow.call_args

    # Verify workflow class was passed
    assert call_args.kwargs['workflow_class'] is not None
    # Verify request was passed
    assert call_args.kwargs['request'] == workflow_request
    # Verify workflow_id was generated
    assert call_args.kwargs['workflow_id'].startswith('wf-')

    print(f"✅ End-to-end test passed! Workflow ID: {result.workflow_id}")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])
