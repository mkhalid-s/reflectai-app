# Multi-Agent System Architecture

## Overview

ReflectAI's Phase 1 implementation uses a simplified 2-agent system (Analysis Agent + Advisor Agent) orchestrated by Temporal workflows. This provides accurate competency analysis without the complexity overhead of 4 specialized agents. CrewAI orchestration is deferred until >500 requests/day when complexity becomes justified.

## Enhanced Workflow Engine Integration

### Current Enhanced Agent Capabilities

The system includes an **Enhanced Workflow Engine** that preserves all core functionality while adding intelligent natural language understanding:

#### **Advanced Intent Analysis**
```python
class UserIntent(Enum):
    # Core functionality (preserved)
    CLASSIFY_ACTIVITY = "classify_activity"
    SUMMARIZE_CONTENT = "summarize_content"
    STORE_ACTIVITY = "store_activity"
    GENERATE_REPORT = "generate_report"

    # Enhanced capabilities (new)
    ANALYZE_AND_STORE = "analyze_and_store"  # Full workflow
    COMPREHENSIVE_ANALYSIS = "comprehensive_analysis"  # 2-agent workflow trigger
    CLARIFICATION_NEEDED = "clarification_needed"  # Interactive follow-up
    GENERAL_QUESTION = "general_question"  # Conversational support
```

#### **Intelligent Routing Logic**
```python
# Enhanced agent can handle follow-up questions and clarifications
async def _analyze_user_intent(self, context: WorkflowContext):
    """LLM-powered intent analysis with confidence scoring"""

    # Returns structured analysis with:
    # - Intent classification
    # - Confidence score (0-1)
    # - Extracted content
    # - Follow-up questions for clarification
    # - Reasoning for transparency
```

#### **Interactive Capabilities**
The enhanced agent can:
- ✅ **Ask clarifying questions** when intent is unclear
- ✅ **Provide follow-up suggestions** based on user context
- ✅ **Handle conversational requests** beyond simple commands
- ✅ **Preserve all existing functionality** while adding intelligence
- ✅ **Route complex requests** to 2-agent Temporal workflow when needed

### 2-Agent Workflow Triggers

The enhanced workflow engine determines when to escalate to 2-agent processing:

```python
# Automatic escalation to Analysis + Advisor agents via Temporal workflow
TWO_AGENT_TRIGGERS = [
    "comprehensive analysis",
    "detailed assessment", 
    "promotion readiness evaluation",
    "career development planning",
    "skill gap analysis with recommendations",
    "complex competency matrix analysis"
]

# Enhanced agent handles standard requests
SINGLE_AGENT_REQUESTS = [
    "classify this activity",
    "summarize content", 
    "store activity",
    "generate standard report",
    "get role requirements",
    "show my activities"
]

# UPGRADE PATH: When >500 requests/day, split to 4 specialized agents with CrewAI
```

## Agent Specializations

### 1. Data Analyst Agent
**Role**: Senior Data Analyst
**Specialization**: Historical data analysis and trend identification

**Capabilities**:
- User activity data retrieval and analysis
- Performance trend identification
- Statistical competency modeling
- Benchmarking against industry standards

**Tools**:
- `EnhancedDataRetrievalTool()`: Advanced database queries
- `TrendAnalysisTool()`: Time-series analysis
- `StatisticalAnalysisTool()`: Statistical modeling

### 2. Competency Specialist Agent
**Role**: Competency Assessment Specialist
**Specialization**: Activity classification and skill evaluation

**Capabilities**:
- Activity classification into competency domains
- Skill level assessment and rating
- Gap analysis and improvement identification
- Industry standard comparisons

**Tools**:
- `AdvancedClassificationTool()`: ML-powered classification
- `BenchmarkingTool()`: Industry benchmarking
- `SkillGapAnalysisTool()`: Gap identification

### 3. Career Strategist Agent
**Role**: Senior Career Development Strategist
**Specialization**: Career planning and advancement

**Capabilities**:
- Promotion readiness evaluation
- Career path recommendations
- Development plan creation
- Strategic guidance and mentoring advice

**Tools**:
- `CareerPathAnalysisTool()`: Career trajectory analysis
- `PromotionReadinessTool()`: Readiness assessment
- `DevelopmentPlanTool()`: Personalized plans

### 4. Insights Synthesizer Agent
**Role**: Executive Insights Synthesizer
**Specialization**: Multi-faceted analysis synthesis

**Capabilities**:
- Cross-agent result synthesis
- Report generation and formatting
- Visualization and presentation
- Actionable recommendation creation

**Tools**:
- `ReportSynthesisTool()`: Report generation
- `VisualizationTool()`: Data visualization
- `RecommendationEngineTool()`: AI recommendations

## Intelligent Request Routing with Model Optimization

### Enhanced Complexity Analysis Algorithm

```python
def analyze_request_complexity(message: str, user_context: dict) -> RequestAnalysis:
    """Determine processing approach and optimal models"""

    # Multi-agent trigger keywords
    multi_agent_keywords = [
        "comprehensive", "detailed", "full report",
        "competency report", "career analysis",
        "promotion readiness", "development plan"
    ]

    # Simple query patterns
    simple_patterns = [
        "classify", "what is", "how do",
        "help me", "explain", "define"
    ]

    message_lower = message.lower()
    word_count = len(message.split())

    # Determine processing approach
    if any(keyword in message_lower for keyword in multi_agent_keywords):
        processing_type = "multi_agent"
        complexity = "high"
    elif word_count > 30:
        processing_type = "multi_agent"
        complexity = "medium"
    elif any(pattern in message_lower for pattern in simple_patterns):
        processing_type = "single_agent"
        complexity = "low"
    else:
        processing_type = "single_agent"
        complexity = "medium"

    return RequestAnalysis(
        processing_type=processing_type,
        complexity=complexity,
        estimated_tokens=estimate_token_usage(message, complexity),
        recommended_models=select_optimal_models(processing_type, complexity)
    )

def select_optimal_models(processing_type: str, complexity: str) -> dict:
    """Select optimal models based on processing requirements"""

    if processing_type == "single_agent":
        if complexity == "low":
            return {"primary": "gpt-4.1-nano", "expected_time": "1-2s", "cost": "$0.01"}
        elif complexity == "medium":
            return {"primary": "gpt-4o-mini", "expected_time": "2-3s", "cost": "$0.02"}
        else:
            return {"primary": "gpt-4o", "expected_time": "3-5s", "cost": "$0.05"}

    else:  # multi_agent
        return {
            "data_analyst": "gpt-4o-mini",
            "competency_specialist": "anthropic.claude-3-5-haiku-20241022-v1:0",
            "career_strategist": "gpt-4o-mini",
            "insights_synthesizer": "gpt-4o",
            "expected_time": "5-10s",
            "cost": "$0.15-0.40"
        }
```

### Model-Optimized Agent Configurations

#### **Data Analyst Agent - Speed Optimized**
```python
class OptimizedDataAnalystAgent:
    def __init__(self):
        self.model_config = {
            "primary_model": "gpt-4o-mini",
            "fallback_model": "gpt-3.5-turbo",
            "premium_model": "gpt-4o",
            "max_tokens": 4096,
            "temperature": 0.1,
            "timeout": 30,
            "expected_response_time": "2-3 seconds",
            "cost_per_1k_tokens": 0.15
        }

    async def analyze_user_data(self, user_activities: List[str]) -> DataAnalysis:
        """Fast data analysis with cost optimization"""

        # Use batch processing for multiple activities
        if len(user_activities) > 3:
            return await self.batch_analyze_activities(user_activities)
        else:
            return await self.individual_analyze_activities(user_activities)
```

#### **Competency Specialist Agent - Quality Optimized**
```python
class OptimizedCompetencySpecialistAgent:
    def __init__(self):
        self.model_config = {
            "primary_model": "anthropic.claude-3-5-haiku-20241022-v1:0",
            "fallback_model": "gpt-4o-mini",
            "premium_model": "anthropic.claude-3-5-sonnet-20241022-v2:0",
            "max_tokens": 4096,
            "temperature": 0.1,
            "timeout": 45,
            "expected_response_time": "3-5 seconds",
            "cost_per_1k_tokens": 0.25
        }

    async def classify_competencies(self, activities: List[str]) -> CompetencyClassification:
        """High-quality competency classification with nuanced understanding"""

        # Use Claude for better technical skill understanding
        classification_prompt = self.build_classification_prompt(activities)
        return await self.llm_client.invoke_with_model(
            self.model_config["primary_model"],
            classification_prompt
        )
```

#### **Career Strategist Agent - Balanced Optimization**
```python
class OptimizedCareerStrategistAgent:
    def __init__(self):
        self.model_config = {
            "primary_model": "gpt-4o-mini",
            "fallback_model": "gpt-4.1-mini",
            "premium_model": "gpt-4o",
            "max_tokens": 4096,
            "temperature": 0.2,
            "timeout": 60,
            "expected_response_time": "4-7 seconds",
            "cost_per_1k_tokens": 0.15
        }

    async def develop_career_strategy(self, competency_analysis: dict,
                                   user_goals: str) -> CareerStrategy:
        """Balanced career planning with good reasoning at reasonable cost"""

        # Upgrade to premium model for complex career planning
        if self.is_complex_career_request(user_goals):
            model = self.model_config["premium_model"]
        else:
            model = self.model_config["primary_model"]

        return await self.generate_career_recommendations(model, competency_analysis, user_goals)
```

#### **Insights Synthesizer Agent - Quality Focused**
```python
class OptimizedInsightsSynthesizerAgent:
    def __init__(self):
        self.model_config = {
            "primary_model": "gpt-4o",
            "fallback_model": "gpt-4o-mini",
            "premium_model": "o1-mini",
            "max_tokens": 4096,
            "temperature": 0.1,
            "timeout": 90,
            "expected_response_time": "5-12 seconds",
            "cost_per_1k_tokens": 2.50
        }

    async def synthesize_insights(self, agent_results: List[AgentResult]) -> SynthesizedInsights:
        """High-quality synthesis requiring complex reasoning"""

        # Use o1-mini for complex synthesis requiring deep reasoning
        if self.requires_deep_reasoning(agent_results):
            model = self.model_config["premium_model"]
            expected_time = "8-12 seconds"
        else:
            model = self.model_config["primary_model"]
            expected_time = "3-5 seconds"

        return await self.create_comprehensive_synthesis(model, agent_results)
```

## CrewAI Implementation

### Crew Configuration

```python
class EnterpriseAgentCrew:
    def __init__(self):
        self.agents = self._initialize_agents()
        self.crew = self._create_crew()

    def _create_crew(self):
        return Crew(
            agents=list(self.agents.values()),
            process=Process.sequential,
            verbose=True,
            memory=True,
            max_rpm=10,
            manager_llm=self.get_llm()
        )

    def create_analysis_tasks(self, user_input: str, context: Dict[str, Any]):
        """Create specialized tasks for each agent"""

        tasks = [
            # Data collection task
            Task(
                description=f"""
                Collect and analyze comprehensive data for user {context['user_name']}.
                Retrieve historical activities, determine current level, analyze trends.
                User Input: {user_input}
                """,
                agent=self.agents['data_analyst'],
                expected_output="Comprehensive user data analysis with trends"
            ),

            # Competency analysis task
            Task(
                description=f"""
                Perform detailed competency analysis based on user activities.
                Classify activities, rate competencies, identify gaps.
                Use data analyst findings for context.
                """,
                agent=self.agents['competency_specialist'],
                expected_output="Detailed competency breakdown with ratings"
            ),

            # Career strategy task
            Task(
                description=f"""
                Develop career advancement strategy based on competency analysis.
                Assess promotion readiness, recommend development paths.
                """,
                agent=self.agents['career_strategist'],
                expected_output="Strategic career development plan"
            ),

            # Synthesis task
            Task(
                description=f"""
                Synthesize all analysis into comprehensive report.
                Create actionable insights and recommendations.
                """,
                agent=self.agents['insights_synthesizer'],
                expected_output="Professional competency report"
            )
        ]

        return tasks
```

## Performance Optimization

### Parallel vs Sequential Execution

**Sequential Processing** (Current):
- Tasks execute in dependency order
- Each agent waits for previous completion
- Ensures data consistency and context flow
- Total time: Sum of individual agent times

**Parallel Processing** (Future Enhancement):
- Independent tasks execute simultaneously
- Faster overall execution
- Requires careful dependency management
- Total time: Max of individual agent times

### Caching Strategy

```python
class AgentResultCache:
    def __init__(self):
        self.redis_client = Redis.from_url("redis://redis-cluster:6379")
        self.default_ttl = 1800  # 30 minutes

    async def get_cached_result(self, cache_key: str):
        """Get cached agent result"""
        try:
            cached = await self.redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Cache get failed: {e}")
        return None

    async def cache_result(self, cache_key: str, result: Any, ttl: int = None):
        """Cache agent result"""
        try:
            await self.redis_client.setex(
                cache_key,
                ttl or self.default_ttl,
                json.dumps(result, default=str)
            )
        except Exception as e:
            logger.warning(f"Cache set failed: {e}")

    def generate_cache_key(self, agent_name: str, user_id: str,
                          input_hash: str) -> str:
        """Generate cache key for agent result"""
        return f"agent_result:{agent_name}:{user_id}:{input_hash}"
```

## Monitoring and Analytics

### Agent Performance Metrics

```python
class AgentMetrics:
    def __init__(self):
        self.meter = metrics.get_meter(__name__)

        # Agent-specific metrics
        self.agent_execution_time = self.meter.create_histogram(
            "agent_execution_duration_seconds",
            description="Individual agent execution time"
        )

        self.agent_success_rate = self.meter.create_counter(
            "agent_executions_total",
            description="Agent execution attempts"
        )

        self.crew_coordination_time = self.meter.create_histogram(
            "crew_coordination_duration_seconds",
            description="Time spent on crew coordination"
        )

    def record_agent_execution(self, agent_name: str, duration: float,
                             success: bool, tokens_used: int):
        """Record agent execution metrics"""

        attributes = {
            "agent_name": agent_name,
            "success": str(success)
        }

        self.agent_execution_time.record(duration, attributes)
        self.agent_success_rate.add(1, attributes)

        if tokens_used > 0:
            self.llm_tokens.add(tokens_used, {
                "agent_name": agent_name,
                "operation": "analysis"
            })
```

This multi-agent system provides specialized expertise while maintaining coordination and observability across all agent interactions.
