"""
End-to-end integration tests for ReflectAI system.

OUTDATED: This test file references modules that have been refactored.
Needs rewrite to use current architecture.
"""

import asyncio
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

# SKIP ALL TESTS - Need rewrite for current architecture
pytestmark = pytest.mark.skip(
    reason="Tests need rewrite for current architecture (RedisManager moved)"
)

from src.core.llm.gateway import LLMGateway

# from src.core.storage.redis_manager import RedisManager  # Moved to src.infrastructure.cache.redis_manager
from src.infrastructure.cache.redis_manager import RedisManager
from src.infrastructure.config.config_manager import get_config_manager
from src.services.agents.base import AgentCapability
from src.services.agents.registry import get_agent_registry


class TestEndToEndIntegration:
    """Test complete user journey through the system."""

    @pytest.mark.asyncio
    async def test_user_activity_analysis_flow(self):
        """Test complete flow from user activity to analysis results."""
        # Initialize components
        registry = get_agent_registry()

        # Get analysis agent (using data analyst for analysis capability)
        from src.services.agents.base import AgentRole

        agent = registry.get_agent(AgentRole.DATA_ANALYST)
        assert agent is not None

        # Create test user data
        user_id = str(uuid.uuid4())
        test_activities = [
            "Completed Python microservices architecture design",
            "Led team meeting on API design patterns",
            "Reviewed code for authentication module",
        ]

        # Process activities
        results = []
        for activity in test_activities:
            result = await agent.process_request(
                {
                    "user_id": user_id,
                    "activity": activity,
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            )
            results.append(result)

        # Verify results
        assert len(results) == 3
        for result in results:
            assert "analysis" in result
            assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_advisor_recommendation_flow(self):
        """Test advisor agent recommendation generation."""
        registry = await get_agent_registry()

        # Get advisor agent
        agent = await registry.get_agent(capability=AgentCapability.ADVISORY)
        assert agent is not None

        # Create test context
        context = {
            "user_id": str(uuid.uuid4()),
            "competencies": {"Technical Skills": 0.85, "Leadership": 0.72, "Communication": 0.68},
            "goals": ["Senior Software Engineer", "Tech Lead"],
        }

        # Get recommendations
        recommendations = await agent.process_request(context)

        # Verify recommendations
        assert recommendations is not None
        assert "recommendations" in recommendations
        assert recommendations["status"] == "success"

    @pytest.mark.asyncio
    async def test_agent_coordination(self):
        """Test coordination between multiple agents."""
        registry = await get_agent_registry()

        # Get both agents
        analysis_agent = await registry.get_agent(agent_id="analysis_agent_v4")
        advisor_agent = await registry.get_agent(agent_id="advisor_agent_v4")

        assert analysis_agent is not None
        assert advisor_agent is not None

        # Create workflow
        user_id = str(uuid.uuid4())

        # Step 1: Analyze activities
        analysis_result = await analysis_agent.process_request(
            {
                "user_id": user_id,
                "activities": ["Developed RESTful API", "Conducted code review"],
                "request_type": "competency_assessment",
            }
        )

        # Step 2: Generate recommendations based on analysis
        advisor_result = await advisor_agent.process_request(
            {
                "user_id": user_id,
                "analysis_results": analysis_result,
                "request_type": "career_recommendations",
            }
        )

        # Verify coordination
        assert analysis_result["status"] == "success"
        assert advisor_result["status"] == "success"
        assert "recommendations" in advisor_result

    @pytest.mark.asyncio
    async def test_configuration_loading(self):
        """Test configuration management system."""
        config_manager = get_config_manager()

        # Load configuration
        config = config_manager.load_configuration("development")

        # Verify configuration
        assert config is not None
        assert config.app.environment == "development"
        assert config.database is not None
        assert config.cache is not None
        assert config.agents is not None

        # Test feature flags
        assert config_manager.is_feature_enabled("simplified_agents")
        assert config_manager.is_feature_enabled("redis_pubsub")

    @pytest.mark.asyncio
    @patch("src.core.storage.redis_manager.redis")
    async def test_redis_caching_integration(self, mock_redis):
        """Test Redis caching integration."""
        # Mock Redis client
        mock_client = AsyncMock()
        mock_redis.from_url.return_value = mock_client

        manager = RedisManager()
        await manager.initialize()

        # Test cache operations
        test_key = "test:user:123"
        test_value = {"name": "Test User", "score": 0.85}

        # Set cache
        await manager.set_cache(test_key, test_value, ttl=3600)
        mock_client.setex.assert_called_once()

        # Get cache
        mock_client.get.return_value = '{"name": "Test User", "score": 0.85}'
        cached_value = await manager.get_cache(test_key)
        assert cached_value == test_value

    @pytest.mark.asyncio
    async def test_llm_gateway_integration(self):
        """Test LLM Gateway integration."""
        gateway = LLMGateway()

        # Test with mock response
        with patch.object(gateway, "generate_completion") as mock_generate:
            mock_generate.return_value = {
                "response": "Test response",
                "tokens_used": 100,
                "cost": 0.002,
            }

            result = await gateway.generate_completion(prompt="Test prompt", model="gpt-4o-mini")

            assert result["response"] == "Test response"
            assert "tokens_used" in result
            assert "cost" in result

    @pytest.mark.asyncio
    async def test_tool_registry_integration(self):
        """Test tool registry and discovery."""
        from src.core.tools.tool_registry import ToolRegistry

        registry = ToolRegistry()

        # Register a test tool
        test_tool = Mock()
        test_tool.name = "test_tool"
        test_tool.description = "Test tool"

        registry.register_tool(test_tool)

        # Discover tool
        tool = registry.get_tool("test_tool")
        assert tool is not None
        assert tool.name == "test_tool"

        # List all tools
        all_tools = registry.list_tools()
        assert "test_tool" in all_tools

    @pytest.mark.asyncio
    async def test_error_handling_flow(self):
        """Test system error handling and recovery."""
        registry = await get_agent_registry()

        # Get agent
        agent = await registry.get_agent(capability=AgentCapability.ANALYSIS)

        # Test with invalid input
        result = await agent.process_request({})

        # Should handle gracefully
        assert result["status"] == "error"
        assert "error" in result
        assert "recovery_suggestions" in result

    @pytest.mark.asyncio
    async def test_health_check_endpoints(self):
        """Test system health check endpoints."""
        # Test agent registry health
        registry = await get_agent_registry()
        health = await registry.health_check()

        assert health["registry_initialized"]
        assert health["registered_agents"] > 0
        assert "agent_health" in health

        # Test configuration health
        config_manager = get_config_manager()
        config_health = config_manager.get_health_status()

        assert config_health["config_loaded"]
        assert "environment" in config_health

    @pytest.mark.asyncio
    async def test_concurrent_agent_processing(self):
        """Test concurrent processing with multiple agents."""
        registry = await get_agent_registry()

        # Create multiple concurrent requests
        tasks = []
        for i in range(5):
            agent = await registry.get_agent(capability=AgentCapability.ANALYSIS)
            if agent:
                task = agent.process_request(
                    {
                        "user_id": f"user_{i}",
                        "activity": f"Activity {i}",
                        "request_id": str(uuid.uuid4()),
                    }
                )
                tasks.append(task)

        # Process concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all completed
        successful = [r for r in results if isinstance(r, dict) and r.get("status") == "success"]
        assert len(successful) >= 3  # At least 3 should succeed


@pytest.mark.asyncio
class TestDatabaseIntegration:
    """Test database integration layer."""

    async def test_sqlalchemy_models(self):
        """Test SQLAlchemy model definitions."""
        from src.infrastructure.database.models import Activity, Competency, User

        # Verify models are defined
        assert User.__tablename__ == "users"
        assert Activity.__tablename__ == "activities"
        assert Competency.__tablename__ == "competencies"

    async def test_repository_pattern(self):
        """Test repository pattern implementation."""
        from src.infrastructure.database.repositories.user_repository import UserRepository

        # Create repository instance
        repo = UserRepository(session=Mock())

        # Verify methods exist
        assert hasattr(repo, "create")
        assert hasattr(repo, "get")
        assert hasattr(repo, "update")
        assert hasattr(repo, "delete")

    async def test_alembic_migrations(self):
        """Test Alembic migration setup."""
        from pathlib import Path

        alembic_ini = Path("src/infrastructure/database/alembic/alembic.ini")
        env_py = Path("src/infrastructure/database/alembic/env.py")

        assert alembic_ini.exists()
        assert env_py.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
