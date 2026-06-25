"""
LLM Testing Utilities

Provides mock LLM providers, token counting, cost calculation validation,
and other testing utilities for comprehensive LLM system testing.
"""

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.core.llm.providers import ModelPricing, ModelTier
from src.shared import get_logger

logger = get_logger(__name__)


class MockResponseType(str, Enum):
    """Types of mock responses."""

    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    INVALID_JSON = "invalid_json"
    PARTIAL_RESPONSE = "partial_response"


@dataclass
class MockResponse:
    """Mock LLM response configuration."""

    content: str
    tokens_used: dict[str, int]
    cost_usd: float
    processing_time_ms: int = 250
    response_type: MockResponseType = MockResponseType.SUCCESS
    metadata: dict[str, Any] = field(default_factory=dict)


class MockLLMProvider:
    """
    Mock LLM provider for testing without API calls.

    Features:
    - Configurable response patterns
    - Realistic token usage simulation
    - Cost calculation validation
    - Error scenario simulation
    - Performance simulation
    """

    def __init__(self):
        self.response_patterns: dict[str, MockResponse] = {}
        self.default_responses: dict[ModelTier, MockResponse] = {}
        self.call_history: list[dict[str, Any]] = []
        self.error_rate = 0.0  # 0.0 = no errors, 1.0 = all errors

        # Initialize default responses
        self._initialize_default_responses()

        logger.info("Mock LLM provider initialized")

    def _initialize_default_responses(self):
        """Initialize default responses for different model tiers."""

        self.default_responses = {
            ModelTier.TIER_1: MockResponse(
                content=json.dumps(
                    {
                        "classification": "technical_skills",
                        "confidence": 0.85,
                        "evidence": ["debugging", "system analysis", "problem solving"],
                        "recommendations": ["continue developing technical expertise"],
                    },
                    indent=2,
                ),
                tokens_used={"prompt_tokens": 150, "completion_tokens": 80, "total_tokens": 230},
                cost_usd=0.035,  # Realistic for gpt-4o-mini
                processing_time_ms=200,
            ),
            ModelTier.TIER_2: MockResponse(
                content=json.dumps(
                    {
                        "score": 3.5,
                        "gaps": ["advanced architecture design", "team leadership"],
                        "recommendations": [
                            "Seek opportunities to lead technical initiatives",
                            "Study system design patterns and best practices",
                            "Mentor junior team members",
                        ],
                        "evidence": ["strong technical execution", "problem-solving ability"],
                    },
                    indent=2,
                ),
                tokens_used={"prompt_tokens": 200, "completion_tokens": 120, "total_tokens": 320},
                cost_usd=0.080,  # Realistic for claude-3-5-haiku
                processing_time_ms=350,
            ),
            ModelTier.TIER_3: MockResponse(
                content=json.dumps(
                    {
                        "opportunities": [
                            "Technical Lead position in current team",
                            "Cross-functional project leadership",
                            "Architecture committee participation",
                        ],
                        "development_plan": {
                            "objectives": [
                                "develop leadership skills",
                                "expand system design knowledge",
                            ],
                            "timeline": "6-12 months",
                            "milestones": ["complete leadership training", "lead major project"],
                        },
                        "timeline": "12-18 months for transition to Tech Lead role",
                        "insights": ["strong foundation for leadership growth"],
                        "summary": "Well-positioned for leadership advancement with focused development",
                        "actions": [
                            "enroll in leadership program",
                            "identify mentorship opportunities",
                        ],
                    },
                    indent=2,
                ),
                tokens_used={"prompt_tokens": 300, "completion_tokens": 200, "total_tokens": 500},
                cost_usd=1.25,  # Realistic for gpt-4o
                processing_time_ms=600,
            ),
            ModelTier.TIER_4: MockResponse(
                content=json.dumps(
                    {
                        "insights": [
                            "Multi-faceted competency development indicates high potential",
                            "Strategic thinking evident in approach to complex problems",
                            "Leadership qualities emerging through mentoring activities",
                        ],
                        "summary": "Comprehensive analysis reveals strong growth trajectory with specific areas for strategic focus",
                        "actions": [
                            "Create formal development plan with measurable milestones",
                            "Establish mentor relationship with senior technical leader",
                            "Lead cross-team initiative to develop leadership experience",
                        ],
                        "synthesis": "Integration of technical depth with emerging leadership capabilities",
                    },
                    indent=2,
                ),
                tokens_used={"prompt_tokens": 400, "completion_tokens": 250, "total_tokens": 650},
                cost_usd=1.625,  # Realistic for gpt-4o advanced
                processing_time_ms=800,
            ),
        }

    def add_response_pattern(self, pattern: str, response: MockResponse):
        """Add response pattern for specific input matching."""
        self.response_patterns[pattern.lower()] = response
        logger.debug(f"Added mock response pattern: {pattern}")

    def set_error_rate(self, rate: float):
        """Set error rate for testing error handling (0.0 to 1.0)."""
        self.error_rate = max(0.0, min(1.0, rate))
        logger.info(f"Mock provider error rate set to {rate}")

    async def generate_response(self, prompt: str, model_tier: ModelTier, **kwargs) -> MockResponse:
        """Generate mock response based on prompt and model tier."""

        start_time = time.time()

        # Record call
        call_record = {
            "timestamp": start_time,
            "prompt_length": len(prompt),
            "model_tier": model_tier.value,
            "kwargs": kwargs,
        }
        self.call_history.append(call_record)

        # Simulate error scenarios
        if self.error_rate > 0:
            import random

            if random.random() < self.error_rate:
                return MockResponse(
                    content="ERROR: Mock provider simulated failure",
                    tokens_used={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                    cost_usd=0.0,
                    response_type=MockResponseType.ERROR,
                )

        # Check for pattern matches
        prompt_lower = prompt.lower()
        for pattern, response in self.response_patterns.items():
            if pattern in prompt_lower:
                logger.debug(f"Using pattern response for: {pattern}")
                return response

        # Use default response for tier
        base_response = self.default_responses.get(model_tier)
        if not base_response:
            base_response = self.default_responses[ModelTier.TIER_1]

        # Add some variation to make testing more realistic
        varied_response = self._add_response_variation(base_response, prompt)

        # Simulate processing time
        processing_time = (time.time() - start_time) * 1000
        varied_response.processing_time_ms = max(100, int(processing_time))

        return varied_response

    def _add_response_variation(self, base_response: MockResponse, prompt: str) -> MockResponse:
        """Add variation to base response based on prompt content."""

        # Create copy of base response
        varied_content = base_response.content
        varied_tokens = base_response.tokens_used.copy()
        varied_cost = base_response.cost_usd

        # Adjust based on prompt characteristics
        prompt_words = len(prompt.split())

        if prompt_words > 200:
            # Longer prompt = slightly longer response
            varied_tokens["completion_tokens"] = int(varied_tokens["completion_tokens"] * 1.2)
            varied_tokens["total_tokens"] = (
                varied_tokens["prompt_tokens"] + varied_tokens["completion_tokens"]
            )
            varied_cost *= 1.2
        elif prompt_words < 50:
            # Shorter prompt = slightly shorter response
            varied_tokens["completion_tokens"] = int(varied_tokens["completion_tokens"] * 0.8)
            varied_tokens["total_tokens"] = (
                varied_tokens["prompt_tokens"] + varied_tokens["completion_tokens"]
            )
            varied_cost *= 0.8

        return MockResponse(
            content=varied_content,
            tokens_used=varied_tokens,
            cost_usd=round(varied_cost, 4),
            processing_time_ms=base_response.processing_time_ms,
            response_type=base_response.response_type,
            metadata={"variation_applied": True, "prompt_words": prompt_words},
        )

    def get_call_history(self) -> list[dict[str, Any]]:
        """Get history of mock provider calls."""
        return self.call_history.copy()

    def reset_history(self):
        """Reset call history."""
        self.call_history.clear()
        logger.debug("Mock provider call history reset")

    def get_statistics(self) -> dict[str, Any]:
        """Get mock provider usage statistics."""

        if not self.call_history:
            return {"total_calls": 0}

        total_calls = len(self.call_history)
        avg_prompt_length = sum(call["prompt_length"] for call in self.call_history) / total_calls

        tier_usage = {}
        for call in self.call_history:
            tier = call["model_tier"]
            tier_usage[tier] = tier_usage.get(tier, 0) + 1

        return {
            "total_calls": total_calls,
            "average_prompt_length": avg_prompt_length,
            "tier_usage": tier_usage,
            "error_rate": self.error_rate,
            "patterns_configured": len(self.response_patterns),
        }


class TokenCounter:
    """
    Token counting utilities for validation and testing.

    Provides approximate token counting for different models and validation
    of token usage calculations.
    """

    def __init__(self):
        # Approximate tokens per character for different models
        self.tokens_per_char = {
            "gpt": 0.25,  # GPT models
            "claude": 0.24,  # Claude models
            "default": 0.25,  # Default estimate
        }

        logger.debug("Token counter initialized")

    def estimate_tokens(self, text: str, model_family: str = "default") -> int:
        """Estimate token count for text."""

        if not text:
            return 0

        # Use character-based estimation
        char_count = len(text)
        multiplier = self.tokens_per_char.get(model_family, self.tokens_per_char["default"])

        # Apply word-based adjustment
        word_count = len(text.split())
        word_adjustment = word_count * 0.1  # Slight boost for word boundaries

        estimated_tokens = int(char_count * multiplier + word_adjustment)

        return max(1, estimated_tokens)  # At least 1 token

    def validate_token_count(
        self, text: str, reported_tokens: int, model_family: str = "default", tolerance: float = 0.2
    ) -> dict[str, Any]:
        """
        Validate reported token count against estimation.

        Args:
            text: Input text
            reported_tokens: Tokens reported by model
            model_family: Model family for estimation
            tolerance: Tolerance for validation (0.2 = 20%)

        Returns:
            Validation result with details
        """

        estimated_tokens = self.estimate_tokens(text, model_family)

        if estimated_tokens == 0:
            return {
                "valid": True,
                "estimated_tokens": 0,
                "reported_tokens": reported_tokens,
                "difference": 0,
                "difference_percent": 0.0,
            }

        difference = abs(reported_tokens - estimated_tokens)
        difference_percent = difference / estimated_tokens

        is_valid = difference_percent <= tolerance

        return {
            "valid": is_valid,
            "estimated_tokens": estimated_tokens,
            "reported_tokens": reported_tokens,
            "difference": difference,
            "difference_percent": difference_percent,
            "tolerance": tolerance,
            "model_family": model_family,
        }

    def get_token_statistics(
        self, texts: list[str], model_family: str = "default"
    ) -> dict[str, Any]:
        """Get token statistics for a list of texts."""

        if not texts:
            return {"count": 0}

        token_counts = [self.estimate_tokens(text, model_family) for text in texts]

        return {
            "count": len(texts),
            "total_tokens": sum(token_counts),
            "average_tokens": sum(token_counts) / len(token_counts),
            "min_tokens": min(token_counts),
            "max_tokens": max(token_counts),
            "model_family": model_family,
        }


class CostCalculator:
    """
    Cost calculation utilities and validation for LLM testing.

    Validates cost calculations and provides cost estimation tools.
    """

    def __init__(self):
        # Standard pricing (matches provider configurations)
        self.pricing_data = {
            ModelTier.TIER_1: ModelPricing(
                input_cost_per_1k=0.15,
                output_cost_per_1k=0.60,
                max_response_time_s=3,
                max_tokens=16000,
                context_window=128000,
            ),
            ModelTier.TIER_2: ModelPricing(
                input_cost_per_1k=0.25,
                output_cost_per_1k=1.25,
                max_response_time_s=5,
                max_tokens=8000,
                context_window=200000,
            ),
            ModelTier.TIER_3: ModelPricing(
                input_cost_per_1k=2.50,
                output_cost_per_1k=10.00,
                max_response_time_s=8,
                max_tokens=4000,
                context_window=128000,
            ),
            ModelTier.TIER_4: ModelPricing(
                input_cost_per_1k=2.50,
                output_cost_per_1k=10.00,
                max_response_time_s=10,
                max_tokens=4000,
                context_window=128000,
            ),
        }

        logger.debug("Cost calculator initialized")

    def calculate_cost(
        self, model_tier: ModelTier, prompt_tokens: int, completion_tokens: int
    ) -> float:
        """Calculate cost for token usage."""

        pricing = self.pricing_data.get(model_tier)
        if not pricing:
            logger.warning(f"No pricing data for tier {model_tier}")
            return 0.0

        input_cost = (prompt_tokens / 1000) * pricing.input_cost_per_1k
        output_cost = (completion_tokens / 1000) * pricing.output_cost_per_1k

        total_cost = input_cost + output_cost

        return round(total_cost, 6)  # Round to 6 decimal places

    def validate_cost_calculation(
        self,
        model_tier: ModelTier,
        prompt_tokens: int,
        completion_tokens: int,
        reported_cost: float,
        tolerance: float = 0.01,
    ) -> dict[str, Any]:
        """
        Validate reported cost against expected calculation.

        Args:
            model_tier: Model tier used
            prompt_tokens: Input tokens
            completion_tokens: Output tokens
            reported_cost: Cost reported by provider
            tolerance: Tolerance for validation ($0.01)

        Returns:
            Validation result with details
        """

        expected_cost = self.calculate_cost(model_tier, prompt_tokens, completion_tokens)
        difference = abs(reported_cost - expected_cost)

        is_valid = difference <= tolerance

        return {
            "valid": is_valid,
            "expected_cost": expected_cost,
            "reported_cost": reported_cost,
            "difference": difference,
            "tolerance": tolerance,
            "model_tier": model_tier.value,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        }

    def estimate_batch_savings(
        self, individual_costs: list[float], batch_efficiency: float = 0.35
    ) -> dict[str, Any]:
        """
        Estimate cost savings from batch processing.

        Args:
            individual_costs: Costs if processed individually
            batch_efficiency: Expected efficiency gain (0.35 = 35% reduction)

        Returns:
            Savings analysis
        """

        if not individual_costs:
            return {"total_individual": 0.0, "total_batch": 0.0, "savings": 0.0}

        total_individual = sum(individual_costs)
        total_batch = total_individual * (1.0 - batch_efficiency)
        savings = total_individual - total_batch
        savings_percent = (savings / total_individual) * 100 if total_individual > 0 else 0

        return {
            "total_individual": total_individual,
            "total_batch": total_batch,
            "savings": savings,
            "savings_percent": savings_percent,
            "batch_efficiency": batch_efficiency,
            "request_count": len(individual_costs),
        }

    def get_pricing_info(self) -> dict[str, Any]:
        """Get pricing information for all tiers."""

        return {
            tier.value: {
                "input_cost_per_1k": pricing.input_cost_per_1k,
                "output_cost_per_1k": pricing.output_cost_per_1k,
                "max_response_time_s": pricing.max_response_time_s,
                "max_tokens": pricing.max_tokens,
                "context_window": pricing.context_window,
            }
            for tier, pricing in self.pricing_data.items()
        }


# Global instances
_mock_llm_provider: MockLLMProvider | None = None
_token_counter: TokenCounter | None = None
_cost_calculator: CostCalculator | None = None


def get_mock_llm_provider() -> MockLLMProvider:
    """Get or create global mock LLM provider."""
    global _mock_llm_provider
    if _mock_llm_provider is None:
        _mock_llm_provider = MockLLMProvider()
    return _mock_llm_provider


def get_token_counter() -> TokenCounter:
    """Get or create global token counter."""
    global _token_counter
    if _token_counter is None:
        _token_counter = TokenCounter()
    return _token_counter


def get_cost_calculator() -> CostCalculator:
    """Get or create global cost calculator."""
    global _cost_calculator
    if _cost_calculator is None:
        _cost_calculator = CostCalculator()
    return _cost_calculator
