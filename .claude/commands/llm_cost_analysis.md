---
description: Analyze LLM usage patterns, identify cost optimization opportunities, and generate savings recommendations
---

# LLM Cost Analysis - Usage and Cost Optimization

Analyze LLM usage patterns and identify cost optimization opportunities.

## Analysis Process

### Step 1: Find All LLM Calls (2 min)
1. **Search codebase** for LLM gateway usage
2. **Identify patterns** - Direct calls vs. workflow usage
3. **Map providers** - OpenAI, Anthropic, etc.
4. **Check cost tracking** - Verify all calls are tracked
5. **Find orphaned calls** - Calls without cost tracking

### Step 2: Cost Tracking Audit (2-3 min)
1. **Review cost_tracker.py** - Implementation completeness
2. **Check provider rates** - Current pricing for each model
3. **Analyze token usage** - Average tokens per request
4. **Calculate costs** - Estimate monthly spending
5. **Identify high-cost operations** - Most expensive calls

### Step 3: Usage Pattern Analysis (2-3 min)
1. **Frequency analysis** - How often are LLMs called?
2. **Model distribution** - Which models are used most?
3. **Prompt analysis** - Are prompts optimized?
4. **Response caching** - What can be cached?
5. **Redundant calls** - Are we making duplicate requests?

### Step 4: Optimization Opportunities (3 min)
1. **Caching candidates** - Identify cacheable responses
2. **Model selection** - Can cheaper models work?
3. **Prompt optimization** - Reduce token usage
4. **Batch processing** - Combine multiple requests
5. **Rate limiting** - Prevent runaway costs

### Step 5: Recommendations (2 min)
1. **Quick wins** - Easy optimizations with high impact
2. **Budget alerts** - Set up cost monitoring
3. **Provider strategy** - Optimize provider selection
4. **Architecture changes** - Long-term improvements
5. **Monitoring setup** - Track costs in production

## Example Output

```markdown
# 💰 LLM Cost Analysis

## Current Usage

### LLM Calls Found: 47 locations
- Gateway calls: 42
- Direct calls: 5 ⚠️  (should use gateway)

### Provider Distribution
- OpenAI: 38 calls (81%)
- Anthropic: 7 calls (15%)
- Local/Fallback: 2 calls (4%)

### Cost Tracking Status
✅ 42/47 calls tracked (89%)
❌ 5 calls without tracking (needs fix)

## Estimated Monthly Costs

### By Provider
- OpenAI (GPT-4): ~$850/month
- OpenAI (GPT-3.5): ~$120/month
- Anthropic (Claude): ~$95/month
- **Total**: ~$1,065/month

### By Feature
- Competency Analysis: $680/month (64%)
- Chat Responses: $245/month (23%)
- Report Generation: $140/month (13%)

### High-Cost Operations
🔴 Competency assessment (gpt-4): ~$2.50/request
🟡 Gap analysis (gpt-4): ~$1.20/request
🟢 Quick summaries (gpt-3.5-turbo): ~$0.08/request

## Optimization Opportunities

### 1. Response Caching (HIGH IMPACT)
**Potential Savings**: $320/month (30%)

Cacheable operations:
- Framework descriptions: $180/month saved
- Competency definitions: $95/month saved
- Common query responses: $45/month saved

**Action**: Implement Redis caching in `src/core/llm/cache.py`

### 2. Model Selection (MEDIUM IMPACT)
**Potential Savings**: $210/month (20%)

Operations that can use cheaper models:
- Simple classification: gpt-4 → gpt-3.5-turbo
- Formatting tasks: gpt-4 → gpt-3.5-turbo
- Data extraction: gpt-4 → gpt-3.5-turbo

**Action**: Update model mapping in `src/core/llm/optimizer.py`

### 3. Prompt Optimization (MEDIUM IMPACT)
**Potential Savings**: $160/month (15%)

Verbose prompts found:
- `analyze_competency_gap()`: 2,500 tokens → optimize to 1,500
- `generate_recommendations()`: 1,800 tokens → optimize to 1,200
- `format_report()`: 1,200 tokens → optimize to 800

**Action**: Refactor prompts in `src/core/prompts/`

### 4. Batch Processing (LOW IMPACT)
**Potential Savings**: $40/month (4%)

Operations that can be batched:
- Multiple competency checks
- Bulk analysis requests

**Action**: Add batch processing in workflows

## Cost Tracking Issues

### Missing Cost Tracking
```python
# src/services/chat_responder.py:145
response = await openai.chat.completions.create(...)  # ❌ No tracking

# FIX:
from src.core.llm.gateway import llm_gateway
response = await llm_gateway.complete(...)  # ✅ Tracked
```

### Untracked Locations
1. `src/services/chat_responder.py:145`
2. `src/core/analysis/quick_analyzer.py:78`
3. `src/services/reporting/report_generator.py:234`
4. `src/core/tools/advisor/resource_finder.py:56`
5. `src/interfaces/slack/intelligent_dm.py:123`

## Budget Alert Setup

### Current Status
❌ No budget alerts configured

### Recommended Configuration
```python
# Budget: $1,500/month
BUDGET_WARNING_THRESHOLD=75  # Alert at $1,125
BUDGET_CRITICAL_THRESHOLD=90  # Alert at $1,350
BUDGET_EXCEEDED_THRESHOLD=100  # Throttle at $1,500
BUDGET_ALERT_CHANNEL="#budget-alerts"
```

### Implementation
See `/design_feature` for budget alert system design

## Provider Strategy

### Current Strategy
- Primary: OpenAI (GPT-4, GPT-3.5)
- Fallback: Anthropic (Claude)

### Optimization Opportunities
1. **Model routing**: Use cheaper models when appropriate
2. **Provider selection**: Compare costs across providers
3. **Failover strategy**: Cost-aware failover logic

## Monitoring Recommendations

### Metrics to Track
```python
# Cost metrics
llm_cost_total_usd
llm_cost_by_provider_usd
llm_cost_by_model_usd
llm_cost_by_operation_usd

# Usage metrics
llm_requests_total
llm_tokens_used_total
llm_cache_hit_rate

# Performance metrics
llm_response_time_seconds
llm_error_rate
```

### Alerts to Configure
```yaml
- name: llm_cost_spike
  condition: increase(llm_cost_total_usd[1h]) > 50
  severity: warning

- name: llm_cache_low
  condition: llm_cache_hit_rate < 0.3
  severity: info
```

## Action Plan

### Immediate (This Week)
1. ✅ Fix 5 untracked LLM calls
2. ✅ Implement response caching (30% savings)
3. ✅ Set up budget alerts

### Short-term (This Month)
1. ⏳ Optimize prompts (15% savings)
2. ⏳ Update model selection logic (20% savings)
3. ⏳ Add cost monitoring dashboard

### Long-term (Next Quarter)
1. 📋 Implement batch processing
2. 📋 Predictive cost analysis
3. 📋 Multi-provider cost optimization

## Expected Impact

### Before Optimization
- Monthly cost: $1,065
- Cache hit rate: 0%
- Cost tracking: 89%

### After Optimization
- Monthly cost: $435-$645 (40-60% reduction)
- Cache hit rate: 30-40%
- Cost tracking: 100%

**Total Savings**: $420-$630/month

---

*Priority: HIGH - Immediate cost savings available*
*Estimated effort: 2-3 days for quick wins*
```

## Cost Optimization Checklist

- [ ] All LLM calls use gateway for tracking
- [ ] Response caching implemented
- [ ] Model selection optimized
- [ ] Prompts are concise and effective
- [ ] Budget alerts configured
- [ ] Cost monitoring dashboard available
- [ ] Regular cost review scheduled

Remember: Every optimized LLM call saves money!
