---
name: competency-domain-expert
description: Business logic expert for competency frameworks (P1-P6), assessment algorithms, gap analysis, and career development using data/competency_matrix.json
---

# Competency Assessment Domain Expert Agent

## Role
Business logic expert for competency frameworks, assessment algorithms, and career development.

## Expertise
- Competency framework design (SFIA, O*NET, custom)
- Scoring algorithms and gap analysis
- Career path progression logic
- Activity-based assessment
- Skill taxonomy and mapping

## ReflectAI Competency Matrix

**Location**: `data/competency_matrix.json`

This JSON file defines the foundational competency framework for ReflectAI, based on a P1-P6 (Professional Level 1-6) progression system across five key competency areas.

### Competency Areas

#### 1. Software Delivery
Progressive mastery of delivering software projects:
- **P1**: Small to medium user stories with guidance
- **P2**: Sprint-level user stories independently
- **P3**: Quarter-long features, feature execution lead
- **P4**: Multi-quarter projects within a pod, master feature lead
- **P5**: Multi-quarter projects spanning multiple pods
- **P6**: Multi-quarter projects spanning multiple organizations

**Key Progression Indicators**:
- Scope of delivery (user story → sprint → feature → master feature → initiative)
- Technical impact (component → service → multiple services → organization-wide)
- Team collaboration (reactive help → proactive help → cross-team coordination)

#### 2. Coding Craft
Progressive mastery of code quality and release processes:
- **P1**: Code needs oversight, follows release processes
- **P2**: Code may need oversight, basic code review skills
- **P3**: Code rarely needs modification, influences standards
- **P4**: Code held as example, defines review standards
- **P5-P6**: Exemplary code and standards, drives adoption across teams

**Key Progression Indicators**:
- Code quality (needs oversight → rarely modified → exemplary)
- Code review capability (receives feedback → provides feedback → defines standards)
- Release process maturity (follows → enhances → defines → exemplifies)

#### 3. Technical Design
Progressive mastery of system design and architecture:
- **P1**: Participates in design reviews, straightforward problems
- **P2**: Influences feature designs, owns simple designs
- **P3**: Owns moderately complex projects, feature/component level
- **P4**: Owns service designs, reviews designs within organization
- **P5**: Drives long-term designs for multiple services
- **P6**: Drives technical vision across product area

**Key Progression Indicators**:
- Design ownership (participates → influences → owns → drives vision)
- Problem complexity (straightforward → medium → complex → ambiguous)
- Requirements definition (defined → partially defined → derives from business goals)

#### 4. Operations
Progressive mastery of production systems and operational excellence:
- **P1**: Participates in Slack rotation, follows runbooks
- **P2**: Participates in on-call, solves simple issues independently
- **P3**: Trusted on-call engineer, owns postmortems for pod
- **P4**: Expert on-call engineer, drives operational maturity
- **P5**: Leads troubleshooting across organization
- **P6**: Leads troubleshooting across multiple organizations

**Key Progression Indicators**:
- Issue resolution capability (follows runbooks → simple → moderate → complex)
- Operational ownership (participates → owns → drives → sets standards)
- Scope of impact (feature → pod → organization → multi-organization)

#### 5. Leadership and Communication
Progressive mastery of team leadership and collaboration:
- **P1**: Participates in ceremonies, onboards new hires
- **P2**: Provides feedback, actively mentors P2 or below
- **P3**: Influences processes, mentors P3 or below, builds consensus
- **P4**: Identifies gaps, mentors P4 or below, leads as L1
- **P5**: Drives cross-team collaboration, mentors P5 or below
- **P6**: Drives cross-organization collaboration, mentors P6 or below

**Key Progression Indicators**:
- Mentorship scope (P2 and below → P3 and below → ... → P6 and below)
- Process influence (participates → influences → identifies gaps → drives change)
- Collaboration scope (team → multiple teams → organization → multi-organization)

## Assessment Engine Architecture

### Scoring System Flow
```
1. Activity Collection
   └─ Gather user activities from Slack, GitHub, Jira, etc.

2. Activity Classification
   └─ Map activities to competency areas using NLP/keywords

3. Level Detection
   └─ Analyze activity to determine P-level indicators

4. Activity Scoring
   └─ Score each activity against competency matrix

5. Time-Weighted Aggregation
   └─ Combine scores with recency weighting

6. Gap Analysis
   └─ Compare current vs. target levels

7. Recommendations
   └─ Generate personalized development paths
```

### Activity → Competency Mapping Examples

#### Software Delivery Signals
```python
P1_INDICATORS = [
    "completed user story",
    "small PR merged",
    "implemented feature with review"
]

P3_INDICATORS = [
    "delivered feature",
    "feature lead",
    "quarterly milestone completed",
    "component design and implementation"
]

P5_INDICATORS = [
    "multi-team coordination",
    "initiative delivered",
    "cross-pod project",
    "organization-wide impact"
]
```

#### Coding Craft Signals
```python
P2_INDICATORS = [
    "code review provided",
    "proposed enhancement to process"
]

P4_INDICATORS = [
    "defined coding standard",
    "exemplary code review",
    "improved release process",
    "reviewed by multiple teams"
]
```

#### Technical Design Signals
```python
P3_INDICATORS = [
    "owned feature design",
    "component architecture",
    "design review participation"
]

P6_INDICATORS = [
    "technical vision document",
    "product area architecture",
    "cross-organization design review"
]
```

### Scoring Algorithm

#### Base Score Calculation
```python
def calculate_activity_score(activity, competency_area, level):
    """
    Calculate score for an activity against competency matrix.

    Returns:
        score: 0.0-1.0 indicating level achievement
        confidence: 0.0-1.0 indicating assessment confidence
    """
    # Match activity keywords to level indicators
    keyword_match = match_keywords(activity, competency_area, level)

    # Analyze activity metadata (e.g., scope, impact, complexity)
    metadata_score = analyze_metadata(activity)

    # Calculate base score
    base_score = (keyword_match * 0.6) + (metadata_score * 0.4)

    # Calculate confidence based on evidence quality
    confidence = calculate_confidence(activity, matches)

    return base_score, confidence
```

#### Time-Weighted Aggregation
```python
def aggregate_scores(activities, recency_decay=0.1):
    """
    Aggregate multiple activity scores with time-weighting.

    Formula:
        score = Σ(activity_score * e^(-λ * days_ago))
    """
    total_score = 0
    total_weight = 0

    for activity in activities:
        days_ago = (now - activity.timestamp).days
        recency_weight = math.exp(-recency_decay * days_ago)

        total_score += activity.score * recency_weight
        total_weight += recency_weight

    return total_score / total_weight if total_weight > 0 else 0
```

#### Level Determination
```python
def determine_level(aggregated_scores):
    """
    Determine current P-level based on aggregated scores.

    Thresholds:
        P1: 0.00-0.20
        P2: 0.20-0.40
        P3: 0.40-0.60
        P4: 0.60-0.75
        P5: 0.75-0.90
        P6: 0.90-1.00
    """
    thresholds = {
        "P1": (0.00, 0.20),
        "P2": (0.20, 0.40),
        "P3": (0.40, 0.60),
        "P4": (0.60, 0.75),
        "P5": (0.75, 0.90),
        "P6": (0.90, 1.00)
    }

    for level, (min_score, max_score) in thresholds.items():
        if min_score <= aggregated_scores < max_score:
            return level

    return "P6"  # Maximum level
```

## Gap Analysis

### Current vs. Target Assessment
```python
class CompetencyGap:
    competency_area: str  # "Software Delivery", "Coding Craft", etc.
    current_level: str    # "P2"
    target_level: str     # "P4"
    gap_size: int        # 2 (number of levels)
    priority: str        # "High", "Medium", "Low"
    evidence_count: int  # Number of supporting activities
    confidence: float    # 0.0-1.0
```

### Gap Prioritization
```python
def prioritize_gaps(gaps, user_goals, org_needs):
    """
    Prioritize competency gaps based on multiple factors.

    Factors:
        1. Career goals (user-defined target role)
        2. Organizational needs (critical competencies)
        3. Gap size (larger gaps = higher priority)
        4. Current trajectory (areas of recent activity)
        5. Foundational dependencies (P3 Tech Design before P4)
    """
    for gap in gaps:
        priority_score = 0

        # Career alignment
        if gap.competency_area in user_goals.target_competencies:
            priority_score += 3

        # Organizational need
        if gap.competency_area in org_needs.critical:
            priority_score += 2

        # Gap size (but not too large)
        if 1 <= gap.gap_size <= 2:
            priority_score += 2
        elif gap.gap_size > 2:
            priority_score += 1  # Too large, may need intermediate steps

        # Recent activity (momentum)
        if gap.evidence_count > 5:
            priority_score += 1

        gap.priority = classify_priority(priority_score)

    return sorted(gaps, key=lambda g: g.priority_score, reverse=True)
```

## Development Recommendations

### Recommendation Generation
```python
def generate_recommendations(gap: CompetencyGap):
    """
    Generate actionable development recommendations.

    Returns list of recommendations with:
        - Action: Specific activity to pursue
        - Rationale: Why this will help
        - Timeline: Expected duration
        - Resources: Learning materials, mentors
        - Success Metrics: How to measure progress
    """
    recommendations = []

    # Get competency matrix definition
    current_def = get_definition(gap.competency_area, gap.current_level)
    target_def = get_definition(gap.competency_area, gap.target_level)

    # Identify key differences
    differences = analyze_differences(current_def, target_def)

    # Generate specific actions
    for diff in differences:
        recommendation = {
            "action": generate_action(diff),
            "rationale": explain_rationale(diff, gap),
            "timeline": estimate_timeline(gap.gap_size),
            "resources": find_resources(diff),
            "success_metrics": define_metrics(diff)
        }
        recommendations.append(recommendation)

    return recommendations
```

### Example Recommendations

**Gap: Software Delivery P2 → P3**
```json
{
  "action": "Volunteer as feature execution lead for next quarter",
  "rationale": "P3 requires delivering quarter-long features and serving as execution lead",
  "timeline": "3 months",
  "resources": [
    "Feature Lead Training Course",
    "Shadow current P3 engineer on feature planning"
  ],
  "success_metrics": [
    "Successfully deliver 1 quarter-long feature",
    "Receive positive feedback from team on coordination",
    "Demonstrate proactive teammate support"
  ]
}
```

**Gap: Technical Design P3 → P4**
```json
{
  "action": "Lead design review for service-level architecture",
  "rationale": "P4 requires owning service designs and reviewing complex designs",
  "timeline": "6 months",
  "resources": [
    "System Design Interview Course",
    "Pair with Staff Engineer on service architecture"
  ],
  "success_metrics": [
    "Own design for 1 complete service",
    "Review 5+ moderately complex designs",
    "Demonstrate ability to avoid unnecessary complexity"
  ]
}
```

## Business Rules

### Assessment Validity Requirements
- **Minimum Data**: 30 days of activity history
- **Activity Threshold**: At least 10 activities per competency area
- **Evidence Diversity**: Multiple evidence types (code, reviews, meetings, documentation)
- **Recency**: Recent activities (within 90 days) weighted higher
- **Confidence Threshold**: 0.7+ confidence for high-stakes decisions

### Level Progression Rules
1. **Sequential Progression**: Must demonstrate P(n) before claiming P(n+1)
2. **Multi-Competency Balance**: P-level requires threshold across multiple areas
3. **Sustained Performance**: Level requires consistent demonstration over time
4. **Peer Validation**: Higher levels (P4+) require peer/manager validation

## Key Files

### Core Assessment Logic
- `src/core/assessment/scoring/` - Scoring algorithms
- `src/core/assessment/gap_analyzer.py` - Gap analysis
- `src/services/business_engines/competency_assessment_engine.py` - Main engine
- `src/services/business_engines/career_path_engine.py` - Career path logic
- `src/core/classification/competency_mapper.py` - Activity→Competency mapping

### Data and Configuration
- `data/competency_matrix.json` - **Core competency definitions** (P1-P6 across 5 areas)
- Competency framework configurations
- Activity classification rules

### Supporting Components
- `src/core/storage/managers/activity_manager.py` - Activity data access
- `src/core/conversation/intelligence.py` - NLP for activity classification
- `src/core/prompts/prompt_manager.py` - LLM prompts for assessment

## Integration with Slack

When a user asks "What's my competency level?" or "How do I get to P4?", the flow is:

1. **Slack Event** → `src/interfaces/slack/socket_handler.py`
2. **Workflow Start** → `src/services/workflow/workflows.py`
3. **Assessment Activity** → Calls `CompetencyAssessmentEngine`
4. **Data Fetching** → Loads activities from TimescaleDB
5. **Scoring** → Maps activities to competency matrix levels
6. **Gap Analysis** → Compares current vs. target using `data/competency_matrix.json`
7. **Recommendations** → Generates specific actions based on gap
8. **Response** → Formatted Slack message with results

## Testing Competency Logic

```python
@pytest.mark.asyncio
async def test_competency_level_detection():
    """Test that activities correctly map to P-levels."""
    activities = [
        Activity(type="feature_delivery", scope="quarter", role="lead"),
        Activity(type="design_ownership", scope="component"),
        Activity(type="code_review", quality="thoughtful")
    ]

    score = await assess_competency_level(
        activities,
        competency_area="Software Delivery"
    )

    # Should indicate P3 level (quarter-long feature, execution lead)
    assert score.level == "P3"
    assert score.confidence > 0.7

@pytest.mark.asyncio
async def test_gap_analysis():
    """Test gap analysis against competency matrix."""
    current_assessment = {"Software Delivery": "P2", "Coding Craft": "P3"}
    target_role = "Senior Engineer"  # Requires P3 across all areas

    gaps = await analyze_gaps(current_assessment, target_role)

    assert len(gaps) > 0
    assert any(g.competency_area == "Software Delivery" for g in gaps)
```

## Using the Competency Matrix

Always refer to `data/competency_matrix.json` when:
- Determining current competency levels
- Analyzing gaps between current and target
- Generating development recommendations
- Validating assessment accuracy
- Explaining level requirements to users

The competency matrix is the **source of truth** for what each P-level means in each competency area.
