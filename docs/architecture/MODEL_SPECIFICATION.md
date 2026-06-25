# ReflectAI Model Specification

## Overview

This specification defines the complete data models, interfaces, and contracts for ReflectAI implementation. It serves as a blueprint for any development team or IDE to implement the system consistently.

## 🏗️ **Core Domain Models**

### **User Domain**
```python
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from uuid import UUID

class UserLevel(Enum):
    P1 = "P1"  # Junior
    P2 = "P2"  # Mid-level
    P3 = "P3"  # Senior
    P4 = "P4"  # Staff
    P5 = "P5"  # Principal
    P6 = "P6"  # Distinguished

class User(BaseModel):
    """Core user entity"""
    id: UUID
    slack_user_id: str = Field(..., description="Slack user identifier")
    email: Optional[str] = None
    name: str = Field(..., description="User's full name")
    title: Optional[str] = Field(None, description="Job title")
    level: Optional[UserLevel] = Field(None, description="Career level")
    department: Optional[str] = None
    manager_id: Optional[UUID] = None
    organization_id: Optional[UUID] = None
    settings: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }
```#
## **Activity Domain**
```python
class ActivitySource(Enum):
    SLACK = "slack"
    API = "api"
    WEB = "web"
    IMPORT = "import"

class ActivityStatus(Enum):
    PENDING = "pending"
    CLASSIFIED = "classified"
    STORED = "stored"
    ERROR = "error"

class Activity(BaseModel):
    """User activity entity"""
    id: UUID
    user_id: UUID = Field(..., description="User who performed the activity")
    content: str = Field(..., description="Activity description")
    source: ActivitySource = Field(..., description="Source of the activity")
    category: Optional[str] = Field(None, description="Competency category")
    classification_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    summary: Optional[str] = Field(None, description="Activity summary")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    status: ActivityStatus = Field(default=ActivityStatus.PENDING)
    slack_message_ts: Optional[str] = None
    slack_channel_id: Optional[str] = None
    slack_thread_ts: Optional[str] = None
    processed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True

class ActivityClassification(BaseModel):
    """Activity classification result"""
    activity_id: UUID
    category: str = Field(..., description="Primary competency category")
    subcategories: List[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: Optional[str] = None
    skill_indicators: List[str] = Field(default_factory=list)
    complexity_level: Optional[str] = Field(None, description="beginner|intermediate|advanced|expert")
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

### **Competency Domain**
```python
class CompetencyCategory(Enum):
    SOFTWARE_DELIVERY = "Software delivery"
    TECHNICAL_DESIGN = "Technical design"
    CODING_CRAFT = "Coding craft"
    OPERATIONS = "Operations"
    LEADERSHIP_COMMUNICATION = "Leadership and Communication"

class CompetencyLevel(Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"

class CompetencyAssessment(BaseModel):
    """User competency assessment"""
    id: UUID
    user_id: UUID
    category: CompetencyCategory
    level: CompetencyLevel
    score: float = Field(..., ge=0.0, le=5.0, description="Competency score 0-5")
    evidence_count: int = Field(default=0, description="Number of supporting activities")
    last_activity_date: Optional[datetime] = None
    trend: Optional[str] = Field(None, description="improving|stable|declining")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class CompetencyRequirement(BaseModel):
    """Competency requirements for roles/levels"""
    id: UUID
    role_title: str
    level: UserLevel
    category: CompetencyCategory
    required_level: CompetencyLevel
    required_score: float = Field(..., ge=0.0, le=5.0)
    description: str
    examples: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

### **Report Domain**
```python
class ReportType(Enum):
    SLACK = "slack"
    PDF = "pdf"
    JSON = "json"

class ReportStatus(Enum):
    REQUESTED = "requested"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"

class CompetencyReport(BaseModel):
    """Competency report entity"""
    id: UUID
    user_id: UUID
    report_type: ReportType
    status: ReportStatus = Field(default=ReportStatus.REQUESTED)
    title: str
    content: Optional[str] = None
    file_path: Optional[str] = None
    file_url: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    generated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ReportMetrics(BaseModel):
    """Report generation metrics"""
    total_activities: int = 0
    activities_by_category: Dict[str, int] = Field(default_factory=dict)
    competency_scores: Dict[str, float] = Field(default_factory=dict)
    overall_score: float = Field(default=0.0, ge=0.0, le=5.0)
    strong_areas: List[str] = Field(default_factory=list)
    development_areas: List[str] = Field(default_factory=list)
    promotion_readiness: Optional[str] = None
    report_period: Dict[str, str] = Field(default_factory=dict)
```## 🔌 **Serv
ice Interfaces**

### **Core Service Contracts**
```python
from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable

@runtime_checkable
class ActivityClassifier(Protocol):
    """Protocol for activity classification services"""

    async def classify_activity(self, content: str, user_context: Dict[str, Any]) -> ActivityClassification:
        """Classify a single activity"""
        ...

    async def classify_batch(self, activities: List[str], user_context: Dict[str, Any]) -> List[ActivityClassification]:
        """Classify multiple activities efficiently"""
        ...

@runtime_checkable
class ContentSummarizer(Protocol):
    """Protocol for content summarization services"""

    async def summarize_content(self, content: str, max_length: Optional[int] = None) -> str:
        """Summarize content to specified length"""
        ...

    async def extract_key_points(self, content: str, num_points: int = 5) -> List[str]:
        """Extract key points from content"""
        ...

@runtime_checkable
class ActivityStorage(Protocol):
    """Protocol for activity storage services"""

    async def store_activity(self, activity: Activity) -> UUID:
        """Store a single activity"""
        ...

    async def get_user_activities(self, user_id: UUID, filters: Optional[Dict[str, Any]] = None) -> List[Activity]:
        """Retrieve user activities with optional filters"""
        ...

    async def update_activity(self, activity_id: UUID, updates: Dict[str, Any]) -> bool:
        """Update activity with new information"""
        ...

@runtime_checkable
class ReportGenerator(Protocol):
    """Protocol for report generation services"""

    async def generate_competency_report(self, user_id: UUID, report_type: ReportType,
                                       options: Optional[Dict[str, Any]] = None) -> CompetencyReport:
        """Generate competency report for user"""
        ...

    async def get_report_status(self, report_id: UUID) -> ReportStatus:
        """Get report generation status"""
        ...
```

### **Multi-Agent System Interfaces**
```python
class AgentType(Enum):
    DATA_ANALYST = "data_analyst"
    COMPETENCY_SPECIALIST = "competency_specialist"
    CAREER_STRATEGIST = "career_strategist"
    INSIGHTS_SYNTHESIZER = "insights_synthesizer"

class AgentResult(BaseModel):
    """Result from individual agent execution"""
    agent_type: AgentType
    success: bool
    result: Any
    execution_time: float
    tokens_used: int = 0
    confidence: Optional[float] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class MultiAgentRequest(BaseModel):
    """Request for multi-agent processing"""
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: UUID
    user_context: Dict[str, Any]
    message: str
    analysis_type: str = "comprehensive"
    priority: str = "normal"  # low|normal|high
    timeout_seconds: int = 300
    requested_agents: Optional[List[AgentType]] = None

class MultiAgentResponse(BaseModel):
    """Response from multi-agent processing"""
    request_id: str
    success: bool
    agent_results: Dict[str, AgentResult]
    synthesized_result: Optional[str] = None
    total_execution_time: float
    total_tokens_used: int = 0
    total_cost: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

@runtime_checkable
class MultiAgentOrchestrator(Protocol):
    """Protocol for multi-agent orchestration"""

    async def execute_analysis(self, request: MultiAgentRequest) -> MultiAgentResponse:
        """Execute multi-agent analysis"""
        ...

    async def get_agent_status(self) -> Dict[str, Any]:
        """Get status of all agents"""
        ...

    async def health_check(self) -> bool:
        """Check if multi-agent system is healthy"""
        ...
```

### **Event System Interfaces**
```python
class EventType(Enum):
    USER_ACTIVITY_CREATED = "user.activity.created"
    USER_ACTIVITY_UPDATED = "user.activity.updated"
    ANALYSIS_REQUESTED = "analysis.requested"
    ANALYSIS_COMPLETED = "analysis.completed"
    REPORT_GENERATED = "report.generated"
    SYSTEM_HEALTH_CHECK = "system.health.check"

class BaseEvent(BaseModel):
    """Base event structure"""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source_service: str
    user_id: Optional[UUID] = None
    correlation_id: Optional[str] = None
    trace_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)

@runtime_checkable
class EventPublisher(Protocol):
    """Protocol for event publishing"""

    async def publish_event(self, event: BaseEvent) -> str:
        """Publish event and return event ID"""
        ...

    async def publish_batch(self, events: List[BaseEvent]) -> List[str]:
        """Publish multiple events"""
        ...

@runtime_checkable
class EventConsumer(Protocol):
    """Protocol for event consumption"""

    async def subscribe(self, event_types: List[EventType], handler: Callable) -> str:
        """Subscribe to event types with handler"""
        ...

    async def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from events"""
        ...
```## 🎯 **AP
I Specifications**

### **REST API Endpoints**
```python
from fastapi import FastAPI, HTTPException, Depends, Query
from typing import List, Optional

# User Management API
@app.post("/api/v1/users", response_model=User)
async def create_user(user: UserCreate) -> User:
    """Create new user"""
    pass

@app.get("/api/v1/users/{user_id}", response_model=User)
async def get_user(user_id: UUID) -> User:
    """Get user by ID"""
    pass

@app.put("/api/v1/users/{user_id}", response_model=User)
async def update_user(user_id: UUID, updates: UserUpdate) -> User:
    """Update user information"""
    pass

# Activity Management API
@app.post("/api/v1/activities", response_model=Activity)
async def create_activity(activity: ActivityCreate) -> Activity:
    """Create new activity"""
    pass

@app.get("/api/v1/users/{user_id}/activities", response_model=List[Activity])
async def get_user_activities(
    user_id: UUID,
    category: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    limit: int = Query(100, le=1000)
) -> List[Activity]:
    """Get user activities with filters"""
    pass

@app.post("/api/v1/activities/{activity_id}/classify", response_model=ActivityClassification)
async def classify_activity(activity_id: UUID) -> ActivityClassification:
    """Classify existing activity"""
    pass

# Analysis API
@app.post("/api/v1/analysis/single-agent", response_model=Dict[str, Any])
async def single_agent_analysis(request: SingleAgentRequest) -> Dict[str, Any]:
    """Execute single-agent analysis"""
    pass

@app.post("/api/v1/analysis/multi-agent", response_model=MultiAgentResponse)
async def multi_agent_analysis(request: MultiAgentRequest) -> MultiAgentResponse:
    """Execute multi-agent analysis"""
    pass

@app.get("/api/v1/analysis/{request_id}/status", response_model=Dict[str, Any])
async def get_analysis_status(request_id: str) -> Dict[str, Any]:
    """Get analysis status"""
    pass

# Report Generation API
@app.post("/api/v1/reports", response_model=CompetencyReport)
async def generate_report(request: ReportRequest) -> CompetencyReport:
    """Generate competency report"""
    pass

@app.get("/api/v1/reports/{report_id}", response_model=CompetencyReport)
async def get_report(report_id: UUID) -> CompetencyReport:
    """Get report by ID"""
    pass

@app.get("/api/v1/reports/{report_id}/download")
async def download_report(report_id: UUID) -> FileResponse:
    """Download report file"""
    pass

# Competency API
@app.get("/api/v1/competencies/requirements", response_model=List[CompetencyRequirement])
async def get_competency_requirements(
    role: Optional[str] = Query(None),
    level: Optional[UserLevel] = Query(None)
) -> List[CompetencyRequirement]:
    """Get competency requirements"""
    pass

@app.get("/api/v1/users/{user_id}/competencies", response_model=List[CompetencyAssessment])
async def get_user_competencies(user_id: UUID) -> List[CompetencyAssessment]:
    """Get user competency assessments"""
    pass

# Health and Status API
@app.get("/api/v1/health", response_model=Dict[str, Any])
async def health_check() -> Dict[str, Any]:
    """Basic health check"""
    pass

@app.get("/api/v1/health/detailed", response_model=Dict[str, Any])
async def detailed_health() -> Dict[str, Any]:
    """Detailed health check"""
    pass

@app.get("/api/v1/status", response_model=Dict[str, Any])
async def system_status() -> Dict[str, Any]:
    """System status and metrics"""
    pass
```

### **Request/Response Models**
```python
# Request Models
class UserCreate(BaseModel):
    slack_user_id: str
    email: Optional[str] = None
    name: str
    title: Optional[str] = None
    department: Optional[str] = None

class UserUpdate(BaseModel):
    name: Optional[str] = None
    title: Optional[str] = None
    level: Optional[UserLevel] = None
    department: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None

class ActivityCreate(BaseModel):
    user_id: UUID
    content: str
    source: ActivitySource = ActivitySource.API
    metadata: Optional[Dict[str, Any]] = None

class SingleAgentRequest(BaseModel):
    user_id: UUID
    message: str
    intent: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

class ReportRequest(BaseModel):
    user_id: UUID
    report_type: ReportType = ReportType.SLACK
    date_range: Optional[Dict[str, str]] = None
    options: Optional[Dict[str, Any]] = None

# Response Models
class APIResponse(BaseModel):
    """Standard API response wrapper"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class PaginatedResponse(BaseModel):
    """Paginated response wrapper"""
    items: List[Any]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool
```## 🗄️
**Database Schema Specification**

### **PostgreSQL Schema**
```sql
-- Core schema for ReflectAI
CREATE SCHEMA reflectai;

-- Users table
CREATE TABLE reflectai.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slack_user_id VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255),
    name VARCHAR(255) NOT NULL,
    title VARCHAR(255),
    level VARCHAR(10) CHECK (level IN ('P1', 'P2', 'P3', 'P4', 'P5', 'P6')),
    department VARCHAR(255),
    manager_id UUID REFERENCES reflectai.users(id),
    organization_id UUID,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Activities table (partitioned by date for performance)
CREATE TABLE reflectai.activities (
    id UUID DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES reflectai.users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    source VARCHAR(50) NOT NULL CHECK (source IN ('slack', 'api', 'web', 'import')),
    category VARCHAR(255),
    classification_confidence DECIMAL(3,2) CHECK (classification_confidence BETWEEN 0 AND 1),
    summary TEXT,
    metadata JSONB DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'classified', 'stored', 'error')),
    slack_message_ts VARCHAR(255),
    slack_channel_id VARCHAR(255),
    slack_thread_ts VARCHAR(255),
    processed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
) PARTITION BY RANGE (created_at);

-- Create monthly partitions (example for 2024)
CREATE TABLE reflectai.activities_2024_01 PARTITION OF reflectai.activities
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
CREATE TABLE reflectai.activities_2024_02 PARTITION OF reflectai.activities
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
-- ... continue for all months

-- Activity classifications table
CREATE TABLE reflectai.activity_classifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    activity_id UUID NOT NULL REFERENCES reflectai.activities(id) ON DELETE CASCADE,
    category VARCHAR(255) NOT NULL,
    subcategories TEXT[],
    confidence DECIMAL(3,2) NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    reasoning TEXT,
    skill_indicators TEXT[],
    complexity_level VARCHAR(20) CHECK (complexity_level IN ('beginner', 'intermediate', 'advanced', 'expert')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Competency assessments table
CREATE TABLE reflectai.competency_assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES reflectai.users(id) ON DELETE CASCADE,
    category VARCHAR(255) NOT NULL,
    level VARCHAR(20) NOT NULL CHECK (level IN ('beginner', 'intermediate', 'advanced', 'expert')),
    score DECIMAL(3,2) NOT NULL CHECK (score BETWEEN 0 AND 5),
    evidence_count INTEGER DEFAULT 0,
    last_activity_date TIMESTAMP WITH TIME ZONE,
    trend VARCHAR(20) CHECK (trend IN ('improving', 'stable', 'declining')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, category)
);

-- Competency requirements table
CREATE TABLE reflectai.competency_requirements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_title VARCHAR(255) NOT NULL,
    level VARCHAR(10) NOT NULL CHECK (level IN ('P1', 'P2', 'P3', 'P4', 'P5', 'P6')),
    category VARCHAR(255) NOT NULL,
    required_level VARCHAR(20) NOT NULL CHECK (required_level IN ('beginner', 'intermediate', 'advanced', 'expert')),
    required_score DECIMAL(3,2) NOT NULL CHECK (required_score BETWEEN 0 AND 5),
    description TEXT NOT NULL,
    examples TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(role_title, level, category)
);

-- Reports table
CREATE TABLE reflectai.reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES reflectai.users(id) ON DELETE CASCADE,
    report_type VARCHAR(20) NOT NULL CHECK (report_type IN ('slack', 'pdf', 'json')),
    status VARCHAR(20) DEFAULT 'requested' CHECK (status IN ('requested', 'generating', 'completed', 'failed')),
    title VARCHAR(500) NOT NULL,
    content TEXT,
    file_path VARCHAR(1000),
    file_url VARCHAR(1000),
    metadata JSONB DEFAULT '{}',
    generated_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_users_slack_id ON reflectai.users(slack_user_id);
CREATE INDEX idx_users_organization ON reflectai.users(organization_id);
CREATE INDEX idx_activities_user_created ON reflectai.activities(user_id, created_at);
CREATE INDEX idx_activities_category ON reflectai.activities(category);
CREATE INDEX idx_activities_status ON reflectai.activities(status);
CREATE INDEX idx_activities_slack_ts ON reflectai.activities(slack_message_ts);
CREATE INDEX idx_classifications_activity ON reflectai.activity_classifications(activity_id);
CREATE INDEX idx_classifications_category ON reflectai.activity_classifications(category);
CREATE INDEX idx_assessments_user_category ON reflectai.competency_assessments(user_id, category);
CREATE INDEX idx_requirements_role_level ON reflectai.competency_requirements(role_title, level);
CREATE INDEX idx_reports_user_status ON reflectai.reports(user_id, status);

-- Full-text search indexes
CREATE INDEX idx_activities_content_fts ON reflectai.activities
    USING GIN(to_tsvector('english', content));
CREATE INDEX idx_activities_summary_fts ON reflectai.activities
    USING GIN(to_tsvector('english', summary));
```

### **Redis Schema Specification**
```python
# Redis key patterns and data structures
REDIS_KEY_PATTERNS = {
    # User data caching
    "user_profile": "user:{user_id}:profile",
    "user_activities": "user:{user_id}:activities:{date_range}",
    "user_competencies": "user:{user_id}:competencies",

    # LLM response caching (context-aware)
    "llm_cache": "llm:{tool_name}:{user_context_hash}:{content_hash}",
    "batch_classification": "batch_classify:{user_id}:{activities_hash}",

    # Static data caching
    "competency_matrix": "static:competency_matrix",
    "level_to_title_matrix": "static:level_to_title_matrix",

    # Session management
    "user_session": "session:{session_id}",
    "conversation_context": "conversation:{user_id}:{thread_id}",

    # System caching
    "system_health": "system:health:{service_name}",
    "performance_metrics": "metrics:{service_name}:{metric_type}",

    # Rate limiting
    "rate_limit": "rate_limit:{user_id}:{endpoint}",
    "api_quota": "quota:{api_key}:{period}"
}

# TTL specifications
REDIS_TTL_CONFIG = {
    "user_profile": 3600,           # 1 hour
    "user_activities": 1800,        # 30 minutes
    "llm_cache": 3600,             # 1 hour
    "static_data": 86400,          # 24 hours
    "session_data": 7200,          # 2 hours
    "system_health": 300,          # 5 minutes
    "rate_limit": 3600             # 1 hour
}
```
#
# ⚙️ **Configuration Specification**

### **Environment Configuration**
```python
from pydantic import BaseSettings, Field
from typing import List, Optional

class DatabaseConfig(BaseSettings):
    """Database configuration"""
    host: str = Field(..., env="DB_HOST")
    port: int = Field(5432, env="DB_PORT")
    database: str = Field(..., env="DB_NAME")
    username: str = Field(..., env="DB_USERNAME")
    password: str = Field(..., env="DB_PASSWORD")
    pool_size: int = Field(10, env="DB_POOL_SIZE")
    max_overflow: int = Field(20, env="DB_MAX_OVERFLOW")
    ssl_mode: str = Field("require", env="DB_SSL_MODE")

    @property
    def url(self) -> str:
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"

class RedisConfig(BaseSettings):
    """Redis configuration"""
    host: str = Field(..., env="REDIS_HOST")
    port: int = Field(6379, env="REDIS_PORT")
    password: Optional[str] = Field(None, env="REDIS_PASSWORD")
    database: int = Field(0, env="REDIS_DB")
    ssl: bool = Field(False, env="REDIS_SSL")
    pool_size: int = Field(10, env="REDIS_POOL_SIZE")

    @property
    def url(self) -> str:
        protocol = "rediss" if self.ssl else "redis"
        auth = f":{self.password}@" if self.password else ""
        return f"{protocol}://{auth}{self.host}:{self.port}/{self.database}"

class NATSConfig(BaseSettings):
    """NATS JetStream configuration"""
    servers: List[str] = Field(..., env="NATS_SERVERS")
    username: Optional[str] = Field(None, env="NATS_USERNAME")
    password: Optional[str] = Field(None, env="NATS_PASSWORD")
    tls_enabled: bool = Field(False, env="NATS_TLS_ENABLED")
    max_reconnect_attempts: int = Field(10, env="NATS_MAX_RECONNECT")
    reconnect_time_wait: int = Field(2, env="NATS_RECONNECT_WAIT")

class LLMConfig(BaseSettings):
    """LLM provider configuration"""
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(None, env="ANTHROPIC_API_KEY")
    aws_access_key_id: Optional[str] = Field(None, env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = Field(None, env="AWS_SECRET_ACCESS_KEY")
    aws_region: str = Field("us-east-1", env="AWS_REGION")
    default_model: str = Field("gpt-4o-mini", env="DEFAULT_LLM_MODEL")
    max_tokens: int = Field(4096, env="LLM_MAX_TOKENS")
    temperature: float = Field(0.1, env="LLM_TEMPERATURE")
    timeout: int = Field(60, env="LLM_TIMEOUT")

class SlackConfig(BaseSettings):
    """Slack integration configuration"""
    bot_token: str = Field(..., env="SLACK_BOT_TOKEN")
    app_token: str = Field(..., env="SLACK_APP_TOKEN")
    signing_secret: str = Field(..., env="SLACK_SIGNING_SECRET")
    client_id: str = Field(..., env="SLACK_CLIENT_ID")
    client_secret: str = Field(..., env="SLACK_CLIENT_SECRET")
    socket_mode: bool = Field(True, env="SLACK_SOCKET_MODE")

class ObservabilityConfig(BaseSettings):
    """Observability configuration"""
    jaeger_endpoint: Optional[str] = Field(None, env="JAEGER_ENDPOINT")
    prometheus_endpoint: Optional[str] = Field(None, env="PROMETHEUS_ENDPOINT")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    enable_tracing: bool = Field(True, env="ENABLE_TRACING")
    enable_metrics: bool = Field(True, env="ENABLE_METRICS")
    service_name: str = Field("reflectai", env="SERVICE_NAME")
    service_version: str = Field("1.0.0", env="SERVICE_VERSION")

class SecurityConfig(BaseSettings):
    """Security configuration"""
    jwt_secret_key: str = Field(..., env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    jwt_expiration_hours: int = Field(24, env="JWT_EXPIRATION_HOURS")
    api_key_header: str = Field("X-API-Key", env="API_KEY_HEADER")
    cors_origins: List[str] = Field(["*"], env="CORS_ORIGINS")
    rate_limit_per_minute: int = Field(100, env="RATE_LIMIT_PER_MINUTE")

class ReflectAIConfig(BaseSettings):
    """Main application configuration"""
    environment: str = Field("development", env="ENVIRONMENT")
    debug: bool = Field(False, env="DEBUG")
    host: str = Field("0.0.0.0", env="HOST")
    port: int = Field(8000, env="PORT")

    # Sub-configurations
    database: DatabaseConfig = DatabaseConfig()
    redis: RedisConfig = RedisConfig()
    nats: NATSConfig = NATSConfig()
    llm: LLMConfig = LLMConfig()
    slack: SlackConfig = SlackConfig()
    observability: ObservabilityConfig = ObservabilityConfig()
    security: SecurityConfig = SecurityConfig()

    class Config:
        env_file = ".env"
        env_nested_delimiter = "__"
```

### **Kubernetes Configuration Templates**
```yaml
# ConfigMap for application configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: reflectai-config
  namespace: reflectai
data:
  ENVIRONMENT: "production"
  DEBUG: "false"
  HOST: "0.0.0.0"
  PORT: "8000"

  # Database configuration
  DB_HOST: "postgresql.reflectai.svc.cluster.local"
  DB_PORT: "5432"
  DB_NAME: "reflectai"
  DB_POOL_SIZE: "20"
  DB_MAX_OVERFLOW: "40"
  DB_SSL_MODE: "require"

  # Redis configuration
  REDIS_HOST: "redis.reflectai.svc.cluster.local"
  REDIS_PORT: "6379"
  REDIS_DB: "0"
  REDIS_POOL_SIZE: "20"

  # NATS configuration
  NATS_SERVERS: "nats://nats.reflectai.svc.cluster.local:4222"
  NATS_MAX_RECONNECT: "10"
  NATS_RECONNECT_WAIT: "2"

  # LLM configuration
  AWS_REGION: "us-east-1"
  DEFAULT_LLM_MODEL: "gpt-4o-mini"
  LLM_MAX_TOKENS: "4096"
  LLM_TEMPERATURE: "0.1"
  LLM_TIMEOUT: "60"

  # Observability
  LOG_LEVEL: "INFO"
  ENABLE_TRACING: "true"
  ENABLE_METRICS: "true"
  SERVICE_NAME: "reflectai"
  SERVICE_VERSION: "1.0.0"

  # Security
  JWT_ALGORITHM: "HS256"
  JWT_EXPIRATION_HOURS: "24"
  API_KEY_HEADER: "X-API-Key"
  CORS_ORIGINS: "https://app.reflectai.com,https://admin.reflectai.com"
  RATE_LIMIT_PER_MINUTE: "100"

---
# Secret for sensitive configuration
apiVersion: v1
kind: Secret
metadata:
  name: reflectai-secrets
  namespace: reflectai
type: Opaque
stringData:
  DB_USERNAME: "reflectai_user"
  DB_PASSWORD: "secure_db_password"
  REDIS_PASSWORD: "secure_redis_password"
  OPENAI_API_KEY: "sk-..."
  ANTHROPIC_API_KEY: "sk-ant-..."
  AWS_ACCESS_KEY_ID: "AKIA..."
  AWS_SECRET_ACCESS_KEY: "..."
  SLACK_BOT_TOKEN: "xoxb-..."
  SLACK_APP_TOKEN: "xapp-..."
  SLACK_SIGNING_SECRET: "..."
  SLACK_CLIENT_ID: "..."
  SLACK_CLIENT_SECRET: "..."
  JWT_SECRET_KEY: "secure_jwt_secret_key"
```

## 🔄 **Event Schema Specification**

### **Event Definitions**
```python
class UserActivityCreatedEvent(BaseEvent):
    """Event published when user activity is created"""
    event_type: EventType = EventType.USER_ACTIVITY_CREATED
    payload: Dict[str, Any] = Field(default_factory=lambda: {
        "activity_id": None,
        "user_id": None,
        "content": None,
        "source": None,
        "metadata": {}
    })

class AnalysisRequestedEvent(BaseEvent):
    """Event published when analysis is requested"""
    event_type: EventType = EventType.ANALYSIS_REQUESTED
    payload: Dict[str, Any] = Field(default_factory=lambda: {
        "request_id": None,
        "user_id": None,
        "analysis_type": None,  # "single_agent" or "multi_agent"
        "message": None,
        "priority": "normal",
        "timeout_seconds": 300
    })

class AnalysisCompletedEvent(BaseEvent):
    """Event published when analysis is completed"""
    event_type: EventType = EventType.ANALYSIS_COMPLETED
    payload: Dict[str, Any] = Field(default_factory=lambda: {
        "request_id": None,
        "user_id": None,
        "analysis_type": None,
        "success": True,
        "result": None,
        "execution_time": 0.0,
        "tokens_used": 0,
        "cost": 0.0
    })

class ReportGeneratedEvent(BaseEvent):
    """Event published when report is generated"""
    event_type: EventType = EventType.REPORT_GENERATED
    payload: Dict[str, Any] = Field(default_factory=lambda: {
        "report_id": None,
        "user_id": None,
        "report_type": None,
        "file_path": None,
        "file_url": None,
        "generation_time": 0.0
    })
```

### **NATS JetStream Configuration**
```python
NATS_STREAM_CONFIG = {
    "USER_ACTIVITIES": {
        "name": "USER_ACTIVITIES",
        "subjects": ["user.activity.>"],
        "retention": "limits",
        "max_age": 30 * 24 * 3600,  # 30 days
        "max_msgs": 1000000,
        "storage": "file",
        "replicas": 3,
        "discard": "old"
    },

    "ANALYSIS_EVENTS": {
        "name": "ANALYSIS_EVENTS",
        "subjects": ["analysis.>"],
        "retention": "limits",
        "max_age": 7 * 24 * 3600,  # 7 days
        "max_msgs": 500000,
        "storage": "memory",
        "replicas": 3,
        "discard": "old"
    },

    "REPORT_EVENTS": {
        "name": "REPORT_EVENTS",
        "subjects": ["report.>"],
        "retention": "limits",
        "max_age": 14 * 24 * 3600,  # 14 days
        "max_msgs": 100000,
        "storage": "file",
        "replicas": 3,
        "discard": "old"
    },

    "SYSTEM_EVENTS": {
        "name": "SYSTEM_EVENTS",
        "subjects": ["system.>"],
        "retention": "limits",
        "max_age": 7 * 24 * 3600,  # 7 days
        "max_msgs": 200000,
        "storage": "file",
        "replicas": 3,
        "discard": "old"
    }
}
```

## 🧪 **Testing Specifications**

### **Test Data Models**
```python
class TestUser(BaseModel):
    """Test user for integration tests"""
    slack_user_id: str = "U123TEST"
    name: str = "Test User"
    title: str = "Software Engineer"
    level: UserLevel = UserLevel.P2
    department: str = "Engineering"

class TestActivity(BaseModel):
    """Test activity for integration tests"""
    content: str = "Implemented REST API with authentication and error handling"
    source: ActivitySource = ActivitySource.API
    expected_category: str = "Software delivery"
    expected_confidence: float = 0.85

class TestScenario(BaseModel):
    """Test scenario definition"""
    name: str
    description: str
    user: TestUser
    activities: List[TestActivity]
    expected_outcomes: Dict[str, Any]
    setup_steps: List[str]
    cleanup_steps: List[str]

# Predefined test scenarios
TEST_SCENARIOS = {
    "basic_classification": TestScenario(
        name="Basic Activity Classification",
        description="Test basic activity classification workflow",
        user=TestUser(),
        activities=[
            TestActivity(
                content="Implemented user authentication using JWT tokens",
                expected_category="Software delivery",
                expected_confidence=0.9
            )
        ],
        expected_outcomes={
            "classification_success": True,
            "response_time_ms": {"max": 3000},
            "confidence_score": {"min": 0.8}
        },
        setup_steps=["create_test_user", "clear_activities"],
        cleanup_steps=["delete_test_activities"]
    ),

    "multi_agent_analysis": TestScenario(
        name="Multi-Agent Comprehensive Analysis",
        description="Test multi-agent system with complex request",
        user=TestUser(),
        activities=[
            TestActivity(content="Led architecture discussion for microservices migration"),
            TestActivity(content="Mentored 3 junior developers on React best practices"),
            TestActivity(content="Implemented CI/CD pipeline with automated testing")
        ],
        expected_outcomes={
            "multi_agent_success": True,
            "agents_executed": 4,
            "response_time_ms": {"max": 15000},
            "synthesis_quality": {"min": 0.85}
        },
        setup_steps=["create_test_user", "seed_test_activities"],
        cleanup_steps=["cleanup_test_data"]
    )
}
```

### **Performance Test Specifications**
```python
class PerformanceTestConfig(BaseModel):
    """Performance test configuration"""
    test_name: str
    duration_seconds: int = 300  # 5 minutes
    ramp_up_seconds: int = 60    # 1 minute
    target_rps: int = 10         # Requests per second
    max_response_time_ms: int = 5000
    error_rate_threshold: float = 0.01  # 1%

PERFORMANCE_TESTS = {
    "api_load_test": PerformanceTestConfig(
        test_name="API Load Test",
        target_rps=50,
        max_response_time_ms=2000
    ),

    "classification_stress_test": PerformanceTestConfig(
        test_name="Classification Stress Test",
        target_rps=20,
        max_response_time_ms=5000,
        duration_seconds=600  # 10 minutes
    ),

    "multi_agent_capacity_test": PerformanceTestConfig(
        test_name="Multi-Agent Capacity Test",
        target_rps=5,
        max_response_time_ms=15000,
        duration_seconds=900  # 15 minutes
    )
}
```

## 🚀 **Deployment Specifications**

### **Docker Configuration**
```dockerfile
# Multi-stage Dockerfile for ReflectAI
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Default command
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Production stage
FROM base as production
ENV ENVIRONMENT=production
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### **Kubernetes Deployment**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: reflectai-api
  namespace: reflectai
  labels:
    app: reflectai-api
    version: v1
spec:
  replicas: 3
  selector:
    matchLabels:
      app: reflectai-api
  template:
    metadata:
      labels:
        app: reflectai-api
        version: v1
    spec:
      serviceAccountName: reflectai-api
      containers:
      - name: api
        image: reflectai/api:latest
        ports:
        - containerPort: 8000
          name: http
        env:
        - name: ENVIRONMENT
          value: "production"
        envFrom:
        - configMapRef:
            name: reflectai-config
        - secretRef:
            name: reflectai-secrets
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /api/v1/health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/v1/health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        securityContext:
          runAsNonRoot: true
          runAsUser: 1000
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        - name: cache
          mountPath: /app/cache
      volumes:
      - name: tmp
        emptyDir: {}
      - name: cache
        emptyDir: {}
      nodeSelector:
        kubernetes.io/arch: amd64
      tolerations:
      - key: "reflectai.com/dedicated"
        operator: "Equal"
        value: "api"
        effect: "NoSchedule"
```

## 📊 **Monitoring Specifications**

### **Prometheus Metrics**
```python
# Custom metrics definitions
CUSTOM_METRICS = {
    "reflectai_requests_total": {
        "type": "counter",
        "description": "Total number of requests",
        "labels": ["method", "endpoint", "status_code"]
    },

    "reflectai_request_duration_seconds": {
        "type": "histogram",
        "description": "Request duration in seconds",
        "labels": ["method", "endpoint"],
        "buckets": [0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
    },

    "reflectai_llm_requests_total": {
        "type": "counter",
        "description": "Total LLM requests",
        "labels": ["model", "agent_type", "success"]
    },

    "reflectai_llm_tokens_total": {
        "type": "counter",
        "description": "Total LLM tokens consumed",
        "labels": ["model", "agent_type", "token_type"]
    },

    "reflectai_llm_cost_total": {
        "type": "counter",
        "description": "Total LLM cost in USD",
        "labels": ["model", "agent_type"]
    },

    "reflectai_activities_processed_total": {
        "type": "counter",
        "description": "Total activities processed",
        "labels": ["source", "category", "success"]
    },

    "reflectai_reports_generated_total": {
        "type": "counter",
        "description": "Total reports generated",
        "labels": ["report_type", "success"]
    },

    "reflectai_cache_hits_total": {
        "type": "counter",
        "description": "Total cache hits",
        "labels": ["cache_type", "hit"]
    }
}
```

## 🔐 **Security Specifications**

### **Authentication & Authorization**
```python
class SecurityPolicy(BaseModel):
    """Security policy configuration"""

    # JWT Configuration
    jwt_issuer: str = "reflectai.com"
    jwt_audience: str = "reflectai-api"
    jwt_algorithm: str = "RS256"
    jwt_public_key_url: str = "https://auth.reflectai.com/.well-known/jwks.json"

    # RBAC Configuration
    roles: Dict[str, List[str]] = {
        "admin": ["*"],
        "manager": [
            "read:reports", "read:team_data", "read:competencies",
            "write:team_settings", "generate:team_reports"
        ],
        "user": [
            "read:own_data", "write:own_activities", "read:own_reports",
            "generate:own_reports", "read:competency_requirements"
        ],
        "readonly": [
            "read:own_data", "read:own_reports", "read:competency_requirements"
        ]
    }

    # Rate Limiting
    rate_limits: Dict[str, str] = {
        "anonymous": "10/minute",
        "user": "100/minute",
        "manager": "500/minute",
        "admin": "1000/minute",
        "service": "10000/minute"
    }

    # Data Classification
    data_classifications: Dict[str, str] = {
        "user_activities": "confidential",
        "competency_assessments": "confidential",
        "reports": "confidential",
        "user_profiles": "restricted",
        "system_metrics": "internal",
        "competency_requirements": "public"
    }
```

## 📋 **Implementation Checklist**

### **Phase 1: Core Infrastructure (Weeks 1-4)**
- [ ] Set up development environment with Docker Compose
- [ ] Implement core domain models and database schema
- [ ] Create basic API endpoints with FastAPI
- [ ] Set up PostgreSQL with migrations (Alembic)
- [ ] Implement Redis caching layer
- [ ] Create basic authentication and authorization
- [ ] Set up logging and basic monitoring
- [ ] Implement health check endpoints

### **Phase 2: Core Functionality (Weeks 5-8)**
- [ ] Implement activity classification service
- [ ] Create content summarization service
- [ ] Build activity storage and retrieval
- [ ] Implement basic report generation
- [ ] Create Slack integration
- [ ] Set up NATS JetStream for events
- [ ] Implement basic caching strategies
- [ ] Add comprehensive error handling

### **Phase 3: Enhanced Features (Weeks 9-12)**
- [ ] Implement enhanced workflow engine
- [ ] Create multi-agent orchestration system
- [ ] Add intelligent model selection
- [ ] Implement advanced caching with user context
- [ ] Create comprehensive monitoring and alerting
- [ ] Add performance optimization features
- [ ] Implement security hardening
- [ ] Create comprehensive test suite

### **Phase 4: Production Readiness (Weeks 13-16)**
- [ ] Set up CI/CD pipeline
- [ ] Implement backup and disaster recovery
- [ ] Create production deployment configurations
- [ ] Perform load testing and optimization
- [ ] Complete security audit
- [ ] Create operational runbooks
- [ ] Implement compliance features (GDPR, etc.)
- [ ] Conduct user acceptance testing

This model specification provides a complete blueprint for implementing ReflectAI with any development stack or IDE, ensuring consistency, scalability, and maintainability across all components.
