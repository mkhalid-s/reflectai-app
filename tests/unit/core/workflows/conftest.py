"""
Fixtures and mocks for workflow tests
"""

import sys
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Mock problematic modules at import time (before pytest fixtures run)

# Mock workflow engine
mock_engine_module = MagicMock()
mock_engine_module.WorkflowEngine = MagicMock
mock_engine_module.get_workflow_engine = Mock(return_value=MagicMock())
sys.modules["src.services.workflow.engine"] = mock_engine_module

# Mock database manager
mock_db_manager_module = MagicMock()
mock_db_manager_module.DatabaseManager = MagicMock
mock_db_manager_module.get_db_manager = Mock(return_value=MagicMock())
sys.modules["src.infrastructure.database.db_manager"] = mock_db_manager_module

# Mock cache manager
mock_cache_module = MagicMock()
mock_cache_module.CacheManager = MagicMock
mock_cache_module.get_cache_manager = Mock(return_value=MagicMock())
sys.modules["src.infrastructure.cache.cache_manager"] = mock_cache_module


@pytest.fixture(autouse=True)
def mock_get_config():
    """Mock get_config for all workflow tests"""
    mock_config = Mock()
    mock_config.get = Mock(return_value=None)

    # Patch the import
    with patch("src.core.workflows.workflow_router.get_config", return_value=mock_config):
        yield mock_config


@pytest.fixture(autouse=True)
def mock_temporal_client():
    """Mock Temporal client to avoid requiring Temporal server"""
    with patch("src.core.workflows.workflow_router.get_temporal_client", return_value=None):
        yield


@pytest.fixture
def mock_conversation_intelligence():
    """Mock ConversationIntelligence for workflow router tests"""
    mock_ci = AsyncMock()
    mock_ci.analyze_message = AsyncMock()
    return mock_ci
