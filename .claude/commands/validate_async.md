---
description: Validate async/await patterns, detect blocking calls, race conditions, and performance issues across the codebase
---

# Validate Async - Async/Await Pattern Compliance

Validate async/await patterns across the ReflectAI codebase.

## Validation Process

### Step 1: Find Async Functions (1 min)
1. **Scan for async def** - Locate all async functions
2. **Identify I/O operations** - Database, Redis, LLM, HTTP calls
3. **Map function calls** - Who calls what
4. **Check decorators** - Proper async decorators

### Step 2: Pattern Validation (3-4 min)
1. **Missing await** - Async calls without await
2. **Blocking calls** - Synchronous I/O in async functions
3. **Race conditions** - Concurrent operations without proper locking
4. **Resource leaks** - Unclosed connections or files
5. **Error handling** - Proper exception handling in async contexts

### Step 3: Performance Issues (2 min)
1. **Sequential await** - Operations that could run in parallel
2. **Unnecessary async** - Functions that don't need to be async
3. **Async overhead** - Too many context switches
4. **Connection pooling** - Proper pool management

### Step 4: ReflectAI-Specific Checks (2 min)
1. **Database operations** - All database calls use async
2. **Redis operations** - All cache calls use async
3. **LLM calls** - All LLM operations are async
4. **Temporal activities** - Async patterns in activities
5. **Slack API** - Async Slack SDK usage

### Step 5: Generate Report (1 min)
1. **Summarize findings** - Count of each issue type
2. **Prioritize issues** - Critical vs. minor
3. **Provide fixes** - Code examples for each issue
4. **Suggest tests** - Tests to prevent regressions

## Example Output

```markdown
# ⚡ Async Pattern Validation

## Summary
Scanned 145 Python files
Found 423 async functions
Identified 18 issues

## Critical Issues 🔴

### 1. Missing await on async call
**Location**: `src/infrastructure/database/db_manager.py:145`
**Issue**: Async function called without await
```python
# BEFORE (WRONG):
async def get_user(user_id: str):
    user = session.execute(query)  # ❌ Missing await
    return user

# AFTER (CORRECT):
async def get_user(user_id: str):
    user = await session.execute(query)  # ✅ Proper await
    return user
```

### 2. Blocking I/O in async function
**Location**: `src/core/llm/cache.py:78`
**Issue**: Synchronous file I/O in async function
```python
# BEFORE (WRONG):
async def save_cache(key: str, value: str):
    with open(f"cache/{key}", "w") as f:  # ❌ Blocking
        f.write(value)

# AFTER (CORRECT):
async def save_cache(key: str, value: str):
    async with aiofiles.open(f"cache/{key}", "w") as f:  # ✅ Async
        await f.write(value)
```

### 3. Resource leak - connection not closed
**Location**: `src/services/workflow/activities.py:234`
**Issue**: Database connection not released on error
```python
# BEFORE (WRONG):
async def execute_activity():
    conn = await get_connection()
    result = await conn.execute(query)
    await conn.close()  # ❌ Not called if error occurs
    return result

# AFTER (CORRECT):
async def execute_activity():
    conn = await get_connection()
    try:
        result = await conn.execute(query)
        return result
    finally:
        await conn.close()  # ✅ Always called
```

## High Priority Issues 🟡

### 4. Sequential operations that could be parallel
**Location**: `src/core/assessment/competency_assessor.py:156`
**Optimization**: Run independent operations concurrently
```python
# BEFORE (SLOW):
async def assess_competencies():
    result1 = await get_user_data()      # 200ms
    result2 = await get_framework()      # 150ms
    result3 = await get_activities()     # 300ms
    # Total: 650ms

# AFTER (FAST):
async def assess_competencies():
    result1, result2, result3 = await asyncio.gather(
        get_user_data(),      # \
        get_framework(),      #  } Run in parallel
        get_activities()      # /
    )
    # Total: 300ms (45% faster)
```

### 5. Async function with no async operations
**Location**: `src/shared/validation.py:89`
**Issue**: Function doesn't need to be async
```python
# BEFORE (UNNECESSARY):
async def validate_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))  # ❌ No async operations

# AFTER (CORRECT):
def validate_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))  # ✅ Regular function
```

## Medium Priority Issues 🟢

### 6. Missing error handling in async context
**Location**: `src/interfaces/slack/socket_handler.py:123`
```python
# Add proper error handling:
try:
    result = await async_operation()
except asyncio.CancelledError:
    logger.info("Operation cancelled")
    raise
except Exception as e:
    logger.error("Operation failed", error=str(e))
    raise
```

### 7. Race condition in concurrent access
**Location**: `src/infrastructure/cache/redis_manager.py`
```python
# Use asyncio.Lock for thread-safe access:
_lock = asyncio.Lock()

async def update_cache(key: str, value: str):
    async with _lock:
        await redis.set(key, value)
```

## ReflectAI-Specific Compliance

### Database Operations ✅
✅ All database calls use async SQLAlchemy
✅ Connection pooling properly configured
✅ Transactions use async context managers
✅ No blocking database calls found

### Redis Operations ✅
✅ All Redis calls use async redis-py
✅ Connection pooling enabled
✅ Proper error handling
✅ No blocking Redis calls

### LLM Integration ⚠️
✅ All LLM gateway calls are async
⚠️  1 direct OpenAI call without async (line 145)
✅ Cost tracking is async
✅ Caching operations are async

### Temporal Workflows ✅
✅ All activities use async patterns
✅ Activity calls properly awaited
✅ No blocking operations in workflows
✅ Async resource cleanup

### Slack API ✅
✅ Using async Slack SDK (slack_bolt)
✅ Event handlers are async
✅ API calls properly awaited
✅ No blocking Slack operations

## Summary by Category

### Issue Distribution
- Critical (blocking bugs): 3
- High priority (performance): 2
- Medium priority (best practices): 7
- Low priority (code quality): 6

### By Module
- src/infrastructure: 6 issues
- src/core: 5 issues
- src/services: 4 issues
- src/interfaces: 3 issues

## Quick Fixes

### Top 3 Critical Fixes (30 minutes)
1. **Add await to db_manager.py:145** (5 min)
2. **Fix file I/O in cache.py:78** (10 min)
3. **Add finally block in activities.py:234** (5 min)

### Performance Optimizations (1 hour)
1. **Parallelize competency_assessor.py:156** (20 min)
2. **Make validation.py:89 synchronous** (10 min)
3. **Add error handling to socket_handler.py:123** (15 min)

## Testing Recommendations

### Async Pattern Tests
```python
@pytest.mark.asyncio
async def test_async_operations_awaited():
    """Ensure all async calls are properly awaited."""
    # Test implementation

@pytest.mark.asyncio
async def test_resource_cleanup():
    """Verify resources are cleaned up on error."""
    # Test implementation

@pytest.mark.asyncio
async def test_parallel_execution():
    """Verify operations run in parallel when possible."""
    # Test implementation
```

## Prevention Guidelines

### Code Review Checklist
- [ ] All async functions have await keywords
- [ ] No blocking I/O in async functions
- [ ] Resources cleaned up in finally blocks
- [ ] Independent operations run in parallel (asyncio.gather)
- [ ] Proper error handling for CancelledError
- [ ] Connection pools used for I/O operations
- [ ] Race conditions prevented with locks

### Pre-commit Hooks
Add async pattern linting to pre-commit:
```yaml
- repo: local
  hooks:
    - id: check-async-patterns
      name: Check async/await patterns
      entry: python scripts/check_async.py
      language: system
```

---

*Found 18 issues - 3 critical, 2 high, 7 medium, 6 low*
*Estimated fix time: 2-3 hours*
*Priority: HIGH - Critical issues affect reliability*
```

## Async Best Practices for ReflectAI

### Always Async
- Database operations (SQLAlchemy)
- Redis operations (redis-py)
- HTTP requests (httpx, aiohttp)
- LLM API calls (OpenAI, Anthropic)
- Slack API calls (slack_bolt async)
- File I/O (aiofiles)

### Never Async
- Pure computation (calculations, validation)
- String operations
- Data transformation
- Configuration loading

### Common Pitfalls
1. Forgetting `await` keyword
2. Using sync I/O in async functions
3. Not cleaning up resources
4. Running operations sequentially when they could be parallel
5. Not handling CancelledError

Remember: Async is about I/O concurrency, not CPU parallelism!
