"""
Integration Test: Workflow Result Delivery
Tests the monitoring and delivery of workflow results back to Slack.
"""
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from src.services.workflow.models import WorkflowResponse, WorkflowStatus, WorkflowType


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_workflow_status_method_exists():
    """Test that get_workflow_status method exists in WorkflowRouter."""
    from src.core.workflows.workflow_router import get_workflow_router

    router = await get_workflow_router()

    assert hasattr(router, 'get_workflow_status'), "get_workflow_status method should exist"
    assert callable(router.get_workflow_status), "get_workflow_status should be callable"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_workflow_status_with_completed_workflow(mocker):
    """Test get_workflow_status returns completed workflow results."""
    from src.core.workflows.workflow_router import get_workflow_router

    router = await get_workflow_router()

    # Mock temporal_client to return completed workflow
    mock_workflow_response = WorkflowResponse(
        workflow_id="test-wf-123",
        workflow_type=WorkflowType.INLINE_ANALYSIS,
        status=WorkflowStatus.COMPLETED,
        result={
            "analysis": {"classification": "code_review", "confidence": 0.85},
            "competencies": {"competencies": {"python": {"score": 4.5, "level": "Advanced"}}},
            "advice": {"advice": "Continue building leadership skills"},
            "synthesis": {"key_insights": ["Strong technical abilities"]}
        },
        user_id="test_user",
        team_id="default",
        correlation_id="test-corr-123",
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC)
    )

    mock_temporal_client = mocker.AsyncMock()
    mock_temporal_client.get_workflow_status.return_value = mock_workflow_response
    router.temporal_client = mock_temporal_client

    # Call get_workflow_status
    status = await router.get_workflow_status("test-wf-123")

    # Verify response
    assert status["status"] == "COMPLETED"
    assert status["workflow_id"] == "test-wf-123"
    assert "result" in status
    assert status["result"]["analysis"]["classification"] == "code_review"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_monitor_workflow_completion(mocker):
    """Test workflow monitoring completes and delivers results."""
    import redis.asyncio as redis

    from src.core.conversation.intelligence import ConversationIntelligence
    from src.core.workflows.workflow_router import get_workflow_router
    from src.interfaces.slack.conversation_manager import ConversationManager
    from src.interfaces.slack.enhanced_home_tab import EnhancedHomeTabManager

    # Create mocked dependencies
    redis_mock = mocker.AsyncMock(spec=redis.Redis)
    conversation_intel_mock = mocker.AsyncMock(spec=ConversationIntelligence)
    home_tab_mock = mocker.AsyncMock(spec=EnhancedHomeTabManager)
    slack_app_mock = mocker.AsyncMock()
    slack_app_mock.client = mocker.AsyncMock()

    # Get workflow router with mocked temporal client
    workflow_router = await get_workflow_router()

    # Mock workflow responses: first RUNNING, then COMPLETED
    workflow_responses = [
        {
            "status": "RUNNING",
            "workflow_id": "test-wf-456",
        },
        {
            "status": "COMPLETED",
            "workflow_id": "test-wf-456",
            "result": {
                "analysis": {"classification": "feature_development", "confidence": 0.90},
                "competencies": {"competencies": {"system_design": {"score": 4.0, "level": "Proficient"}}},
                "advice": {"advice": "Focus on scalability patterns"},
                "synthesis": {"key_insights": ["Excellent problem-solving"]}
            }
        }
    ]

    call_count = [0]

    async def mock_get_workflow_status(workflow_id):
        response = workflow_responses[min(call_count[0], len(workflow_responses) - 1)]
        call_count[0] += 1
        return response

    workflow_router.get_workflow_status = mock_get_workflow_status

    # Create ConversationManager
    conv_manager = ConversationManager(
        redis_client=redis_mock,
        conversation_intelligence=conversation_intel_mock,
        home_tab_manager=home_tab_mock,
        workflow_router=workflow_router,
        slack_app=slack_app_mock
    )

    # Monitor workflow
    await conv_manager._monitor_and_deliver_workflow_results(
        workflow_id="test-wf-456",
        user_id="test_user",
        channel_id="test_channel",
        thread_ts=None,
        max_wait_seconds=10  # Short timeout for testing
    )

    # Verify Slack message was sent
    slack_app_mock.client.chat_postMessage.assert_called_once()
    call_args = slack_app_mock.client.chat_postMessage.call_args

    assert call_args.kwargs['channel'] == "test_channel"
    assert 'blocks' in call_args.kwargs
    blocks = call_args.kwargs['blocks']
    assert len(blocks) > 0
    assert blocks[0]['type'] == 'header'
    assert 'Analysis Complete' in blocks[0]['text']['text']


@pytest.mark.integration
@pytest.mark.asyncio
async def test_monitor_workflow_timeout(mocker):
    """Test workflow monitoring handles timeout."""
    import redis.asyncio as redis

    from src.core.conversation.intelligence import ConversationIntelligence
    from src.core.workflows.workflow_router import get_workflow_router
    from src.interfaces.slack.conversation_manager import ConversationManager
    from src.interfaces.slack.enhanced_home_tab import EnhancedHomeTabManager

    # Create mocked dependencies
    redis_mock = mocker.AsyncMock(spec=redis.Redis)
    conversation_intel_mock = mocker.AsyncMock(spec=ConversationIntelligence)
    home_tab_mock = mocker.AsyncMock(spec=EnhancedHomeTabManager)
    slack_app_mock = mocker.AsyncMock()
    slack_app_mock.client = mocker.AsyncMock()

    # Get workflow router
    workflow_router = await get_workflow_router()

    # Mock workflow that never completes (always RUNNING)
    async def mock_get_workflow_status(workflow_id):
        return {
            "status": "RUNNING",
            "workflow_id": workflow_id
        }

    workflow_router.get_workflow_status = mock_get_workflow_status

    # Create ConversationManager
    conv_manager = ConversationManager(
        redis_client=redis_mock,
        conversation_intelligence=conversation_intel_mock,
        home_tab_manager=home_tab_mock,
        workflow_router=workflow_router,
        slack_app=slack_app_mock
    )

    # Monitor workflow with short timeout
    await conv_manager._monitor_and_deliver_workflow_results(
        workflow_id="test-wf-timeout",
        user_id="test_user",
        channel_id="test_channel",
        thread_ts=None,
        max_wait_seconds=2  # Very short timeout
    )

    # Verify timeout message was sent
    slack_app_mock.client.chat_postMessage.assert_called_once()
    call_args = slack_app_mock.client.chat_postMessage.call_args

    assert call_args.kwargs['channel'] == "test_channel"
    assert '❌' in call_args.kwargs['text']
    assert 'longer than expected' in call_args.kwargs['text'].lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_monitor_workflow_failure(mocker):
    """Test workflow monitoring handles failures."""
    import redis.asyncio as redis

    from src.core.conversation.intelligence import ConversationIntelligence
    from src.core.workflows.workflow_router import get_workflow_router
    from src.interfaces.slack.conversation_manager import ConversationManager
    from src.interfaces.slack.enhanced_home_tab import EnhancedHomeTabManager

    # Create mocked dependencies
    redis_mock = mocker.AsyncMock(spec=redis.Redis)
    conversation_intel_mock = mocker.AsyncMock(spec=ConversationIntelligence)
    home_tab_mock = mocker.AsyncMock(spec=EnhancedHomeTabManager)
    slack_app_mock = mocker.AsyncMock()
    slack_app_mock.client = mocker.AsyncMock()

    # Get workflow router
    workflow_router = await get_workflow_router()

    # Mock failed workflow
    async def mock_get_workflow_status(workflow_id):
        return {
            "status": "FAILED",
            "workflow_id": workflow_id,
            "error": "Test error: Activity timeout"
        }

    workflow_router.get_workflow_status = mock_get_workflow_status

    # Create ConversationManager
    conv_manager = ConversationManager(
        redis_client=redis_mock,
        conversation_intelligence=conversation_intel_mock,
        home_tab_manager=home_tab_mock,
        workflow_router=workflow_router,
        slack_app=slack_app_mock
    )

    # Monitor workflow
    await conv_manager._monitor_and_deliver_workflow_results(
        workflow_id="test-wf-failed",
        user_id="test_user",
        channel_id="test_channel",
        thread_ts=None,
        max_wait_seconds=10
    )

    # Verify error message was sent
    slack_app_mock.client.chat_postMessage.assert_called_once()
    call_args = slack_app_mock.client.chat_postMessage.call_args

    assert call_args.kwargs['channel'] == "test_channel"
    assert '❌' in call_args.kwargs['text']
    assert 'failed' in call_args.kwargs['text'].lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_format_workflow_results():
    """Test workflow result formatting."""
    import redis.asyncio as redis

    from src.core.conversation.intelligence import ConversationIntelligence
    from src.interfaces.slack.conversation_manager import ConversationManager
    from src.interfaces.slack.enhanced_home_tab import EnhancedHomeTabManager

    # Create mocked dependencies
    redis_mock = AsyncMock(spec=redis.Redis)
    conversation_intel_mock = AsyncMock(spec=ConversationIntelligence)
    home_tab_mock = AsyncMock(spec=EnhancedHomeTabManager)
    slack_app_mock = AsyncMock()

    # Create ConversationManager
    conv_manager = ConversationManager(
        redis_client=redis_mock,
        conversation_intelligence=conversation_intel_mock,
        home_tab_manager=home_tab_mock,
        workflow_router=None,  # Not needed for formatting test
        slack_app=slack_app_mock
    )

    # Test result
    result = {
        "analysis": {
            "classification": "technical_discussion",
            "confidence": 0.88
        },
        "competencies": {
            "competencies": {
                "leadership": {"score": 3.5, "level": "Proficient"},
                "communication": {"score": 4.2, "level": "Advanced"}
            }
        },
        "advice": {
            "advice": "Focus on technical mentorship opportunities"
        },
        "synthesis": {
            "key_insights": [
                "Strong collaboration skills",
                "Growing technical leadership",
                "Effective team communication"
            ]
        },
        "total_llm_cost": 0.0234
    }

    # Format results
    blocks = await conv_manager._format_workflow_results(result)

    # Verify blocks structure
    assert isinstance(blocks, list)
    assert len(blocks) > 0

    # Verify header block
    assert blocks[0]['type'] == 'header'
    assert 'Analysis Complete' in blocks[0]['text']['text']

    # Verify content blocks exist
    block_texts = ' '.join([
        str(b.get('text', {}).get('text', ''))
        for b in blocks
        if b.get('type') == 'section'
    ])

    assert 'technical_discussion' in block_texts.lower() or 'technical discussion' in block_texts.lower()
    assert 'leadership' in block_texts.lower()
    assert 'communication' in block_texts.lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_end_to_end_workflow_monitoring():
    """
    Test complete end-to-end workflow monitoring flow.

    Simulates:
    1. Workflow starts (RUNNING)
    2. Workflow completes (COMPLETED)
    3. Results formatted
    4. Results delivered to Slack
    """
    import redis.asyncio as redis

    from src.core.conversation.intelligence import ConversationIntelligence
    from src.core.workflows.workflow_router import get_workflow_router
    from src.interfaces.slack.conversation_manager import ConversationManager
    from src.interfaces.slack.enhanced_home_tab import EnhancedHomeTabManager

    # Create mocks
    redis_mock = AsyncMock(spec=redis.Redis)
    conversation_intel_mock = AsyncMock(spec=ConversationIntelligence)
    home_tab_mock = AsyncMock(spec=EnhancedHomeTabManager)
    slack_app_mock = AsyncMock()
    slack_app_mock.client = AsyncMock()

    # Create workflow router
    workflow_router = await get_workflow_router()

    # Simulate workflow lifecycle
    states = [
        {"status": "RUNNING", "workflow_id": "e2e-wf"},
        {"status": "RUNNING", "workflow_id": "e2e-wf"},
        {
            "status": "COMPLETED",
            "workflow_id": "e2e-wf",
            "result": {
                "analysis": {"classification": "code_review", "confidence": 0.95},
                "competencies": {"competencies": {"code_review": {"score": 4.8, "level": "Expert"}}},
                "advice": {"advice": "Mentor junior developers on code review best practices"},
                "synthesis": {"key_insights": ["Expert-level code review skills"]},
                "total_llm_cost": 0.0156
            }
        }
    ]

    call_index = [0]

    async def mock_get_workflow_status(workflow_id):
        idx = min(call_index[0], len(states) - 1)
        call_index[0] += 1
        return states[idx]

    workflow_router.get_workflow_status = mock_get_workflow_status

    # Create ConversationManager
    conv_manager = ConversationManager(
        redis_client=redis_mock,
        conversation_intelligence=conversation_intel_mock,
        home_tab_manager=home_tab_mock,
        workflow_router=workflow_router,
        slack_app=slack_app_mock
    )

    # Monitor workflow
    await conv_manager._monitor_and_deliver_workflow_results(
        workflow_id="e2e-wf",
        user_id="e2e_user",
        channel_id="e2e_channel",
        thread_ts="1234.5678",
        max_wait_seconds=10
    )

    # Verify workflow was monitored (multiple status checks)
    assert call_index[0] >= 2  # At least 2 checks (RUNNING then COMPLETED)

    # Verify Slack message was posted
    slack_app_mock.client.chat_postMessage.assert_called_once()
    call_args = slack_app_mock.client.chat_postMessage.call_args

    # Verify channel and thread
    assert call_args.kwargs['channel'] == "e2e_channel"
    assert call_args.kwargs['thread_ts'] == "1234.5678"

    # Verify blocks contain expected content
    blocks = call_args.kwargs['blocks']
    block_content = str(blocks).lower()

    assert 'analysis complete' in block_content
    assert 'code' in block_content or 'review' in block_content
    assert 'expert' in block_content


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])
