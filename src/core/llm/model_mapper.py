"""
Dynamic Model Mapping for Enterprise LLM Gateway

This module provides intelligent mapping of Enterprise LLM Gateway models to our tier system
based on the actual models available from the gateway.
"""

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from src.shared import get_logger

logger = get_logger(__name__)


class ModelProvider(str, Enum):
    """Model providers supported by the system."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AWS = "aws"
    META = "meta"
    GOOGLE = "google"
    COHERE = "cohere"
    LLM_GATEWAY = "enterprise_gateway"


# Mock EnterpriseGatewayClient removed - migrated to src.core.llm.enterprise_gateway_client
# See src/core/llm/enterprise_gateway_client.py for the production implementation


class ModelTier(str, Enum):
    """Model tiers for cost-effective routing based on Task 13 specifications."""

    TIER_1 = "tier_1"  # Data Analyst: fast model
    TIER_2 = "tier_2"  # Competency Specialist: balanced model
    TIER_3 = "tier_3"  # Career Strategist: advanced model
    TIER_4 = "tier_4"  # Insight Synthesizer: Enterprise LLM Gateway - Premium model


@dataclass
class ModelInfo:
    """Information about a model available through Enterprise LLM Gateway."""

    id: str
    provider: ModelProvider
    family: str  # e.g., "nova", "claude", "llama", "gpt"
    model_name: str  # e.g., "nova-micro", "claude-3-5-sonnet", "llama3-8b"
    context_window: int
    tier_score: int  # Higher score = better model for complex tasks
    cost_efficiency: float  # Cost per token efficiency
    is_available: bool = True


class ModelMapper:
    """
    Maps Enterprise LLM Gateway models to our tier system dynamically.

    This class fetches available models from Enterprise LLM Gateway and creates
    intelligent mappings based on model capabilities and pricing.
    """

    def __init__(self, enterprise_gateway_client: Any | None = None):
        """Initialize model mapper with an optional enterprise gateway client."""
        self.enterprise_gateway_client = enterprise_gateway_client
        self._model_cache: dict[str, ModelInfo] = {}
        self._tier_cache: dict[str, list[str]] = {}
        self._cache_expires_at: datetime | None = None
        self._cache_ttl = timedelta(minutes=15)  # Cache for 15 minutes

    async def _ensure_enterprise_gateway_client(self):
        """Ensure we have an Enterprise LLM Gateway client."""
        if self.enterprise_gateway_client is None:
            from .enterprise_gateway_client import EnterpriseGatewayClient

            self.enterprise_gateway_client = EnterpriseGatewayClient(
                base_url="https://your-llm-gateway.example.com",
                client_id="your_client_id",
                client_secret="your_client_secret",
                token_endpoint="https://your-llm-gateway.example.com/oauth/token",
            )
        return self.enterprise_gateway_client

    def _parse_model_id(self, model_id: str) -> tuple[ModelProvider, str, str]:
        """Parse model ID to extract provider, family, and model name."""
        # AWS Bedrock models
        if model_id.startswith("amazon."):
            parts = model_id.split(".")
            if len(parts) >= 3:
                family = parts[1]  # e.g., "nova"
                model_name = parts[2].split("-")[0]  # e.g., "micro", "pro", "lite"
                return ModelProvider.AWS, family, model_name

        # Anthropic models
        elif model_id.startswith("anthropic."):
            parts = model_id.split(".")
            if len(parts) >= 2:
                family = "claude"
                model_name = parts[1].split("-")[0]  # e.g., "claude-3-5-sonnet" -> "claude"
                return ModelProvider.ANTHROPIC, family, model_name

        # Meta models
        elif model_id.startswith("meta."):
            parts = model_id.split(".")
            if len(parts) >= 2:
                family = "llama"
                model_name = parts[1].split("-")[0]  # e.g., "llama3-8b" -> "llama3"
                return ModelProvider.META, family, model_name

        # OpenAI models
        elif any(
            prefix in model_id
            for prefix in ["gpt-", "davinci", "babbage", "codex", "o1-", "o3-", "o4-"]
        ):
            family = "gpt"
            model_name = model_id.split("-")[0]  # e.g., "gpt-4o-mini" -> "gpt"
            return ModelProvider.OPENAI, family, model_name

        # Default fallback
        return ModelProvider.OPENAI, "unknown", model_id

    def _calculate_tier_score(self, provider: ModelProvider, family: str, model_name: str) -> int:
        """Calculate tier score for model routing."""
        base_score = 0

        # Provider scoring
        if provider == ModelProvider.OPENAI:
            base_score += 10
        elif provider == ModelProvider.ANTHROPIC:
            base_score += 8
        elif provider == ModelProvider.AWS:
            base_score += 7
        elif provider == ModelProvider.META:
            base_score += 6

        # Model-specific adjustments
        if "gpt-4o" in model_name or "claude-3-5" in model_name or "nova-pro" in model_name:
            base_score += 5  # Advanced models
        elif "gpt-4" in model_name or "claude-3" in model_name or "nova-lite" in model_name:
            base_score += 3  # Good models
        elif "gpt-3.5" in model_name or "claude-haiku" in model_name or "nova-micro" in model_name:
            base_score += 1  # Basic models
        elif "o1" in model_name or "opus" in model_name:
            base_score += 7  # Reasoning models

        return base_score

    def _estimate_context_window(self, model_id: str) -> int:
        """Estimate context window based on model ID."""
        # AWS Bedrock models
        if "amazon.nova" in model_id:
            if "micro" in model_id:
                return 128000
            elif "lite" in model_id:
                return 300000
            else:
                return 1000000  # Pro and Premier

        # Anthropic models
        elif "claude" in model_id:
            if "haiku" in model_id:
                return 200000
            else:
                return 200000  # Sonnet and Opus models

        # Meta models
        elif "llama" in model_id:
            if "70b" in model_id or "405b" in model_id:
                return 128000
            else:
                return 8000  # Smaller models

        # OpenAI models
        else:
            if "gpt-4o" in model_id or "gpt-4" in model_id:
                return 128000
            elif "gpt-3.5" in model_id:
                return 16000
            elif "o1" in model_id:
                return 200000
            else:
                return 8000  # Default

    async def fetch_available_models(self) -> dict[str, ModelInfo]:
        """
        Fetch available models from Enterprise LLM Gateway and cache them.

        Returns:
            Dictionary mapping model IDs to ModelInfo objects
        """
        # Check cache first
        now = datetime.now(UTC)
        if self._model_cache and self._cache_expires_at and now < self._cache_expires_at:
            return self._model_cache

        try:
            client = await self._ensure_enterprise_gateway_client()
            async with client:
                models_response = await client.get_available_models()

                # Parse models from response
                models_data = models_response.get("data", [])
                model_infos: dict[str, ModelInfo] = {}

                for model_data in models_data:
                    model_id = model_data["id"]
                    provider, family, model_name = self._parse_model_id(model_id)

                    model_info = ModelInfo(
                        id=model_id,
                        provider=provider,
                        family=family,
                        model_name=model_name,
                        context_window=self._estimate_context_window(model_id),
                        tier_score=self._calculate_tier_score(provider, family, model_name),
                        cost_efficiency=1.0,  # Default, can be updated with real pricing
                        is_available=True,
                    )

                    model_infos[model_id] = model_info

                # Cache the results
                self._model_cache = model_infos
                self._cache_expires_at = now + self._cache_ttl

                logger.info(
                    "Fetched available models from Enterprise LLM Gateway",
                    extra={
                        "model_count": len(model_infos),
                        "providers": list({m.provider.value for m in model_infos.values()}),
                    },
                )

                return model_infos

        except Exception as e:
            logger.error(
                "Failed to fetch models from Enterprise LLM Gateway",
                extra={"error": str(e)},
            )
            # Return cached models if available, empty dict otherwise
            return self._model_cache or {}

    def get_models_by_tier(self) -> dict[str, list[str]]:
        """
        Get models grouped by tier.

        Returns:
            Dictionary mapping tier names to lists of model IDs
        """
        if not self._model_cache:
            # Trigger async fetch (but don't wait for it)
            asyncio.create_task(self.fetch_available_models())

        if self._tier_cache:
            return self._tier_cache

        # Create tier mapping based on available models
        tiers = {
            "tier_1": [],  # Fast, cost-effective models
            "tier_2": [],  # Balanced performance/cost
            "tier_3": [],  # High performance
            "tier_4": [],  # Premium/experimental models
        }

        for model_id, model_info in self._model_cache.items():
            if model_info.tier_score <= 10:
                tiers["tier_1"].append(model_id)
            elif model_info.tier_score <= 15:
                tiers["tier_2"].append(model_id)
            elif model_info.tier_score <= 20:
                tiers["tier_3"].append(model_id)
            else:
                tiers["tier_4"].append(model_id)

        # Sort by tier score within each tier
        for tier in tiers:
            tiers[tier].sort(
                key=lambda m: self._model_cache.get(
                    m, ModelInfo("", ModelProvider.OPENAI, "", "", 0, 0, 1.0)
                ).tier_score,
                reverse=True,
            )

        self._tier_cache = tiers
        return tiers

    def get_best_model_for_tier(self, tier: str) -> str | None:
        """
        Get the best available model for a specific tier.

        Args:
            tier: Tier name (tier_1, tier_2, tier_3, tier_4)

        Returns:
            Best model ID for the tier, or None if no models available
        """
        tiers = self.get_models_by_tier()
        models = tiers.get(tier, [])
        return models[0] if models else None

    def get_all_available_models(self) -> list[str]:
        """
        Get all available model IDs.

        Returns:
            List of all available model IDs
        """
        return list(self._model_cache.keys())

    def get_models_by_provider(self, provider: ModelProvider) -> list[str]:
        """
        Get models from a specific provider.

        Args:
            provider: Provider to filter by

        Returns:
            List of model IDs from the specified provider
        """
        return [
            model_id
            for model_id, model_info in self._model_cache.items()
            if model_info.provider == provider
        ]

    def invalidate_cache(self):
        """Invalidate the model cache."""
        self._model_cache = {}
        self._tier_cache = {}
        self._cache_expires_at = None
        logger.info("Model cache invalidated")


# Global model mapper instance
_model_mapper: ModelMapper | None = None


def get_model_mapper() -> ModelMapper:
    """Get or create global model mapper instance."""
    global _model_mapper
    if _model_mapper is None:
        _model_mapper = ModelMapper()
    return _model_mapper


async def refresh_model_cache():
    """Refresh the global model cache."""
    mapper = get_model_mapper()
    await mapper.fetch_available_models()
    logger.info("Global model cache refreshed")
