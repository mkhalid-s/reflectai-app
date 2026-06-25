"""
Classification and Analysis Engine for ReflectAI

Implements  Classification and analysis tools including:
- Activity Classification Engine with rule-based and LLM-assisted classification
- Intent Classification and Analysis for user requests
- Competency Framework Mapping with dynamic loading
- Trend Analysis and Progression Tracking for competencies

Provides sophisticated classification capabilities for activity categorization,
intent detection, and competency analysis with confidence scoring.
"""

from .activity_classifier import (
    ActivityClassificationEngine,
    ActivityClassificationResult,
    ClassificationMethod,
    get_activity_classifier,
)
from .competency_mapper import (
    CompetencyMapper,
    CompetencyMapping,
    SkillExtraction,
    get_competency_mapper,
)
from .intent_analyzer import (
    IntentAnalyzer,
    IntentClassificationResult,
    IntentType,
    get_intent_analyzer,
)
from .trend_analyzer import CompetencyTrend, ProgressionMetrics, TrendAnalyzer, get_trend_analyzer

__all__ = [
    # Activity Classification
    "ActivityClassificationEngine",
    "ClassificationMethod",
    "ActivityClassificationResult",
    "get_activity_classifier",
    # Intent Analysis
    "IntentAnalyzer",
    "IntentType",
    "IntentClassificationResult",
    "get_intent_analyzer",
    # Competency Mapping
    "CompetencyMapper",
    "CompetencyMapping",
    "SkillExtraction",
    "get_competency_mapper",
    # Trend Analysis
    "TrendAnalyzer",
    "CompetencyTrend",
    "ProgressionMetrics",
    "get_trend_analyzer",
]
