# ReflectAI Platform - AI Development Context

## Project Overview
ReflectAI is a Python-based AI-powered competency analysis system that helps organizations understand and develop their team capabilities through intelligent assessment and personalized development recommendations.

**Version**: 0.1.2-alpha
**Python**: >=3.11,<3.13 (managed via PDM)
**Architecture**: Microservices with event-driven workflows

## Technology Stack

### Core Backend
- **Framework**: FastAPI (v0.104.1+) with async/await patterns
- **Database**: PostgreSQL 15 + TimescaleDB for time-series analytics
- **Cache**: Redis 7 for session management and performance optimization
- **Dependencies**: PDM (v2.20.1+) for Python dependency management

### AI & Processing
- **LLM Integration**: OpenAI (v1.3.0+) + LiteLLM (v1.0.0+) with custom gateway pattern in `src/core/llm/`
- **Workflows**: Temporal (v1.22.0) for orchestration in `src/services/workflow/`
- **Business Logic**: Competency assessment engine in `src/core/assessment/`
- **Guardrails**: guardrails-ai (v0.4.0+) for LLM output validation

### Integrations
- **Slack**: Real-time interaction via Slack SDK (v3.24.0+) and Slack Bolt (v1.18.0+)
- **External APIs**: OAuth2, health checks, cost tracking
- **Security**: Doppler SDK for secrets management

## Architecture Overview

```
src/
├── shared/                      # Shared utilities (PRODUCTION READY ✅)
│   ├── exceptions.py           # Structured error types
│   ├── error_handlers.py       # Retry, circuit breaker, context mgmt
│   ├── error_metrics.py        # Prometheus metrics collection
│   ├── logging.py              # Structured logging with correlation IDs
│   └── validation.py           # Data validation framework
├── core/                        # Core business logic
│   ├── llm/                    # LLM gateway with failover (CRITICAL)
│   │   ├── gateway.py          # Main routing and provider management
│   │   ├── cost_tracker.py     # Budget monitoring and alerts
│   │   ├── optimizer.py        # Model selection logic
│   │   ├── cache.py            # Response caching
│   │   ├── enterprise_gateway_client.py # EnterpriseGateway integration
│   │   ├── guardrails.py       # LLM output validation
│   │   └── providers.py        # Provider implementations
│   ├── assessment/             # Competency scoring engine
│   │   ├── competency_assessor.py # Main assessment logic
│   │   ├── gap_analyzer.py     # Competency gap analysis
│   │   ├── level_calculator.py # Level calculation
│   │   └── scoring/            # Activity scoring algorithms
│   ├── classification/         # Content classification
│   │   ├── activity_classifier.py  # Activity type classification
│   │   ├── competency_mapper.py    # Competency mapping
│   │   ├── intent_analyzer.py      # User intent analysis
│   │   └── trend_analyzer.py       # Trend detection
│   ├── business/               # Business engines
│   │   ├── analytics_engine.py     # Analytics processing
│   │   ├── growth_engine.py        # Growth recommendations
│   │   ├── matching_engine.py      # Matching algorithms
│   │   ├── reporting_engine.py     # Report generation
│   │   ├── engines/                # Specialized engines
│   │   │   └── recommendation_engine.py
│   │   └── analytics/              # Analytics modules
│   ├── conversation/           # Conversation management
│   │   ├── context_manager.py      # Context tracking
│   │   └── intelligence.py         # Conversation intelligence
│   ├── tools/                  # Agent tools and utilities
│   │   ├── advisor/            # Advisor tools
│   │   │   ├── goal_tracker.py
│   │   │   ├── report_generator.py
│   │   │   └── resource_finder.py
│   │   ├── analysis/           # Analysis tools
│   │   │   └── database_query.py
│   │   ├── tool_registry.py    # Tool registration
│   │   ├── base_tool.py        # Base tool interface
│   │   └── task_processor.py   # Task processing
│   ├── frameworks/             # Framework validation
│   │   └── framework_validator.py
│   ├── security/               # Security utilities
│   │   ├── audit_trail.py
│   │   ├── privacy_compliance.py
│   │   └── security_hardening.py
│   ├── prompts/                # Prompt management
│   │   └── prompt_manager.py
│   ├── reporting/              # Reporting utilities
│   │   ├── data_aggregator.py
│   │   └── date_manager.py
│   ├── workflows/              # Workflow routing
│   │   └── workflow_router.py
│   └── storage/                # Data management layer
│       ├── managers/           # Data access layer
│       ├── models/             # Pydantic models
│       └── utils/              # Storage utilities
├── services/                    # Application services
│   ├── workflow/               # Temporal orchestration (CRITICAL)
│   │   ├── workflows.py        # Workflow definitions
│   │   ├── activities.py       # Activity implementations
│   │   ├── temporal_client.py  # Client setup
│   │   ├── worker.py           # Worker configuration
│   │   ├── engine.py           # Workflow engine
│   │   └── models.py           # Workflow models
│   ├── agents/                 # AI agents
│   │   ├── base.py             # Base agent
│   │   ├── advisor_agent.py    # Advisor agent
│   │   ├── analysis_agent.py   # Analysis agent
│   │   ├── chat_responder.py   # Chat responder
│   │   └── registry.py         # Agent registry
│   ├── business_engines/       # Business logic engines
│   │   ├── activity_classification_engine.py
│   │   ├── career_path_engine.py
│   │   └── competency_assessment_engine.py
│   ├── conversation/           # Conversation services
│   ├── notification/           # Notification service
│   │   └── notification_engine.py
│   ├── reporting/              # Reporting service
│   │   └── pdf_report_engine.py
│   └── analytics/              # Analytics service
├── interfaces/                  # External interfaces
│   └── slack/                  # Slack integration (CRITICAL)
│       ├── socket_handler.py           # Event handling
│       ├── workflow_integration.py     # Slack-Temporal bridge
│       ├── handlers.py                 # Command processors
│       ├── slash_commands.py           # Slash command handlers
│       ├── conversation_manager.py     # Conversation state
│       ├── intelligent_dm.py           # DM intelligence
│       ├── enhanced_home_tab.py        # Home tab UI
│       ├── response_formatter.py       # Response formatting
│       ├── block_builder.py            # Slack Block Kit builder
│       ├── threading.py                # Message threading
│       ├── adapter.py                  # Slack adapter
│       └── app.py                      # Slack app setup
└── infrastructure/              # Infrastructure services
    ├── config/                 # Configuration management
    │   ├── config_manager.py
    │   └── secrets_manager.py
    ├── database/               # Database connections
    │   ├── db_manager.py
    │   ├── models/            # Database models
    │   └── repositories/      # Data repositories
    ├── cache/                  # Cache management (Redis with memory fallback)
    │   ├── redis_manager.py    # Main Redis cache (single source of truth)
    │   └── memory_cache.py     # Memory fallback for Redis
    ├── monitoring/             # Health checks and metrics
    │   ├── simple_middleware.py # HTTP middleware with error metrics
    │   └── simple/             # Simple monitoring utilities
    ├── events/                 # Event bus
    ├── security/               # Security infrastructure
    └── performance/            # Performance monitoring
```

## Development Standards

### Code Quality
- **Linting**: `ruff` (v0.1.6+) for code quality (configured in pyproject.toml)
- **Type Checking**: `mypy` (v1.7.0+) with strict settings
- **Testing**: `pytest` (v7.4.0+) with async support, **80% coverage minimum**
- **Pre-commit**: Automated formatting and checks (v3.5.0+)
- **Security**: `bandit` (v1.7.5+) and `safety` (v2.3.0+) for security scanning

### Development Patterns
- **Async/Await**: ALL I/O operations must be async
- **Dependency Injection**: Use FastAPI's DI system
- **Error Handling**: Structured error responses with proper HTTP status codes
- **Logging**: Structured logging via `structlog` (v23.2.0+)
- **Configuration**: Environment-based config with Pydantic settings
- **Secrets Management**: Doppler SDK for production secrets

### Testing Requirements
```python
# Standard test pattern for async functions
@pytest.mark.asyncio
async def test_competency_assessment():
    # Arrange, Act, Assert pattern
    pass

# FastAPI testing pattern
def test_api_endpoint(client: TestClient):
    response = client.get("/api/endpoint")
    assert response.status_code == 200

# Unit test marking
@pytest.mark.unit
async def test_unit():
    pass

# Integration test marking
@pytest.mark.integration
async def test_integration():
    pass
```

## Critical Context for AI Development

### LLM Gateway Patterns (`src/core/llm/`)
- **Provider Failover**: Multiple LLM providers with health checks
- **Cost Tracking**: ALL LLM calls must track usage and costs via `cost_tracker.py`
- **Response Caching**: Cache responses via `cache.py` and `redis_cache_backend.py` to reduce costs
- **Budget Alerts**: Slack notifications when approaching budget limits
- **Rate Limiting**: Respect provider rate limits
- **Guardrails**: Output validation using guardrails-ai
- **Model Mapping**: Intelligent model selection via `optimizer.py`

### Temporal Workflow Rules (`src/services/workflow/`)
- **Determinism**: Workflows must be deterministic (no random, no direct external calls)
- **Activities**: External operations (DB, API calls) happen in activities only
- **Error Handling**: Use retry policies and compensation logic
- **Versioning**: Consider workflow versioning for production changes
- **Worker Management**: Proper worker configuration in `worker.py`
- **Temporal Version**: Using Temporal 1.22.0 with UI 2.21.0

### Slack Integration Constraints (`src/interfaces/slack/`)
- **Response Time**: Must respond within 3 seconds or use threading
- **Event Handling**: Use socket mode for real-time events via `socket_handler.py`
- **Threading**: Long operations must use Slack's threading API via `threading.py`
- **Error Handling**: Graceful degradation with user-friendly messages
- **Block Kit**: Use `block_builder.py` for rich message formatting
- **Conversation State**: Maintain context via `conversation_manager.py`
- **DM Intelligence**: Smart DM handling via `intelligent_dm.py`

### Database Patterns
- **Async ORM**: Use async SQLAlchemy patterns via `asyncpg` (v0.29.0+)
- **Migrations**: Alembic (v1.13.0+) for database schema changes
- **TimescaleDB**: Time-series data for analytics
- **Connection Pooling**: Proper connection management via `db_manager.py`
- **PostgreSQL**: Version 15 with Alpine Linux

### Shared Utilities (`src/shared/`) ✅ PRODUCTION READY

**Status**: Fully tested, production-ready error handling and monitoring system

#### Error Handling (`exceptions.py`, `error_handlers.py`)

Use structured error types for all exceptions:

```python
from src.shared.exceptions import DatabaseError, ValidationError, ErrorCategory
from src.shared.error_handlers import retry_with_exponential_backoff, CircuitBreaker

# Raise structured errors
raise DatabaseError(
    message="Connection timeout",
    query="SELECT * FROM users",
    context={"timeout": 30}
)

# Retry with exponential backoff
@retry_with_exponential_backoff(max_retries=3, base_delay=1.0)
async def fetch_data():
    return await api_call()

# Circuit breaker for external services
cb = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
result = await cb.call(external_service)
```

**Key Features:**
- ✅ 165+ tests, 85%+ coverage
- ✅ Async-safe error context with `contextvars`
- ✅ Automatic retry with exponential backoff and jitter
- ✅ Circuit breaker pattern for cascade failure prevention
- ✅ Prometheus metrics integration
- ✅ User-friendly error messages

**Error Types:**
- `ReflectAIError` - Base error class
- `DatabaseError` - Database operations
- `ValidationError` - Input validation
- `SlackAPIError` - Slack API interactions
- `LLMProviderError` - LLM provider issues
- `NetworkError` - Network failures
- `TemporalWorkflowError` - Workflow errors

#### Logging (`logging.py`)

Structured logging with correlation IDs:

```python
from src.shared.logging import get_logger, LoggingContext

logger = get_logger(__name__)

# Use logging context for request tracking
async def handle_request(user_id: str):
    with LoggingContext(correlation_id="req-123", user_id=user_id):
        logger.info("Processing request")
        await process_data()
```

#### Metrics (`error_metrics.py`)

Prometheus metrics for error monitoring:

```python
from src.shared.error_metrics import ErrorMetricsCollector

metrics = ErrorMetricsCollector(component="my_service")

try:
    result = await operation()
except ReflectAIError as e:
    metrics.track_error(e, handler_type="retry", processing_duration=0.123)
    raise
```

**Available Metrics:**
- `reflectai_errors_total` - Error counts by category/severity
- `reflectai_error_handling_duration_seconds` - Processing time
- `reflectai_circuit_breaker_state` - Circuit breaker states
- `reflectai_retry_attempts_total` - Retry statistics
- `reflectai_user_facing_errors_total` - User impact tracking

#### Documentation

- **[Error Handling Guide](docs/error-handling-guide.md)** - Complete usage guide
- **[Shared Utilities README](src/shared/README.md)** - API reference
- **[Unit Tests](tests/unit/shared/)** - 5 comprehensive test files
- **[Integration Tests](tests/integration/)** - Integration test suite with error_handling tests

## Common Development Commands

### Environment Setup
```bash
./rai setup all           # Complete development environment setup
./rai setup pdm           # Install PDM package manager
./rai setup deps          # Install dependencies
./rai setup db            # Setup database
./rai setup redis         # Setup Redis
./rai setup secrets       # Configure secrets (Doppler)
```

### Development
```bash
./rai run app             # Start FastAPI server (port 3000)
./rai run worker          # Run background workers
```

### Docker Commands
```bash
./rai docker build        # Build Docker images (dev/prod/test)
./rai docker up dev       # Start development containers
./rai docker down         # Stop containers (--volumes to remove data)
./rai docker restart      # Restart containers
./rai docker logs app     # View application logs (-f to follow)
./rai docker exec app bash # Shell into app container
./rai docker status       # Show container status and resource usage
./rai docker clean        # Clean up Docker resources
./rai docker test         # Run tests in Docker
./rai docker health       # Check health status of all containers
./rai docker stats        # Live resource usage statistics
```

### Database Commands
```bash
./rai db migrate          # Run database migrations
./rai db reset            # Reset database (DESTRUCTIVE)
./rai db seed             # Seed database with test data
./rai db connect          # Open PostgreSQL interactive shell (psql)
./rai db backup           # Backup database to file
./rai db restore          # Restore database from backup
./rai db query            # Execute SQL query
./rai db tables           # List all database tables
./rai db indexes          # List all database indexes
./rai db connections      # Show active database connections
./rai db slow-queries     # Show slow queries
./rai db vacuum           # Vacuum database (cleanup and optimize)
./rai db analyze          # Analyze database statistics
./rai db size             # Show database and table sizes
```

### Redis Commands
```bash
./rai redis status        # Check Redis status and connection
./rai redis cli           # Open interactive Redis CLI
./rai redis info          # Show detailed Redis information
./rai redis keys          # List Redis keys (with optional pattern)
./rai redis get           # Get value of a key
./rai redis del           # Delete a key
./rai redis flushdb       # Flush current database (CAREFUL!)
./rai redis memory        # Show memory usage statistics
./rai redis monitor       # Monitor Redis commands in real-time
./rai redis cache-clear   # Clear application cache
./rai redis backup        # Backup Redis data
```

### Temporal Commands
```bash
./rai temporal ui                   # Open Temporal Web UI in browser
./rai temporal workflows list       # List all workflows
./rai temporal workflows describe   # Describe workflow details
./rai temporal workflows cancel     # Cancel running workflow
./rai temporal workflows terminate  # Terminate workflow (forcefully)
./rai temporal workflows retry      # Retry failed workflow
./rai temporal workflows history    # Show workflow execution history
./rai temporal workflows query      # Query workflow state
./rai temporal queues list          # List all task queues
./rai temporal queues describe      # Describe task queue
./rai temporal queues stats         # Show task queue statistics
./rai temporal workers list         # List all active workers
./rai temporal workers status       # Show worker status
./rai temporal workers restart      # Restart worker containers
./rai temporal health               # Check Temporal server health
```

### Testing
```bash
./rai test                # Run all tests with coverage
./rai test unit           # Run unit tests only
./rai test coverage       # Run tests with detailed coverage report
```

### Quality Checks
```bash
./rai check               # Run all code quality checks
./rai check lint          # Run ruff linting
./rai check format        # Format code with ruff
./rai check type          # Run mypy type checking
./rai check security      # Run bandit security scanning
```

## Application Ports

- **App Port**: 3000 (main application)
- **Metrics Port**: 8080 (Prometheus metrics)
- **Health Check Port**: 8090 (health endpoints)
- **Database Port**: 5432 (PostgreSQL)
- **Redis Port**: 6379 (Redis)
- **Temporal Port**: 7233 (Temporal server)
- **Temporal Web Port**: 8088 (Temporal UI)

## Monitoring & Observability

### Health & Readiness Endpoints
```bash
# Liveness probe - Is the app running?
curl http://localhost:3000/health
# Returns: {"status": "healthy", "version": "0.1.2-alpha", "timestamp": "..."}

# Readiness probe - Can the app handle requests?
curl http://localhost:3000/ready
# Returns: {"ready": true, "checks": {"database": "ready", "redis": "ready", ...}}

# Detailed health check
curl http://localhost:3000/health/detailed
# Returns: Component-level health status with dependencies
```

### Prometheus Metrics
```bash
# Metrics server runs on separate port (8080)
curl http://localhost:8080/metrics

# Available metrics:
# - reflectai_http_requests_total - HTTP request counter
# - reflectai_http_request_duration_seconds - Request latency histogram
# - reflectai_errors_total - Error counter by category/severity
# - reflectai_circuit_breaker_state - Circuit breaker states
# - reflectai_retry_attempts_total - Retry statistics
# - reflectai_user_facing_errors_total - User-visible errors
```

### Rate Limiting
```bash
# Rate limits are enforced per endpoint with response headers
curl -v http://localhost:3000/api/v1/llm/generate

# Response headers include:
# X-RateLimit-Limit: 100
# X-RateLimit-Remaining: 99
# X-RateLimit-Reset: 1698765432
# X-RateLimit-Client: <client-hash>

# Rate limit exceeded returns 429:
# {"error": "Rate limit exceeded", "retry_after": 60}
```

### Correlation IDs
```bash
# All requests include correlation IDs for tracing
curl -v http://localhost:3000/health

# Response includes:
# X-Correlation-ID: 550e8400-e29b-41d4-a716-446655440000
# X-Request-ID: 550e8400-e29b-41d4-a716-446655440000

# Provide your own correlation ID:
curl -H "X-Correlation-ID: my-trace-123" http://localhost:3000/health
# Response will include the same ID
```

### Endpoint Rate Limits
Default limits (configurable in `src/infrastructure/security/rate_limiter.py`):
- `/api/v1/llm/generate`: 2/sec, 20/min, 200/hour
- `/api/v1/analyze`: 5/sec, 50/min, 500/hour
- `/api/v1/slack/events`: 10/sec, 100/min, 1000/hour
- `/api/v1/workflows/start`: 1/sec, 10/min, 100/hour
- Global default: 100/sec, 1000/min, 10000/hour

Authenticated users get 2x multiplier on all limits.

## Key Configuration Files

- `pyproject.toml` - Project dependencies and tool configuration (PDM, ruff, mypy, pytest, coverage)
- `rai` - Unified development CLI (Python script - executable)
- `.env` - Environment variables (create from `.env.example`)
- `.env.example` - Environment variable template with all required settings
- `docker-compose.yml` - Development containers configuration
- `Dockerfile` - Multi-stage Docker build configuration
- `pytest.ini` - Pytest configuration with test markers and settings
- `tests/conftest.py` - Test configuration and fixtures
- `.pre-commit-config.yaml` - Pre-commit hook configuration

## Testing Infrastructure

### Test Organization
```
tests/
├── conftest.py                    # Shared fixtures and configuration
├── mocks/                         # Mock infrastructure
│   ├── llm_mock.py               # LLM response mocking
│   ├── slack_mock.py             # Slack API mocking
│   ├── temporal_mock.py          # Temporal workflow mocking
│   └── external_services_mock.py # External service mocking
├── testcontainers.py             # Containerized test environments
├── unit/                         # Unit tests (fast, isolated)
│   ├── shared/                   # Shared utilities tests (5 files)
│   ├── core/                     # Core logic tests
│   ├── infrastructure/           # Infrastructure tests
│   └── interfaces/               # Interface tests
├── integration/                  # Integration tests (slower, with dependencies)
│   └── system/                   # System integration tests
├── factories/                    # Test data factories
└── fixtures/                     # Test fixtures and golden datasets
```

### Test Features
- **Comprehensive Mocking**: LLM, Slack, Temporal, external services
- **Testcontainers**: Isolated PostgreSQL, Redis, and NATS testing
- **Performance Validation**: Automatic timing validation and regression detection
- **Coverage Enforcement**: 80% minimum coverage target
- **Test Markers**: unit, integration, e2e, slow, performance, security, phase1-5
- **Async Support**: Full async/await test support with pytest-asyncio

### LLM Testing
- Mock OpenAI responses using `tests/mocks/llm_mock.py`
- Test cost tracking with different providers
- Validate failover logic with provider outages
- Test guardrails validation

### Temporal Testing
- Use `WorkflowEnvironment` for workflow tests
- Test activity retry logic
- Validate workflow state transitions
- Mock temporal client using `tests/mocks/temporal_mock.py`

### Slack Testing
- Mock Slack SDK responses using `tests/mocks/slack_mock.py`
- Test event handling with sample payloads
- Validate threading and response timing
- Test Block Kit builder output

## Performance Considerations

- **LLM Response Time**: Target <2 seconds for 95th percentile
- **Database Queries**: Use async connections, optimize with indexes
- **Cache Strategy**: Redis for session data and LLM response caching
- **Memory Usage**: Monitor Python memory usage in long-running workflows
- **Connection Pooling**: Configured in database and Redis managers

## Security Notes

- **Secrets Management**: Use Doppler SDK for production secrets
- **API Keys**: Never log or commit API keys
- **User Data**: PII handling compliance required via `privacy_compliance.py`
- **Authentication**: OAuth2 integration for user management
- **Rate Limiting**: Protect against abuse
- **Audit Trail**: Track security-relevant events via `audit_trail.py`
- **Security Scanning**: Regular bandit and safety checks

## Development Workflow

1. **Planning**: Create detailed implementation plan before coding
2. **Research**: Understand existing patterns before changes
3. **Implementation**: Follow TDD where possible
4. **Testing**: Maintain 80% coverage, test async patterns
5. **Review**: Code review focusing on async patterns and error handling
6. **Documentation**: Update relevant docs with changes
7. **Pre-commit**: Run pre-commit hooks before committing

## Current Focus Areas (v0.1.2-alpha)

The platform is in active development with focus on:

- **Core Infrastructure**: Shared utilities, error handling, monitoring (✅ Complete)
- **LLM Integration**: Cost management, provider failover, caching
- **Competency Assessment**: Scoring algorithms, gap analysis, level calculation
- **Slack Integration**: Real-time interaction, slash commands, conversation management
- **Temporal Workflows**: Orchestration, long-running operations, activity management
- **Testing**: Comprehensive test coverage with mocks and testcontainers
- **Documentation**: Architecture docs, API docs, deployment guides

---

*This context file is automatically loaded by Claude Code to provide project-specific guidance for AI-assisted development.*
*Last Updated: October 7, 2025*
