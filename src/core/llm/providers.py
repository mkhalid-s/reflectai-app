"""
LLM Provider Configuration and Management

Implements provider-specific configurations, model tiers, and failover logic
for the LLM gateway system.
"""

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from src.shared import get_logger

from .cache import CacheStrategy
from .model_mapper import ModelProvider, ModelTier, get_model_mapper

logger = get_logger(__name__)


@dataclass
class ModelPricing:
    """Model pricing and performance characteristics."""

    input_cost_per_1k: float
    output_cost_per_1k: float
    max_response_time_s: int
    max_tokens: int
    context_window: int


@dataclass
class ProviderConfig:
    """LLM provider configuration."""

    name: str
    priority: int  # Lower number = higher priority
    models: dict[str, str]  # tier -> model_name mapping
    pricing: dict[str, ModelPricing]
    health_check_url: str | None = None
    api_key_secret: str = ""
    base_url: str | None = None

    def get_model_for_tier(self, tier: ModelTier) -> str | None:
        """Get model name for specified tier."""
        return self.models.get(tier.value)

    def get_pricing_for_model(self, model_name: str) -> ModelPricing | None:
        """Get pricing information for model."""
        return self.pricing.get(model_name)


class ProviderManager:
    """Manages LLM providers with health checking and failover."""

    def __init__(self):
        self.providers: list[ProviderConfig] = []
        self._provider_health: dict[str, bool] = {}
        self._last_health_check: dict[str, datetime] = {}
        self.health_check_interval = timedelta(minutes=5)
        self._secrets_manager = None
        self._initialized = False
        self._health_check_lock = asyncio.Lock()  # Prevent concurrent health checks

        # Redis-backed cache for provider health (optional)
        self._health_cache = None  # Lazy-initialized
        self._use_redis_cache = self._should_use_redis_cache()

        # Initialize providers synchronously with defaults
        self._initialize_providers_sync()

        logger.info(
            "Provider manager initialized",
            extra={
                "provider_count": len(self.providers),
                "redis_cache_enabled": self._use_redis_cache,
            },
        )

    def _should_use_redis_cache(self) -> bool:
        """Check if Redis cache should be used for provider health."""
        import os

        return os.getenv("PROVIDER_HEALTH_CACHE", "memory").lower() == "redis"

    async def _get_health_cache(self):
        """Get or initialize Redis health cache."""
        if not self._use_redis_cache:
            return None

        if self._health_cache is None:
            try:
                from .redis_cache_backend import get_redis_cache_backend

                self._health_cache = get_redis_cache_backend(
                    namespace="provider_health",
                    max_size=100,  # Small cache for provider health
                    enable_fallback=True,
                )
                logger.info("Redis provider health cache initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Redis health cache: {e}")
                self._use_redis_cache = False  # Disable for this instance
                return None

        return self._health_cache

    async def _get_health_from_cache(self, provider_name: str) -> bool | None:
        """Get provider health status from Redis cache."""
        cache = await self._get_health_cache()
        if not cache:
            return None

        try:
            # Use provider_name as query
            result = await cache.get(
                query=provider_name,
                context={"type": "provider_health"},
                strategy=CacheStrategy.DEFAULT,
            )

            if result:
                # Health status stored as metadata
                return result["metadata"].get("is_healthy")

        except Exception as e:
            logger.debug(f"Failed to get health from Redis cache: {e}")

        return None

    async def _set_health_in_cache(self, provider_name: str, is_healthy: bool):
        """Set provider health status in Redis cache."""
        cache = await self._get_health_cache()
        if not cache:
            return

        try:
            await cache.set(
                query=provider_name,
                response="",  # Not storing response content
                metadata={"is_healthy": is_healthy, "checked_at": datetime.now(UTC).isoformat()},
                context={"type": "provider_health"},
                intent="provider_health",
                tags=["provider", provider_name],
            )
        except Exception as e:
            logger.debug(f"Failed to set health in Redis cache: {e}")

    async def _get_secrets_manager(self):
        """Get or initialize secrets manager."""
        if self._secrets_manager is None:
            from infrastructure.config import get_secrets_manager as get_sm

            self._secrets_manager = get_sm()
        return self._secrets_manager

    def _initialize_providers_sync(self):
        """Initialize provider configurations synchronously with defaults."""
        # Initialize OpenAI provider with static configuration
        openai_config = self._create_openai_provider_config()

        # Initialize fallback Enterprise LLM Gateway provider
        enterprise_gateway_config = self._create_fallback_enterprise_gateway_provider_config()

        # Initialize fallback Bedrock provider
        bedrock_config = self._create_fallback_bedrock_provider_config()

        # Add providers in priority order
        self.providers = [openai_config, enterprise_gateway_config, bedrock_config]

        # Initialize health status
        for provider in self.providers:
            self._provider_health[provider.name] = True
            self._last_health_check[provider.name] = datetime.now(UTC)

    def _create_fallback_enterprise_gateway_provider_config(self) -> ProviderConfig:
        """Create fallback Enterprise LLM Gateway provider configuration."""
        return ProviderConfig(
            name="enterprise_gateway",
            priority=2,
            models={
                ModelTier.TIER_1.value: "gpt-4o-mini",
                ModelTier.TIER_2.value: "claude-3-5-haiku",
                ModelTier.TIER_3.value: "gpt-4o",
                ModelTier.TIER_4.value: "gpt-4o",
            },
            pricing={
                "gpt-4o-mini": ModelPricing(
                    input_cost_per_1k=0.15,
                    output_cost_per_1k=0.60,
                    max_response_time_s=3,
                    max_tokens=16000,
                    context_window=128000,
                ),
                "claude-3-5-haiku": ModelPricing(
                    input_cost_per_1k=0.25,
                    output_cost_per_1k=1.25,
                    max_response_time_s=5,
                    max_tokens=8000,
                    context_window=200000,
                ),
                "gpt-4o": ModelPricing(
                    input_cost_per_1k=2.50,
                    output_cost_per_1k=10.00,
                    max_response_time_s=8,
                    max_tokens=4000,
                    context_window=128000,
                ),
            },
            api_key_secret="LLM_GATEWAY_BASE_URL",
            base_url="https://localhost:8080",
            health_check_url="https://localhost:8080/health-check",
        )

    def _create_fallback_bedrock_provider_config(self) -> ProviderConfig:
        """Create fallback Bedrock provider configuration."""
        return ProviderConfig(
            name="bedrock",
            priority=3,
            models={
                ModelTier.TIER_1.value: "claude-3-5-haiku",
                ModelTier.TIER_2.value: "claude-3-5-sonnet",
                ModelTier.TIER_3.value: "claude-3-5-sonnet",
                ModelTier.TIER_4.value: "claude-3-opus",
            },
            pricing={
                "claude-3-5-haiku": ModelPricing(
                    input_cost_per_1k=0.25,
                    output_cost_per_1k=1.25,
                    max_response_time_s=5,
                    max_tokens=8000,
                    context_window=200000,
                ),
                "claude-3-5-sonnet": ModelPricing(
                    input_cost_per_1k=3.00,
                    output_cost_per_1k=15.00,
                    max_response_time_s=10,
                    max_tokens=8000,
                    context_window=200000,
                ),
                "claude-3-opus": ModelPricing(
                    input_cost_per_1k=15.00,
                    output_cost_per_1k=75.00,
                    max_response_time_s=15,
                    max_tokens=4000,
                    context_window=200000,
                ),
            },
            api_key_secret="AWS_BEDROCK_ACCESS_KEY",
            base_url="https://bedrock-runtime.us-east-1.amazonaws.com",
            health_check_url="https://bedrock-runtime.us-east-1.amazonaws.com",
        )

    async def _initialize_providers_async(self):
        """Initialize provider configurations asynchronously."""
        # Get secrets manager
        secrets_manager = await self._get_secrets_manager()

        # Initialize OpenAI provider with static configuration
        openai_config = self._create_openai_provider_config()

        # Initialize Enterprise LLM Gateway provider with dynamic configuration
        enterprise_gateway_config = await self._create_enterprise_gateway_provider_config(
            secrets_manager
        )

        # Initialize Bedrock provider with dynamic configuration
        bedrock_config = await self._create_bedrock_provider_config(secrets_manager)

        # Add providers in priority order
        self.providers = [openai_config, enterprise_gateway_config, bedrock_config]

        # Initialize health status
        for provider in self.providers:
            self._provider_health[provider.name] = True
            self._last_health_check[provider.name] = datetime.now(UTC)

    def _create_openai_provider_config(self) -> ProviderConfig:
        """Create OpenAI provider configuration."""
        return ProviderConfig(
            name="openai",
            priority=1,
            models={
                ModelTier.TIER_1.value: "gpt-4o-mini",
                ModelTier.TIER_3.value: "gpt-4o",
                ModelTier.TIER_4.value: "gpt-4o",
            },
            pricing={
                "gpt-4o-mini": ModelPricing(
                    input_cost_per_1k=0.15,
                    output_cost_per_1k=0.60,
                    max_response_time_s=3,
                    max_tokens=16000,
                    context_window=128000,
                ),
                "gpt-4o": ModelPricing(
                    input_cost_per_1k=2.50,
                    output_cost_per_1k=10.00,
                    max_response_time_s=8,
                    max_tokens=4000,
                    context_window=128000,
                ),
            },
            api_key_secret="OPENAI_API_KEY",
            health_check_url="https://api.openai.com/v1/models",
        )

    async def _create_enterprise_gateway_provider_config(self, secrets_manager) -> ProviderConfig:
        """Create Enterprise LLM Gateway provider configuration with dynamic model loading."""
        try:
            # Get Enterprise LLM Gateway secrets from config management
            enterprise_gateway_secrets = secrets_manager.get_enterprise_gateway_secrets()

            # Get model mapper and fetch available models
            model_mapper = get_model_mapper()

            # Create Enterprise LLM Gateway client with credentials from config
            from .enterprise_gateway_client import EnterpriseGatewayClient

            enterprise_gateway_client = EnterpriseGatewayClient(
                base_url=enterprise_gateway_secrets.get("base_url", ""),
                client_id=enterprise_gateway_secrets.get("client_id", ""),
                client_secret=enterprise_gateway_secrets.get("client_secret", ""),
                tenant=enterprise_gateway_secrets.get("tenant", "default"),
                star=enterprise_gateway_secrets.get("star", "default"),
                token_endpoint=enterprise_gateway_secrets.get("token_url"),
            )

            # Set the client in the model mapper
            model_mapper.enterprise_gateway_client = enterprise_gateway_client

            # Fetch available models
            model_infos = await model_mapper.fetch_available_models()

            # Create tier-based model mapping
            tier_models = model_mapper.get_models_by_tier()

            # Create pricing configuration based on available models
            pricing = self._create_enterprise_gateway_pricing(model_infos)

            return ProviderConfig(
                name="enterprise_gateway",
                priority=2,
                models={
                    ModelTier.TIER_1.value: tier_models.get(ModelTier.TIER_1.value, []),
                    ModelTier.TIER_2.value: tier_models.get(ModelTier.TIER_2.value, []),
                    ModelTier.TIER_3.value: tier_models.get(ModelTier.TIER_3.value, []),
                    ModelTier.TIER_4.value: tier_models.get(ModelTier.TIER_4.value, []),
                },
                pricing=pricing,
                api_key_secret="LLM_GATEWAY_BASE_URL",
                base_url=enterprise_gateway_secrets["base_url"],
                health_check_url=f"{enterprise_gateway_secrets['base_url']}/health-check",
            )

        except Exception as e:
            logger.error(
                "Failed to initialize Enterprise LLM Gateway provider",
                extra={"error": str(e)},
            )
            # Return fallback configuration
            return ProviderConfig(
                name="enterprise_gateway",
                priority=2,
                models={},  # Empty - will be populated later
                pricing={},
                api_key_secret="LLM_GATEWAY_BASE_URL",
                base_url="https://your-llm-gateway.example.com",
                health_check_url="https://your-llm-gateway.example.com/health-check",
            )

    async def _create_bedrock_provider_config(self, secrets_manager) -> ProviderConfig:
        """Create Bedrock provider config using enterprise gateway OAuth."""
        try:
            # Get Enterprise LLM Gateway secrets for Bedrock OAuth
            enterprise_gateway_secrets = secrets_manager.get_enterprise_gateway_secrets()

            # Create Enterprise LLM Gateway client for Bedrock models
            bedrock_client = self._create_bedrock_client(enterprise_gateway_secrets)

            # Get model mapper and set Bedrock client
            model_mapper = get_model_mapper()
            original_client = model_mapper.enterprise_gateway_client
            model_mapper.enterprise_gateway_client = bedrock_client

            try:
                # Fetch available models specifically for Bedrock
                model_infos = await model_mapper.fetch_available_models()

                # Filter only AWS/Bedrock models
                bedrock_models = []
                bedrock_pricing = {}

                for model_id, model_info in model_infos.items():
                    if model_info.provider == ModelProvider.AWS:
                        bedrock_models.append(model_id)
                        # Create pricing for Bedrock models
                        bedrock_pricing[model_id] = self._create_bedrock_pricing(model_info)

                # Create tier-based model mapping for Bedrock
                tier_models = model_mapper.get_models_by_tier()

                # Filter tier models to only include Bedrock models
                bedrock_tier_models = {}
                for tier, models in tier_models.items():
                    bedrock_models_in_tier = [
                        m
                        for m in models
                        if any(bedrock_model in m for bedrock_model in bedrock_models)
                    ]
                    if bedrock_models_in_tier:
                        bedrock_tier_models[tier] = bedrock_models_in_tier

                return ProviderConfig(
                    name="bedrock",
                    priority=3,
                    models=bedrock_tier_models,
                    pricing=bedrock_pricing,
                    api_key_secret="LLM_GATEWAY_BASE_URL",  # Uses Enterprise LLM Gateway OAuth
                    base_url=enterprise_gateway_secrets["base_url"],
                    health_check_url=f"{enterprise_gateway_secrets['base_url']}/health-check",
                )

            finally:
                # Restore original client
                model_mapper.enterprise_gateway_client = original_client

        except Exception as e:
            logger.error(
                "Failed to initialize Bedrock provider via Enterprise LLM Gateway",
                extra={"error": str(e)},
            )
            # Return fallback configuration
            return ProviderConfig(
                name="bedrock",
                priority=3,
                models={},  # Empty - will be populated later
                pricing={},
                api_key_secret="LLM_GATEWAY_BASE_URL",
                base_url="https://your-llm-gateway.example.com",
                health_check_url="https://your-llm-gateway.example.com/health-check",
            )

    def _create_bedrock_client(self, secrets: dict[str, str]):
        """Create Enterprise LLM Gateway client specifically for Bedrock models."""
        from .enterprise_gateway_client import EnterpriseGatewayClient

        # Create client with Bedrock-specific tenant/star configuration
        return EnterpriseGatewayClient(
            base_url=secrets["base_url"],
            client_id=secrets["client_id"],
            client_secret=secrets["client_secret"],
            token_endpoint=secrets.get("token_url"),
            tenant=secrets.get("tenant", "default"),
            star=secrets.get("star", "default"),
        )

    def _create_bedrock_pricing(self, model_info) -> ModelPricing:
        """Create pricing configuration for Bedrock models."""
        # AWS Bedrock pricing - more specific pricing based on model family
        if "nova-micro" in model_info.id:
            return ModelPricing(
                input_cost_per_1k=0.15,
                output_cost_per_1k=0.60,
                max_response_time_s=3,
                max_tokens=16000,
                context_window=model_info.context_window,
            )
        elif "nova-lite" in model_info.id:
            return ModelPricing(
                input_cost_per_1k=0.25,
                output_cost_per_1k=1.25,
                max_response_time_s=5,
                max_tokens=8000,
                context_window=model_info.context_window,
            )
        elif "nova-pro" in model_info.id or "nova-premier" in model_info.id:
            return ModelPricing(
                input_cost_per_1k=2.50,
                output_cost_per_1k=10.00,
                max_response_time_s=8,
                max_tokens=4000,
                context_window=model_info.context_window,
            )
        elif "claude" in model_info.id:
            # Anthropic models via Bedrock
            if "haiku" in model_info.id:
                return ModelPricing(
                    input_cost_per_1k=0.25,
                    output_cost_per_1k=1.25,
                    max_response_time_s=5,
                    max_tokens=8000,
                    context_window=model_info.context_window,
                )
            else:  # sonnet, opus
                return ModelPricing(
                    input_cost_per_1k=3.00,
                    output_cost_per_1k=15.00,
                    max_response_time_s=10,
                    max_tokens=8000,
                    context_window=model_info.context_window,
                )
        else:
            # Default Bedrock pricing for other models
            return ModelPricing(
                input_cost_per_1k=0.25,
                output_cost_per_1k=1.25,
                max_response_time_s=6,
                max_tokens=8000,
                context_window=model_info.context_window,
            )

    def _create_enterprise_gateway_pricing(
        self, model_infos: dict[str, Any]
    ) -> dict[str, ModelPricing]:
        """Create pricing configuration for Enterprise LLM Gateway models."""
        pricing = {}

        for model_id, model_info in model_infos.items():
            # Base pricing on model provider and family
            if model_info.provider == ModelProvider.AWS:
                # AWS Bedrock pricing
                if "nova-micro" in model_id:
                    pricing[model_id] = ModelPricing(
                        input_cost_per_1k=0.15,
                        output_cost_per_1k=0.60,
                        max_response_time_s=3,
                        max_tokens=16000,
                        context_window=model_info.context_window,
                    )
                elif "nova-lite" in model_id:
                    pricing[model_id] = ModelPricing(
                        input_cost_per_1k=0.25,
                        output_cost_per_1k=1.25,
                        max_response_time_s=5,
                        max_tokens=8000,
                        context_window=model_info.context_window,
                    )
                else:  # nova-pro, nova-premier
                    pricing[model_id] = ModelPricing(
                        input_cost_per_1k=2.50,
                        output_cost_per_1k=10.00,
                        max_response_time_s=8,
                        max_tokens=4000,
                        context_window=model_info.context_window,
                    )

            elif model_info.provider == ModelProvider.ANTHROPIC:
                # Anthropic pricing
                if "haiku" in model_id:
                    pricing[model_id] = ModelPricing(
                        input_cost_per_1k=0.25,
                        output_cost_per_1k=1.25,
                        max_response_time_s=5,
                        max_tokens=8000,
                        context_window=model_info.context_window,
                    )
                else:  # sonnet, opus
                    pricing[model_id] = ModelPricing(
                        input_cost_per_1k=3.00,
                        output_cost_per_1k=15.00,
                        max_response_time_s=10,
                        max_tokens=8000,
                        context_window=model_info.context_window,
                    )

            elif model_info.provider == ModelProvider.META:
                # Meta pricing (estimated)
                if "8b" in model_id or "1b" in model_id or "3b" in model_id:
                    pricing[model_id] = ModelPricing(
                        input_cost_per_1k=0.10,
                        output_cost_per_1k=0.30,
                        max_response_time_s=3,
                        max_tokens=8000,
                        context_window=model_info.context_window,
                    )
                else:  # 70b, 90b, 405b models
                    pricing[model_id] = ModelPricing(
                        input_cost_per_1k=0.50,
                        output_cost_per_1k=2.00,
                        max_response_time_s=6,
                        max_tokens=8000,
                        context_window=model_info.context_window,
                    )

            elif model_info.provider == ModelProvider.OPENAI:
                # OpenAI pricing
                if "gpt-4o-mini" in model_id:
                    pricing[model_id] = ModelPricing(
                        input_cost_per_1k=0.15,
                        output_cost_per_1k=0.60,
                        max_response_time_s=3,
                        max_tokens=16000,
                        context_window=model_info.context_window,
                    )
                elif "gpt-4o" in model_id:
                    pricing[model_id] = ModelPricing(
                        input_cost_per_1k=2.50,
                        output_cost_per_1k=10.00,
                        max_response_time_s=8,
                        max_tokens=4000,
                        context_window=model_info.context_window,
                    )
                else:
                    # Default pricing for other OpenAI models
                    pricing[model_id] = ModelPricing(
                        input_cost_per_1k=2.50,
                        output_cost_per_1k=10.00,
                        max_response_time_s=8,
                        max_tokens=4000,
                        context_window=model_info.context_window,
                    )

        return pricing

    async def get_provider_for_tier(
        self, tier: ModelTier, exclude_unhealthy: bool = True
    ) -> ProviderConfig | None:
        """
        Get the best available provider for specified model tier.

        Args:
            tier: Model tier needed
            exclude_unhealthy: Skip unhealthy providers

        Returns:
            Provider configuration or None if none available
        """
        # Sort providers by priority
        sorted_providers = sorted(self.providers, key=lambda p: p.priority)

        for provider in sorted_providers:
            # Skip if provider doesn't support this tier
            if tier.value not in provider.models:
                continue

            # Skip if provider is unhealthy (optional)
            if exclude_unhealthy and not await self._is_provider_healthy(provider.name):
                continue

            return provider

        # If no healthy provider found and we excluded unhealthy ones, try again without exclusion
        if exclude_unhealthy:
            logger.warning(
                f"No healthy providers found for tier {tier.value}, trying all providers"
            )
            return await self.get_provider_for_tier(tier, exclude_unhealthy=False)

        return None

    async def get_model_for_tier(
        self, tier: ModelTier, exclude_unhealthy: bool = True
    ) -> tuple[str, ProviderConfig] | None:
        """
        Get model name and provider config for specified tier.

        Args:
            tier: Model tier to get provider for
            exclude_unhealthy: Skip unhealthy providers

        Returns:
            Tuple of (model_name, provider_config) or None
        """
        provider = await self.get_provider_for_tier(tier, exclude_unhealthy=exclude_unhealthy)
        if not provider:
            return None

        model_name = provider.get_model_for_tier(tier)
        if not model_name:
            return None

        return model_name, provider

    async def _is_provider_healthy(self, provider_name: str) -> bool:
        """Check if provider is healthy (with caching) - async version."""
        # Quick check of in-memory cache outside lock (optimization)
        last_check = self._last_health_check.get(provider_name)
        if last_check and datetime.now(UTC) - last_check < self.health_check_interval:
            return self._provider_health.get(provider_name, False)

        # Perform actual health check with locking to prevent concurrent checks
        async with self._health_check_lock:
            # Double-check Redis cache after acquiring lock (prevents redundant checks)
            if self._use_redis_cache:
                cached_health = await self._get_health_from_cache(provider_name)
                if cached_health is not None:
                    logger.debug(
                        f"Provider {provider_name} health from Redis: {cached_health}"
                    )
                    # Update in-memory cache from Redis
                    self._provider_health[provider_name] = cached_health
                    self._last_health_check[provider_name] = datetime.now(UTC)
                    return cached_health

            # Double-check in-memory cache after acquiring lock
            last_check = self._last_health_check.get(provider_name)
            if last_check and datetime.now(UTC) - last_check < self.health_check_interval:
                return self._provider_health.get(provider_name, False)

            try:
                # Run async health check with timeout
                is_healthy = await asyncio.wait_for(
                    self._check_provider_health_async(provider_name),
                    timeout=5.0,  # 5 second timeout
                )

                # Update in-memory cache
                self._provider_health[provider_name] = is_healthy
                self._last_health_check[provider_name] = datetime.now(UTC)

                # Update Redis cache if enabled
                if self._use_redis_cache:
                    await self._set_health_in_cache(provider_name, is_healthy)

                return is_healthy
            except TimeoutError:
                logger.warning(f"Health check timed out for {provider_name}")
                is_healthy = False
                self._provider_health[provider_name] = is_healthy
                self._last_health_check[provider_name] = datetime.now(UTC)

                if self._use_redis_cache:
                    await self._set_health_in_cache(provider_name, is_healthy)

                return False
            except Exception as e:
                logger.warning(f"Health check failed for {provider_name}: {str(e)}")
                is_healthy = False
                self._provider_health[provider_name] = is_healthy
                self._last_health_check[provider_name] = datetime.now(UTC)

                if self._use_redis_cache:
                    await self._set_health_in_cache(provider_name, is_healthy)

                return False

    async def _check_provider_health_async(self, provider_name: str) -> bool:
        """Perform actual health check for a provider."""
        try:
            provider = next((p for p in self.providers if p.name == provider_name), None)
            if not provider:
                return False

            # If provider has a health check URL, test it
            if provider.health_check_url:
                import aiohttp

                timeout = aiohttp.ClientTimeout(total=5)  # 5 second timeout
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    try:
                        # Get auth headers if needed
                        headers = {}
                        if provider.name in ["openai", "enterprise_gateway"]:
                            api_key = await self._get_api_key(provider.api_key_secret)
                            if api_key:
                                headers["Authorization"] = f"Bearer {api_key}"

                        async with session.get(
                            provider.health_check_url, headers=headers
                        ) as response:
                            # Consider 200-299 status codes as healthy
                            is_healthy = 200 <= response.status < 300

                            if is_healthy:
                                logger.debug(f"Provider {provider_name} health check passed")
                            else:
                                logger.warning(
                                    "Provider "
                                    f"{provider_name} health check failed with status "
                                    f"{response.status}"
                                )

                            return is_healthy

                    except TimeoutError:
                        logger.warning(f"Provider {provider_name} health check timed out")
                        return False
                    except Exception as e:
                        logger.warning(f"Provider {provider_name} health check error: {str(e)}")
                        return False
            else:
                # If no health check URL, check if we can get API credentials
                api_key = await self._get_api_key(provider.api_key_secret)
                return bool(api_key)

        except Exception as e:
            logger.error(f"Health check failed for provider {provider_name}: {str(e)}")
            return False

    async def _get_api_key(self, secret_name: str) -> str | None:
        """Get API key from secrets manager."""
        try:
            if not self._secrets_manager:
                from src.infrastructure.config import get_secrets_manager

                self._secrets_manager = get_secrets_manager()

            secret = await self._secrets_manager.get_secret(secret_name)
            return secret if secret else None
        except Exception:
            return None

    def mark_provider_unhealthy(self, provider_name: str):
        """Mark a provider as unhealthy (for failover)."""
        logger.warning(f"Marking provider {provider_name} as unhealthy")
        self._provider_health[provider_name] = False
        self._last_health_check[provider_name] = datetime.now(UTC)

    def get_all_providers(self) -> list[ProviderConfig]:
        """Get all configured providers."""
        return self.providers.copy()

    async def get_provider_health_status(self) -> dict[str, Any]:
        """Get health status of all providers."""
        # Check health for all providers concurrently
        provider_names = [p.name for p in self.providers]
        health_checks = await asyncio.gather(
            *[self._is_provider_healthy(name) for name in provider_names], return_exceptions=True
        )

        # Build status dictionary
        providers_status = {}
        healthy_count = 0

        for name, is_healthy in zip(provider_names, health_checks, strict=False):
            # Handle exceptions from gather
            if isinstance(is_healthy, Exception):
                is_healthy = False
                logger.error(f"Error checking health for {name}: {is_healthy}")

            if is_healthy:
                healthy_count += 1

            providers_status[name] = {
                "healthy": is_healthy,
                "last_check": self._last_health_check.get(name),
                "priority": next((p.priority for p in self.providers if p.name == name), None),
            }

        return {
            "providers": providers_status,
            "total_providers": len(self.providers),
            "healthy_providers": healthy_count,
        }


# Global provider manager instance
_provider_manager: ProviderManager | None = None


def get_provider_manager() -> ProviderManager:
    """Get or create global provider manager instance."""
    global _provider_manager
    if _provider_manager is None:
        _provider_manager = ProviderManager()
    return _provider_manager
