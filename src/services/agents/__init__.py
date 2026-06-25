"""
AI Agents for ReflectAI - Phase 1 Simplified Architecture

Provides combined agents for efficient analysis and advisory services.
Phase 1 simplification: 5 agents → 2 combined agents + chat responder
"""

from .advisor_agent import AdvisorAgent  # Combined career strategy + insight synthesis
from .analysis_agent import AnalysisAgent  # Combined data analysis + competency assessment
from .base import AgentRequest, AgentResponse, AgentRole, BaseAgent
from .chat_responder import ChatResponderAgent
from .registry import AgentRegistry, get_agent_registry

__all__ = [
    # Base classes
    "BaseAgent",
    "AgentResponse",
    "AgentRequest",
    "AgentRole",
    # Combined Agents (Phase 1)
    "AnalysisAgent",  # Replaces DataAnalystAgent + CompetencySpecialistAgent
    "AdvisorAgent",  # Replaces CareerStrategistAgent + InsightSynthesizerAgent
    "ChatResponderAgent",
    # Registry
    "AgentRegistry",
    "get_agent_registry",
]
