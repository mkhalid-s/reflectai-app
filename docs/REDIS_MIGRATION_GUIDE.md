# Redis 8 Migration Guide
## ReflectAI Platform - Comprehensive Migration Documentation

**Last Updated**: November 23, 2025
**Status**: CURRENT
**Relevance to v0.1.2-alpha**: HIGH
**Document Version**: 2.0 (Consolidated)

**Owner**: Infrastructure Team
**Target Redis Version**: 8.0.5 (or 8.2.3)
**Current Redis Version**: 7.4.6
**Migration Status**: Ready for Execution

---

## 📑 Table of Contents

1. [Executive Overview](#executive-overview)
2. [Architecture & System Design](#architecture--system-design)
3. [Migration Strategy](#migration-strategy)
4. [Detailed Procedures](#detailed-procedures)
5. [Validation & Testing](#validation--testing)
6. [Rollback & Emergency Response](#rollback--emergency-response)
7. [Monitoring & Observability](#monitoring--observability)
8. [Troubleshooting](#troubleshooting)
9. [Scripts & Automation](#scripts--automation)
10. [Quick Reference](#quick-reference)

---

## Executive Overview

### Objective

Upgrade ReflectAI Platform's Redis cache infrastructure from **Redis 7.4.6** to **Redis 8.0.5** (or 8.2.3) to address security vulnerabilities, improve performance, and ensure long-term maintainability.

### Key Benefits

| Category | Benefit | Impact |
|----------|---------|--------|
| **Security** | Patch CVE-2025-62507 (RCE vulnerability in Redis Streams) | Critical |
| **Performance** | 30+ improvements including up to 87% faster commands | High |
| **Throughput** | Up to 2x throughput gains | High |
| **Stability** | Bug fixes across core functionality and modules | Medium |
| **Future-Proof** | Stay on actively supported versions | Strategic |

### Risk Assessment

**Overall Risk Level**: **LOW** (12/100)

#### Risk Heat Map

```
Impact vs Probability Matrix

HIGH    │              │              │ [Data Loss]  │
        │              │              │   (1%, Low)  │
IMPACT  │              │              │              │
        │[Performance] │              │              │
MEDIUM  │  (5%, Med)   │              │              │
        │              │              │              │
LOW     │  [Compat]    │   [Config]   │              │
        │  (2%, Low)   │   (3%, Low)  │              │
        └──────────────┴──────────────┴──────────────┘
           LOW         MEDIUM         HIGH
                    PROBABILITY

Risk Score Calculation: (Probability × Impact × Severity) / 100
Overall Score: 12/100 = LOW RISK
```

#### Why Low Risk for ReflectAI

✅ **Usage Patterns**:
- Only basic Redis operations (GET, SET, DELETE, EXPIRE, KEYS, HGET, HSET)
- No Redis Streams (CVE doesn't affect us)
- No complex ACL rules (simple password auth)
- No Redis modules (JSON, Search, Graph, Bloom)
- No breaking changes affect our codebase

✅ **Infrastructure**:
- Simple Docker-based deployment
- AOF persistence enabled (data safety)
- Memory usage well below limits (150-300 MB / 512 MB)
- Rolling update capable

✅ **Preparation**:
- Automated rollback procedures
- Comprehensive validation scripts
- Health monitoring in place
- Blue-green deployment strategy for production

### Timeline Overview

```
Migration Timeline (12 Business Days)

┌─────────────┬─────────────┬─────────────┬─────────────┐
│   Phase 1   │   Phase 2   │   Phase 3   │   Phase 4   │
│   Dev Env   │  Test Env   │ Staging Env │  Prod Env   │
│   2 Days    │   3 Days    │   5 Days    │   1 Day     │
├─────────────┼─────────────┼─────────────┼─────────────┤
│ Nov 8-9     │ Nov 11-13   │ Nov 14-18   │  Nov 19     │
│             │             │             │             │
│ ▓▓▓▓▓▓▓▓    │ ▓▓▓▓▓▓▓▓▓▓▓ │ ▓▓▓▓▓▓▓▓▓▓▓ │ ▓▓▓▓▓       │
│ Migration   │ Full QA     │ Perf Test   │ Production  │
│ + Validate  │ + UAT       │ + Soak Test │ + Monitor   │
└─────────────┴─────────────┴─────────────┴─────────────┘

Gate ▶        Gate ▶        Gate ▶        Gate ▶
```

**Approval Gates**:
- **Phase 1 → 2**: Dev validation successful
- **Phase 2 → 3**: QA sign-off complete
- **Phase 3 → 4**: Staging performance validated
- **Phase 4 Complete**: 30-day monitoring successful

### Expected Downtime

| Environment | Strategy | Downtime | User Impact |
|-------------|----------|----------|-------------|
| Development | Rolling update | ~30 seconds | None (internal) |
| Testing | Rolling update | ~30 seconds | None (internal) |
| Staging | Rolling update | ~30 seconds | None (internal) |
| **Production** | **Blue-green** | **Zero** | **None** |

---

## Architecture & System Design

### Current Architecture

```
┌───────────────────────────────────────────────────────────┐
│                  ReflectAI Application                     │
│                      (FastAPI)                             │
│                                                            │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐         │
│  │   Slack    │  │ Temporal   │  │    LLM     │         │
│  │ Integration│  │  Workers   │  │  Gateway   │         │
│  └──────┬─────┘  └──────┬─────┘  └──────┬─────┘         │
└─────────┼────────────────┼────────────────┼───────────────┘
          │                │                │
          └────────────────┼────────────────┘
                           │
                  ┌────────▼────────┐
                  │  Redis Client   │
                  │ (redis.asyncio) │
                  └────────┬────────┘
                           │
                  ┌────────▼────────┐
                  │  Redis Server   │
                  │   v7.4.6 Alpine │
                  │                 │
                  │  Port: 6379     │
                  │  Memory: 512MB  │
                  │  Policy: LRU    │
                  │  AOF: Enabled   │
                  └─────────────────┘

Data Operations:
━━━━━━━━━━━━━━━━
• GET/SET/DELETE - Key-value operations
• EXPIRE - TTL management
• KEYS - Pattern matching
• HGET/HSET - Hash operations
• Basic sets/lists

Not Used:
━━━━━━━━
• Streams (XADD, XREAD, XACK)
• JSON module
• Search module
• Graph module
• Complex ACL
```

### Target Architecture

```
┌───────────────────────────────────────────────────────────┐
│                  ReflectAI Application                     │
│                      (FastAPI)                             │
│              *** No Changes Required ***                   │
│                                                            │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐         │
│  │   Slack    │  │ Temporal   │  │    LLM     │         │
│  │ Integration│  │  Workers   │  │  Gateway   │         │
│  └──────┬─────┘  └──────┬─────┘  └──────┬─────┘         │
└─────────┼────────────────┼────────────────┼───────────────┘
          │                │                │
          └────────────────┼────────────────┘
                           │
                  ┌────────▼────────┐
                  │  Redis Client   │
                  │ (redis.asyncio) │  ← Same client
                  └────────┬────────┘     library
                           │
                  ┌────────▼────────┐
                  │  Redis Server   │
                  │   v8.0.5 Alpine │  ← Version upgrade
                  │                 │
                  │  Port: 6379     │  ← Same config
                  │  Memory: 512MB  │  ← Same config
                  │  Policy: LRU    │  ← Same config
                  │  AOF: Enabled   │  ← Same config
                  └─────────────────┘

Performance Improvements:
━━━━━━━━━━━━━━━━━━━━━━━
• 87% faster commands
• 2x throughput
• 18% faster replication
• Better memory efficiency
• Security patches applied
```

### Data Flow Architecture

```
User Request Flow with Redis
━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Cache Hit Path (Fast Path)
   ┌─────────┐      ┌───────────┐      ┌─────────┐
   │ Request │─────▶│   Redis   │─────▶│Response │
   │         │      │ GET key   │      │ (Cached)│
   └─────────┘      └───────────┘      └─────────┘
                      Hit ✓
                      ~1ms

2. Cache Miss Path (Slow Path)
   ┌─────────┐      ┌───────────┐      ┌──────────┐
   │ Request │─────▶│   Redis   │      │          │
   │         │      │ GET key   │      │          │
   └─────────┘      └─────┬─────┘      │          │
                      Miss ✗            │          │
                       │                │          │
                       ▼                │          │
                  ┌─────────┐           │          │
                  │Database │           │ Business │
                  │  Query  │──────────▶│  Logic   │
                  └─────────┘           │          │
                       │                │          │
                       ▼                │          │
                  ┌─────────┐           │          │
                  │  Redis  │           │          │
                  │SET key  │◀──────────│          │
                  │TTL=3600 │           └────┬─────┘
                  └─────────┘                │
                                            ▼
                                       ┌─────────┐
                                       │Response │
                                       │  (New)  │
                                       └─────────┘
                      ~100-500ms

3. Write Path
   ┌─────────┐      ┌───────────┐      ┌──────────┐
   │  Write  │─────▶│ Database  │─────▶│  Redis   │
   │ Request │      │  Update   │      │ Invalidate
   └─────────┘      └───────────┘      └──────────┘
                                         DEL key

Key Usage Patterns:
━━━━━━━━━━━━━━━━━
session:*          - User sessions (TTL: 1h)
conversation:*     - Slack conversations (TTL: 30m)
llm:cache:*        - LLM response cache (TTL: 24h)
workflow:state:*   - Temporal workflow state (TTL: 1h)
rate_limit:*       - API rate limiting (TTL: 1m)
```

### Migration Data Flow

```
Blue-Green Deployment Strategy (Production)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Phase 1: Current State
┌────────────────┐
│  Application   │
│  (Blue)        │
└───────┬────────┘
        │
        ▼
┌────────────────┐
│  Redis 7.4.6   │
│  (Active)      │
└────────────────┘


Phase 2: Deploy Redis 8
┌────────────────┐
│  Application   │
│  (Blue)        │◀──── Still using Redis 7
└───────┬────────┘
        │
        ▼
┌────────────────┐      ┌────────────────┐
│  Redis 7.4.6   │      │  Redis 8.0.5   │
│  (Active)      │      │  (Standby)     │
└────────────────┘      └────────────────┘
                          ↑
                          │
                     Warming up...


Phase 3: Switch Traffic
┌────────────────┐
│  Application   │◀──── Connection switched
│  (Blue)        │       to Redis 8
└───────┬────────┘
        │
        ├───────────────────────┐
        │                       ▼
┌────────────────┐      ┌────────────────┐
│  Redis 7.4.6   │      │  Redis 8.0.5   │
│  (Draining)    │      │  (Active)      │
└────────────────┘      └────────────────┘


Phase 4: Decommission Old
┌────────────────┐
│  Application   │
│  (Blue)        │
└───────┬────────┘
        │
        ▼
┌────────────────┐      ┌────────────────┐
│  Redis 7.4.6   │      │  Redis 8.0.5   │
│ (Stopped)      │      │  (Active)      │
└────────────────┘      └────────────────┘
```

---

## Migration Strategy

### Four-Phase Approach

```
Phase Progression with Validation Gates
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌──────────────────────────────────────────────────────────┐
│ Phase 1: Development Environment                          │
│ Duration: 2 days | Risk: Lowest | Users: 0 (internal)    │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  Migrate → Validate → Benchmark → Document               │
│     │         │          │            │                  │
│     1h       30m        30m         1-2h                 │
│                                                           │
│  Success Criteria:                                        │
│  ☑ Redis 8 running                                       │
│  ☑ All health checks pass                                │
│  ☑ Performance >= baseline                               │
│  ☑ No errors in logs                                     │
└──────────────────────────────────────────────────────────┘
            │
            ▼ Approval Gate: Dev Lead Sign-off
┌──────────────────────────────────────────────────────────┐
│ Phase 2: Testing Environment                              │
│ Duration: 3 days | Risk: Low | Users: 5-10 (QA team)     │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  Migrate → Full QA → UAT → Regression → Sign-off         │
│     │        │       │        │           │              │
│    1h       1d      1d       1d         4h              │
│                                                           │
│  Success Criteria:                                        │
│  ☑ All test suites pass (unit, integration, e2e)        │
│  ☑ No functional regressions                             │
│  ☑ UAT approved by QA team                               │
│  ☑ Performance validated                                 │
└──────────────────────────────────────────────────────────┘
            │
            ▼ Approval Gate: QA Sign-off
┌──────────────────────────────────────────────────────────┐
│ Phase 3: Staging Environment                              │
│ Duration: 5 days | Risk: Medium | Users: 50 (beta)       │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  Migrate → Load Test → Soak Test → Monitor → Review      │
│     │         │           │           │         │        │
│    1h        1d          2d          1d        4h        │
│                                                           │
│  Success Criteria:                                        │
│  ☑ Load test: 2x normal traffic handled                  │
│  ☑ Soak test: 48h stable operation                       │
│  ☑ No memory leaks                                        │
│  ☑ No error rate increase                                │
│  ☑ Performance improvement validated                     │
└──────────────────────────────────────────────────────────┘
            │
            ▼ Approval Gate: Engineering + Product Sign-off
┌──────────────────────────────────────────────────────────┐
│ Phase 4: Production Environment                           │
│ Duration: 1 day + 30-day monitor | Risk: Low | Users: All│
├──────────────────────────────────────────────────────────┤
│                                                           │
│  Pre-checks → Migrate → Validate → Monitor → Report      │
│      │          │         │          │          │        │
│     2h         1h        1h        30d         1h        │
│                                                           │
│  Success Criteria:                                        │
│  ☑ Zero downtime achieved                                │
│  ☑ All health checks pass                                │
│  ☑ No user-reported issues                               │
│  ☑ Performance improved                                  │
│  ☑ 30-day stability confirmed                            │
└──────────────────────────────────────────────────────────┘
            │
            ▼ Final Gate: Migration Complete
```

### Rollback Strategy

```
Rollback Decision Tree
━━━━━━━━━━━━━━━━━━━━

                     ┌──────────────┐
                     │  Issue       │
                     │  Detected?   │
                     └──────┬───────┘
                            │
              ┌─────────────┴─────────────┐
              │                           │
              ▼ YES                       ▼ NO
     ┌─────────────────┐         ┌──────────────┐
     │ Severity Level? │         │  Continue    │
     └────────┬────────┘         │  Monitoring  │
              │                   └──────────────┘
     ┌────────┼────────┐
     │        │        │
     ▼        ▼        ▼
  CRITICAL  HIGH     LOW/MED
     │        │        │
     │        │        │
     ▼        ▼        ▼
┌─────────┐ ┌─────────┐ ┌───────────────┐
│IMMEDIATE│ │ ASSESS  │ │ TROUBLESHOOT  │
│ROLLBACK │ │ROLLBACK?│ │  & MONITOR    │
└─────────┘ └────┬────┘ └───────┬───────┘
                 │               │
          ┌──────┴──────┐        │
          │             │        │
          ▼ FIX         ▼ CAN'T  │
      ┌────────┐    ┌────────┐  │
      │ PATCH  │    │ROLLBACK│  │
      │ APPLY  │    └────────┘  │
      └────────┘                │
                                │
                        ┌───────▼───────┐
                        │  Issue Fixed? │
                        └───────┬───────┘
                                │
                          ┌─────┴─────┐
                          │           │
                          ▼ YES       ▼ NO
                      ┌────────┐  ┌────────┐
                      │CONTINUE│  │ROLLBACK│
                      └────────┘  └────────┘

Severity Criteria:
━━━━━━━━━━━━━━━━━
CRITICAL:  Complete service outage, data loss, security breach
HIGH:      Partial outage, 50%+ error rate, major performance degradation
MEDIUM:    10-50% error rate, noticeable performance impact
LOW:       <10% error rate, minor performance variance

Rollback Time Estimates:
━━━━━━━━━━━━━━━━━━━━━━━
• Automated rollback: 2-3 minutes
• Manual rollback: 5-10 minutes
• Full validation: 15-20 minutes
```

---

## Detailed Procedures

### Phase 1: Development Environment (2 Days)

**Timeline**: November 8-9, 2025
**Risk**: Lowest
**Impact**: Internal only

#### Step-by-Step Procedure

```
Day 1: Migration & Initial Validation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Hour 0-1: Pre-Migration
  ☐ Run pre-migration check script
  ☐ Verify current Redis version (7.4.6)
  ☐ Record baseline metrics
  ☐ Backup current data (if any)

Hour 1-2: Migration Execution
  ☐ Update docker-compose.yml (redis:7-alpine → redis:8-alpine)
  ☐ Stop application containers
  ☐ Stop Redis 7 container
  ☐ Start Redis 8 container
  ☐ Verify Redis 8 running
  ☐ Start application containers

Hour 2-3: Initial Validation
  ☐ Run health check script
  ☐ Verify all 12 checks pass
  ☐ Test GET/SET operations
  ☐ Test TTL functionality
  ☐ Check application logs for errors

Hour 3-4: Performance Benchmark
  ☐ Run benchmark script
  ☐ Compare to baseline
  ☐ Validate performance improvement
  ☐ Document results

Day 2: Extended Testing
  ☐ Run full test suite
  ☐ Monitor for 24 hours
  ☐ Review metrics
  ☐ Document findings
  ☐ Get dev lead approval
```

**Commands**:

```bash
# Pre-migration
./scripts/migration/pre_migration_check.sh dev
./scripts/migration/health_check.sh dev > pre-migration-health.txt

# Migration
cd /Users/mshaikh/CascadeProjects/reflectai-platform
./rai docker down dev
# Edit docker-compose.yml: redis:7-alpine → redis:8-alpine
./rai docker up dev

# Validation
./scripts/migration/health_check.sh dev
./scripts/migration/validate_data.sh dev
./scripts/migration/redis_benchmark.sh dev > benchmark-results.txt

# Rollback (if needed)
./scripts/migration/rollback_redis.sh dev
```

#### Success Criteria

| Category | Criteria | Status |
|----------|----------|--------|
| **Deployment** | Redis 8 container running | ☐ |
| **Connectivity** | Application can connect to Redis | ☐ |
| **Operations** | GET/SET/DELETE commands work | ☐ |
| **TTL** | EXPIRE and TTL commands work | ☐ |
| **Performance** | Benchmark >= baseline | ☐ |
| **Errors** | Zero errors in application logs | ☐ |
| **Persistence** | AOF file created and functioning | ☐ |
| **Memory** | Memory usage within limits | ☐ |

---

### Phase 2: Testing Environment (3 Days)

**Timeline**: November 11-13, 2025
**Risk**: Low
**Impact**: QA team only

#### Step-by-Step Procedure

```
Day 1: Migration & QA Preparation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Morning (4 hours):
  ☐ Run pre-migration checks
  ☐ Notify QA team of migration window
  ☐ Execute migration (same as Dev)
  ☐ Validate initial health checks

Afternoon (4 hours):
  ☐ Run smoke tests
  ☐ Execute sanity test suite
  ☐ Verify all endpoints functional
  ☐ Prepare test plans for QA

Day 2: Full QA Testing
━━━━━━━━━━━━━━━━━━━━━

  ☐ Unit test suite (pytest)
  ☐ Integration test suite
  ☐ End-to-end test suite
  ☐ Slack integration tests
  ☐ LLM gateway tests
  ☐ Temporal workflow tests
  ☐ Performance regression tests

Day 3: UAT & Sign-off
━━━━━━━━━━━━━━━━━━━━

  ☐ User acceptance testing
  ☐ Regression testing
  ☐ Performance validation
  ☐ Documentation review
  ☐ QA sign-off
```

#### Success Criteria

| Category | Criteria | Status |
|----------|----------|--------|
| **Unit Tests** | 100% pass rate | ☐ |
| **Integration Tests** | 100% pass rate | ☐ |
| **E2E Tests** | 100% pass rate | ☐ |
| **Performance** | No regressions detected | ☐ |
| **Functional** | All features working | ☐ |
| **UAT** | QA team approval | ☐ |

---

### Phase 3: Staging Environment (5 Days)

**Timeline**: November 14-18, 2025
**Risk**: Medium
**Impact**: Beta users (50 people)

#### Step-by-Step Procedure

```
Day 1: Migration & Initial Validation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ☐ Pre-migration checks
  ☐ Notify beta users
  ☐ Execute migration
  ☐ Validate health checks
  ☐ Monitor for 8 hours
  ☐ Review error logs

Day 2: Load Testing
━━━━━━━━━━━━━━━━━━

  ☐ Run load test (2x normal traffic)
  ☐ Monitor response times
  ☐ Monitor error rates
  ☐ Monitor memory usage
  ☐ Monitor connection pool
  ☐ Document results

Day 3-4: Soak Testing (48 hours)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ☐ Start continuous load
  ☐ Monitor every 4 hours
  ☐ Check for memory leaks
  ☐ Check for connection leaks
  ☐ Review metrics trends
  ☐ Gather user feedback

Day 5: Review & Approval
━━━━━━━━━━━━━━━━━━━━━━━

  ☐ Analyze 48h metrics
  ☐ Review error logs
  ☐ Performance comparison
  ☐ User feedback review
  ☐ Engineering sign-off
  ☐ Product sign-off
```

#### Success Criteria

| Category | Criteria | Status |
|----------|----------|--------|
| **Load Test** | Handles 2x traffic | ☐ |
| **Soak Test** | 48h stable operation | ☐ |
| **Memory** | No leaks detected | ☐ |
| **Errors** | Error rate unchanged | ☐ |
| **Performance** | Improved response times | ☐ |
| **User Feedback** | No negative reports | ☐ |

---

### Phase 4: Production Environment (1 Day + 30-Day Monitoring)

**Timeline**: November 19, 2025 (Migration) + 30 days monitoring
**Risk**: Low (with blue-green deployment)
**Impact**: All users

#### Production Day Timeline (T-Indexed)

```
Production Migration Timeline
━━━━━━━━━━━━━━━━━━━━━━━━━━━

T-120 min │ PRE-DEPLOYMENT CHECKS
          │ ┌─────────────────────────────────┐
          │ │ • Environment validation        │
          │ │ • Team sync call                │
          │ │ • Backup verification           │
          │ │ • Rollback readiness test       │
          │ └─────────────────────────────────┘
          │
T-60 min  │ FINAL PREPARATION
          │ ┌─────────────────────────────────┐
          │ │ • Record baseline metrics       │
          │ │ • Notify stakeholders           │
          │ │ • Final backups                 │
          │ └─────────────────────────────────┘
          │
T-15 min  │ GO/NO-GO DECISION
          │ ┌─────────────────────────────────┐
          │ │ • Review checklist              │
          │ │ • Confirm team ready            │
          │ │ • Authority approval            │
          │ └─────────────────────────────────┘
          │
T-0       │ MIGRATION START
━━━━━━━━━━┿━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
          │ ┌─────────────────────────────────┐
          │ │ Phase 1: Deploy Redis 8         │
          │ │ • Start Redis 8 container       │
          │ │ • Wait for healthy status       │
          │ │ Duration: 2 min                 │
          │ └─────────────────────────────────┘
T+2 min   │
          │ ┌─────────────────────────────────┐
          │ │ Phase 2: Switch Application     │
          │ │ • Update connection config      │
          │ │ • Restart app containers        │
          │ │ Duration: 3 min                 │
          │ └─────────────────────────────────┘
T+5 min   │
          │ ┌─────────────────────────────────┐
          │ │ Phase 3: Validation             │
          │ │ • Health checks (12/12)         │
          │ │ • Smoke tests                   │
          │ │ • Monitor error rates           │
          │ │ Duration: 10 min                │
          │ └─────────────────────────────────┘
T+15 min  │
━━━━━━━━━━┿━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
          │ MONITORING PHASE
          │
T+30 min  │ ┌─────────────────────────────────┐
          │ │ Extended Monitoring             │
          │ │ • Performance validation        │
          │ │ • Error rate analysis           │
          │ │ • User-facing validation        │
          │ │ Duration: 30 min                │
          │ └─────────────────────────────────┘
          │
T+60 min  │ ┌─────────────────────────────────┐
          │ │ Success Confirmation            │
          │ │ • Metrics review                │
          │ │ • Team sign-off                 │
          │ │ • Stakeholder notification      │
          │ └─────────────────────────────────┘
          │
T+120 min │ POST-DEPLOYMENT
          │ ┌─────────────────────────────────┐
          │ │ • Decommission Redis 7          │
          │ │ • Update documentation          │
          │ │ • Create migration report       │
          │ │ • Begin 30-day monitoring       │
          │ └─────────────────────────────────┘

Total Active Time: ~2 hours
Critical Window: T-0 to T+15 (15 minutes)
User Downtime: ZERO (Blue-Green)
```

#### Commands

```bash
# T-120: Pre-deployment checks
./scripts/migration/pre_migration_check.sh prod
./scripts/migration/health_check.sh prod > prod-pre-migration.txt
./rai redis cli DBSIZE  # Record key count

# T-60: Final backups
./rai db backup prod-backup-$(date +%Y%m%d-%H%M).sql
./rai redis backup > prod-redis-backup-$(date +%Y%m%d-%H%M).rdb

# T-0: Execute migration (Blue-Green)
# Step 1: Deploy Redis 8 alongside Redis 7
docker-compose -f docker-compose.prod.yml up -d redis8

# Step 2: Wait for healthy
./scripts/migration/health_check.sh prod --redis redis8

# Step 3: Switch application configuration
./rai docker exec app update-redis-connection redis8:6379

# Step 4: Restart application (rolling)
./rai docker restart app --rolling

# T+5: Validation
./scripts/migration/health_check.sh prod
./scripts/migration/validate_data.sh prod

# T+30: Extended monitoring (automated)
watch -n 60 './scripts/migration/health_check.sh prod'

# T+120: Decommission old Redis
docker-compose -f docker-compose.prod.yml stop redis7
docker-compose -f docker-compose.prod.yml rm redis7
```

#### Success Criteria

| Timepoint | Criteria | Status |
|-----------|----------|--------|
| **T+5 min** | Health checks: 12/12 pass | ☐ |
| **T+5 min** | Error rate: Unchanged | ☐ |
| **T+5 min** | Response time: Improved | ☐ |
| **T+15 min** | No user-reported issues | ☐ |
| **T+30 min** | Performance validated | ☐ |
| **T+60 min** | All metrics stable | ☐ |
| **T+120 min** | Sign-off received | ☐ |
| **Day 7** | Week 1 report complete | ☐ |
| **Day 30** | Migration success confirmed | ☐ |

---

## Validation & Testing

### Health Check Components

```
12-Point Health Check System
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌─────────────────────────────────────────────┐
│         Infrastructure Layer                 │
├─────────────────────────────────────────────┤
│ 1. Container Health     │ Is Redis running? │
│ 2. Port Binding         │ Is 6379 open?     │
│ 3. Process Status       │ Redis responsive? │
└─────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────┐
│         Redis Server Layer                   │
├─────────────────────────────────────────────┤
│ 4. Ping Response        │ PING → PONG?      │
│ 5. Auth Working         │ Password auth OK? │
│ 6. Memory Usage         │ < 512MB limit?    │
│ 7. Persistence Status   │ AOF healthy?      │
└─────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────┐
│         Application Layer                    │
├─────────────────────────────────────────────┤
│ 8. Client Connectivity  │ App → Redis OK?   │
│ 9. GET Operation        │ Can read data?    │
│ 10. SET Operation       │ Can write data?   │
│ 11. DELETE Operation    │ Can delete data?  │
│ 12. TTL Operation       │ Expiry working?   │
└─────────────────────────────────────────────┘

Script: ./scripts/migration/health_check.sh
Expected: 12/12 PASS
```

### Performance Benchmarking

```
Benchmark Categories
━━━━━━━━━━━━━━━━━━━━

┌──────────────────────┐
│  Command Performance  │
├──────────────────────┤
│ GET                  │  Baseline: 0.05ms
│ SET                  │  Baseline: 0.08ms
│ DELETE               │  Baseline: 0.06ms
│ EXPIRE               │  Baseline: 0.07ms
│ KEYS *               │  Baseline: 1.2ms
│ HGET                 │  Baseline: 0.06ms
│ HSET                 │  Baseline: 0.09ms
└──────────────────────┘

┌──────────────────────┐
│  Throughput          │
├──────────────────────┤
│ Requests/sec         │  Baseline: 50,000
│ Concurrent conns     │  Baseline: 100
│ Memory efficiency    │  Baseline: 150MB/5K keys
└──────────────────────┘

┌──────────────────────┐
│  Latency Percentiles │
├──────────────────────┤
│ P50                  │  Baseline: 0.05ms
│ P95                  │  Baseline: 0.15ms
│ P99                  │  Baseline: 0.5ms
└──────────────────────┘

Expected Improvements:
• GET: 87% faster (0.05ms → 0.006ms)
• SET: 50% faster (0.08ms → 0.04ms)
• Throughput: 2x (50K → 100K req/s)
```

### Data Validation

```
Data Integrity Checks
━━━━━━━━━━━━━━━━━━━━━

1. Key Count Validation
   ┌────────────────────────────┐
   │ Before: DBSIZE             │
   │ After:  DBSIZE             │
   │ Delta:  Should be ~0       │
   └────────────────────────────┘

2. Sample Data Validation
   ┌────────────────────────────┐
   │ • Select 100 random keys   │
   │ • Verify values unchanged  │
   │ • Verify TTLs preserved    │
   │ • Verify data types intact │
   └────────────────────────────┘

3. Pattern Validation
   ┌────────────────────────────┐
   │ • session:* keys exist     │
   │ • conversation:* keys exist│
   │ • llm:cache:* keys exist   │
   │ • rate_limit:* keys exist  │
   └────────────────────────────┘

Script: ./scripts/migration/validate_data.sh
Expected: 100% match rate
```

---

## Rollback & Emergency Response

### Automated Rollback Procedure

```
One-Command Rollback
━━━━━━━━━━━━━━━━━━━━

./scripts/migration/rollback_redis.sh [environment]

Rollback Flow:
━━━━━━━━━━━━━

┌─────────────────────────┐
│ 1. Detect Issue         │
│    Decision to rollback │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ 2. Execute Script       │
│    ./rollback_redis.sh  │
└────────┬────────────────┘
         │
         ├──▶ Stop application
         │
         ├──▶ Stop Redis 8
         │
         ├──▶ Revert config (8 → 7)
         │
         ├──▶ Start Redis 7
         │
         ├──▶ Start application
         │
         ├──▶ Run health checks
         │
         ▼
┌─────────────────────────┐
│ 3. Validate Rollback    │
│    • Health: 12/12 pass │
│    • App functioning    │
│    • Data intact        │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ 4. Notify Team          │
│    • Slack alert sent   │
│    • Incident logged    │
│    • Report generated   │
└─────────────────────────┘

Time to Complete: 2-3 minutes
```

### Manual Rollback Steps

If automated rollback fails:

```bash
# 1. Stop application (prevent writes)
./rai docker stop app worker

# 2. Stop Redis 8
docker-compose stop redis

# 3. Revert docker-compose.yml
sed -i 's/redis:8-alpine/redis:7-alpine/g' docker-compose.yml

# 4. Start Redis 7
docker-compose up -d redis

# 5. Verify Redis 7 running
./rai docker exec redis redis-server --version
# Expected: Redis server v=7.4.6

# 6. Start application
./rai docker start app worker

# 7. Validate
./scripts/migration/health_check.sh prod
```

### Emergency Contacts

```
Escalation Path
━━━━━━━━━━━━━━━

Level 1: Migration Team
├─ Migration Lead: ________________
├─ Database Lead: ________________
└─ DevOps Engineer: ________________
         │
         │ If unresolved in 15 minutes
         ▼
Level 2: Engineering Leadership
├─ Engineering Manager: ________________
├─ Technical Lead: ________________
└─ On-Call Architect: ________________
         │
         │ If unresolved in 30 minutes
         ▼
Level 3: Executive
├─ CTO: ________________
└─ VP Engineering: ________________

Communication Channels:
• Primary: Slack #infrastructure
• Incident: Slack #incidents
• Escalation: PagerDuty / Phone
```

---

## Monitoring & Observability

### 30-Day Monitoring Plan

```
Monitoring Intensity Timeline
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Week 1: INTENSIVE (Day 1-7)
═══════════════════════════════════════
Frequency: Every 4 hours + alerts
│
├─ Day 1:  Hourly monitoring
│          ████████████████████████
│
├─ Day 2:  Every 2 hours
│          ████████░░░░████████░░░░
│
├─ Day 3-7: Every 4 hours
│          ████░░░░░░░░████░░░░░░░░
│
└─ End Week 1 Report

Week 2-4: STANDARD (Day 8-30)
═══════════════════════════════════════
Frequency: Daily checks + alerts
│
├─ Week 2: Daily review
│          ██░░░░░░░░░░██░░░░░░░░░░
│
├─ Week 3: Daily review
│          ██░░░░░░░░░░██░░░░░░░░░░
│
├─ Week 4: Daily review
│          ██░░░░░░░░░░██░░░░░░░░░░
│
└─ End 30-Day Report

Day 30: MIGRATION COMPLETE ✓
```

### Key Metrics to Monitor

```
Metrics Dashboard
━━━━━━━━━━━━━━━━━

┌────────────────────────────────────────┐
│  Redis Performance                      │
├────────────────────────────────────────┤
│ • Commands/sec                         │
│ • Hit rate %                           │
│ • Avg response time                    │
│ • P95 response time                    │
│ • P99 response time                    │
└────────────────────────────────────────┘

┌────────────────────────────────────────┐
│  Resource Usage                         │
├────────────────────────────────────────┤
│ • Memory usage (MB)                    │
│ • Memory % of limit                    │
│ • CPU usage %                          │
│ • Network I/O                          │
│ • Disk I/O (AOF)                       │
└────────────────────────────────────────┘

┌────────────────────────────────────────┐
│  Application Health                     │
├────────────────────────────────────────┤
│ • Error rate %                         │
│ • Connection failures                  │
│ • Timeout rate                         │
│ • Retry attempts                       │
│ • Cache hit rate                       │
└────────────────────────────────────────┘

┌────────────────────────────────────────┐
│  Data Integrity                         │
├────────────────────────────────────────┤
│ • Key count trend                      │
│ • AOF file size                        │
│ • Persistence status                   │
│ • Replication lag (if applicable)     │
└────────────────────────────────────────┘
```

### Alert Configuration

```yaml
# Prometheus Alert Rules
# File: redis-alerts.yml

groups:
  - name: redis_migration
    interval: 30s
    rules:
      - alert: RedisHighMemoryUsage
        expr: redis_memory_used_bytes / redis_memory_max_bytes > 0.9
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Redis memory usage above 90%"

      - alert: RedisHighErrorRate
        expr: rate(redis_errors_total[5m]) > 10
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Redis error rate elevated"

      - alert: RedisSlowCommands
        expr: redis_command_duration_seconds{quantile="0.95"} > 0.001
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Redis P95 latency degraded"

      - alert: RedisConnectionFailures
        expr: rate(redis_connection_errors_total[5m]) > 5
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Redis connection failures detected"
```

---

## Troubleshooting

### Common Issues & Solutions

#### Issue 1: Connection Refused

```
Symptom: Application cannot connect to Redis
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Error: Connection refused on 127.0.0.1:6379

Diagnosis Steps:
1. Check if Redis container is running
   $ docker ps | grep redis

2. Check Redis logs
   $ ./rai docker logs redis --tail 50

3. Verify port binding
   $ netstat -an | grep 6379

4. Test direct connection
   $ redis-cli -h localhost -p 6379 ping

Solutions:
┌────────────────────────────────────────┐
│ If container not running:              │
│   $ ./rai docker restart redis         │
│                                        │
│ If port not bound:                     │
│   Check docker-compose.yml ports       │
│   Restart Docker daemon                │
│                                        │
│ If authentication failing:             │
│   Verify REDIS_PASSWORD env var        │
│   Check redis.conf requirepass         │
└────────────────────────────────────────┘

Prevention:
• Add health checks in docker-compose
• Implement connection retry logic
• Monitor port binding
```

#### Issue 2: Performance Degradation

```
Symptom: Response times slower than baseline
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Observed: P95 latency 10x baseline

Diagnosis Steps:
1. Run performance benchmark
   $ ./scripts/migration/redis_benchmark.sh prod

2. Check memory usage
   $ ./rai redis cli INFO memory

3. Check slow log
   $ ./rai redis cli SLOWLOG GET 10

4. Check for key evictions
   $ ./rai redis cli INFO stats | grep evicted

Solutions:
┌────────────────────────────────────────┐
│ If memory pressure:                    │
│   • Increase maxmemory limit           │
│   • Review key TTLs                    │
│   • Implement cache pruning            │
│                                        │
│ If slow commands:                      │
│   • Optimize KEYS usage → SCAN         │
│   • Batch operations                   │
│   • Add indexes                        │
│                                        │
│ If evictions occurring:                │
│   • Review LRU policy                  │
│   • Increase memory limit              │
│   • Reduce cache size                  │
└────────────────────────────────────────┘

Rollback Consideration:
If degradation > 50% and unfixable → ROLLBACK
```

#### Issue 3: Data Loss or Corruption

```
Symptom: Missing keys or incorrect values
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Observed: Key count mismatch or data discrepancies

Diagnosis Steps:
1. Compare key counts
   $ ./rai redis cli DBSIZE

2. Run data validation
   $ ./scripts/migration/validate_data.sh prod

3. Check AOF integrity
   $ redis-check-aof /data/appendonly.aof

4. Review Redis logs for errors
   $ ./rai docker logs redis | grep -i error

Solutions:
┌────────────────────────────────────────┐
│ CRITICAL: Data Loss Detected           │
│                                        │
│ IMMEDIATE ROLLBACK REQUIRED            │
│                                        │
│ 1. Execute rollback script             │
│    $ ./scripts/migration/rollback      │
│                                        │
│ 2. Restore from backup                 │
│    $ ./rai redis restore backup.rdb    │
│                                        │
│ 3. Validate data integrity             │
│    $ ./scripts/migration/validate      │
│                                        │
│ 4. Investigate root cause              │
│    • Review migration logs             │
│    • Check Redis compatibility         │
│    • Verify backup procedures          │
└────────────────────────────────────────┘

Prevention:
• Always backup before migration
• Validate backups are restorable
• Test migration in non-prod first
• Enable AOF persistence
```

#### Issue 4: High Memory Usage

```
Symptom: Memory usage exceeding limits
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Observed: Memory usage > 90% of maxmemory

Diagnosis Steps:
1. Check current memory usage
   $ ./rai redis cli INFO memory

2. Analyze key distribution
   $ ./rai redis cli --bigkeys

3. Check fragmentation
   $ ./rai redis cli INFO | grep mem_fragmentation_ratio

4. Review eviction policy
   $ ./rai redis cli CONFIG GET maxmemory-policy

Solutions:
┌────────────────────────────────────────┐
│ If legitimate growth:                  │
│   • Increase maxmemory limit           │
│   • Scale horizontally (sharding)      │
│   • Implement cache layers             │
│                                        │
│ If memory leak suspected:              │
│   • Review application code            │
│   • Check for key leaks                │
│   • Verify TTL settings                │
│   • Consider rollback                  │
│                                        │
│ If fragmentation high (>1.5):          │
│   • Schedule Redis restart             │
│   • Enable active defrag              │
│   • Review data patterns               │
└────────────────────────────────────────┘

Monitoring:
• Set alert at 80% memory usage
• Track memory growth rate
• Monitor eviction events
```

#### Issue 5: Authentication Failures

```
Symptom: NOAUTH or AUTH failed errors
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Error: NOAUTH Authentication required

Diagnosis Steps:
1. Check Redis password config
   $ ./rai redis cli CONFIG GET requirepass

2. Verify environment variable
   $ echo $REDIS_PASSWORD

3. Test authentication
   $ redis-cli -a "$REDIS_PASSWORD" ping

4. Check application config
   $ ./rai docker exec app env | grep REDIS

Solutions:
┌────────────────────────────────────────┐
│ If password mismatch:                  │
│   • Verify .env file                   │
│   • Check Doppler secrets              │
│   • Restart application containers     │
│                                        │
│ If password not set in Redis:          │
│   • Update docker-compose.yml          │
│   • Add --requirepass flag             │
│   • Restart Redis container            │
│                                        │
│ If environment variable missing:       │
│   • Check docker-compose env_file      │
│   • Verify secret management           │
│   • Restart affected containers        │
└────────────────────────────────────────┘
```

---

## Scripts & Automation

### Available Scripts

All scripts located in: `/scripts/migration/`

#### 1. Pre-Migration Check Script

**File**: `pre_migration_check.sh`
**Purpose**: Validate environment readiness before migration
**Usage**: `./scripts/migration/pre_migration_check.sh [environment]`

**What it checks**:
- Current Redis version
- Docker/Docker Compose installed
- Sufficient disk space
- Network connectivity
- Backup directory exists
- Required environment variables
- Application health

**Output**: PASS/WARN/FAIL for each check

#### 2. Health Check Script

**File**: `health_check.sh`
**Purpose**: Comprehensive 12-point health validation
**Usage**: `./scripts/migration/health_check.sh [environment]`

**What it checks**:
1. Container running
2. Port binding
3. Process status
4. Ping response
5. Authentication
6. Memory usage
7. Persistence status
8. Client connectivity
9-12. CRUD operations

**Output**: 12/12 checks with detailed status

#### 3. Redis Benchmark Script

**File**: `redis_benchmark.sh`
**Purpose**: Performance comparison before/after migration
**Usage**: `./scripts/migration/redis_benchmark.sh [environment]`

**What it measures**:
- Command latency (GET, SET, DELETE, etc.)
- Throughput (requests/second)
- Concurrent connections
- P50/P95/P99 latencies

**Output**: Comparison table with baseline

#### 4. Data Validation Script

**File**: `validate_data.sh`
**Purpose**: Verify data integrity after migration
**Usage**: `./scripts/migration/validate_data.sh [environment]`

**What it validates**:
- Key count matches
- Sample data integrity
- TTL preservation
- Data type integrity
- Pattern validation

**Output**: Pass/Fail with discrepancy details

#### 5. Rollback Script

**File**: `rollback_redis.sh`
**Purpose**: Automated rollback to Redis 7
**Usage**: `./scripts/migration/rollback_redis.sh [environment]`

**What it does**:
1. Stop application
2. Stop Redis 8
3. Revert configuration
4. Start Redis 7
5. Start application
6. Validate rollback
7. Notify team

**Output**: Success/Failure with detailed log

### Script Execution Flow

```
Typical Migration Script Flow
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. PRE-MIGRATION
   ┌────────────────────────────────┐
   │ pre_migration_check.sh         │
   │ ├─ Environment checks          │
   │ ├─ Dependency checks           │
   │ └─ Resource checks             │
   └────────┬───────────────────────┘
            │ PASS
            ▼
2. BASELINE
   ┌────────────────────────────────┐
   │ health_check.sh (before)       │
   │ redis_benchmark.sh (baseline)  │
   └────────┬───────────────────────┘
            │
            ▼
3. MIGRATION (Manual)
   ┌────────────────────────────────┐
   │ • Update docker-compose.yml    │
   │ • Restart containers           │
   └────────┬───────────────────────┘
            │
            ▼
4. VALIDATION
   ┌────────────────────────────────┐
   │ health_check.sh (after)        │
   │ validate_data.sh               │
   │ redis_benchmark.sh (compare)   │
   └────────┬───────────────────────┘
            │
      ┌─────┴─────┐
      │           │
      ▼ PASS      ▼ FAIL
   SUCCESS     ROLLBACK
               ┌────────────────────┐
               │ rollback_redis.sh  │
               └────────────────────┘
```

---

## Quick Reference

### Essential Commands

```bash
# PRE-MIGRATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
./scripts/migration/pre_migration_check.sh [env]
./scripts/migration/health_check.sh [env] > pre-health.txt
./rai redis cli DBSIZE  # Record key count
./rai redis backup > backup-$(date +%Y%m%d).rdb

# MIGRATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Edit docker-compose.yml: redis:7-alpine → redis:8-alpine
./rai docker down [env]
./rai docker up [env]

# VALIDATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
./scripts/migration/health_check.sh [env]
./scripts/migration/validate_data.sh [env]
./scripts/migration/redis_benchmark.sh [env]

# ROLLBACK
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
./scripts/migration/rollback_redis.sh [env]

# MONITORING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
./rai redis cli INFO
./rai redis cli INFO memory
./rai redis cli INFO stats
./rai redis cli SLOWLOG GET 10
./rai docker logs redis --tail 100 -f
```

### Success Criteria Checklist

```
Migration Success Checklist
━━━━━━━━━━━━━━━━━━━━━━━━━━

Pre-Migration:
☐ Pre-flight checks pass
☐ Baseline metrics recorded
☐ Backups completed
☐ Team notified

Migration:
☐ Redis 8 container running
☐ Version verified (8.0.5)
☐ Application connected
☐ Health checks: 12/12 pass

Validation:
☐ Key count matches
☐ Data integrity verified
☐ Performance improved or equal
☐ Zero errors in logs
☐ TTLs preserved

Post-Migration:
☐ 24h monitoring completed
☐ No user-reported issues
☐ Metrics stable
☐ Documentation updated
☐ Team sign-off received

30-Day Monitoring:
☐ Week 1 report completed
☐ Week 2 check completed
☐ Week 3 check completed
☐ Week 4 check completed
☐ Final report generated
☐ Migration declared success
```

### Time Estimates

| Environment | Pre-Migration | Migration | Validation | Total |
|-------------|---------------|-----------|------------|-------|
| Development | 30 min | 1 hour | 1 hour | **2.5 hours** |
| Testing | 1 hour | 1 hour | 4 hours | **6 hours** |
| Staging | 2 hours | 1 hour | 8 hours | **11 hours** |
| Production | 2 hours | 30 min | 2 hours | **4.5 hours** |

**Plus**:
- Testing: 3 days full QA
- Staging: 5 days soak testing
- Production: 30 days monitoring

---

## Supporting Documentation

### Related Documents

**Keep these specialized documents for reference**:

1. **REDIS_MIGRATION_START_HERE.md**
   - Orientation guide for newcomers
   - Scenarios and FAQ
   - Quick start paths

2. **REDIS_MIGRATION_RUNBOOK_PRODUCTION.md**
   - Production deployment day checklist
   - T-indexed timeline with checkboxes
   - Emergency procedures

3. **REDIS_MIGRATION_POSTMORTEM_TEMPLATE.md**
   - Post-migration analysis framework
   - Lessons learned template
   - Success metrics evaluation

### External Resources

- **Redis 8 Release Notes**: https://github.com/redis/redis/releases/tag/8.0.5
- **Redis Documentation**: https://redis.io/docs/
- **Redis Docker Hub**: https://hub.docker.com/_/redis
- **Redis Migration Guide**: https://redis.io/docs/getting-started/migration/

### Contact Information

**Migration Team**:
- Migration Lead: ________________
- Database Lead: ________________
- DevOps Engineer: ________________
- QA Lead: ________________

**Support Channels**:
- Slack: #infrastructure
- Incidents: #incidents-prod
- Email: infrastructure@company.com

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 2.0 | Nov 23, 2025 | Infrastructure Team | Consolidated from 7 docs, added diagrams |
| 1.0 | Nov 4, 2025 | Infrastructure Team | Initial migration plan created |

---

**End of Document**

*This consolidated guide replaces: REDIS_8_MIGRATION_PLAN.md, REDIS_MIGRATION_INDEX.md, REDIS_MIGRATION_QUICK_REFERENCE.md, REDIS_MIGRATION_DELIVERABLES.md, and related documents. Keep START_HERE.md, RUNBOOK_PRODUCTION.md, and POSTMORTEM_TEMPLATE.md as separate specialized documents.*
