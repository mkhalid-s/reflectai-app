---
description: Run comprehensive tests with coverage analysis, identify gaps, and generate test enhancement suggestions
argument-hint: [module path]
---

# Test ReflectAI Module with Coverage

Run comprehensive tests for the specified module with coverage analysis and gap identification: $ARGUMENTS

## Test Process

### Step 1: Module Identification (1 minute)
1. **Validate module path** - Ensure the file exists and is testable
2. **Identify module type** - Core logic, service, interface, or infrastructure
3. **Find test files** - Locate all tests for this module
4. **Check current coverage** - Run existing tests to baseline coverage

### Step 2: Run Tests with Coverage (2-3 minutes)
1. **Execute unit tests** - Run all unit tests for the module
2. **Execute integration tests** - Run integration tests if applicable
3. **Generate coverage report** - Analyze line and branch coverage
4. **Identify uncovered code** - List functions/methods without tests
5. **Check async patterns** - Verify async/await test patterns

### Step 3: Gap Analysis (2-3 minutes)
1. **Analyze uncovered lines** - Determine why they're not covered
2. **Identify missing scenarios** - Error cases, edge cases, async paths
3. **Assess risk** - Prioritize untested code by criticality
4. **Review test quality** - Check if tests are thorough or just basic

### Step 4: Test Enhancement Suggestions (2 minutes)
1. **Propose new test cases** - Specific scenarios to add
2. **Generate test stubs** - Provide skeleton code for missing tests
3. **Suggest test fixtures** - Reusable test data or mocks needed
4. **Identify integration test needs** - External service testing requirements

## Output Format

```markdown
# 🧪 Test Analysis: [MODULE_PATH]

## Current Test Status

### Test Files Found
- `tests/unit/[path]/test_[module].py` - [XX tests, coverage: XX%]
- `tests/integration/test_[module]_integration.py` - [XX tests]

### Coverage Summary
- **Line Coverage**: XX% (Target: 80%+)
- **Branch Coverage**: XX%
- **Functions Covered**: XX/XX (XX%)
- **Classes Covered**: XX/XX (XX%)

## Test Execution Results

### Unit Tests (Fast - <100ms per test)
✅ test_basic_functionality - PASSED (XXms)
✅ test_error_handling - PASSED (XXms)
❌ test_edge_case - FAILED (XXms)
   Error: [specific error message]
⚠️  test_async_operation - SKIPPED (missing fixture)

### Integration Tests (Slower - with dependencies)
✅ test_database_integration - PASSED (XXXms)
✅ test_redis_cache - PASSED (XXXms)
⚠️  test_temporal_workflow - WARNING (slow: >1s)

## Coverage Gaps

### Uncovered Code (Priority Order)

#### 🔴 CRITICAL - Must Cover
**File**: `src/[path]/[file].py`
**Lines**: 45-60
**Function**: `handle_critical_operation()`
**Why Critical**: Error handling for user data
**Missing Scenarios**:
- [ ] Database connection failure
- [ ] Invalid input validation
- [ ] Async timeout handling

#### 🟡 MEDIUM - Should Cover
**File**: `src/[path]/[file].py`
**Lines**: 120-135
**Function**: `calculate_metrics()`
**Why Important**: Business logic calculation
**Missing Scenarios**:
- [ ] Zero division edge case
- [ ] Empty data handling

#### 🟢 LOW - Nice to Have
**File**: `src/[path]/[file].py`
**Lines**: 200-210
**Function**: `format_output()`
**Why Low**: Simple formatting logic
**Missing Scenarios**:
- [ ] None input handling

## ReflectAI-Specific Checks

### Async Pattern Validation
✅ All I/O operations use async/await
✅ Proper exception handling in async contexts
⚠️  Missing async test for database operation (line 78)
❌ Blocking call in async function (line 145) - MUST FIX

### Integration Compliance
✅ LLM cost tracking present
✅ Error handling uses `src.shared.exceptions`
⚠️  Missing circuit breaker for external service call
✅ Proper logging with correlation IDs

### Performance Validation
✅ Unit tests complete in <100ms
⚠️  Integration test slow: 1.2s (target: <1s)
✅ No memory leaks detected

## Proposed Test Cases

### Test Case 1: Database Connection Failure
```python
@pytest.mark.asyncio
@pytest.mark.unit
async def test_handle_db_connection_failure():
    """Test graceful handling of database connection failures."""
    # Arrange
    mock_db = AsyncMock()
    mock_db.execute.side_effect = DatabaseError(
        message="Connection timeout",
        query="SELECT * FROM users"
    )

    # Act
    with pytest.raises(DatabaseError) as exc_info:
        await handle_critical_operation(mock_db)

    # Assert
    assert "Connection timeout" in str(exc_info.value)
    assert exc_info.value.category == ErrorCategory.DATABASE
```

### Test Case 2: Async Timeout Handling
```python
@pytest.mark.asyncio
@pytest.mark.unit
async def test_async_timeout_handling():
    """Test timeout handling for long-running async operations."""
    # Arrange
    async def slow_operation():
        await asyncio.sleep(10)  # Simulate slow operation

    # Act & Assert
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(slow_operation(), timeout=0.5)
```

### Test Case 3: LLM Provider Failover
```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_llm_provider_failover():
    """Test LLM provider failover when primary fails."""
    # Arrange
    primary_provider = AsyncMock()
    primary_provider.complete.side_effect = LLMProviderError("API timeout")
    fallback_provider = AsyncMock()
    fallback_provider.complete.return_value = "Success response"

    # Act
    result = await llm_gateway.complete_with_failover(
        prompt="Test",
        providers=[primary_provider, fallback_provider]
    )

    # Assert
    assert result == "Success response"
    assert fallback_provider.complete.called
```

## Test Fixtures Needed

### Fixture 1: Mock LLM Response
```python
@pytest.fixture
async def mock_llm_response():
    """Fixture for mocking LLM provider responses."""
    return {
        "content": "Test response",
        "model": "gpt-4",
        "tokens": 100,
        "cost": 0.002
    }
```

### Fixture 2: Mock Database Session
```python
@pytest.fixture
async def mock_db_session():
    """Fixture for mocking async database sessions."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session
```

## Integration Test Requirements

### External Services to Mock
- **PostgreSQL**: Use testcontainers or mock async connections
- **Redis**: Use fakeredis or testcontainers
- **LLM Providers**: Use `tests/mocks/llm_mock.py`
- **Slack API**: Use `tests/mocks/slack_mock.py`
- **Temporal**: Use `tests/mocks/temporal_mock.py`

### End-to-End Scenarios
- [ ] Full workflow: User request → LLM processing → DB storage → Response
- [ ] Error propagation: External failure → Retry → Fallback → User notification
- [ ] Performance: Response time <2s for 95th percentile

## Quick Wins

**Top 3 tests to add immediately for maximum coverage gain:**

1. **Test database error handling** → +15% coverage
   - File: `tests/unit/[module]/test_[module]_errors.py`
   - Estimated time: 15 minutes

2. **Test async timeout scenarios** → +10% coverage
   - File: `tests/unit/[module]/test_[module]_async.py`
   - Estimated time: 10 minutes

3. **Test input validation edge cases** → +8% coverage
   - File: `tests/unit/[module]/test_[module]_validation.py`
   - Estimated time: 10 minutes

**Total effort**: ~35 minutes for +33% coverage gain

## Action Items

- [ ] Run tests: `./rai test unit -k test_[module]`
- [ ] Fix failing test: `test_edge_case`
- [ ] Add 3 quick win tests
- [ ] Fix blocking call in async function (line 145)
- [ ] Add integration test for slow operation
- [ ] Update test documentation
- [ ] Run full coverage: `./rai test coverage`

## Commands to Run

```bash
# Run unit tests for this module
./rai test unit -k test_[module_name]

# Run with coverage report
pdm run pytest tests/unit/[path]/test_[module].py --cov=src/[path] --cov-report=html

# Run integration tests
./rai test unit -k test_[module]_integration

# View coverage report
open htmlcov/index.html
```

---

*Coverage target: 80%+*
*Current: XX% → Target: 80%+ (Gap: XX%)*
*Estimated effort: XX minutes to reach target*
```

## Testing Best Practices for ReflectAI

### Async Testing Patterns
1. **Always use `@pytest.mark.asyncio`** for async tests
2. **Use `AsyncMock`** for mocking async functions
3. **Test timeout scenarios** with `asyncio.wait_for()`
4. **Verify proper cleanup** of async resources

### ReflectAI-Specific Testing
1. **LLM Integration**: Always mock LLM providers, never call real APIs in tests
2. **Temporal Workflows**: Test determinism - no random, no timestamps, no external calls
3. **Slack Integration**: Test 3-second response time requirement
4. **Database**: Use async patterns, test connection pooling, test transactions
5. **Error Handling**: Use `src.shared.exceptions` error types
6. **Cost Tracking**: Verify all LLM calls track costs
7. **Logging**: Verify correlation IDs are propagated

### Test Organization
- **Unit tests**: Fast (<100ms), isolated, no external dependencies
- **Integration tests**: Slower, with real or containerized dependencies
- **Use markers**: `@pytest.mark.unit`, `@pytest.mark.integration`
- **Use factories**: Create test data with factory-boy
- **Use fixtures**: Reusable test setup in `conftest.py`

### Coverage Goals
- **Minimum**: 80% overall coverage
- **Critical paths**: 100% coverage (error handling, data operations)
- **New code**: 90%+ coverage before merging
- **Focus**: Line coverage + branch coverage

Remember: Good tests document behavior, prevent regressions, and enable confident refactoring. Quality over quantity!
