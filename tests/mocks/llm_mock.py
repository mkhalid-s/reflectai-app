#!/usr/bin/env python3
"""
LLM Mock Infrastructure for ReflectAI Testing

Provides predefined responses per prompt pattern for reliable testing.
Supports different model types and response scenarios.
"""

import json
from dataclasses import dataclass
from enum import Enum
from unittest.mock import AsyncMock, Mock


class PromptPattern(str, Enum):
    """Common prompt patterns for testing."""

    ACTIVITY_CLASSIFICATION = "classify_activity"
    COMPETENCY_ASSESSMENT = "assess_competency"
    WORKFLOW_DECISION = "workflow_decision"
    REPORT_GENERATION = "generate_report"
    USER_CONTEXT_UPDATE = "update_context"
    ERROR_HANDLING = "error_scenario"
    RATE_LIMITED = "rate_limited"
    NETWORK_ERROR = "network_error"


class ModelType(str, Enum):
    """LLM model types for testing."""

    GPT_4 = "gpt-4"
    GPT_3_5_TURBO = "gpt-3.5-turbo"
    CLAUDE_3 = "claude-3-sonnet-20240229"
    BEDROCK_NOVA = "amazon.nova-lite-v1:0"


@dataclass
class MockResponse:
    """Mock response configuration."""

    content: str | dict | list
    usage: dict[str, int]
    finish_reason: str = "stop"
    model: str = ModelType.GPT_3_5_TURBO


class LLMResponseFactory:
    """Factory for generating LLM responses based on prompt patterns."""

    def __init__(self):
        self.pattern_responses = self._initialize_pattern_responses()

    def _initialize_pattern_responses(self) -> dict[PromptPattern, MockResponse]:
        """Initialize predefined responses for each pattern."""
        return {
            PromptPattern.ACTIVITY_CLASSIFICATION: MockResponse(
                content={
                    "activity_type": "professional_development",
                    "confidence": 0.95,
                    "category": "learning",
                    "tags": ["skill_development", "continuous_learning"],
                },
                usage={"prompt_tokens": 150, "completion_tokens": 45},
                model=ModelType.GPT_4,
            ),
            PromptPattern.COMPETENCY_ASSESSMENT: MockResponse(
                content={
                    "competency_level": "intermediate",
                    "score": 7.5,
                    "evidence": "Demonstrated strong analytical skills and technical knowledge",
                    "recommendations": ["Focus on advanced topics", "Take leadership training"],
                },
                usage={"prompt_tokens": 200, "completion_tokens": 80},
                model=ModelType.CLAUDE_3,
            ),
            PromptPattern.WORKFLOW_DECISION: MockResponse(
                content={
                    "decision": "proceed_to_review",
                    "confidence": 0.88,
                    "next_steps": ["gather_feedback", "prepare_summary"],
                    "priority": "high",
                },
                usage={"prompt_tokens": 120, "completion_tokens": 35},
                model=ModelType.BEDROCK_NOVA,
            ),
            PromptPattern.REPORT_GENERATION: MockResponse(
                content={
                    "summary": "Weekly progress report",
                    "highlights": ["Completed 5 tasks", "Exceeded targets by 15%"],
                    "challenges": ["Resource constraints"],
                    "next_week_goals": ["Complete project milestone"],
                },
                usage={"prompt_tokens": 300, "completion_tokens": 120},
                model=ModelType.GPT_4,
            ),
            PromptPattern.USER_CONTEXT_UPDATE: MockResponse(
                content={
                    "context_updated": True,
                    "new_topics": ["machine_learning", "data_science"],
                    "confidence": 0.92,
                    "action_items": ["Schedule ML training", "Review data projects"],
                },
                usage={"prompt_tokens": 180, "completion_tokens": 60},
                model=ModelType.GPT_3_5_TURBO,
            ),
            PromptPattern.ERROR_HANDLING: MockResponse(
                content={
                    "error": "Invalid input format",
                    "suggestion": "Please provide activity description in proper format",
                    "retryable": True,
                },
                usage={"prompt_tokens": 100, "completion_tokens": 30},
                model=ModelType.GPT_3_5_TURBO,
            ),
            PromptPattern.RATE_LIMITED: MockResponse(
                content="Rate limit exceeded. Please try again later.",
                usage={"prompt_tokens": 50, "completion_tokens": 10},
                finish_reason="length",
                model=ModelType.GPT_3_5_TURBO,
            ),
            PromptPattern.NETWORK_ERROR: MockResponse(
                content="Network connection failed. Please check connectivity.",
                usage={"prompt_tokens": 30, "completion_tokens": 8},
                finish_reason="stop",
                model=ModelType.GPT_3_5_TURBO,
            ),
        }

    def get_response_for_pattern(self, pattern: PromptPattern, model: str = None) -> MockResponse:
        """Get mock response for a specific pattern."""
        response = self.pattern_responses[pattern]
        if model:
            response.model = model
        return response

    def create_llm_mock(self, model: str = ModelType.GPT_3_5_TURBO) -> AsyncMock:
        """Create a mock LLM client with predefined responses."""
        mock_client = AsyncMock()

        async def mock_completion(*args, **kwargs):
            # Extract prompt from messages
            messages = kwargs.get("messages", args[0] if args else [])
            if isinstance(messages, list) and messages:
                prompt_text = messages[-1].get("content", "")
            else:
                prompt_text = str(messages)

            # Determine pattern from prompt content
            pattern = self._classify_prompt(prompt_text)

            # Get response for pattern
            response = self.get_response_for_pattern(pattern, model)

            # Create mock response object
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message = Mock()
            mock_response.choices[0].message.content = (
                response.content
                if isinstance(response.content, str)
                else json.dumps(response.content)
            )
            mock_response.choices[0].finish_reason = response.finish_reason
            mock_response.usage = Mock()
            mock_response.usage.prompt_tokens = response.usage["prompt_tokens"]
            mock_response.usage.completion_tokens = response.usage["completion_tokens"]

            return mock_response

        mock_client.chat.completions.create = mock_completion
        return mock_client

    def _classify_prompt(self, prompt: str) -> PromptPattern:
        """Classify prompt text into a pattern."""
        prompt_lower = prompt.lower()

        if any(word in prompt_lower for word in ["classify", "category", "type"]):
            return PromptPattern.ACTIVITY_CLASSIFICATION
        elif any(word in prompt_lower for word in ["competency", "skill", "level"]):
            return PromptPattern.COMPETENCY_ASSESSMENT
        elif any(word in prompt_lower for word in ["workflow", "decision", "next step"]):
            return PromptPattern.WORKFLOW_DECISION
        elif any(word in prompt_lower for word in ["report", "summary", "generate"]):
            return PromptPattern.REPORT_GENERATION
        elif any(word in prompt_lower for word in ["context", "update", "profile"]):
            return PromptPattern.USER_CONTEXT_UPDATE
        elif any(word in prompt_lower for word in ["error", "invalid", "failed"]):
            return PromptPattern.ERROR_HANDLING
        elif "rate limit" in prompt_lower:
            return PromptPattern.RATE_LIMITED
        elif "network" in prompt_lower or "connection" in prompt_lower:
            return PromptPattern.NETWORK_ERROR
        else:
            return PromptPattern.ACTIVITY_CLASSIFICATION  # default


# Global instance for easy access
llm_factory = LLMResponseFactory()


def get_llm_mock(model: str = ModelType.GPT_3_5_TURBO) -> AsyncMock:
    """Get a pre-configured LLM mock."""
    return llm_factory.create_llm_mock(model)
