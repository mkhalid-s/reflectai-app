---
description: Comprehensive system health check covering code quality, tests, security, infrastructure, and ReflectAI-specific components
---

# Check Health - System Health Dashboard

Quick health check of the entire ReflectAI system.

## Health Check Process

### Step 1: Code Quality (1-2 minutes)
1. **Run ruff linting** - Check code style and quality
2. **Run mypy type checking** - Verify type annotations
3. **Check for common issues** - Async patterns, error handling
4. **Count warnings/errors** - Assess overall code quality

### Step 2: Test Health (2-3 minutes)
1. **Run test suite** - Execute all tests
2. **Check coverage** - Verify 80%+ coverage target
3. **Identify failing tests** - List any test failures
4. **Check test performance** - Flag slow tests

### Step 3: Security Scan (1-2 minutes)
1. **Run bandit** - Security vulnerability scan
2. **Check dependencies** - Look for known vulnerabilities
3. **Scan for secrets** - Ensure no API keys in code
4. **Review security issues** - Prioritize by severity

### Step 4: Infrastructure Health (1-2 minutes)
1. **Check Docker services** - Verify all containers running
2. **Database connectivity** - Test PostgreSQL connection
3. **Redis connectivity** - Test Redis connection
4. **Temporal health** - Check workflow server
5. **Check disk space** - Ensure adequate space

### Step 5: ReflectAI-Specific Checks (2 minutes)
1. **LLM provider health** - Check API connectivity
2. **Cost tracking status** - Verify cost tracking working
3. **Async pattern compliance** - Scan for async violations
4. **Error handling compliance** - Check exception usage
5. **Logging configuration** - Verify structured logging

## Example Output

```markdown
# 🏥 ReflectAI System Health Check

## Overall Health Score: 85/100 🟢

Last checked: October 7, 2025 15:45:32

---

## Code Quality: 90/100 ✅

### Linting (ruff)
✅ **Status**: Passed
- Files scanned: 145
- Errors: 0
- Warnings: 3 (non-critical)

### Type Checking (mypy)
✅ **Status**: Passed
- Files checked: 145
- Type errors: 0
- Coverage: 95%

### Code Patterns
✅ Async patterns: Compliant
✅ Error handling: Using structured exceptions
⚠️  3 files missing type hints

---

## Test Health: 85/100 ⚠️

### Test Execution
✅ **Unit Tests**: 130/130 passing (100%)
⚠️  **Integration Tests**: 12/15 passing (80%)
   - 3 failures in streaming tests
✅ **Test Speed**: Average 45ms per test

### Coverage
📊 **Overall Coverage**: 88% (Target: 80%+)
- Excellent: >90% - 45 files
- Good: 80-90% - 78 files
- Needs work: <80% - 22 files

### Critical Gaps
⚠️  `src/core/llm/stream_handler.py` - 65% coverage
⚠️  `src/interfaces/slack/threading.py` - 72% coverage

---

## Security: 75/100 ⚠️

### Vulnerability Scan (bandit)
⚠️  **Status**: Issues found
- High: 0
- Medium: 2
- Low: 5

### Critical Issues
🔴 **SQL Injection Risk**
- File: `src/infrastructure/database/query_builder.py:45`
- Action: Use parameterized queries

🟡 **Hardcoded Secret**
- File: `src/config/settings.py:78`
- Action: Move to environment variables

### Dependency Security
✅ All dependencies up to date
✅ No known CVEs in dependencies

---

## Infrastructure: 95/100 ✅

### Docker Services
✅ **App**: Running (port 3000, healthy)
✅ **Database**: Running (PostgreSQL 15, healthy)
✅ **Redis**: Running (Redis 7, healthy)
✅ **Temporal**: Running (UI on 8088, healthy)

### Connectivity
✅ Database: Connected (5ms latency)
✅ Redis: Connected (2ms latency)
✅ Temporal: Connected (8ms latency)

### Resources
✅ **Disk Space**: 125GB free (65% available)
✅ **Memory**: 8GB free (50% available)
✅ **CPU**: 25% average usage

---

## ReflectAI-Specific: 80/100 ⚠️

### LLM Integration
✅ **OpenAI**: Connected and healthy
⚠️  **Cost Tracking**: Working but no budget alerts configured
✅ **Caching**: Redis cache operational
✅ **Failover**: Provider failover configured

### Slack Integration
✅ **Connection**: Socket mode connected
✅ **Response Time**: Average 1.2s (target: <3s)
✅ **Threading**: Properly implemented
✅ **Block Kit**: Formatting validated

### Temporal Workflows
✅ **Worker**: Active and processing
⚠️  **Workflows**: 2 workflows stuck in retry
✅ **Activities**: All activities registered
✅ **Task Queue**: Healthy

### Database Patterns
✅ **Async Operations**: All operations async
✅ **Connection Pool**: 18/20 connections available
✅ **Migrations**: Up to date
⚠️  **Slow Queries**: 3 queries >1s (needs optimization)

---

## Recommendations

### 🔴 Critical (Fix Now)
1. Fix SQL injection in `query_builder.py:45`
2. Remove hardcoded secret in `settings.py:78`
3. Fix 3 failing streaming integration tests

### 🟡 High Priority (This Week)
1. Configure LLM budget alerts
2. Investigate 2 stuck Temporal workflows
3. Optimize 3 slow database queries
4. Improve test coverage for `stream_handler.py` and `threading.py`

### 🟢 Medium Priority (This Sprint)
1. Add type hints to 3 files missing them
2. Address 5 low-severity security warnings
3. Document LLM streaming architecture
4. Add monitoring for workflow retries

---

## Quick Actions

```bash
# Fix critical issues
./rai check security --fix
./rai test integration -k streaming --verbose

# Investigate stuck workflows
./rai temporal workflows list --status=failed

# Check slow queries
./rai db slow-queries

# Improve coverage
./rai test coverage --show-missing
```

---

## Trend Analysis

```
Last 7 Days:
Code Quality:  88 → 90 ✅ (+2%)
Test Coverage: 85 → 88 ✅ (+3%)
Security:      78 → 75 ⚠️  (-3%)
Uptime:        99.8% ✅
```

**Overall Trend**: Improving 📈

---

## Next Health Check
Recommended: In 4 hours or after major changes
```

## Health Score Calculation

### Scoring Breakdown
- **Code Quality** (25 points):
  - Linting: 10 points
  - Type checking: 10 points
  - Code patterns: 5 points

- **Test Health** (25 points):
  - Test pass rate: 15 points
  - Coverage: 10 points

- **Security** (20 points):
  - Vulnerability scan: 15 points
  - Dependency security: 5 points

- **Infrastructure** (15 points):
  - Services running: 10 points
  - Resource availability: 5 points

- **ReflectAI-Specific** (15 points):
  - LLM integration: 5 points
  - Slack integration: 3 points
  - Temporal workflows: 4 points
  - Database patterns: 3 points

### Score Interpretation
- **90-100**: Excellent 🟢
- **75-89**: Good ⚠️
- **60-74**: Needs Attention 🟡
- **<60**: Critical Issues 🔴

Remember: Regular health checks prevent production fires!
