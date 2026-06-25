---
description: Identify test coverage gaps and generate tests to reach 80%+ coverage with prioritized recommendations
---

# Fix Coverage - Identify and Fix Test Coverage Gaps

Identify test coverage gaps and generate tests to reach 80%+ coverage.

## Coverage Fix Process

### Step 1: Run Coverage Analysis (1 min)
1. **Run full test suite** with coverage
2. **Generate coverage report** (HTML and terminal)
3. **Identify modules** below 80% threshold
4. **List uncovered lines** for each module
5. **Categorize gaps** by type (error handling, edge cases, etc.)

### Step 2: Prioritize Gaps (2 min)
1. **Critical paths** - Core business logic (100% target)
2. **High risk** - Error handling, data operations (90% target)
3. **Medium risk** - Helper functions, utilities (80% target)
4. **Low risk** - Configuration, simple getters (70% acceptable)
5. **Exclude** - Generated code, deprecated code

### Step 3: Generate Test Cases (3-4 min)
1. **Analyze uncovered code** - Understand what it does
2. **Identify test scenarios** - Happy path, errors, edge cases
3. **Generate test stubs** - Skeleton code for each scenario
4. **Add test fixtures** - Mock data and dependencies
5. **Write assertions** - What to verify

### Step 4: Implement Tests (varies)
1. **Start with quick wins** - Easy tests with high coverage gain
2. **Add error handling tests** - Common source of gaps
3. **Add edge case tests** - Boundary conditions
4. **Add integration tests** - End-to-end scenarios
5. **Run and verify** - Ensure tests pass and coverage improves

### Step 5: Validate Results (1 min)
1. **Re-run coverage** - Check improvement
2. **Verify quality** - Tests actually test something
3. **Check performance** - Tests run reasonably fast
4. **Update documentation** - Note test patterns used
5. **Mark complete** - Track progress

## Example Output

```markdown
# 🎯 Test Coverage Gap Analysis

## Current Coverage: 73% (Target: 80%+)

Analyzed 145 files
Below threshold: 28 files
Total uncovered lines: 1,245

## Priority Modules (Need Immediate Attention)

### 🔴 CRITICAL: Core Business Logic

#### 1. src/core/assessment/competency_assessor.py
**Current**: 65% | **Target**: 90%+ | **Gap**: 25%
**Uncovered Lines**: 145-160, 178-195, 234-256

**Missing Scenarios**:
```python
# Test 1: Error handling for missing framework
@pytest.mark.asyncio
@pytest.mark.unit
async def test_assess_with_missing_framework():
    """Test competency assessment when framework not found."""
    assessor = CompetencyAssessor()

    with pytest.raises(ValidationError) as exc:
        await assessor.assess(
            user_id="test",
            framework_id="nonexistent"
        )

    assert "framework not found" in str(exc.value).lower()

# Test 2: Edge case - zero activities
@pytest.mark.asyncio
@pytest.mark.unit
async def test_assess_with_no_activities():
    """Test assessment with user who has no activities."""
    assessor = CompetencyAssessor()

    result = await assessor.assess(
        user_id="empty_user",
        framework_id="test_framework"
    )

    assert result.level == "beginner"
    assert len(result.gaps) > 0

# Test 3: Concurrent assessment calls
@pytest.mark.asyncio
@pytest.mark.integration
async def test_concurrent_assessments():
    """Test multiple simultaneous assessments."""
    assessor = CompetencyAssessor()

    results = await asyncio.gather(
        assessor.assess("user1", "framework1"),
        assessor.assess("user2", "framework1"),
        assessor.assess("user3", "framework2")
    )

    assert len(results) == 3
    assert all(r.level is not None for r in results)
```

**Quick Win**: +15% coverage in 30 minutes

---

#### 2. src/core/llm/gateway.py
**Current**: 71% | **Target**: 90%+ | **Gap**: 19%
**Uncovered Lines**: 89-105, 145-167, 234-245

**Missing Scenarios**:
```python
# Test 1: Provider failover
@pytest.mark.asyncio
@pytest.mark.integration
async def test_provider_failover():
    """Test LLM provider failover when primary fails."""
    gateway = LLMGateway()

    # Mock primary provider to fail
    with patch_llm_provider("openai", side_effect=TimeoutError()):
        response = await gateway.complete("test prompt")

    # Should have used fallback provider
    assert response is not None
    assert gateway.last_provider == "anthropic"

# Test 2: Cost tracking
@pytest.mark.asyncio
@pytest.mark.unit
async def test_cost_tracking():
    """Verify cost tracking for all LLM calls."""
    gateway = LLMGateway()

    await gateway.complete("test prompt", model="gpt-4")

    # Check cost was recorded
    cost_record = await get_latest_cost_record()
    assert cost_record.model == "gpt-4"
    assert cost_record.cost_usd > 0

# Test 3: Rate limit handling
@pytest.mark.asyncio
@pytest.mark.integration
async def test_rate_limit_handling():
    """Test handling of provider rate limits."""
    gateway = LLMGateway()

    with patch_llm_provider("openai", side_effect=RateLimitError()):
        with pytest.raises(LLMProviderError) as exc:
            await gateway.complete("test prompt")

    assert "rate limit" in str(exc.value).lower()
```

**Quick Win**: +12% coverage in 25 minutes

---

### 🟡 HIGH: Error Handling & Data Operations

#### 3. src/infrastructure/database/db_manager.py
**Current**: 68% | **Target**: 85%+ | **Gap**: 17%
**Uncovered Lines**: 45-62, 89-95, 123-134

**Missing Scenarios**:
- Connection timeout handling
- Transaction rollback on error
- Connection pool exhaustion
- Duplicate key violations
- Foreign key constraint errors

**Quick Win**: +10% coverage in 20 minutes

---

#### 4. src/interfaces/slack/socket_handler.py
**Current**: 72% | **Target**: 85%+ | **Gap**: 13%
**Uncovered Lines**: 78-89, 145-156, 234-241

**Missing Scenarios**:
- Slack API timeout
- Invalid event format
- Message too long
- Rate limiting
- Webhook verification failure

**Quick Win**: +8% coverage in 15 minutes

---

### 🟢 MEDIUM: Utilities & Helpers

#### 5. src/shared/validation.py
**Current**: 76% | **Target**: 80%+ | **Gap**: 4%
**Uncovered Lines**: 123-130, 178-182

**Missing Scenarios**:
- Edge case validations
- Invalid input formats

**Quick Win**: +4% coverage in 10 minutes

---

## Coverage Improvement Plan

### Phase 1: Critical Gaps (Week 1)
**Target**: 73% → 82% (+9%)

1. ✅ competency_assessor.py (+15%)
2. ✅ gateway.py (+12%)
3. ✅ db_manager.py (+10%)

**Estimated Effort**: 1.5 hours
**Expected Coverage**: 82%

### Phase 2: High Priority (Week 2)
**Target**: 82% → 87% (+5%)

1. ⏳ socket_handler.py (+8%)
2. ⏳ workflow activities (+6%)
3. ⏳ cache operations (+5%)

**Estimated Effort**: 1 hour
**Expected Coverage**: 87%

### Phase 3: Cleanup (Week 3)
**Target**: 87% → 90%+ (+3%)

1. 📋 All remaining gaps
2. 📋 Edge cases
3. 📋 Integration tests

**Estimated Effort**: 30 minutes
**Expected Coverage**: 90%+

---

## Generated Test Stubs

### Template: Error Handling Test
```python
@pytest.mark.asyncio
@pytest.mark.unit
async def test_[function]_error_[scenario]():
    """Test [function] handles [error scenario] correctly."""
    # Arrange
    mock_dependency = AsyncMock()
    mock_dependency.method.side_effect = [ErrorType]("Error message")

    # Act
    with pytest.raises([ExpectedError]) as exc_info:
        await function_under_test(mock_dependency)

    # Assert
    assert "expected message" in str(exc_info.value)
    assert exc_info.value.category == ErrorCategory.[CATEGORY]
```

### Template: Edge Case Test
```python
@pytest.mark.asyncio
@pytest.mark.unit
async def test_[function]_edge_case_[scenario]():
    """Test [function] with edge case: [description]."""
    # Arrange
    edge_case_input = [special value]

    # Act
    result = await function_under_test(edge_case_input)

    # Assert
    assert result == [expected outcome]
```

### Template: Integration Test
```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_[feature]_end_to_end():
    """Test [feature] end-to-end workflow."""
    # Arrange
    setup_test_data()

    # Act
    result = await complete_workflow()

    # Assert
    verify_expected_state(result)
```

---

## Quick Wins (2 hours total)

### Top 5 Tests for Maximum Impact

1. **Error handling in competency_assessor.py** → +15% (30 min)
2. **Provider failover in gateway.py** → +12% (25 min)
3. **Connection errors in db_manager.py** → +10% (20 min)
4. **Slack timeout in socket_handler.py** → +8% (15 min)
5. **Edge cases in validation.py** → +4% (10 min)

**Total Impact**: +49% coverage gain
**Total Effort**: 1h 40m

---

## Commands to Run

```bash
# Run coverage analysis
./rai test coverage

# View HTML report
open htmlcov/index.html

# Run specific test file
pdm run pytest tests/unit/core/assessment/test_competency_assessor.py -v

# Check coverage for specific module
pdm run pytest --cov=src/core/assessment --cov-report=term-missing

# Run only uncovered lines
pdm run pytest --cov=src --cov-report=term:skip-covered
```

---

## Progress Tracking

### Before
- Overall: 73%
- Critical modules: 65-72%
- Test count: 145

### Target
- Overall: 90%+
- Critical modules: 90%+
- Test count: 220+

### Current Progress
- [ ] Phase 1: Critical gaps (0/3 completed)
- [ ] Phase 2: High priority (0/3 completed)
- [ ] Phase 3: Cleanup (0/1 completed)

---

*Coverage improvement plan: 73% → 90%+ in 3 weeks*
*Quick wins available: +49% in 2 hours*
```

## Coverage Best Practices

### What to Test
- ✅ Business logic and algorithms
- ✅ Error handling paths
- ✅ Edge cases and boundaries
- ✅ Integration points
- ✅ Async operations

### What Not to Test
- ❌ Generated code
- ❌ Simple getters/setters
- ❌ Configuration constants
- ❌ Third-party library code
- ❌ Deprecated code (mark for deletion)

### Quality Over Quantity
- Tests should verify behavior, not just execute code
- Aim for meaningful assertions
- Test realistic scenarios
- Use proper test isolation

Remember: 80% coverage with quality tests beats 100% with poor tests!
