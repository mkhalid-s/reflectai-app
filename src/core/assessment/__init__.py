"""
Competency Assessment System for ReflectAI

Implements Production
- Simple competency scoring based on activity frequency and recency
- Time decay weighting for activity relevance over 90-day window
- Evidence thresholds and competency level calculations
- Level advancement logic with time-in-role requirements
- Competency gap analysis and development recommendations
- Peer comparison and benchmarking capabilities

Provides comprehensive competency assessment infrastructure for ReflectAI.
"""

from .competency_assessor import (
    AssessmentResult,
    CompetencyAssessor,
    CompetencyScore,
    get_competency_assessor,
)
from .gap_analyzer import GapAnalysisResult, GapAnalyzer, SkillGap, get_gap_analyzer
from .level_calculator import (
    CompetencyLevel,
    LevelAdvancementResult,
    LevelCalculator,
    get_level_calculator,
)

# ValidationEngine removed - functionality integrated into other components
from .scoring import ActivityScorer, EvidenceThreshold, TimeDecayCalculator

__all__ = [
    # Core assessment
    "CompetencyAssessor",
    "AssessmentResult",
    "CompetencyScore",
    "get_competency_assessor",
    # Level calculation
    "LevelCalculator",
    "LevelAdvancementResult",
    "CompetencyLevel",
    "get_level_calculator",
    # Gap analysis
    "GapAnalyzer",
    "GapAnalysisResult",
    "SkillGap",
    "get_gap_analyzer",
    # Validation functionality integrated into other components
    # Scoring components
    "ActivityScorer",
    "TimeDecayCalculator",
    "EvidenceThreshold",
]
