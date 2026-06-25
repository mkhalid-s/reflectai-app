---
description: Intelligent error analysis with root cause identification, ReflectAI-specific patterns, and solution generation
argument-hint: [error message or file path]
---

# Debug Error - Intelligent Error Analysis

Analyze and debug errors in the ReflectAI codebase: $ARGUMENTS

## Debug Process

### Step 1: Error Parsing (30 seconds)
1. **Parse error message** - Extract error type, message, and context
2. **Parse stack trace** - Identify error location and call chain
3. **Identify error category** - Database, LLM, Slack, Temporal, Network, Validation
4. **Extract key information** - File, line number, function, variables

### Step 2: Code Context Analysis (1-2 minutes)
1. **Read error location** - Get the code causing the error
2. **Read surrounding context** - Understand the function/method
3. **Analyze control flow** - Trace the execution path to the error
4. **Check error handling** - Verify existing error handling patterns
5. **Review async patterns** - Check if error is async-related

### Step 3: Root Cause Analysis (2-3 minutes)
1. **Identify immediate cause** - What directly caused the error?
2. **Identify root cause** - Why did the error occur?
3. **Check common patterns** - Is this a known issue pattern?
4. **Review dependencies** - Check external service dependencies
5. **Check configuration** - Verify environment variables and settings

### Step 4: ReflectAI-Specific Analysis (1-2 minutes)
1. **Async/await issues** - Missing await, blocking calls, race conditions
2. **Database issues** - Connection pooling, transactions, async patterns
3. **LLM provider issues** - Failover, rate limits, cost tracking
4. **Temporal issues** - Determinism violations, activity failures
5. **Slack issues** - Timeout, threading, response format
6. **Redis issues** - Connection, caching, serialization

### Step 5: Solution Generation (2-3 minutes)
1. **Propose immediate fix** - Code changes to resolve the error
2. **Suggest root cause fix** - Changes to prevent recurrence
3. **Recommend tests** - Tests to verify the fix
4. **Identify related issues** - Similar problems that might exist
5. **Document prevention** - How to avoid this in the future

## Example Output

```markdown
# 🐛 Error Debug Analysis

## Error Summary
**Type**: DatabaseError
**Location**: src/infrastructure/database/db_manager.py:78
**Severity**: High

### Root Cause
Database connection timeout due to missing timeout configuration

### Immediate Fix
Add timeout to asyncio.wait_for() call

### Root Cause Fix
- Configure connection pool timeouts
- Add retry logic with exponential backoff
- Use circuit breaker pattern
- Add proper error handling with src.shared.exceptions

### Tests Needed
- Test timeout scenario
- Test connection cleanup on error
- Test retry logic for transient failures

## Code Fix
```python
# Before:
result = await async_operation()

# After:
from src.shared.exceptions import DatabaseError
from src.shared.error_handlers import retry_with_exponential_backoff

@retry_with_exponential_backoff(max_retries=3)
async def operation():
    try:
        result = await asyncio.wait_for(async_operation(), timeout=30.0)
        return result
    except asyncio.TimeoutError as e:
        raise DatabaseError(
            message="Database operation timed out",
            query="async_operation",
            context={"timeout": 30},
            original_exception=e
        )
```

## Related Issues
Similar timeout issues found in:
- src/core/llm/gateway.py:145
- src/interfaces/slack/socket_handler.py:89
```

## Common ReflectAI Error Patterns

### Async/Await Issues
- Missing `await` keyword
- Blocking calls in async functions
- Race conditions
- Resource leaks

### Database Issues
- Connection pool exhaustion
- Missing timeout configuration
- Transaction handling
- Async pattern violations

### LLM Provider Issues
- Missing cost tracking
- No failover logic
- Rate limit exceeded
- Missing validation

### Temporal Issues
- Non-deterministic code
- Missing retry policies
- Activity failures
- Version incompatibility

### Slack Issues
- Response timeout (>3s)
- Missing threading
- Block Kit formatting
- Event acknowledgment

Remember: Good error handling means graceful degradation and informative feedback!
