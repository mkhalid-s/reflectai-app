"""
ReflectAI Test Configuration

Pytest configuration and fixtures for all test phases.
Provides common test utilities, fixtures, and setup/teardown logic.
"""

import asyncio
import shutil
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# Add src to path for imports during testing
test_dir = Path(__file__).parent
src_dir = test_dir.parent / "src"
sys.path.insert(0, str(src_dir))

# Import centralized version
from src.version import get_base_version


# Test Configuration
class TestConfig:
    """Test configuration constants"""

    # Database
    TEST_DATABASE_URL = "postgresql://test_user:test_pass@localhost:5432/test_reflectai"
    TEST_REDIS_URL = "redis://localhost:6379/1"

    # API
    TEST_API_BASE_URL = "http://localhost:8000"

    # Slack
    TEST_SLACK_BOT_TOKEN = "test-slack-bot-token"
    TEST_SLACK_SIGNING_SECRET = "test-signing-secret"

    # LLM
    TEST_OPENAI_API_KEY = "test-openai-key"
    TEST_ANTHROPIC_API_KEY = "test-anthropic-key"


# Event Loop Fixture
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Temporary Directory Fixture
@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


# Mock Configuration Fixture
@pytest.fixture
def mock_config():
    """Mock configuration for testing"""
    config = MagicMock()
    config.app.name = "ReflectAI Test"
    # Use centralized version with -test suffix for test environment
    config.app.version = f"{get_base_version()}-test"
    config.app.environment = "test"
    config.app.debug = True
    config.database.url = TestConfig.TEST_DATABASE_URL
    return config


# Mock Logger Fixture
@pytest.fixture
def mock_logger():
    """Mock logger for testing"""
    logger = MagicMock()
    logger.info = MagicMock()
    logger.error = MagicMock()
    logger.warning = MagicMock()
    logger.debug = MagicMock()
    return logger


# Mock LLM Client Fixture
@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing"""
    client = AsyncMock()
    client.generate_response = AsyncMock(
        return_value={
            "response": "Test response",
            "model": "gpt-3.5-turbo",
            "usage": {"tokens": 100, "cost": 0.001},
        }
    )
    return client


# Sample User Data Fixture
@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        "id": "user_test_123",
        "user_id": "test_user_123",
        "slack_user_id": "U12345ABC",
        "email": "test@example.com",
        "name": "Test User",
        "created_at": datetime.now(),
        "active": True,
    }


# Sample Activity Data Fixture
@pytest.fixture
def sample_activity_data():
    """Sample activity data for testing"""
    return {
        "id": "activity_test_001",
        "user_id": "test_user_123",
        "content": "Reviewed pull request #123 for authentication module",
        "category": "code_review",
        "timestamp": datetime.now() - timedelta(days=1),
        "confidence": 0.92,
        "keywords": ["python", "code_review", "authentication"],
        "metadata": {"repository": "test-repo", "pull_request": "123"},
    }


# Sample Activity List Fixture
@pytest.fixture
def sample_activity_list():
    """Sample activity list for testing"""
    return [
        {
            "activity_id": "act_001",
            "user_id": "test_user_123",
            "activity_type": "code_review",
            "timestamp": datetime.now() - timedelta(days=1),
            "duration_minutes": 45,
            "quality_score": 85,
            "complexity_level": 3,
            "associated_skills": ["python", "code_review", "collaboration"],
            "metadata": {"repository": "test-repo", "pull_request": "123"},
        },
        {
            "activity_id": "act_002",
            "user_id": "test_user_123",
            "activity_type": "documentation",
            "timestamp": datetime.now() - timedelta(days=2),
            "duration_minutes": 60,
            "quality_score": 90,
            "complexity_level": 2,
            "associated_skills": ["technical_writing", "documentation"],
            "metadata": {"document_type": "api_spec", "pages": 5},
        },
    ]


# Sample Competency Scores Fixture
@pytest.fixture
def sample_competency_scores():
    """Sample competency scores for testing"""
    return {
        "python": 85.5,
        "code_review": 78.2,
        "collaboration": 92.1,
        "mentoring": 65.8,
        "technical_writing": 88.3,
    }


# Mock Database Session Fixture
@pytest.fixture
async def mock_db_session():
    """Mock database session for testing"""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session


# Mock Redis Client Fixture
@pytest.fixture
async def mock_redis_client():
    """Mock Redis client for testing"""
    client = AsyncMock()
    client.get = AsyncMock()
    client.set = AsyncMock()
    client.delete = AsyncMock()
    client.exists = AsyncMock()
    client.expire = AsyncMock()
    return client


# Mock Slack Client Fixture
@pytest.fixture
def mock_slack_client():
    """Mock Slack client for testing"""
    client = AsyncMock()
    client.chat_postMessage = AsyncMock(return_value={"ok": True, "ts": "1234567890.123"})
    client.conversations_history = AsyncMock(return_value={"ok": True, "messages": []})
    client.users_info = AsyncMock(return_value={"ok": True, "user": {"name": "testuser"}})
    return client


# Phase-specific Fixtures
@pytest.fixture
def phase1_config():
    """Phase 1 configuration fixture"""
    return {"environment": "test", "debug": True, "log_level": "DEBUG"}


@pytest.fixture
def phase2_agent_config():
    """Phase 2 agent configuration fixture"""
    return {"max_agents": 3, "agent_timeout": 30, "slack_enabled": True}


@pytest.fixture
def phase3_llm_config():
    """Phase 3 LLM configuration fixture"""
    return {
        "providers": ["openai", "anthropic"],
        "default_model": "gpt-3.5-turbo",
        "max_tokens": 1000,
        "temperature": 0.7,
    }


@pytest.fixture
def phase4_infrastructure_config():
    """Phase 4 infrastructure configuration fixture"""
    return {"database_pool_size": 5, "redis_max_connections": 10, "monitoring_enabled": True}


@pytest.fixture
def phase5_business_config():
    """Phase 5 business logic configuration fixture"""
    return {
        "competency_weights": {"recency": 0.3, "frequency": 0.4, "complexity": 0.3},
        "evidence_thresholds": {"strong": 8, "moderate": 4, "weak": 1},
        "confidence_level": 0.9,
    }


# Pytest Configuration
def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "slow: Slow tests")
    config.addinivalue_line("markers", "phase1: Phase 1 tests")
    config.addinivalue_line("markers", "phase2: Phase 2 tests")
    config.addinivalue_line("markers", "phase3: Phase 3 tests")
    config.addinivalue_line("markers", "phase4: Phase 4 tests")
    config.addinivalue_line("markers", "phase5: Phase 5 tests")


pytest_plugins = ["tests.performance", "tests.coverage_enforcement"]
