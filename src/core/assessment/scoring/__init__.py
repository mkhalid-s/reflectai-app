"""
Competency Scoring System for ReflectAI

Implements scoring algorithms including:
- Activity-based competency scoring
- Time decay calculations for activity relevance
- Evidence thresholds (Strong/Moderate/Weak)
- Score normalization and validation

Provides the mathematical foundation for competency assessment.
"""

from .activity_scorer import ActivityScorer, CompetencyScoreLevel, ScoringMethod, ScoringResult
from .evidence_thresholds import EvidenceAssessment, EvidenceThreshold, ThresholdLevel
from .time_decay import DecayFunction, DecayParameters, TimeDecayCalculator

# Singleton instances
_activity_scorer_instance = None
_time_decay_calculator_instance = None
_evidence_threshold_instance = None


def get_activity_scorer() -> ActivityScorer:
    """Get singleton ActivityScorer instance"""
    global _activity_scorer_instance
    if _activity_scorer_instance is None:
        _activity_scorer_instance = ActivityScorer()
    return _activity_scorer_instance


def get_time_decay_calculator() -> TimeDecayCalculator:
    """Get singleton TimeDecayCalculator instance"""
    global _time_decay_calculator_instance
    if _time_decay_calculator_instance is None:
        _time_decay_calculator_instance = TimeDecayCalculator()
    return _time_decay_calculator_instance


def get_evidence_threshold() -> EvidenceThreshold:
    """Get singleton EvidenceThreshold instance"""
    global _evidence_threshold_instance
    if _evidence_threshold_instance is None:
        _evidence_threshold_instance = EvidenceThreshold()
    return _evidence_threshold_instance


__all__ = [
    # Activity scoring
    "ActivityScorer",
    "CompetencyScoreLevel",
    "ScoringMethod",
    "ScoringResult",
    "get_activity_scorer",
    # Time decay
    "TimeDecayCalculator",
    "DecayFunction",
    "DecayParameters",
    "get_time_decay_calculator",
    # Evidence thresholds
    "EvidenceThreshold",
    "ThresholdLevel",
    "EvidenceAssessment",
    "get_evidence_threshold",
]
