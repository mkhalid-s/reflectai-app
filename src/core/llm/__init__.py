"""
LLM Gateway and Provider Integration for ReflectAI

Implements Production
- LiteLLM Gateway for multi-provider support
- Guardrails AI for structured output validation
- Response caching with semantic similarity
- Cost optimization and monitoring

Provides unified interface for AI agents with provider failover,
cost tracking, and performance monitoring.
"""

from .cache import CacheStrategy, SemanticCache, get_semantic_cache
from .cost_tracker import CostTracker, get_cost_tracker
from .gateway import LLMGateway, LLMRequest, LLMResponse, get_llm_gateway
from .guardrails import AgentOutputSchema, GuardrailsValidator, get_guardrails_validator
from .oauth2_provider import (
    OAuth2FlowType,
    OAuth2Provider,
    get_llm_auth_headers,
    get_oauth_provider,
    register_custom_oauth_provider,
)
from .optimizer import get_batch_processor, get_model_selector
from .providers import ModelPricing, ModelTier, ProviderConfig, get_provider_manager

__all__ = [
    # Gateway core
    "LLMGateway",
    "LLMRequest",
    "LLMResponse",
    "get_llm_gateway",
    # Provider configuration
    "ProviderConfig",
    "ModelTier",
    "ModelPricing",
    "get_provider_manager",
    # Output validation
    "GuardrailsValidator",
    "AgentOutputSchema",
    "get_guardrails_validator",
    # Caching
    "SemanticCache",
    "CacheStrategy",
    "get_semantic_cache",
    # Cost tracking
    "CostTracker",
    "get_cost_tracker",
    # Optimization
    "get_model_selector",
    "get_batch_processor",
    # OAuth 2.0 Authentication
    "OAuth2Provider",
    "OAuth2FlowType",
    "get_oauth_provider",
    "get_llm_auth_headers",
    "register_custom_oauth_provider",
]
