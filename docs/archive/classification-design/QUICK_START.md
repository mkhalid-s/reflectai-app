# Intent Classification v2.0 - Quick Start Guide

**Purpose**: Get started with the 3-tier intent classification system
**Audience**: Developers ready to implement
**Time to Read**: 10 minutes

## What You Need to Know

### The Problem (in 30 seconds)
Current pattern-based system:
- 60-70% accuracy, 40% clarification rate
- Generic keywords override specific intents ("help with career" → HELP_REQUEST ❌)
- Unmaintainable exclusion keyword lists
- 100-200ms average latency

### The Solution (in 30 seconds)
3-tier progressive classification:
- **Tier 1**: Exact phrases (<1ms) - Common greetings, status checks
- **Tier 2**: Semantic embeddings (25ms) - Main classifier (80-85% of messages)
- **Tier 3**: LLM via gateway (400ms) - Ambiguous cases only (<5% of messages)

**Result**: 85-95% accuracy, <15% clarification, <50ms average latency

## Read This First

1. **[README.md](README.md)** - Complete overview with architecture diagram
2. **[PROBLEM_ANALYSIS.md](PROBLEM_ANALYSIS.md)** - Why we're doing this
3. **[LLM_GATEWAY_INTEGRATION.md](LLM_GATEWAY_INTEGRATION.md)** - How to use existing LLM gateway

## Implementation Checklist

### Phase 1: Semantic Classifier (2-3 hours)

**File to Create**: `src/core/classification/semantic_classifier.py` (~200 lines)

**Key Code**:
```python
from sentence_transformers import SentenceTransformer

class SemanticIntentClassifier:
    def __init__(self):
        # Load lightweight model (80MB, 20-30ms inference)
        self.model = SentenceTransformer('all-MiniLM-L6-v2')

        # Pre-compute intent prototypes
        self.intent_prototypes = self._compute_prototypes()

    def classify(self, message: str) -> tuple[IntentType, float]:
        # Encode message
        message_emb = self.model.encode(message)

        # Compare to prototypes
        similarities = {
            intent: cosine_sim(message_emb, prototype)
            for intent, prototype in self.intent_prototypes.items()
        }

        # Return best match
        best_intent = max(similarities, key=similarities.get)
        return best_intent, similarities[best_intent]
```

**Intent Examples** (7 per intent):
```python
INTENT_EXAMPLES = {
    IntentType.CAREER_ADVICE: [
        "help with my career development",
        "career advice needed",
        "how to advance my career",
        "what should I focus on for growth",
        "career path recommendations",
        "advice for career progression",
        "how can I get promoted",
    ],
    # ... 9 more intents
}
```

**Test It**:
```bash
pdm add sentence-transformers
python -c "
from semantic_classifier import SemanticIntentClassifier
classifier = SemanticIntentClassifier()
intent, conf = classifier.classify('help with career development')
print(f'{intent}: {conf:.2f}')  # Should be CAREER_ADVICE: 0.82+
"
```

### Phase 2: LLM Classifier with Gateway (2-3 hours)

**File to Create**: `src/core/classification/llm_classifier.py` (~250 lines)

**Key Integration** (use existing gateway!):
```python
from src.core.llm.gateway import LLMRequest, get_llm_gateway
from src.core.llm.model_mapper import ModelTier

class LLMIntentClassifier:
    def __init__(self):
        self.llm_gateway = get_llm_gateway()  # ✅ Existing gateway
        self.cache = get_redis_cache()

    async def classify(self, message: str, ...) -> tuple[IntentType, float]:
        # Check cache first
        cached = await self.cache.get(cache_key)
        if cached:
            return cached

        # Build prompt
        prompt = self._build_prompt(message, context, semantic_hint)

        # Call gateway
        llm_request = LLMRequest(
            messages=[{"role": "user", "content": prompt}],
            model_tier=ModelTier.TIER_1,  # ✅ Fast & cheap
            user_id=user_id,
            temperature=0.0,
            cache_strategy="aggressive",  # ✅ 1-hour cache
        )

        llm_response = await self.llm_gateway.process_request(llm_request)

        # Parse and cache
        intent, conf = self._parse_response(llm_response.content)
        await self.cache.set(cache_key, (intent, conf), ttl=3600)

        return intent, conf
```

**Test It**:
```python
import asyncio

async def test():
    classifier = await get_llm_classifier()
    intent, conf = await classifier.classify("ambiguous message")
    print(f"{intent}: {conf:.2f}")

asyncio.run(test())
```

### Phase 3: Refactor intent_analyzer.py (2-3 hours)

**Add at Top**:
```python
# Tier 1: Exact phrases
EXACT_PHRASES = {
    "hello": IntentType.GENERAL_CHAT,
    "hi": IntentType.GENERAL_CHAT,
    "help": IntentType.HELP_REQUEST,
    "status": IntentType.STATUS_INQUIRY,
    # ... 30-40 total
}
```

**New `__init__`**:
```python
def __init__(self):
    self.logger = get_logger("classification.intent")

    # Initialize 3-tier classifiers
    self.semantic_classifier = get_semantic_classifier()
    self.llm_classifier = None  # Lazy load
    self.exact_phrases = EXACT_PHRASES
```

**New `analyze_intent`** (3-tier logic):
```python
async def analyze_intent(self, user_input: str, ...) -> IntentClassificationResult:
    start_time = datetime.now(UTC)
    processed = self._preprocess_input(user_input)
    normalized = processed.lower().strip()

    # TIER 1: Exact phrases (<1ms)
    if normalized in self.exact_phrases:
        intent = self.exact_phrases[normalized]
        return self._create_result(intent, 1.0, "exact_match", start_time)

    # TIER 2: Semantic embeddings (20-30ms)
    intent, confidence = self.semantic_classifier.classify(normalized)
    if confidence >= 0.4:  # Single threshold
        return self._create_result(intent, confidence, "semantic_embedding", start_time)

    # TIER 3: LLM via gateway (300-500ms)
    if self.llm_classifier is None:
        self.llm_classifier = await get_llm_classifier()

    intent, confidence = await self.llm_classifier.classify(
        user_input, context, (intent, confidence), conversation_history
    )
    return self._create_result(intent, confidence, "llm_assisted", start_time)
```

**Remove** (lines to delete):
```python
# Line 238-308:  _classify_with_patterns() - DELETE
# Line 310-350:  _classify_with_llm() - DELETE
# Line 352-412:  _calculate_pattern_score() - DELETE
# Line 486-747:  _build_intent_patterns() - DELETE (~260 lines!)
# Line 749-788:  _build_llm_prompt_template() - DELETE
# Line 790-895:  _prepare_llm_context(), _parse_llm_response() - DELETE
```

**Result**: 1,091 lines → ~841 lines (-250 lines)

### Phase 4: Simplify intelligence.py (1 hour)

**Before** (tiered thresholds):
```python
self.actionable_confidence_threshold = 0.7
self.informational_confidence_threshold = 0.15

threshold = (
    self.informational_confidence_threshold
    if is_informational_intent(intent)
    else self.actionable_confidence_threshold
)
```

**After** (single threshold):
```python
self.confidence_threshold = 0.4  # Single threshold

if intent_result.confidence < self.confidence_threshold:
    # Generate clarification
    intent_result.needs_clarification = True
```

### Phase 5: Test & Validate (2-3 hours)

**Run Tests**:
```bash
# Unit tests
pdm run pytest tests/unit/core/classification/ -v

# Integration tests
pdm run pytest tests/integration/ -k intent -v

# Performance test
python -m timeit -s "from intent_analyzer import IntentAnalyzer; a=IntentAnalyzer()" \
    "a.analyze_intent('hello')"
# Should be < 1ms for Tier 1

python -m timeit -s "from intent_analyzer import IntentAnalyzer; a=IntentAnalyzer()" \
    "a.analyze_intent('help with career development')"
# Should be 20-30ms for Tier 2
```

**Validate Accuracy**:
```python
# Test with 100 diverse messages
test_messages = [
    ("hello", IntentType.GENERAL_CHAT),
    ("help with career development", IntentType.CAREER_ADVICE),
    ("analyze my activities", IntentType.ACTIVITY_CLASSIFICATION),
    # ... 97 more
]

analyzer = IntentAnalyzer()
correct = 0
for message, expected in test_messages:
    result = await analyzer.analyze_intent(message)
    if result.primary_intent == expected:
        correct += 1

accuracy = correct / len(test_messages)
print(f"Accuracy: {accuracy:.1%}")  # Target: 85%+
```

## Common Issues & Solutions

### Issue: Model Download Fails
```bash
# Pre-download model
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Check download
ls ~/.cache/torch/sentence_transformers/
```

### Issue: Slow First Request
**Cause**: Model loading takes 2-3 seconds on first call

**Solution**: Warm up on startup
```python
# In app startup
async def warmup():
    classifier = get_semantic_classifier()
    _ = classifier.classify("warmup message")
```

### Issue: Low Accuracy
**Cause**: Need more INTENT_EXAMPLES

**Solution**: Add 2-3 more examples per intent
```python
IntentType.CAREER_ADVICE: [
    # Original 7 examples +
    "professional development advice",  # Add 1
    "how to grow in my career",         # Add 2
    "career growth suggestions",        # Add 3
]
```

### Issue: High Tier 3 Usage (>10%)
**Cause**: Semantic threshold too high or poor examples

**Solution**:
1. Lower threshold: 0.4 → 0.35
2. Add more INTENT_EXAMPLES
3. Check logs to see which messages go to Tier 3

## Performance Targets

| Metric | Target | How to Measure |
|--------|--------|----------------|
| **Accuracy** | 85-95% | Test on 100-message dataset |
| **Clarification Rate** | <15% | Count `needs_clarification=True` |
| **Tier 1 Latency** | <1ms | `timeit` on exact matches |
| **Tier 2 Latency** | 20-30ms | `timeit` on semantic |
| **Tier 3 Latency** | <500ms | Log `processing_time_ms` |
| **Overall P50** | <50ms | Median of all requests |
| **Overall P95** | <100ms | 95th percentile (includes Tier 3) |
| **Tier 3 Usage** | <5% | `stats['tier3_llm'] / stats['total']` |
| **Cache Hit Rate** | >80% | Intent cache + gateway cache |
| **Cost per 100** | <$0.001 | Track LLM API costs |

## Monitoring

**Key Metrics to Track**:
```python
# Add to intent_analyzer.py stats
self._stats = {
    "total_classifications": 0,
    "tier1_exact": 0,
    "tier2_semantic": 0,
    "tier3_llm": 0,
    "average_confidence": 0.0,
    "average_latency_ms": 0.0,
}

# Log every N requests
if self._stats["total_classifications"] % 100 == 0:
    logger.info("Classification stats", extra=self._stats)
```

**Prometheus Metrics** (optional):
```python
from prometheus_client import Counter, Histogram

intent_classifications = Counter(
    'intent_classifications_total',
    'Total intent classifications',
    ['tier', 'intent']
)

intent_latency = Histogram(
    'intent_classification_latency_seconds',
    'Intent classification latency',
    ['tier']
)
```

## Next Steps

1. ✅ **Read this guide** - You just did!
2. 📖 **Read detailed docs**:
   - [LLM_GATEWAY_INTEGRATION.md](LLM_GATEWAY_INTEGRATION.md) - Gateway usage
   - [RESEARCH_FINDINGS.md](RESEARCH_FINDINGS.md) - Why semantic embeddings work
3. 🔨 **Start Phase 1**: Create `semantic_classifier.py`
4. 🧪 **Test each phase**: Don't move forward until tests pass
5. 📊 **Validate**: Test on 100 diverse messages
6. 🚀 **Deploy**: Gradual rollout (10% → 50% → 100%)

## Success Criteria

Before marking complete, ensure:
- [ ] All 5 phases implemented
- [ ] Unit tests pass (80%+ coverage)
- [ ] Accuracy ≥85% on test dataset
- [ ] Clarification rate <15%
- [ ] P50 latency <50ms
- [ ] P95 latency <100ms
- [ ] Tier 3 usage <5%
- [ ] Cache hit rate >80%
- [ ] Documentation updated

## Get Help

- **Review logs**: Check `classification.intent`, `classification.semantic`, `classification.llm`
- **Check stats**: `analyzer.get_intent_stats()`
- **Test individual tiers**: Test each classifier independently
- **Read detailed docs**: Full implementation in [DOCUMENTATION_STATUS.md](DOCUMENTATION_STATUS.md)

## Time Estimate

- **Phase 1**: 2-3 hours (semantic classifier)
- **Phase 2**: 2-3 hours (LLM classifier)
- **Phase 3**: 2-3 hours (refactor analyzer)
- **Phase 4**: 1 hour (simplify intelligence)
- **Phase 5**: 2-3 hours (testing)
- **Total**: 9-13 hours

**Can be done in 2-3 days of focused work!**

---

**Ready to start?** Begin with Phase 1: Create `semantic_classifier.py`

See [RESEARCH_FINDINGS.md](RESEARCH_FINDINGS.md) for technical background, and [LLM_GATEWAY_INTEGRATION.md](LLM_GATEWAY_INTEGRATION.md) for gateway integration details.
