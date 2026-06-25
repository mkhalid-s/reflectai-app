---
description: Analyze module dependencies, coupling, integration points, and generate refactoring recommendations
---

# Analyze Dependencies - Module Dependency Analysis

Analyze module dependencies, coupling, and integration points: $ARGUMENTS

## Analysis Process

### Step 1: Module Identification (30 sec)
1. **Validate module path** - Ensure file exists
2. **Identify module type** - Core, service, interface, infrastructure
3. **Read module code** - Understand module purpose
4. **Extract imports** - Both internal and external

### Step 2: Dependency Mapping (2-3 min)
1. **Internal dependencies** - Other ReflectAI modules used
2. **External dependencies** - Third-party packages
3. **Service dependencies** - Database, Redis, LLM, Temporal, Slack
4. **Reverse dependencies** - What depends on this module
5. **Circular dependencies** - Identify dependency cycles

### Step 3: Coupling Analysis (2 min)
1. **Direct coupling** - Explicit imports and calls
2. **Indirect coupling** - Shared state or global variables
3. **Data coupling** - Shared data structures
4. **Interface coupling** - API contracts
5. **Temporal coupling** - Execution order dependencies

### Step 4: Integration Points (2 min)
1. **Database integration** - Tables, queries, models
2. **Cache integration** - Redis keys and patterns
3. **LLM integration** - Provider usage and costs
4. **Workflow integration** - Temporal workflows/activities
5. **API integration** - External service calls

### Step 5: Recommendations (1 min)
1. **Decoupling opportunities** - Reduce tight coupling
2. **Interface improvements** - Better abstractions
3. **Refactoring suggestions** - Code organization
4. **Testing strategies** - How to test independently
5. **Risk assessment** - Impact of changes

## Example Output

```markdown
# 🔗 Dependency Analysis: src/core/assessment/competency_assessor.py

## Module Overview
**Type**: Core Business Logic
**Purpose**: Assess user competency levels based on activity data
**Lines of Code**: 345
**Complexity**: High

---

## Internal Dependencies (ReflectAI Modules)

### Direct Dependencies (8 modules)
```python
# Core modules
from src.core.assessment.gap_analyzer import GapAnalyzer
from src.core.assessment.level_calculator import LevelCalculator
from src.core.assessment.scoring import ActivityScorer

# Storage layer
from src.core.storage.managers.activity_manager import ActivityManager
from src.core.storage.managers.framework_manager import FrameworkManager

# Shared utilities
from src.shared.exceptions import ValidationError, DatabaseError
from src.shared.logging import get_logger
from src.shared.error_handlers import retry_with_exponential_backoff
```

**Dependency Level**: Medium (8 direct dependencies)

### Dependency Graph
```
competency_assessor.py
├── gap_analyzer.py (core/assessment)
├── level_calculator.py (core/assessment)
├── scoring/ (core/assessment)
│   ├── activity_scorer.py
│   └── score_aggregator.py
├── activity_manager.py (storage)
├── framework_manager.py (storage)
└── shared/
    ├── exceptions.py
    ├── logging.py
    └── error_handlers.py
```

### Reverse Dependencies (Used by 12 modules)
```python
# Services
src/services/business_engines/competency_assessment_engine.py
src/services/agents/analysis_agent.py
src/services/workflow/activities.py

# Interfaces
src/interfaces/slack/handlers.py
src/interfaces/slack/slash_commands.py

# Core
src/core/business/analytics_engine.py
src/core/business/reporting_engine.py

# ... 5 more
```

**Impact Score**: High (12 modules depend on this)

---

## External Dependencies (Third-party)

### Required Packages
- `pydantic` (v2.5.0+) - Data validation
- `numpy` (v1.24.0+) - Numerical calculations
- `scipy` (v1.11.0+) - Statistical analysis

### Usage Patterns
```python
# Pydantic for models
class AssessmentResult(BaseModel):
    user_id: str
    level: CompetencyLevel
    score: float

# NumPy for calculations
scores_array = np.array(scores)
mean_score = np.mean(scores_array)

# SciPy for statistical analysis
from scipy import stats
correlation = stats.pearsonr(x, y)
```

---

## Service Dependencies

### Database (PostgreSQL)
**Tables Used**:
- `activities` - User activity records
- `frameworks` - Competency frameworks
- `assessments` - Historical assessments
- `user_progress` - Progress tracking

**Query Patterns**:
- Complex joins across activities and frameworks
- Time-range queries for activity aggregation
- Aggregations for score calculations

**Connection**: Via `ActivityManager` and `FrameworkManager`

### Cache (Redis)
**Keys Used**:
- `assessment:{user_id}:{framework_id}` - Cached results
- `scores:{user_id}:{period}` - Score cache
- `framework:{framework_id}` - Framework definition

**TTL**: 1 hour for assessments, 24 hours for frameworks

### LLM Integration
**Usage**: Gap analysis and recommendations
**Provider**: OpenAI (GPT-4)
**Cost Impact**: ~$1.20 per assessment
**Fallback**: Rule-based analysis if LLM fails

### Temporal Workflows
**Workflows**:
- `competency_assessment_workflow` - Long-running assessments
- `bulk_assessment_workflow` - Batch processing

**Activities**:
- `assess_user_activity` - Individual assessment
- `generate_recommendations_activity` - AI recommendations

---

## Coupling Analysis

### Coupling Score: 6/10 (Medium)

**Tight Coupling** 🔴
1. **GapAnalyzer**: Direct instantiation, no interface
   ```python
   # Current:
   analyzer = GapAnalyzer()

   # Recommendation: Dependency injection
   def __init__(self, gap_analyzer: IGapAnalyzer):
       self.gap_analyzer = gap_analyzer
   ```

2. **Storage Managers**: Direct database access
   - Tightly coupled to ActivityManager implementation
   - Hard to test without real database

**Loose Coupling** ✅
1. **Shared utilities**: Well abstracted (exceptions, logging)
2. **LLM integration**: Via gateway pattern
3. **Configuration**: Environment-based, injectable

### Circular Dependencies
❌ **None found** - Good!

### Hidden Dependencies
⚠️  **Global State**:
- Module-level logger (acceptable pattern)
- No other global state detected

---

## Integration Points

### Database Integration
**Complexity**: High

**Queries**:
```sql
-- Activity aggregation (most expensive query)
SELECT
    competency_id,
    COUNT(*) as activity_count,
    AVG(quality_score) as avg_score
FROM activities
WHERE user_id = $1
  AND timestamp >= $2
GROUP BY competency_id

-- Framework lookup
SELECT * FROM frameworks WHERE framework_id = $1

-- Historical assessments
SELECT * FROM assessments
WHERE user_id = $1
ORDER BY created_at DESC
LIMIT 10
```

**Performance**:
- Activity query: ~150ms (needs optimization)
- Framework lookup: ~5ms (cached)
- Historical query: ~20ms

### Cache Integration
**Cache Hit Rate**: 35% (target: 50%+)

**Caching Strategy**:
- Assessment results: 1 hour TTL
- Framework definitions: 24 hour TTL
- Activity scores: 30 minutes TTL

**Recommendation**: Increase TTL for stable frameworks to 7 days

### LLM Integration
**Cost Per Assessment**: $1.20
**Monthly Cost**: ~$680 (560 assessments/month)

**Optimization Opportunities**:
- Cache common gap patterns: Save $240/month
- Use GPT-3.5 for simple gaps: Save $180/month
- Batch similar assessments: Save $95/month

**Total Savings Potential**: $515/month (76% reduction)

---

## Dependency Issues

### 🔴 Critical Issues

1. **Direct Database Access**
   - Module directly uses storage managers
   - Difficult to test without database
   - **Fix**: Add repository interface layer

2. **No Dependency Injection**
   - Hard-coded dependencies
   - Cannot swap implementations
   - **Fix**: Use constructor injection

### 🟡 Medium Issues

1. **Circular Import Risk**
   - `competency_assessor` imports `analytics_engine`
   - `analytics_engine` imports assessment models
   - Not currently circular, but risky
   - **Fix**: Extract shared models to common module

2. **Hidden Database Complexity**
   - Complex SQL joins embedded in managers
   - Performance implications not obvious
   - **Fix**: Add query performance monitoring

### 🟢 Low Issues

1. **Missing Type Hints**
   - Some function parameters lack type hints
   - **Fix**: Add type annotations

---

## Refactoring Recommendations

### Priority 1: Dependency Injection (2 hours)
```python
# Current:
class CompetencyAssessor:
    def __init__(self):
        self.activity_manager = ActivityManager()
        self.framework_manager = FrameworkManager()
        self.gap_analyzer = GapAnalyzer()

# Recommended:
class CompetencyAssessor:
    def __init__(
        self,
        activity_manager: IActivityManager,
        framework_manager: IFrameworkManager,
        gap_analyzer: IGapAnalyzer
    ):
        self.activity_manager = activity_manager
        self.framework_manager = framework_manager
        self.gap_analyzer = gap_analyzer
```

**Benefits**:
- Easier testing with mocks
- Flexible implementations
- Better separation of concerns

### Priority 2: Repository Pattern (3 hours)
Add repository layer between assessment logic and storage:

```python
class AssessmentRepository:
    """Repository for assessment data access."""

    async def get_user_activities(
        self,
        user_id: str,
        date_range: DateRange
    ) -> List[Activity]:
        """Get activities with proper abstraction."""
        pass

    async def save_assessment(
        self,
        assessment: Assessment
    ) -> None:
        """Save assessment result."""
        pass
```

### Priority 3: Extract Interfaces (1 hour)
Define clear interfaces for all dependencies:

```python
# interfaces/assessment.py
class IGapAnalyzer(Protocol):
    async def analyze_gaps(
        self,
        current_skills: List[Skill],
        required_skills: List[Skill]
    ) -> GapAnalysis:
        ...

class ILevelCalculator(Protocol):
    def calculate_level(
        self,
        scores: List[float]
    ) -> CompetencyLevel:
        ...
```

---

## Testing Strategy

### Current Testability: 5/10 (Medium-Low)

**Challenges**:
- Requires real database for testing
- Hard-coded dependencies difficult to mock
- LLM calls need mocking
- Complex setup required

### Improved Testability (After Refactoring): 9/10

**Unit Tests** (with dependency injection):
```python
@pytest.fixture
def mock_activity_manager():
    manager = AsyncMock(spec=IActivityManager)
    manager.get_activities.return_value = [mock_activity()]
    return manager

@pytest.mark.asyncio
async def test_assess_competency(mock_activity_manager):
    assessor = CompetencyAssessor(
        activity_manager=mock_activity_manager,
        framework_manager=mock_framework_manager,
        gap_analyzer=mock_gap_analyzer
    )

    result = await assessor.assess("user123", "framework456")

    assert result.level == CompetencyLevel.INTERMEDIATE
```

**Integration Tests**:
- Use testcontainers for database
- Mock LLM responses
- Test with realistic data

---

## Impact Assessment

### Change Risk: HIGH

**Why High Risk**:
- Used by 12 other modules
- Core business logic
- Complex database interactions
- LLM integration

**Mitigation Strategies**:
1. **Comprehensive testing**: 90%+ coverage before changes
2. **Gradual refactoring**: Small, incremental changes
3. **Feature flags**: Toggle new implementation
4. **A/B testing**: Validate results match old implementation

### Performance Impact

**Current Performance**:
- Average assessment time: 280ms
- P95: 450ms
- Database: 150ms (54%)
- LLM: 100ms (36%)
- Computation: 30ms (10%)

**Optimization Opportunities**:
- Cache framework lookups: Save 50ms
- Parallel LLM calls: Save 40ms
- Database query optimization: Save 60ms

**Potential**: 280ms → 130ms (54% faster)

---

## Decoupling Roadmap

### Phase 1: Add Interfaces (Week 1)
- Define protocols for all dependencies
- No breaking changes
- **Effort**: 4 hours

### Phase 2: Dependency Injection (Week 2)
- Convert to constructor injection
- Update all callers
- **Effort**: 8 hours

### Phase 3: Repository Pattern (Week 3)
- Add repository layer
- Migrate database access
- **Effort**: 12 hours

### Phase 4: Optimize (Week 4)
- Add caching
- Optimize queries
- Parallel operations
- **Effort**: 6 hours

**Total Effort**: 30 hours over 4 weeks

---

## Summary

### Strengths ✅
- Good use of shared utilities
- No circular dependencies
- Proper error handling
- Structured logging

### Weaknesses ❌
- Tight coupling to storage layer
- No dependency injection
- Hard to test in isolation
- High LLM costs

### Recommendations
1. **Immediate**: Add dependency injection
2. **Short-term**: Implement repository pattern
3. **Long-term**: Optimize LLM usage and caching

**Overall Dependency Health**: 6/10 (Needs improvement)
```

## Dependency Analysis Checklist

- [ ] All internal dependencies identified
- [ ] External package dependencies listed
- [ ] Service dependencies mapped
- [ ] Reverse dependencies found
- [ ] Coupling score calculated
- [ ] Integration points documented
- [ ] Refactoring opportunities identified
- [ ] Testing strategy defined
- [ ] Impact assessment completed

Remember: Low coupling and high cohesion make code maintainable!
