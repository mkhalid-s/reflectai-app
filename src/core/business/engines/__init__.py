"""
Business Logic Engines

This module contains business logic engines for ReflectAI.

Current Engines:
- recommendation_engine: Stub implementation (Phase 5+ feature)
  Returns empty recommendations to maintain workflow compatibility.
  Active import in: src.services.workflow.activities

Historical Context:
- Competency calculation → Moved to src.core.assessment.competency_assessor
- Career progression → Moved to src.core.assessment.gap_analyzer and level_calculator
- Skill assessment → Moved to src.core.assessment.scoring modules

Recommendation Engine Roadmap:
When recommendation features are prioritized (Phase 9):
1. See git history for reference implementation
2. Implement PersonalizedRecommendation generation with LLM
3. Implement DevelopmentPlan creation with career paths
4. Add learning resource matching
5. Update tests in tests/integration/system/

For now, the stub maintains system stability by returning empty results.
"""

from .recommendation_engine import (
    DevelopmentPlan,
    PersonalizedRecommendation,
    RecommendationEngine,
    get_recommendation_engine,
)

__all__ = [
    "RecommendationEngine",
    "PersonalizedRecommendation",
    "DevelopmentPlan",
    "get_recommendation_engine",
]
