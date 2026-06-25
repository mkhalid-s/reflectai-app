# Intent Classification System Documentation

## Overview

This directory contains comprehensive documentation for the ReflectAI intent classification system redesign from fragile pattern matching to a robust 3-tier architecture using semantic embeddings.

**Version**: 2.0 (3-Tier Architecture)
**Status**: Design Complete, Implementation Pending
**Last Updated**: January 2025

## Quick Navigation

- **[Problem Analysis](PROBLEM_ANALYSIS.md)** - Detailed analysis of current system issues
- **[Research Findings](RESEARCH_FINDINGS.md)** - Research on semantic embeddings and modern approaches
- **[Architecture Design](ARCHITECTURE_DESIGN.md)** - Complete 3-tier architecture specification
- **[Implementation Guide](IMPLEMENTATION_GUIDE.md)** - Detailed implementation instructions
- **[Migration Guide](MIGRATION_GUIDE.md)** - Step-by-step migration from v1.0 to v2.0
- **[Performance Benchmarks](PERFORMANCE_BENCHMARKS.md)** - Expected performance metrics

## Executive Summary

### The Problem

The current pattern-based intent classification system (v1.0) has several critical issues:

- **60-70% accuracy** - Frequent misclassifications
- **40% clarification rate** - Excessive user friction
- **Fragile patterns** - Requires constant maintenance for edge cases
- **Generic keyword conflicts** - "help" overrides specific intents like career advice
- **Complex threshold logic** - Multiple cascading thresholds causing unpredictable behavior

### The Solution

A modern 3-tier progressive classification system:

```
Tier 1: Exact Phrases      → <1ms      → 10-15% of messages (common phrases)
Tier 2: Semantic Embeddings → 20-30ms   → 80-85% of messages (main classifier)
Tier 3: LLM Classification  → 300-500ms → <5% of messages (truly ambiguous)
```

### Key Improvements

| Metric | Current (v1.0) | Target (v2.0) | Improvement |
|--------|---------------|---------------|-------------|
| **Accuracy** | 60-70% | 85-95% | +25-35% |
| **Clarification Rate** | 40% | <15% | -25% |
| **Average Latency** | 100-200ms | <50ms | -50-150ms |
| **Code Lines** | 1,091 | 841 | -250 lines |
| **Maintenance** | High (fragile patterns) | Low (semantic handles variations) | Major reduction |
| **Cost per 100 msgs** | N/A | <$0.005 | Minimal |

### Why This Approach?

1. **Performance**: 95% of requests complete in <50ms via Tiers 1 & 2
2. **Accuracy**: Semantic embeddings naturally handle variations and context
3. **Scalability**: LRU and Redis caching minimize compute and cost
4. **Maintainability**: No fragile patterns to maintain
5. **Cost Efficiency**: <5% of messages use paid LLM API

### How Systems Like ChatGPT/Gemini Work

Modern AI systems use similar tiered approaches:

1. **Intent Routing Layer** - Fast classification to determine which specialized system handles the request
2. **Semantic Understanding** - Embeddings capture meaning beyond keywords
3. **LLM as Fallback** - Only for truly ambiguous or complex cases
4. **Aggressive Caching** - Cache results to minimize redundant processing

Our 3-tier system follows these proven patterns used by production AI systems at scale.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    User Message Input                        │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │  Pre-process Input    │ (lowercase, normalize)
        └───────────┬───────────┘
                    │
                    ▼
┌───────────────────────────────────────────────────────────────┐
│ TIER 1: EXACT PHRASE MATCHING (<1ms)                          │
│                                                                │
│ Dict Lookup: {"hello": GENERAL_CHAT, "help": HELP_REQUEST}   │
│ • 30-40 common exact phrases                                  │
│ • 100% confidence, instant response                           │
│ • Handles: greetings, simple help, status checks             │
├────────────────────────────────────────────────────────────────┤
│                     ✓ Match? → Return Result                  │
│                     ✗ No Match? → Continue to Tier 2          │
└────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌───────────────────────────────────────────────────────────────┐
│ TIER 2: SEMANTIC EMBEDDINGS (20-30ms)                         │
│                                                                │
│ SentenceTransformer: 'all-MiniLM-L6-v2' (80MB)               │
│ • Convert message to 384-dim vector                           │
│ • Compare to pre-computed intent prototypes                   │
│ • Cosine similarity for classification                        │
│ • LRU cache for repeated messages                             │
├────────────────────────────────────────────────────────────────┤
│                     ✓ Confidence ≥ 0.4? → Return Result      │
│                     ✗ Low Confidence? → Continue to Tier 3    │
└────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌───────────────────────────────────────────────────────────────┐
│ TIER 3: LLM CLASSIFICATION (300-500ms)                        │
│                                                                │
│ Claude Haiku with Few-Shot Prompting                          │
│ • Context: user profile, conversation history                 │
│ • Semantic hint from Tier 2                                   │
│ • Redis cache (1 hour TTL)                                    │
│ • Only for truly ambiguous cases                              │
├────────────────────────────────────────────────────────────────┤
│                     → Return Final Result                      │
└────────────────────────────────────────────────────────────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │  Extract Metadata     │ (dates, content)
        └───────────┬───────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │  Update Statistics    │
        └───────────┬───────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │   Return to Caller    │
        └───────────────────────┘
```

## File Changes Summary

### New Files to Create

1. **`src/core/classification/semantic_classifier.py`** (~200 lines)
   - SentenceTransformer initialization
   - Intent prototype computation
   - Cosine similarity classification
   - LRU caching

2. **`src/core/classification/llm_classifier.py`** (~250 lines)
   - LLM-based classification
   - Redis caching (1 hour TTL)
   - Few-shot prompting
   - Performance tracking

3. **`tests/unit/core/classification/test_semantic_classifier.py`** (~150 lines)
   - Unit tests for semantic classification

4. **`tests/unit/core/classification/test_llm_classifier.py`** (~150 lines)
   - Unit tests for LLM classification

### Files to Modify

1. **`src/core/classification/intent_analyzer.py`**
   - Remove: ~450 lines of pattern matching code
   - Add: 3-tier classification logic (~200 lines)
   - Net: 1,091 → 841 lines (-250 lines)

2. **`src/core/conversation/intelligence.py`**
   - Simplify threshold logic (single threshold instead of tiered)
   - Remove: ~20 lines

3. **`pyproject.toml`**
   - Add: `sentence-transformers>=2.2.0` dependency

### Files to Remove (Optional Cleanup)

- Pattern-related helper methods can be extracted to archive if needed

## Implementation Phases

### Phase 1: Foundation (1-2 hours)
- Create semantic_classifier.py with tests
- Create llm_classifier.py with tests
- Verify both work independently

### Phase 2: Integration (2-3 hours)
- Refactor intent_analyzer.py with 3-tier logic
- Remove old pattern matching code
- Update statistics tracking

### Phase 3: Simplification (1 hour)
- Simplify intelligence.py thresholds
- Update clarification logic

### Phase 4: Testing & Validation (2-3 hours)
- Run existing test suite
- Integration testing with real messages
- Performance benchmarking
- Production validation

**Total Estimated Effort**: 6-9 hours

## Success Criteria

### Functional Requirements
- ✅ All existing tests pass
- ✅ 85%+ accuracy on test dataset
- ✅ <15% clarification rate
- ✅ Handle all 10 intent types correctly

### Performance Requirements
- ✅ 95% of requests complete in <50ms
- ✅ Tier 1: <1ms (exact phrases)
- ✅ Tier 2: 20-30ms (semantic)
- ✅ Tier 3: <500ms (LLM)

### Cost Requirements
- ✅ <$0.01 per 100 messages
- ✅ <5% of messages use Tier 3 (LLM)
- ✅ Cache hit rate >80% for Tier 3

### Quality Requirements
- ✅ Code coverage >80%
- ✅ All linting/type checks pass
- ✅ Documentation complete

## Dependencies

### New Dependencies
- `sentence-transformers>=2.2.0` - For semantic embeddings
  - Downloads `all-MiniLM-L6-v2` model (80MB) on first run
  - Requires: `torch`, `transformers`, `numpy` (already in project)

### Existing Dependencies (No Changes)
- `openai>=1.3.0` - For LLM classification (Tier 3)
- `redis>=4.5.0` - For caching
- `numpy>=1.24.0` - For embedding operations

## Monitoring & Metrics

### Classification Metrics (Tracked per Tier)
- Total classifications
- Tier 1 exact matches (count, %)
- Tier 2 semantic classifications (count, %, avg latency)
- Tier 3 LLM classifications (count, %, avg latency, cache hit rate)
- Average confidence per intent type
- Clarification request rate

### Performance Metrics
- P50, P95, P99 latency per tier
- Average processing time
- Cache hit rates (LRU and Redis)

### Cost Metrics
- LLM API calls (Tier 3)
- Estimated cost per 100 messages
- Cost per intent type

## Rollback Plan

If issues arise post-deployment:

1. **Feature Flag**: Keep old pattern-based code behind feature flag for 2 weeks
2. **Gradual Rollout**: Deploy to 10% → 50% → 100% of traffic
3. **Monitoring**: Watch accuracy, latency, error rates
4. **Quick Rollback**: Switch feature flag if needed

## Future Enhancements

### Short Term (v2.1)
- Fine-tune semantic model on ReflectAI-specific data
- Expand INTENT_EXAMPLES with user feedback
- Optimize LRU cache size based on production traffic

### Medium Term (v2.2)
- Multi-intent classification (detect multiple intents)
- Confidence calibration for better thresholds
- A/B testing framework for classification

### Long Term (v3.0)
- Train custom intent classifier on ReflectAI data
- Real-time model updates based on feedback
- Multi-language support

## References

- [SentenceTransformers Documentation](https://www.sbert.net/)
- [All-MiniLM-L6-v2 Model Card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
- [Semantic Similarity with Embeddings](https://www.sbert.net/docs/usage/semantic_textual_similarity.html)

## Contact & Support

For questions or issues:
- Review detailed docs in this folder
- Check existing GitHub issues
- Create new issue with label: `classification`

---

**Next Steps**: Read [PROBLEM_ANALYSIS.md](PROBLEM_ANALYSIS.md) for detailed problem analysis, then proceed to [ARCHITECTURE_DESIGN.md](ARCHITECTURE_DESIGN.md) for technical specifications.
