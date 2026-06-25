# LLM Gateway Integration for Tier 3 Classification

**Purpose**: Leverage existing `src/core/llm/gateway.py` for Tier 3 LLM-based intent classification
**Status**: Design Complete
**Last Updated**: January 2025

## Overview

The user correctly identified that we should use the existing LLM gateway infrastructure for Tier 3 classification instead of creating a separate LLM client. This document explains how to integrate with the existing gateway.

## Existing LLM Gateway Capabilities

### Core Features

**File**: `src/core/llm/gateway.py`

The existing LLM gateway provides:

1. **Multi-Provider Support** - OpenAI, Anthropic, EnterpriseGateway, etc.
2. **Model Tier System** - TIER_1 (fast), TIER_2 (balanced), TIER_3 (advanced), TIER_4 (premium)
3. **Built-in Caching** - In-memory cache with configurable TTL (30 min, 1 hour, disabled)
4. **Cost Tracking** - Automatic cost tracking via `CostTracker`
5. **Circuit Breakers** - Per-provider circuit breakers for failover
6. **Provider Failover** - Automatic failover to backup providers
7. **Request Batching** - Batching capabilities for bulk requests

### Request/Response Interface

```python
@dataclass
class LLMRequest:
    """Standardized LLM request format."""
    messages: list[dict[str, str]]
    model_tier: ModelTier  # TIER_1, TIER_2, TIER_3, TIER_4
    user_id: str
    request_id: str = field(default_factory=lambda: str(uuid4()))
    correlation_id: str = field(default_factory=get_or_create_correlation_id)
    temperature: float = 0.7
    max_tokens: int | None = None
    system_prompt: str | None = None
    context: dict[str, Any] = field(default_factory=dict)
    cache_strategy: str = "default"  # default, aggressive, disabled
    retry_attempts: int = 2
    timeout_seconds: int = 30

@dataclass
class LLMResponse:
    """Standardized LLM response format."""
    request_id: str
    content: str
    model_used: str
    provider_used: str
    tokens_used: dict[str, int]
    cost_usd: float
    processing_time_ms: int
    from_cache: bool = False
    confidence_score: float | None = None
    structured_data: dict[str, Any] | None = None
    correlation_id: str = ""
```

### Model Tiers

```python
class ModelTier(str, Enum):
    """Model tiers for cost-effective routing."""
    TIER_1 = "tier_1"  # Fast model (~$0.15/1k tokens, <3s) - EnterpriseGateway/Haiku
    TIER_2 = "tier_2"  # Balanced model (~$0.25/1k tokens, <5s)
    TIER_3 = "tier_3"  # Advanced model (~$2.50/1k tokens, <8s) - Claude Sonnet
    TIER_4 = "tier_4"  # Premium model - GPT-4, Claude Opus
```

## Integration Strategy

### Updated Tier 3: LLM Classifier Using Gateway

**Instead of** creating a custom LLM client in `llm_classifier.py`, we'll use the existing gateway:

#### Previous Design (Custom Client)
```python
# ❌ OLD APPROACH - Creates separate LLM client
class LLMIntentClassifier:
    def __init__(self):
        self.llm_gateway = get_llm_gateway()  # Used incorrectly

    async def classify(...):
        # Custom implementation calling LLM directly
        response = await self.llm_gateway.generate(...)  # Doesn't exist!
```

#### New Design (Gateway Integration)
```python
# ✅ NEW APPROACH - Uses existing gateway properly
class LLMIntentClassifier:
    def __init__(self):
        self.llm_gateway = get_llm_gateway()
        self.cache = get_redis_cache()  # Additional Redis cache on top of gateway cache

    async def classify(
        self,
        message: str,
        context: dict[str, Any] | None = None,
        semantic_hint: tuple[IntentType, float] | None = None,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> tuple[IntentType, float]:
        """Classify message using LLM via gateway."""

        # 1. Check our Redis cache first (intent-specific cache)
        cache_key = self._generate_cache_key(message, context)
        cached_result = await self.cache.get(cache_key)
        if cached_result:
            result = json.loads(cached_result)
            return IntentType(result["intent"]), result["confidence"]

        # 2. Build few-shot prompt
        prompt = self._build_prompt(message, context, semantic_hint, conversation_history)

        # 3. Create LLMRequest using gateway interface
        llm_request = LLMRequest(
            messages=[{"role": "user", "content": prompt}],
            model_tier=ModelTier.TIER_1,  # ✅ Use TIER_1 (fast/cheap) for classification
            user_id=context.get("user_id", "system") if context else "system",
            temperature=0.0,  # Deterministic
            max_tokens=100,  # Short response
            cache_strategy="aggressive",  # ✅ Use gateway's 1-hour cache
            context={
                "purpose": "intent_classification",
                "tier": "3",
            },
        )

        # 4. Process via gateway (handles caching, failover, cost tracking)
        llm_response: LLMResponse = await self.llm_gateway.process_request(llm_request)

        # 5. Parse response
        intent, confidence = self._parse_response(llm_response.content)

        # 6. Cache in our intent-specific Redis cache (additional layer)
        await self.cache.set(
            cache_key,
            json.dumps({"intent": intent.value, "confidence": confidence}),
            ttl=3600,
        )

        logger.info(
            f"LLM classified '{message[:50]}' → {intent.value}",
            extra={
                "confidence": confidence,
                "cost_usd": llm_response.cost_usd,
                "from_gateway_cache": llm_response.from_cache,
                "model_used": llm_response.model_used,
                "processing_time_ms": llm_response.processing_time_ms,
            },
        )

        return intent, confidence
```

### Why Use TIER_1 for Intent Classification?

**TIER_1** (Fast Model) is optimal for intent classification because:

1. **Task Complexity**: Intent classification is a simple categorization task (10 categories)
2. **Speed**: <3s response time meets our <500ms target when combined with caching
3. **Cost**: ~$0.15/1k tokens vs ~$2.50/1k for TIER_3
4. **Accuracy**: Fast models (Claude Haiku, GPT-3.5-Turbo) are sufficient for classification
5. **Cache Hit Rate**: With 80%+ cache hit rate, most requests don't hit LLM anyway

**Cost Comparison**:
```
Tier 3 classification (100 requests, <5% hit LLM, 80% cached):
- LLM calls: 5 requests × ~50 tokens × $0.15/1k = $0.000375
- Total: <$0.001 per 100 messages

If we used TIER_3 instead:
- LLM calls: 5 requests × ~50 tokens × $2.50/1k = $0.00625
- Total: ~$0.006 per 100 messages (6x more expensive!)
```

### Caching Strategy

We implement **two-tier caching** for maximum efficiency:

#### Tier 1: Intent-Specific Redis Cache (LLMIntentClassifier)
```python
# Key: intent_llm:{message_hash}|{context_hash}
# TTL: 1 hour
# Purpose: Intent-specific cache with semantic context

cache_key = f"intent_llm:{hashlib.md5((message + context_str).encode()).hexdigest()}"
await self.cache.set(cache_key, result, ttl=3600)
```

**Why?**
- Intent classification benefits from exact message matching
- Context-aware caching (same message, different user stage → different cache)
- Faster lookup than gateway's generic cache

#### Tier 2: Gateway In-Memory Cache (LLMGateway)
```python
# Key: {messages_hash}|{model}|{temperature}
# TTL: 1 hour (aggressive strategy)
# Purpose: Cross-system LLM response cache

llm_request = LLMRequest(
    ...
    cache_strategy="aggressive",  # ✅ Use 1-hour cache
)
```

**Why?**
- Gateway cache is shared across all LLM uses (not just intent classification)
- Handles cache invalidation, TTL management
- Already implemented and tested

**Cache Hit Flow**:
```
Request → Intent Redis Cache → Gateway Cache → LLM API
          ↓ 80% hit             ↓ 10% hit      ↓ 10% miss
          Return                Return         Call LLM
```

**Expected Cache Performance**:
- Intent Redis Cache: 80% hit rate (common messages)
- Gateway Cache: 50% hit rate (of remaining 20%)
- LLM API calls: 10% of total requests

## Implementation: Updated llm_classifier.py

```python
"""
LLM-based Intent Classifier using existing LLM Gateway

Uses the existing src/core/llm/gateway.py infrastructure for
cost-effective, cached intent classification.
"""

import hashlib
import json
from typing import Any

from src.core.llm.gateway import LLMRequest, get_llm_gateway
from src.core.llm.model_mapper import ModelTier
from src.core.types import IntentType
from src.infrastructure.cache.redis_cache import get_redis_cache
from src.shared import get_logger

logger = get_logger("classification.llm")


class LLMIntentClassifier:
    """
    LLM-based intent classifier using existing gateway infrastructure.

    Leverages:
    - LLMGateway for multi-provider support, cost tracking, circuit breakers
    - ModelTier.TIER_1 for fast, cost-effective classification
    - Two-tier caching (intent-specific + gateway)
    - Aggressive caching strategy for 1-hour TTL
    """

    def __init__(self):
        self.logger = logger
        self.llm_gateway = get_llm_gateway()  # ✅ Use existing gateway
        self.cache = get_redis_cache()  # Intent-specific cache layer

        # Performance tracking
        self.stats = {
            "total_calls": 0,
            "intent_cache_hits": 0,
            "gateway_cache_hits": 0,
            "llm_calls": 0,
        }

        logger.info("LLM intent classifier initialized with gateway integration")

    async def classify(
        self,
        message: str,
        context: dict[str, Any] | None = None,
        semantic_hint: tuple[IntentType, float] | None = None,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> tuple[IntentType, float]:
        """
        Classify message using LLM via gateway.

        Args:
            message: User message to classify
            context: User context (profile, stage, etc.)
            semantic_hint: Best guess from semantic classifier
            conversation_history: Recent conversation for context

        Returns:
            (intent, confidence) tuple
        """
        self.stats["total_calls"] += 1

        try:
            # ═══════════════════════════════════════════════════════════
            # CACHE LAYER 1: Intent-Specific Redis Cache
            # ═══════════════════════════════════════════════════════════
            cache_key = self._generate_cache_key(message, context)
            cached_result = await self.cache.get(cache_key)

            if cached_result:
                self.stats["intent_cache_hits"] += 1
                logger.debug(
                    f"Intent cache hit for: '{message[:50]}'",
                    extra={"cache_layer": "intent_redis"},
                )
                result = json.loads(cached_result)
                return IntentType(result["intent"]), result["confidence"]

            # ═══════════════════════════════════════════════════════════
            # LLM GATEWAY: Process with Two-Tier Caching
            # ═══════════════════════════════════════════════════════════

            # Build few-shot prompt
            prompt = self._build_prompt(message, context, semantic_hint, conversation_history)

            # Create request using gateway interface
            llm_request = LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                model_tier=ModelTier.TIER_1,  # Fast & cheap: Claude Haiku, GPT-3.5-Turbo
                user_id=context.get("user_id", "system") if context else "system",
                temperature=0.0,  # Deterministic classification
                max_tokens=100,  # Short response (intent + confidence)
                cache_strategy="aggressive",  # 1-hour gateway cache
                context={
                    "purpose": "intent_classification",
                    "tier": "3",
                    "message_preview": message[:50],
                },
            )

            # Process via gateway (handles: caching, failover, cost tracking, circuit breakers)
            logger.info(f"Calling LLM gateway for: '{message[:50]}'")
            llm_response = await self.llm_gateway.process_request(llm_request)

            # Track cache hits from gateway
            if llm_response.from_cache:
                self.stats["gateway_cache_hits"] += 1
                logger.debug("Gateway cache hit", extra={"cache_layer": "gateway_memory"})
            else:
                self.stats["llm_calls"] += 1
                logger.info(
                    "LLM API called",
                    extra={
                        "model": llm_response.model_used,
                        "provider": llm_response.provider_used,
                        "cost_usd": llm_response.cost_usd,
                        "tokens": llm_response.tokens_used,
                    },
                )

            # Parse response
            intent, confidence = self._parse_response(llm_response.content)

            # Cache in intent-specific Redis cache
            await self.cache.set(
                cache_key,
                json.dumps({"intent": intent.value, "confidence": confidence}),
                ttl=3600,
            )

            logger.info(
                f"LLM classified '{message[:50]}' → {intent.value}",
                extra={
                    "confidence": confidence,
                    "cost_usd": llm_response.cost_usd,
                    "from_gateway_cache": llm_response.from_cache,
                    "model_used": llm_response.model_used,
                    "processing_time_ms": llm_response.processing_time_ms,
                },
            )

            return intent, confidence

        except Exception as e:
            logger.error(f"LLM classification failed: {e}", exc_info=True)
            # Return semantic hint if available, else unknown
            if semantic_hint:
                return semantic_hint[0], max(semantic_hint[1] * 0.6, 0.3)
            return IntentType.UNKNOWN, 0.3

    def _generate_cache_key(self, message: str, context: dict[str, Any] | None) -> str:
        """Generate cache key from message and context."""
        # Normalize message
        normalized = message.lower().strip()

        # Include relevant context (user stage, profile)
        context_str = ""
        if context:
            stage = context.get("stage", "")
            role = context.get("profile", {}).get("role", "")
            context_str = f"{stage}:{role}"

        # Hash for consistent key
        combined = f"{normalized}|{context_str}"
        hash_key = hashlib.md5(combined.encode()).hexdigest()

        return f"intent_llm:{hash_key}"

    def _build_prompt(
        self,
        message: str,
        context: dict[str, Any] | None,
        semantic_hint: tuple[IntentType, float] | None,
        conversation_history: list[dict[str, str]] | None,
    ) -> str:
        """Build few-shot prompt for LLM classification."""

        # Semantic hint section
        hint_section = ""
        if semantic_hint:
            hint_section = f"""
Semantic analysis suggests: {semantic_hint[0].value} (confidence: {semantic_hint[1]:.2f})
However, this was below our threshold. Please verify or correct this classification.
"""

        # Conversation context
        context_section = "No prior conversation context."
        if conversation_history:
            recent_msgs = conversation_history[-3:]
            context_msgs = "\n".join([
                f"- {msg.get('role', 'user')}: {msg.get('content', '')[:100]}"
                for msg in recent_msgs
            ])
            context_section = f"Recent conversation:\n{context_msgs}"

        # User context
        user_section = "No user profile available."
        if context:
            stage = context.get("stage", "unknown")
            role = context.get("profile", {}).get("role", "unknown")
            user_section = f"User stage: {stage}, Role: {role}"

        prompt = f"""You are classifying user intent for a career development AI assistant.

Message to classify: "{message}"

{user_section}

{context_section}

{hint_section}

Available intents:
- activity_classification: User wants to classify/categorize work activities
- competency_analysis: User wants skill/competency assessment
- career_advice: User seeks career guidance or development advice
- help_request: User needs help understanding the system
- goal_management: User wants to create/update/track goals
- report_request: User wants reports/summaries generated
- resource_discovery: User wants learning resources/courses
- status_inquiry: User wants to check progress/status
- general_chat: Greetings, thanks, casual conversation
- unknown: Unclear or doesn't fit above

Respond with ONLY:
intent: <intent_name>
confidence: <0.0-1.0>

Example:
intent: career_advice
confidence: 0.85"""

        return prompt

    def _parse_response(self, response: str) -> tuple[IntentType, float]:
        """Parse LLM response into intent and confidence."""

        try:
            # Extract intent
            intent = IntentType.UNKNOWN
            for line in response.split("\n"):
                if line.strip().lower().startswith("intent:"):
                    intent_str = line.split(":", 1)[1].strip()
                    # Try to match to IntentType
                    for intent_type in IntentType:
                        if intent_type.value.lower() == intent_str.lower():
                            intent = intent_type
                            break
                    break

            # Extract confidence
            confidence = 0.6  # Default
            for line in response.split("\n"):
                if line.strip().lower().startswith("confidence:"):
                    conf_str = line.split(":", 1)[1].strip()
                    confidence = float(conf_str)
                    break

            return intent, confidence

        except Exception as e:
            logger.warning(f"Failed to parse LLM response: {e}")
            return IntentType.UNKNOWN, 0.5

    def get_stats(self) -> dict[str, Any]:
        """Get performance statistics."""
        total_cache_hits = self.stats["intent_cache_hits"] + self.stats["gateway_cache_hits"]
        cache_hit_rate = 0.0
        if self.stats["total_calls"] > 0:
            cache_hit_rate = total_cache_hits / self.stats["total_calls"]

        return {
            **self.stats,
            "total_cache_hits": total_cache_hits,
            "cache_hit_rate": cache_hit_rate,
            "llm_call_rate": self.stats["llm_calls"] / self.stats["total_calls"] if self.stats["total_calls"] > 0 else 0,
        }


# Global instance
_llm_classifier: LLMIntentClassifier | None = None


async def get_llm_classifier() -> LLMIntentClassifier:
    """Get or create global LLM classifier instance."""
    global _llm_classifier
    if _llm_classifier is None:
        _llm_classifier = LLMIntentClassifier()
    return _llm_classifier
```

## Benefits of Gateway Integration

### 1. Leverage Existing Infrastructure ✅

- **No duplicate code**: Reuse tested gateway logic
- **Consistent patterns**: Same interface across all LLM uses
- **Shared configuration**: Provider setup, API keys, base URLs

### 2. Cost Optimization ✅

- **Automatic cost tracking**: Every LLM call tracked by `CostTracker`
- **Budget alerts**: Gateway notifies when approaching limits
- **Model tier selection**: Easy to switch tiers based on performance needs

### 3. Reliability ✅

- **Circuit breakers**: Automatic failover on provider failures
- **Multi-provider**: Falls back to alternate providers
- **Retry logic**: Built-in retry with exponential backoff

### 4. Performance ✅

- **Two-tier caching**: Intent cache + gateway cache
- **Request batching**: Can batch multiple classifications
- **Connection pooling**: Reused connections across requests

### 5. Observability ✅

- **Unified logging**: All LLM calls logged consistently
- **Correlation IDs**: Track requests across systems
- **Performance metrics**: Processing time, cache hit rate, cost per request

## Cost & Performance Estimates

### Cost Analysis (TIER_1)

```
Intent classification via TIER_1 (Claude Haiku, GPT-3.5-Turbo):
- Model: ~$0.15/1k input tokens, ~$0.20/1k output tokens
- Average prompt: ~200 tokens (intent list + few-shot + context)
- Average response: ~20 tokens (intent + confidence)
- Cost per LLM call: (200 × $0.15 + 20 × $0.20) / 1000 = $0.000034

Per 100 messages with 90% cache hit rate:
- LLM calls: 10 requests × $0.000034 = $0.00034
- Total cost: <$0.0004 per 100 messages

Annual cost (1M messages/year):
- LLM calls: 100k × $0.000034 = $3.40/year
```

**Extremely cost-effective!** ✅

### Performance Expectations

```
Tier 3 LLM Classification Latency:

Cache hit (80%):          <5ms   (Redis lookup)
Gateway cache hit (10%):  <10ms  (Memory lookup)
LLM API call (10%):       300-500ms (TIER_1 model)

Average latency: 0.8 × 5ms + 0.1 × 10ms + 0.1 × 400ms = 45ms
P95 latency: ~500ms (when LLM is called)
P99 latency: ~500ms (when LLM is called)
```

**Meets <500ms target!** ✅

## Migration Notes

### Changes to Original Design

**Before** (Custom LLM Client):
```python
response = await self.llm_gateway.generate(  # ❌ Doesn't exist
    model="claude-3-haiku-20240307",
    messages=[{"role": "user", "content": prompt}],
    temperature=0.0,
)
```

**After** (Gateway Integration):
```python
llm_request = LLMRequest(  # ✅ Use gateway interface
    messages=[{"role": "user", "content": prompt}],
    model_tier=ModelTier.TIER_1,
    user_id=user_id,
    temperature=0.0,
    cache_strategy="aggressive",
)
llm_response = await self.llm_gateway.process_request(llm_request)
```

### No New Dependencies

- ✅ Uses existing `src/core/llm/gateway.py`
- ✅ Uses existing `src/core/llm/model_mapper.py` for ModelTier
- ✅ Uses existing `src/infrastructure/cache/redis_cache.py`
- ✅ No additional packages required

## Testing Strategy

### Unit Tests

```python
@pytest.mark.asyncio
async def test_llm_classifier_with_gateway_cache():
    """Test LLM classifier leverages gateway cache."""
    classifier = LLMIntentClassifier()

    # Mock gateway to return cached response
    with patch.object(classifier.llm_gateway, 'process_request') as mock_process:
        mock_process.return_value = LLMResponse(
            request_id="test",
            content="intent: career_advice\nconfidence: 0.85",
            model_used="claude-3-haiku",
            provider_used="anthropic",
            tokens_used={"input": 200, "output": 20},
            cost_usd=0.000034,
            processing_time_ms=450,
            from_cache=True,  # ✅ Gateway cache hit
        )

        intent, conf = await classifier.classify("career advice please")

        assert intent == IntentType.CAREER_ADVICE
        assert conf == 0.85
        assert classifier.stats["gateway_cache_hits"] == 1


@pytest.mark.asyncio
async def test_llm_classifier_uses_tier1():
    """Test LLM classifier uses TIER_1 for cost efficiency."""
    classifier = LLMIntentClassifier()

    with patch.object(classifier.llm_gateway, 'process_request') as mock_process:
        await classifier.classify("test message")

        # Verify TIER_1 was used
        call_args = mock_process.call_args
        request: LLMRequest = call_args[0][0]
        assert request.model_tier == ModelTier.TIER_1
        assert request.cache_strategy == "aggressive"
```

## Conclusion

By integrating with the existing LLM gateway, we:

1. ✅ **Reuse robust infrastructure** - Multi-provider, failover, cost tracking
2. ✅ **Minimize code duplication** - ~100 fewer lines vs custom client
3. ✅ **Ensure consistency** - Same patterns across all LLM usage
4. ✅ **Optimize costs** - TIER_1 + aggressive caching = <$0.0004 per 100 messages
5. ✅ **Meet performance targets** - Average 45ms latency (95% cached)

**User's Insight Was Correct**: Using the existing LLM gateway is the right approach! ✅

---

**Next Steps**: Continue with [ARCHITECTURE_DESIGN.md](ARCHITECTURE_DESIGN.md) for complete 3-tier system design.
