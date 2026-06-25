"""
Phase 2: AI Agent Foundation - Agent System Tests

Unit tests for the AI agent system including:
- Base agent functionality
- Analysis agent capabilities (Phase 1 simplified architecture)
- Advisor agent capabilities (Phase 1 simplified architecture)
- Agent coordination and workflow

UPDATED for Phase 1 Architecture (v0.1.2-alpha):
- Tests Phase 1 agents: AnalysisAgent, AdvisorAgent, ChatResponderAgent
- Uses current BaseAgent API (name, agent_type, state, execute())
- Updated AgentRequest/AgentResponse signatures
- Removed tests for deprecated Phase 0 agents (AnalysisAgent, AdvisorAgent, etc.)
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

# Import the modules under test
try:
    from src.services.agents.advisor_agent import AdvisorAgent
    from src.services.agents.analysis_agent import AnalysisAgent
    from src.services.agents.base import (
        AgentCapability,
        AgentRequest,
        AgentResponse,
        AgentState,
        BaseAgent,
    )
    from src.services.agents.registry import get_agent_registry
except ImportError as e:
    pytest.skip(f"Agent modules not available: {e}", allow_module_level=True)


@pytest.mark.unit
@pytest.mark.phase2
@pytest.mark.asyncio
class TestBaseAgent:
    """Test base agent functionality"""

    async def test_base_agent_creation(self):
        """Test BaseAgent initialization with AnalysisAgent (Phase 1)"""
        # BaseAgent is abstract, test with AnalysisAgent
        agent = AnalysisAgent()

        # Test agent attributes match AnalysisAgent implementation
        assert agent.name == "AnalysisAgent"
        assert "analyz" in agent.description.lower()
        assert agent.agent_type == "analysisagent"
        assert agent.state == AgentState.IDLE

    async def test_agent_state_management(self):
        """Test agent state tracking during execution"""
        agent = AnalysisAgent()

        # Initial state should be IDLE
        assert agent.state == AgentState.IDLE

        # Create a request
        request = AgentRequest(
            task="Analyze this activity: Wrote unit tests for agent system",
            user_id="user123",
            context={"test": True},
        )

        # Mock the _run method to control execution
        with patch.object(agent, "_run", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {
                "analysis": "Technical task",
                "competency": "testing",
                "confidence": 0.9,
            }

            response = await agent.execute(request)

            # After successful execution, state should be COMPLETED
            assert agent.state == AgentState.COMPLETED
            assert response.success is True

    async def test_agent_execute_timeout(self):
        """Test agent execution timeout handling"""
        agent = AnalysisAgent()

        request = AgentRequest(
            task="Long running task",
            user_id="user123",
            timeout_seconds=1,  # Very short timeout
        )

        # Mock _run to simulate long-running task
        async def long_running_task(req):
            await asyncio.sleep(5)  # Longer than timeout
            return {"result": "completed"}

        with patch.object(agent, "_run", side_effect=long_running_task):
            response = await agent.execute(request)

            # Should timeout and return failure
            assert response.success is False
            assert "timed out" in response.error.lower()
            assert agent.state == AgentState.FAILED

    async def test_agent_execute_error_handling(self):
        """Test agent error handling during execution"""
        agent = AnalysisAgent()

        request = AgentRequest(task="Test error handling", user_id="user123")

        # Mock _run to raise an exception
        with patch.object(agent, "_run", side_effect=Exception("Test error")):
            response = await agent.execute(request)

            # Should handle error gracefully
            assert response.success is False
            assert "Test error" in response.error
            assert agent.state == AgentState.FAILED

    async def test_agent_tool_registration(self):
        """Test agent tool registration"""
        agent = AnalysisAgent()

        # Mock tool function
        async def mock_tool(arg1, arg2):
            return {"result": f"processed {arg1} and {arg2}"}

        # Register tool
        agent.register_tool("test_tool", mock_tool)

        # Verify tool is registered
        assert "test_tool" in agent.tools
        assert agent.tools["test_tool"] == mock_tool

    async def test_agent_metrics_tracking(self):
        """Test agent execution metrics tracking"""
        agent = AnalysisAgent()

        request = AgentRequest(task="Analyze activity: Led team meeting", user_id="user123")

        with patch.object(agent, "_run", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {"analysis": "leadership activity"}

            response = await agent.execute(request)

            # Verify metrics are tracked (duration_ms can be 0 for very fast mocked execution)
            assert response.duration_ms >= 0
            assert agent.total_executions > 0

    async def test_agent_request_validation(self):
        """Test AgentRequest creation and validation"""
        request = AgentRequest(
            task="Test task",
            user_id="user123",
            context={"key": "value"},
            max_iterations=10,
            timeout_seconds=60,
        )

        assert request.task == "Test task"
        assert request.user_id == "user123"
        assert request.context["key"] == "value"
        assert request.max_iterations == 10
        assert request.timeout_seconds == 60

    async def test_agent_response_structure(self):
        """Test AgentResponse structure"""
        response = AgentResponse(
            success=True,
            result={"analysis": "complete"},
            agent_name="TestAgent",
            state=AgentState.COMPLETED,
            duration_ms=250,
            llm_calls=1,
            llm_cost=0.002,
            confidence=0.95,
        )

        assert response.success is True
        assert response.result["analysis"] == "complete"
        assert response.agent_name == "TestAgent"
        assert response.state == AgentState.COMPLETED
        assert response.confidence == 0.95


@pytest.mark.unit
@pytest.mark.phase2
@pytest.mark.asyncio
class TestAnalysisAgent:
    """Test AnalysisAgent functionality"""

    async def test_data_analyst_creation(self):
        """Test AnalysisAgent initialization"""
        agent = AnalysisAgent()

        assert agent.name == "AnalysisAgent"
        assert agent.agent_type == "analysisagent"
        assert AgentCapability.ANALYSIS in agent.capabilities
        assert agent.state == AgentState.IDLE

    async def test_activity_analysis(self):
        """Test activity analysis functionality"""
        agent = AnalysisAgent()

        request = AgentRequest(
            task="Analyze this activity: Implemented OAuth2 authentication system",
            user_id="user123",
            context={"activity_type": "technical"},
        )

        with patch.object(agent, "_run", new_callable=AsyncMock) as mock_run:
            # Mock the analysis result
            mock_run.return_value = {
                "competency": "authentication",
                "level": "advanced",
                "confidence": 0.9,
            }

            response = await agent.execute(request)

            assert response.success is True
            assert response.agent_name == "AnalysisAgent"

    async def test_competency_classification(self):
        """Test competency classification"""
        agent = AnalysisAgent()

        request = AgentRequest(
            task="Classify competencies for: Led code review and mentored junior developers",
            user_id="user123",
        )

        with patch.object(agent, "_run", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {
                "competencies": ["code_review", "mentorship", "leadership"],
                "confidence": 0.88,
            }

            response = await agent.execute(request)

            assert response.success is True
            assert "competencies" in response.result

    async def test_multiple_activity_analysis(self):
        """Test analysis of multiple activities"""
        agent = AnalysisAgent()

        activities = [
            "Wrote unit tests for authentication module",
            "Reviewed pull requests from team members",
            "Presented technical design to stakeholders",
        ]

        request = AgentRequest(
            task=f"Analyze these activities: {activities}",
            user_id="user123",
            context={"activities": activities},
        )

        with patch.object(agent, "_run", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {
                "analyses": [
                    {"activity": activities[0], "competencies": ["testing", "authentication"]},
                    {"activity": activities[1], "competencies": ["code_review", "collaboration"]},
                    {
                        "activity": activities[2],
                        "competencies": ["communication", "technical_design"],
                    },
                ],
            }

            response = await agent.execute(request)

            assert response.success is True
            assert "analyses" in response.result

    async def test_low_confidence_handling(self):
        """Test handling of low confidence results"""
        agent = AnalysisAgent()

        request = AgentRequest(task="Analyze: Did some stuff today", user_id="user123")

        with patch.object(agent, "_run", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {
                "analysis": "unclear activity",
                "confidence": 0.3,
                "needs_clarification": True,
            }

            response = await agent.execute(request)

            assert response.success is True
            # Low confidence should still return result
            assert response.result["confidence"] == 0.3


@pytest.mark.unit
@pytest.mark.phase2
@pytest.mark.asyncio
class TestAdvisorAgent:
    """Test AdvisorAgent functionality"""

    async def test_career_strategist_creation(self):
        """Test AdvisorAgent initialization"""
        agent = AdvisorAgent()

        assert agent.name == "AdvisorAgent"
        assert agent.agent_type == "advisoragent"
        assert AgentCapability.ADVICE in agent.capabilities
        assert agent.state == AgentState.IDLE

    async def test_development_recommendations(self):
        """Test development recommendation generation"""
        agent = AdvisorAgent()

        request = AgentRequest(
            task="Provide development recommendations based on current competencies",
            user_id="user123",
            context={
                "competencies": {
                    "python": 85,
                    "code_review": 78,
                    "system_design": 65,
                }
            },
        )

        with patch.object(agent, "_run", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {
                "recommendations": [
                    {
                        "competency": "system_design",
                        "current_level": 65,
                        "target_level": 85,
                        "actions": [
                            "Study system design patterns",
                            "Design a microservices architecture",
                        ],
                        "timeline": "3-6 months",
                    }
                ],
                "priority_focus": "system_design",
            }

            response = await agent.execute(request)

            assert response.success is True
            assert "recommendations" in response.result

    async def test_career_path_guidance(self):
        """Test career path guidance"""
        agent = AdvisorAgent()

        request = AgentRequest(
            task="Suggest career paths for senior developer",
            user_id="user123",
            context={"current_role": "senior_developer", "years_experience": 5},
        )

        with patch.object(agent, "_run", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {
                "career_paths": [
                    {
                        "role": "tech_lead",
                        "probability": 0.85,
                        "required_skills": ["leadership", "architecture"],
                    },
                    {
                        "role": "principal_engineer",
                        "probability": 0.70,
                        "required_skills": ["system_design", "mentorship"],
                    },
                ],
                "recommended_path": "tech_lead",
            }

            response = await agent.execute(request)

            assert response.success is True
            assert "career_paths" in response.result

    async def test_gap_analysis_advice(self):
        """Test competency gap analysis and advice"""
        agent = AdvisorAgent()

        request = AgentRequest(
            task="Analyze gaps between current and target competencies",
            user_id="user123",
            context={
                "current": {"python": 75, "docker": 60},
                "target": {"python": 90, "docker": 85, "kubernetes": 80},
            },
        )

        with patch.object(agent, "_run", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {
                "gaps": [
                    {"competency": "python", "gap": 15, "priority": "medium"},
                    {"competency": "docker", "gap": 25, "priority": "high"},
                    {"competency": "kubernetes", "gap": 80, "priority": "high"},
                ],
                "development_plan": "Focus on containerization skills first",
            }

            response = await agent.execute(request)

            assert response.success is True
            assert "gaps" in response.result

    async def test_learning_resource_suggestions(self):
        """Test learning resource recommendations"""
        agent = AdvisorAgent()

        request = AgentRequest(
            task="Suggest learning resources for Kubernetes",
            user_id="user123",
            context={"skill": "kubernetes", "current_level": "beginner"},
        )

        with patch.object(agent, "_run", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {
                "resources": [
                    {
                        "type": "course",
                        "title": "Kubernetes Fundamentals",
                        "provider": "CNCF",
                    },
                    {
                        "type": "project",
                        "title": "Deploy microservices to Kubernetes",
                        "difficulty": "intermediate",
                    },
                ],
            }

            response = await agent.execute(request)

            assert response.success is True
            assert "resources" in response.result


@pytest.mark.unit
@pytest.mark.phase2
@pytest.mark.asyncio
class TestAgentRegistry:
    """Test agent registry functionality"""

    async def test_agent_registry_initialization(self):
        """Test agent registry initialization"""
        registry = get_agent_registry()

        assert registry is not None
        # Registry should have agents registered
        assert len(registry.agents) > 0

    async def test_agent_retrieval(self):
        """Test retrieving specific agents from registry"""
        from src.services.agents.base import AgentRole

        registry = get_agent_registry()

        # Get AnalysisAgent (Phase 1)
        analysis_agent = registry.get_agent(AgentRole.ANALYSIS_AGENT)
        assert analysis_agent is not None
        assert analysis_agent.name == "AnalysisAgent"

    async def test_agent_selection_by_capability(self):
        """Test selecting agents by capability"""
        registry = get_agent_registry()

        # Find agents with ANALYSIS capability
        analysis_agents = [
            agent
            for agent in registry.agents.values()
            if AgentCapability.ANALYSIS in agent.capabilities
        ]

        assert len(analysis_agents) > 0
        assert any(agent.name == "AnalysisAgent" for agent in analysis_agents)


@pytest.mark.unit
@pytest.mark.phase2
@pytest.mark.asyncio
class TestAgentCommunication:
    """Test agent communication and messaging"""

    async def test_agent_request_to_dict(self):
        """Test AgentRequest serialization"""
        request = AgentRequest(
            task="Test task",
            user_id="user123",
            context={"key": "value"},
            conversation_history=[{"role": "user", "content": "Hello"}],
        )

        request_dict = request.to_dict()

        assert request_dict["task"] == "Test task"
        assert request_dict["user_id"] == "user123"
        assert request_dict["context"]["key"] == "value"
        assert len(request_dict["conversation_history"]) == 1

    async def test_agent_response_to_dict(self):
        """Test AgentResponse serialization"""
        response = AgentResponse(
            success=True,
            result={"data": "result"},
            agent_name="TestAgent",
            state=AgentState.COMPLETED,
            duration_ms=150,
            llm_calls=2,
            llm_cost=0.005,
        )

        response_dict = response.to_dict()

        assert response_dict["success"] is True
        assert response_dict["result"]["data"] == "result"
        assert response_dict["agent_name"] == "TestAgent"
        assert response_dict["state"] == "completed"

    async def test_context_passing_between_requests(self):
        """Test context preservation across requests"""
        initial_context = {
            "user_id": "user123",
            "session_id": "session_456",
            "previous_analysis": {"score": 85},
        }

        request1 = AgentRequest(task="First task", user_id="user123", context=initial_context)

        # Simulate passing context to next request
        request2_context = {
            **request1.context,
            "previous_task": request1.task,
        }

        request2 = AgentRequest(task="Second task", user_id="user123", context=request2_context)

        # Verify context is preserved and extended
        assert request2.context["session_id"] == "session_456"
        assert request2.context["previous_analysis"]["score"] == 85
        assert request2.context["previous_task"] == "First task"

    async def test_conversation_history_accumulation(self):
        """Test conversation history accumulation"""
        request = AgentRequest(
            task="Continue conversation",
            user_id="user123",
            conversation_history=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi! How can I help?"},
                {"role": "user", "content": "Analyze my skills"},
            ],
        )

        assert len(request.conversation_history) == 3
        assert request.conversation_history[0]["role"] == "user"
        assert request.conversation_history[1]["role"] == "assistant"


@pytest.mark.unit
@pytest.mark.phase2
@pytest.mark.slow
class TestAgentPerformance:
    """Test agent system performance"""

    @pytest.mark.asyncio
    async def test_agent_response_time(self):
        """Test agent response time performance"""
        import time

        agent = AnalysisAgent()

        request = AgentRequest(task="Quick analysis", user_id="user123")

        with patch.object(agent, "_run", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {"analysis": "quick result"}

            start_time = time.time()
            response = await agent.execute(request)
            end_time = time.time()

            # Response should be quick (< 1 second for mocked execution)
            assert (end_time - start_time) < 1.0
            assert response.success is True
            assert response.duration_ms < 1000

    @pytest.mark.asyncio
    async def test_concurrent_agent_requests(self):
        """Test concurrent agent request handling"""
        agent = AnalysisAgent()

        # Create multiple concurrent requests
        requests = [AgentRequest(task=f"Request {i}", user_id="user123") for i in range(10)]

        with patch.object(agent, "_run", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {"result": "processed"}

            # Process requests concurrently
            tasks = [agent.execute(req) for req in requests]
            responses = await asyncio.gather(*tasks)

        assert len(responses) == 10
        assert all(response.success for response in responses)
        # All should have executed
        assert agent.total_executions >= 10

    @pytest.mark.asyncio
    async def test_agent_state_isolation(self):
        """Test that concurrent executions don't interfere with state"""
        agent = AnalysisAgent()

        async def slow_task(request):
            await asyncio.sleep(0.1)
            return {"result": f"processed {request.task}"}

        requests = [AgentRequest(task=f"Task {i}", user_id="user123") for i in range(5)]

        with patch.object(agent, "_run", side_effect=slow_task):
            tasks = [agent.execute(req) for req in requests]
            responses = await asyncio.gather(*tasks)

        # All requests should complete successfully
        assert all(r.success for r in responses)
        # Final state should be COMPLETED (from last execution)
        assert agent.state == AgentState.COMPLETED
