#!/usr/bin/env python3
"""
Test Mocks for ReflectAI

Centralized exports for all test mock utilities.
Provides easy access to mock functions and classes.
"""

# LLM Mock Functions
from .external_services_mock import (
    ExternalServiceMock as ExternalServiceMockAlt,
)
from .external_services_mock import (
    MockServiceRegistry,
    create_mock_credentials,
    create_mock_email_message,
    create_mock_webhook,
    get_service_registry,
)

# External Services Mock Functions
from .external_services_mock import (
    get_external_service_mock as get_external_service_mock_alt,
)
from .llm_mock import PromptPattern, get_llm_mock

# Slack Mock Functions
from .slack_mock import (
    MockSlackEvent,
    MockSlackUser,
    SlackEventType,
    create_test_event,
    get_slack_client_mock,
    get_slack_webhook_mock,
)

# Temporal Mock Functions
from .temporal_mock import (
    ExternalServiceMock,
    MockWorkflowExecution,
    TemporalClientMock,
    create_workflow_execution,
    get_external_service_mock,
    get_temporal_client_mock,
)

__all__ = [
    # LLM Mocks
    "get_llm_mock",
    "PromptPattern",
    # Slack Mocks
    "get_slack_client_mock",
    "get_slack_webhook_mock",
    "create_test_event",
    "SlackEventType",
    "MockSlackEvent",
    "MockSlackUser",
    # Temporal Mocks
    "get_temporal_client_mock",
    "get_external_service_mock",
    "create_workflow_execution",
    "TemporalClientMock",
    "ExternalServiceMock",
    "MockWorkflowExecution",
    # External Services Mocks
    "get_service_registry",
    "create_mock_credentials",
    "create_mock_email_message",
    "create_mock_webhook",
    "MockServiceRegistry",
    "ExternalServiceMockAlt",
]
