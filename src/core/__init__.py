"""
ReflectAI Core Modules

This package contains the core business logic and AI processing capabilities
for the ReflectAI platform.

Version: 0.1.2-alpha
"""

__version__ = "0.1.2-alpha"

# Assessment Module (Production Ready - 85% tested)
from src.core.assessment.competency_assessor import (
    CompetencyAssessor,
    get_competency_assessor,
)
from src.core.assessment.gap_analyzer import GapAnalyzer, get_gap_analyzer
from src.core.assessment.level_calculator import (
    CompetencyLevel,  # Canonical 5-level enum
    LevelCalculator,
    get_level_calculator,
)
from src.core.llm.cost_tracker import CostTracker, get_cost_tracker

# LLM Gateway (Production Ready)
from src.core.llm.gateway import LLMGateway, get_llm_gateway

__all__ = [
    # Version
    "__version__",
    # Assessment
    "CompetencyAssessor",
    "get_competency_assessor",
    "GapAnalyzer",
    "get_gap_analyzer",
    "LevelCalculator",
    "get_level_calculator",
    "CompetencyLevel",
    # LLM
    "LLMGateway",
    "get_llm_gateway",
    "CostTracker",
    "get_cost_tracker",
]
