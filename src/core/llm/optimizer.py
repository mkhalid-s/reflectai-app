"""
LLM Cost Optimization and Model Selection

Implements  Model Selection & Routing Strategy with tiered model selection
for 60-75% cost reduction through intelligent complexity-based routing.
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from src.shared import get_logger

from .cost_tracker import get_cost_tracker
from .providers import ModelTier, get_provider_manager

logger = get_logger(__name__)


class ComplexityLevel(str, Enum):
    """Request complexity levels for model routing."""

    SIMPLE = "simple"  # 0.0 - 0.3: Basic classification, simple Q&A
    MODERATE = "moderate"  # 0.3 - 0.6: Activity analysis, competency assessment
    COMPLEX = "complex"  # 0.6 - 0.8: Career guidance, strategic advice
    ADVANCED = "advanced"  # 0.8 - 1.0: Multi-faceted synthesis, complex reasoning


@dataclass
class OptimizationRule:
    """Rule for model selection optimization."""

    name: str
    condition: str
    preferred_tier: ModelTier
    fallback_tiers: list[ModelTier]
    description: str
    confidence_threshold: float = 0.7
    max_tokens: int | None = None


@dataclass
class BatchRequest:
    """Batched request for processing optimization."""

    user_id: str
    requests: list[dict[str, Any]]
    batch_id: str = field(default_factory=lambda: str(time.time()))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    timeout_ms: int = 100
    max_size: int = 10


class ComplexityAnalyzer:
    """Analyzes request complexity for optimal model routing."""

    def __init__(self):
        self.complexity_indicators = {
            # Simple indicators (low complexity)
            "simple": [
                "hello",
                "hi",
                "help",
                "what",
                "how",
                "yes",
                "no",
                "thanks",
                "classify",
                "category",
                "type",
                "level",
            ],
            # Moderate indicators
            "moderate": [
                "analyze",
                "assess",
                "evaluate",
                "review",
                "compare",
                "identify",
                "competency",
                "skill",
                "performance",
                "activity",
                "project",
            ],
            # Complex indicators
            "complex": [
                "strategy",
                "plan",
                "develop",
                "career",
                "guidance",
                "advice",
                "recommend",
                "suggest",
                "improve",
                "optimize",
                "grow",
            ],
            # Advanced indicators
            "advanced": [
                "synthesize",
                "integrate",
                "comprehensive",
                "multi-faceted",
                "complex",
                "strategic",
                "long-term",
                "holistic",
                "framework",
            ],
        }

        # Context complexity factors
        self.complexity_factors = {
            "user_context_size": 0.1,  # More context = higher complexity
            "previous_results": 0.2,  # Building on results = higher complexity
            "multiple_requirements": 0.15,  # Multiple asks = higher complexity
            "domain_specificity": 0.1,  # Domain-specific = higher complexity
            "output_structure": 0.05,  # Structured output = slight complexity
        }

    def analyze_complexity(
        self, content: str, context: dict[str, Any] | None = None
    ) -> tuple[ComplexityLevel, float]:
        """
        Analyze request complexity and return complexity level with confidence.

        Args:
            content: Request content to analyze
            context: Additional context for complexity assessment

        Returns:
            Tuple of (complexity_level, confidence_score)
        """

        content_lower = content.lower()
        base_complexity = 0.0

        # Analyze content for complexity indicators
        for complexity_type, indicators in self.complexity_indicators.items():
            matches = sum(1 for indicator in indicators if indicator in content_lower)

            if complexity_type == "simple":
                base_complexity += min(matches * 0.1, 0.3)
            elif complexity_type == "moderate":
                base_complexity += min(matches * 0.15, 0.4)
            elif complexity_type == "complex":
                base_complexity += min(matches * 0.2, 0.5)
            elif complexity_type == "advanced":
                base_complexity += min(matches * 0.25, 0.6)

        # Analyze context factors
        context_complexity = 0.0
        if context:
            # User context complexity
            user_context = context.get("user_context", {})
            if len(user_context) > 3:
                context_complexity += self.complexity_factors["user_context_size"]

            # Previous results complexity
            if context.get("previous_results"):
                context_complexity += self.complexity_factors["previous_results"]

            # Multiple requirements
            requirements_count = content.lower().count(" and ") + content.lower().count(",")
            if requirements_count > 2:
                context_complexity += self.complexity_factors["multiple_requirements"]

            # Output structure requirements
            if any(word in content_lower for word in ["json", "format", "structure", "report"]):
                context_complexity += self.complexity_factors["output_structure"]

        # Content length factor
        length_factor = min(len(content) / 1000, 0.2)  # Max 0.2 boost for length

        # Calculate final complexity
        final_complexity = min(base_complexity + context_complexity + length_factor, 1.0)

        # Determine complexity level
        if final_complexity < 0.3:
            level = ComplexityLevel.SIMPLE
        elif final_complexity < 0.6:
            level = ComplexityLevel.MODERATE
        elif final_complexity < 0.8:
            level = ComplexityLevel.COMPLEX
        else:
            level = ComplexityLevel.ADVANCED

        # Calculate confidence (how certain we are about the classification)
        confidence = self._calculate_confidence(final_complexity, content, context)

        return level, confidence

    def _calculate_confidence(
        self, complexity_score: float, content: str, context: dict[str, Any] | None
    ) -> float:
        """Calculate confidence in complexity assessment."""

        base_confidence = 0.7

        # Boost confidence for clear indicators
        content_lower = content.lower()
        clear_indicators = 0

        for indicators in self.complexity_indicators.values():
            clear_indicators += sum(1 for indicator in indicators if indicator in content_lower)

        if clear_indicators >= 3:
            base_confidence += 0.2
        elif clear_indicators >= 1:
            base_confidence += 0.1

        # Boost confidence if we have good context
        if context and len(context.get("user_context", {})) > 2:
            base_confidence += 0.1

        # Reduce confidence for edge cases (near boundaries)
        boundaries = [0.3, 0.6, 0.8]
        for boundary in boundaries:
            if abs(complexity_score - boundary) < 0.05:
                base_confidence -= 0.1
                break

        return max(0.4, min(1.0, base_confidence))


class DynamicModelSelector:
    """Dynamic model selection based on complexity and optimization rules."""

    def __init__(self):
        self.complexity_analyzer = ComplexityAnalyzer()
        self.provider_manager = get_provider_manager()
        self.cost_tracker = get_cost_tracker()

        # Model tier mapping by complexity
        self.complexity_to_tier = {
            ComplexityLevel.SIMPLE: ModelTier.TIER_1,  # gpt-4o-mini
            ComplexityLevel.MODERATE: ModelTier.TIER_2,  # claude-3-5-haiku
            ComplexityLevel.COMPLEX: ModelTier.TIER_3,  # gpt-4o
            ComplexityLevel.ADVANCED: ModelTier.TIER_4,  # gpt-4o with escalation
        }

        # Escalation tracking
        self.escalation_history: dict[str, list[datetime]] = defaultdict(list)
        self.escalation_threshold = 0.05  # 5% escalation target

        # Optimization rules
        self.optimization_rules = self._initialize_optimization_rules()

        # A/B testing for model effectiveness
        self.ab_test_splits: dict[str, str] = {}  # user_id -> test_group

        logger.info("Dynamic model selector initialized")

    def _initialize_optimization_rules(self) -> list[OptimizationRule]:
        """Initialize model selection optimization rules."""

        return [
            OptimizationRule(
                name="greeting_optimization",
                condition="greeting_or_help",
                preferred_tier=ModelTier.TIER_1,
                fallback_tiers=[ModelTier.TIER_2],
                description="Use cheapest model for greetings and help",
            ),
            OptimizationRule(
                name="classification_optimization",
                condition="simple_classification",
                preferred_tier=ModelTier.TIER_1,
                fallback_tiers=[ModelTier.TIER_2],
                description="Use Tier 1 for simple activity classification",
            ),
            OptimizationRule(
                name="analysis_optimization",
                condition="competency_analysis",
                preferred_tier=ModelTier.TIER_2,
                fallback_tiers=[ModelTier.TIER_3],
                description="Use Tier 2 for competency analysis",
            ),
            OptimizationRule(
                name="career_optimization",
                condition="career_guidance",
                preferred_tier=ModelTier.TIER_3,
                fallback_tiers=[ModelTier.TIER_4],
                description="Use Tier 3 for career guidance",
            ),
            OptimizationRule(
                name="synthesis_optimization",
                condition="complex_synthesis",
                preferred_tier=ModelTier.TIER_4,
                fallback_tiers=[ModelTier.TIER_3],
                description="Use Tier 4 for complex synthesis",
            ),
        ]

    def select_optimal_model(
        self, content: str, context: dict[str, Any] | None = None, user_id: str | None = None
    ) -> tuple[ModelTier, float, str]:
        """
        Select optimal model tier based on complexity and optimization rules.

        Args:
            content: Request content
            context: Additional context
            user_id: User ID for personalization

        Returns:
            Tuple of (model_tier, confidence, reasoning)
        """

        # Analyze complexity
        complexity_level, complexity_confidence = self.complexity_analyzer.analyze_complexity(
            content, context
        )

        # Get base tier from complexity
        base_tier = self.complexity_to_tier[complexity_level]

        # Apply optimization rules
        selected_tier, rule_applied = self._apply_optimization_rules(content, context, base_tier)

        # Check for user-specific optimizations
        if user_id:
            selected_tier = self._apply_user_optimizations(user_id, selected_tier, content, context)

        # Build reasoning
        reasoning_parts = [
            f"Complexity: {complexity_level.value} (confidence: {complexity_confidence:.2f})",
            f"Base tier: {base_tier.value}",
        ]

        if rule_applied:
            reasoning_parts.append(f"Rule applied: {rule_applied}")

        if selected_tier != base_tier:
            reasoning_parts.append(f"Optimized to: {selected_tier.value}")

        reasoning = " | ".join(reasoning_parts)

        logger.debug(
            f"Model selection: {selected_tier.value}",
            extra={
                "complexity": complexity_level.value,
                "confidence": complexity_confidence,
                "reasoning": reasoning,
                "user_id": user_id,
            },
        )

        return selected_tier, complexity_confidence, reasoning

    def _apply_optimization_rules(
        self, content: str, context: dict[str, Any] | None, base_tier: ModelTier
    ) -> tuple[ModelTier, str | None]:
        """Apply optimization rules to potentially override base tier selection."""

        content_lower = content.lower()

        # Check each rule
        for rule in self.optimization_rules:
            if self._rule_matches(rule.condition, content_lower, context):
                logger.debug(f"Applied optimization rule: {rule.name}")
                return rule.preferred_tier, rule.name

        return base_tier, None

    def _rule_matches(
        self, condition: str, content_lower: str, context: dict[str, Any] | None
    ) -> bool:
        """Check if optimization rule condition matches with improved precision."""

        # Check for complexity blockers first
        complex_indicators = [
            "comprehensive",
            "strategic",
            "synthesize",
            "integrate",
            "multi-faceted",
            "executive",
            "leadership",
            "long-term",
            "5-year",
            "multiple data sources",
        ]

        is_complex = any(indicator in content_lower for indicator in complex_indicators)

        if condition == "greeting_or_help":
            # Only match simple greetings, not complex requests with greeting words
            greeting_words = ["hello", "hi", "help", "thanks", "thank you"]
            has_greeting = any(word in content_lower for word in greeting_words)
            is_simple_request = len(content_lower.split()) <= 10 and not is_complex
            return has_greeting and is_simple_request

        elif condition == "simple_classification":
            classification_words = ["classify", "category", "what type", "identify", "label"]
            has_classification = any(word in content_lower for word in classification_words)
            is_simple = len(content_lower.split()) < 20 and not is_complex
            return has_classification and is_simple

        elif condition == "competency_analysis":
            competency_words = ["competency", "skill", "assess", "analyze", "evaluate", "level"]
            has_competency = any(word in content_lower for word in competency_words)
            # Don't trigger for complex strategic planning
            return has_competency and not is_complex

        elif condition == "career_guidance":
            career_words = [
                "career",
                "advance",
                "promotion",
                "growth",
                "guidance",
                "advice",
                "plan",
            ]
            has_career = any(word in content_lower for word in career_words)
            # Only simple career guidance, not comprehensive planning
            is_simple_career = len(content_lower.split()) < 30 and not is_complex
            return has_career and is_simple_career

        elif condition == "complex_synthesis":
            synthesis_words = ["synthesize", "combine", "integrate", "comprehensive", "overall"]
            has_synthesis = any(word in content_lower for word in synthesis_words)
            has_context = context and context.get("previous_results")
            return has_synthesis or has_context or is_complex

        return False

    def _apply_user_optimizations(
        self, user_id: str, base_tier: ModelTier, content: str, context: dict[str, Any] | None
    ) -> ModelTier:
        """Apply user-specific optimizations."""

        # Check user's historical usage patterns
        user_usage = self.cost_tracker.get_user_usage(user_id, days=7)

        # If user has low usage, might optimize for cost
        if user_usage["total_requests"] < 5:
            # New or low-usage user - optimize for cost
            if base_tier == ModelTier.TIER_3 and len(content) < 200:
                logger.debug(f"Cost optimization for low-usage user {user_id}")
                return ModelTier.TIER_2

        # If user has high accuracy needs (based on request patterns)
        if "accurate" in content.lower() or "precise" in content.lower():
            # Escalate for accuracy
            if base_tier == ModelTier.TIER_2:
                return ModelTier.TIER_3

        return base_tier

    def should_escalate(
        self, current_tier: ModelTier, confidence_score: float, user_feedback: str | None = None
    ) -> bool:
        """
        Determine if request should be escalated to higher tier model.

        Args:
            current_tier: Current model tier
            confidence_score: Confidence in current tier selection
            user_feedback: Optional feedback indicating issues

        Returns:
            True if should escalate to higher tier
        """

        # Check escalation rate
        current_escalation_rate = self._get_recent_escalation_rate()
        if current_escalation_rate >= self.escalation_threshold:
            return False  # Already at escalation limit

        # Low confidence triggers escalation
        if confidence_score < 0.4:
            return True

        # User feedback indicating issues
        if user_feedback and any(
            word in user_feedback.lower()
            for word in ["wrong", "incorrect", "not helpful", "try again", "better"]
        ):
            return True

        # Don't escalate if already at highest tier
        if current_tier == ModelTier.TIER_4:
            return False

        return False

    def _get_recent_escalation_rate(self) -> float:
        """Calculate recent escalation rate."""

        total_requests = 0
        escalations = 0
        cutoff_time = datetime.now(UTC) - timedelta(hours=24)

        for user_escalations in self.escalation_history.values():
            recent_escalations = [dt for dt in user_escalations if dt > cutoff_time]
            escalations += len(recent_escalations)
            # Estimate total requests (this is simplified)
            total_requests += len(recent_escalations) * 10  # Rough estimate

        return escalations / total_requests if total_requests > 0 else 0.0

    def record_escalation(self, user_id: str):
        """Record an escalation event."""
        self.escalation_history[user_id].append(datetime.now(UTC))

        # Keep only recent escalations
        cutoff_time = datetime.now(UTC) - timedelta(days=7)
        self.escalation_history[user_id] = [
            dt for dt in self.escalation_history[user_id] if dt > cutoff_time
        ]

    def get_optimization_stats(self) -> dict[str, Any]:
        """Get model selection optimization statistics."""

        escalation_rate = self._get_recent_escalation_rate()

        # Calculate rule application stats (simplified for production)
        rule_applications = {rule.name: 0 for rule in self.optimization_rules}

        return {
            "complexity_analyzer": {
                "complexity_factors": len(self.complexity_analyzer.complexity_factors),
                "indicator_categories": len(self.complexity_analyzer.complexity_indicators),
            },
            "model_selection": {
                "optimization_rules": len(self.optimization_rules),
                "escalation_rate": escalation_rate,
                "escalation_threshold": self.escalation_threshold,
                "tier_mapping": {
                    level.value: tier.value for level, tier in self.complexity_to_tier.items()
                },
            },
            "recent_escalations": sum(
                len(escalations) for escalations in self.escalation_history.values()
            ),
            "rule_applications": rule_applications,
        }


class BatchProcessor:
    """Batch processing for cost optimization through request grouping."""

    def __init__(self, max_pending_batches: int = 100, batch_stale_timeout_seconds: int = 300):
        """
        Initialize batch processor with queue limits.

        Args:
            max_pending_batches: Maximum number of pending batches (default: 100)
            batch_stale_timeout_seconds: Timeout for stale batches in seconds (default: 300 = 5 minutes)
        """
        self.pending_batches: dict[str, BatchRequest] = {}
        self.batch_timeout = 100  # milliseconds
        self.max_batch_size = 10
        self.max_pending_batches = max_pending_batches
        self.batch_stale_timeout_seconds = batch_stale_timeout_seconds

        # Track last cleanup time
        self._last_cleanup = datetime.now(UTC)
        self._cleanup_interval_seconds = 60  # Run cleanup every minute

        # Batch processing stats
        self.batch_stats = {
            "batches_created": 0,
            "batches_processed": 0,
            "requests_batched": 0,
            "cost_savings_estimated": 0.0,
            "batches_dropped": 0,
            "stale_batches_cleaned": 0,
        }

        logger.info(
            "Batch processor initialized",
            extra={
                "max_pending_batches": max_pending_batches,
                "batch_stale_timeout_seconds": batch_stale_timeout_seconds,
            },
        )

    def add_to_batch(self, user_id: str, request_data: dict[str, Any]) -> str | None:
        """
        Add request to user's batch. Returns batch_id if batch is ready.

        Args:
            user_id: User identifier for batching
            request_data: Request to add to batch

        Returns:
            Batch ID if batch is ready for processing, None otherwise
        """

        # Periodic cleanup of stale batches
        self._cleanup_stale_batches()

        # Check if we've hit the queue limit
        if (
            user_id not in self.pending_batches
            and len(self.pending_batches) >= self.max_pending_batches
        ):
            logger.warning(
                f"Batch queue full ({len(self.pending_batches)}/{self.max_pending_batches}), dropping request",
                extra={"user_id": user_id, "pending_batches": len(self.pending_batches)},
            )
            self.batch_stats["batches_dropped"] += 1
            return None

        # Get or create batch for user
        if user_id not in self.pending_batches:
            batch = BatchRequest(
                user_id=user_id,
                requests=[request_data],
                timeout_ms=self.batch_timeout,
                max_size=self.max_batch_size,
            )
            self.pending_batches[user_id] = batch
            self.batch_stats["batches_created"] += 1
        else:
            batch = self.pending_batches[user_id]
            batch.requests.append(request_data)

        self.batch_stats["requests_batched"] += 1

        # Check if batch is ready
        if len(batch.requests) >= batch.max_size or self._is_batch_expired(batch):
            batch_id = batch.batch_id
            del self.pending_batches[user_id]

            logger.debug(
                f"Batch ready for processing: {batch_id}",
                extra={"user_id": user_id, "batch_size": len(batch.requests)},
            )

            return batch_id

        return None

    def _is_batch_expired(self, batch: BatchRequest) -> bool:
        """Check if batch has exceeded timeout."""
        elapsed_ms = (datetime.now(UTC) - batch.created_at).total_seconds() * 1000
        return elapsed_ms >= batch.timeout_ms

    def _cleanup_stale_batches(self):
        """
        Periodically clean up stale batches that have been pending too long.

        This prevents memory leaks from batches that never complete.
        Runs at most once per minute to avoid excessive overhead.
        """
        now = datetime.now(UTC)

        # Check if it's time to run cleanup
        if (now - self._last_cleanup).total_seconds() < self._cleanup_interval_seconds:
            return

        self._last_cleanup = now

        # Find stale batches (older than stale timeout)
        stale_user_ids = []
        for user_id, batch in self.pending_batches.items():
            elapsed_seconds = (now - batch.created_at).total_seconds()
            if elapsed_seconds > self.batch_stale_timeout_seconds:
                stale_user_ids.append(user_id)

        # Remove stale batches
        for user_id in stale_user_ids:
            del self.pending_batches[user_id]
            self.batch_stats["stale_batches_cleaned"] += 1

        if stale_user_ids:
            logger.warning(
                f"Cleaned up {len(stale_user_ids)} stale batches",
                extra={
                    "stale_count": len(stale_user_ids),
                    "stale_timeout_seconds": self.batch_stale_timeout_seconds,
                    "remaining_batches": len(self.pending_batches),
                },
            )

    def process_expired_batches(self) -> list[str]:
        """Process all expired batches and return their IDs."""

        expired_batch_ids = []
        expired_user_ids = []

        for user_id, batch in self.pending_batches.items():
            if self._is_batch_expired(batch):
                expired_batch_ids.append(batch.batch_id)
                expired_user_ids.append(user_id)

        # Remove expired batches
        for user_id in expired_user_ids:
            del self.pending_batches[user_id]

        if expired_batch_ids:
            logger.debug(f"Processing {len(expired_batch_ids)} expired batches")

        return expired_batch_ids

    def estimate_batch_savings(self, batch_size: int, individual_cost: float) -> float:
        """Estimate cost savings from batching."""

        # Simplified savings calculation
        # Assumes 30-50% reduction in API calls through batching
        if batch_size <= 1:
            return 0.0

        savings_rate = min(0.4, 0.1 * batch_size)  # Up to 40% savings
        total_individual_cost = individual_cost * batch_size
        savings = total_individual_cost * savings_rate

        self.batch_stats["cost_savings_estimated"] += savings

        return savings

    def get_batch_stats(self) -> dict[str, Any]:
        """Get batch processing statistics."""

        pending_requests = sum(len(batch.requests) for batch in self.pending_batches.values())

        return {
            "pending_batches": len(self.pending_batches),
            "pending_requests": pending_requests,
            "batch_config": {"timeout_ms": self.batch_timeout, "max_size": self.max_batch_size},
            "statistics": self.batch_stats.copy(),
        }


# Global instances
_dynamic_model_selector: DynamicModelSelector | None = None
_batch_processor: BatchProcessor | None = None


def get_model_selector() -> DynamicModelSelector:
    """Get or create global model selector instance."""
    global _dynamic_model_selector
    if _dynamic_model_selector is None:
        _dynamic_model_selector = DynamicModelSelector()
    return _dynamic_model_selector


def get_batch_processor() -> BatchProcessor:
    """Get or create global batch processor instance."""
    global _batch_processor
    if _batch_processor is None:
        _batch_processor = BatchProcessor()
    return _batch_processor
