"""
Recommendation Engine - Stub Implementation

This is a minimal stub implementation to maintain compatibility with existing workflows.
The full recommendation engine was removed as dead code (0 usage outside workflows).

Future Implementation:
- When recommendation features are prioritized, implement full functionality
- See git history for reference implementation with:
  * PersonalizedRecommendation generation
  * DevelopmentPlan creation
  * CareerPath recommendations
  * Resource matching

For now, this stub returns empty/placeholder data to maintain system stability.
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class PersonalizedRecommendation(BaseModel):
    """Stub recommendation model"""

    recommendation_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    recommendation_type: str = "skill_development"
    title: str = "Development Recommendation"
    description: str = ""
    priority_score: float = 50.0
    confidence_score: float = 0.5
    actionable_steps: list[str] = Field(default_factory=list)
    estimated_effort_hours: int = 0
    expected_impact: str = "Medium"
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class DevelopmentPlan(BaseModel):
    """Stub development plan model"""

    plan_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    title: str = "Development Plan"
    phases: list[dict[str, Any]] = Field(default_factory=list)
    total_timeline_months: int = 6
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RecommendationEngine:
    """
    Stub Recommendation Engine

    Provides minimal functionality to maintain workflow compatibility.
    Returns empty/placeholder recommendations.
    """

    def __init__(self):
        """Initialize stub recommendation engine"""
        pass

    async def generate_personalized_recommendations(
        self,
        user_id: str,
        competency_scores: dict[str, float],
        user_context: dict[str, Any],
        recommendation_types: list[str] | None = None,
    ) -> list[PersonalizedRecommendation]:
        """Generate stub recommendations (returns empty list)"""
        return []

    async def create_development_plan(
        self,
        user_id: str,
        current_competencies: dict[str, float],
        target_competencies: dict[str, float],
        timeline_months: int = 6,
    ) -> DevelopmentPlan:
        """Create stub development plan"""
        return DevelopmentPlan(
            user_id=user_id,
            title="Development plan generation not yet implemented",
            phases=[],
            total_timeline_months=timeline_months,
        )


# Singleton instance
_recommendation_engine_instance: RecommendationEngine | None = None


def get_recommendation_engine() -> RecommendationEngine:
    """Get singleton recommendation engine instance"""
    global _recommendation_engine_instance
    if _recommendation_engine_instance is None:
        _recommendation_engine_instance = RecommendationEngine()
    return _recommendation_engine_instance


__all__ = [
    "RecommendationEngine",
    "PersonalizedRecommendation",
    "DevelopmentPlan",
    "get_recommendation_engine",
]
