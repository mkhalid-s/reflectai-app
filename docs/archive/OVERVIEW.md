# ReflectAI Platform - Architecture Overview

## Introduction

ReflectAI is an AI-powered competency analysis system that helps organizations understand and develop team capabilities through intelligent assessment and personalized development recommendations.

**Version**: 0.1.2-alpha
**Architecture**: Microservices with event-driven workflows
**Deployment**: Docker/Kubernetes with cloud-native patterns

---

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Core Components](#core-components)
3. [Data Flow](#data-flow)
4. [Integration Points](#integration-points)
5. [Related Documentation](#related-documentation)

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      External Interfaces                     │
│  ┌───────────┐  ┌───────────┐  ┌────────────┐             │
│  │   Slack   │  │ REST API  │  │ Web Portal │             │
│  └─────┬─────┘  └─────┬─────┘  └─────┬──────┘             │
└────────┼──────────────┼──────────────┼────────────────────┘
         │              │              │
┌────────▼──────────────▼──────────────▼────────────────────┐
│               Application Layer (FastAPI)                   │
│  ┌──────────────┐  ┌───────────────┐  ┌────────────────┐ │
│  │ Slack Adapter│  │  API Routes   │  │  Auth Middleware│ │
│  └──────┬───────┘  └───────┬───────┘  └────────┬───────┘ │
└─────────┼──────────────────┼──────────────────┼──────────┘
          │                  │                  │
┌─────────▼──────────────────▼──────────────────▼──────────┐
│                   Business Logic Layer                     │
│  ┌──────────────┐  ┌───────────────┐  ┌────────────────┐ │
│  │ LLM Gateway  │  │  Assessment   │  │  Classification│ │
│  │  (Failover)  │  │   Engine      │  │     Engine     │ │
│  └──────┬───────┘  └───────┬───────┘  └────────┬───────┘ │
└─────────┼──────────────────┼──────────────────┼──────────┘
          │                  │                  │
┌─────────▼──────────────────▼──────────────────▼──────────┐
│               Workflow Orchestration (Temporal)            │
│  ┌─────────────┐  ┌───────────────┐  ┌────────────────┐ │
│  │  Workflows  │  │   Activities  │  │     Workers    │ │
│  └─────────────┘  └───────────────┘  └────────────────┘ │
└───────────────────────────────────────────────────────────┘
          │                  │                  │
┌─────────▼──────────────────▼──────────────────▼──────────┐
│                     Data Layer                             │
│  ┌──────────────┐  ┌───────────────┐  ┌────────────────┐ │
│  │  PostgreSQL  │  │     Redis     │  │  TimescaleDB   │ │
│  │  (Primary)   │  │    (Cache)    │  │  (Analytics)   │ │
│  └──────────────┘  └───────────────┘  └────────────────┘ │
└───────────────────────────────────────────────────────────┘
```

### Architectural Principles

1. **Async-First**: All I/O operations use async/await patterns
2. **Event-Driven**: Temporal workflows orchestrate long-running processes
3. **Resilient**: LLM gateway with provider failover and retry logic
4. **Observable**: Comprehensive logging, metrics, and health checks
5. **Scalable**: Stateless services, horizontal scaling ready

---

## Core Components

### 1. LLM Gateway (`src/core/llm/`)

**Purpose**: Unified interface to multiple LLM providers with intelligent routing and cost tracking.

**Key Features**:
- Multi-provider support (OpenAI, Anthropic, etc.)
- Automatic failover and retry logic
- Cost tracking and budget alerts
- Response caching (Redis-backed)
- Rate limiting and quota management

**Files**:
- `gateway.py` - Main routing and provider management
- `cost_tracker.py` - Budget monitoring and alerts
- `optimizer.py` - Model selection logic
- `cache.py` - Response caching
- `providers.py` - Provider implementations

**Documentation**: See [Technology Stack](./TECHNOLOGY_STACK.md) for LLM details.

---

### 2. Assessment Engine (`src/core/assessment/`)

**Purpose**: Competency scoring and gap analysis for team development.

**Key Features**:
- Activity-based scoring algorithms
- Competency gap identification
- Personalized development recommendations
- Progress tracking over time

**Files**:
- `competency_assessor.py` - Main assessment orchestration
- `scoring/` - Activity scoring algorithms
- `gap_analyzer.py` - Competency gap analysis

**Data Flow**:
1. User activity → Classification
2. Classification → Scoring
3. Scoring → Competency mapping
4. Competency mapping → Gap analysis
5. Gap analysis → Recommendations

---

### 3. Slack Integration (`src/interfaces/slack/`)

**Purpose**: Real-time interaction via Slack for assessments and queries.

**Key Features**:
- Socket mode for real-time events
- Slash commands for user interaction
- Interactive message components
- Thread-based conversations
- 3-second response time compliance

**Files**:
- `socket_handler.py` - Event handling
- `slash_commands.py` - Command processors
- `adapter.py` - Slack SDK integration
- `block_builder.py` - Message formatting
- `workflow_integration.py` - Slack-Temporal bridge

**Documentation**: See [Slack Integration Architecture](./SLACK_INTEGRATION_ARCHITECTURE.md).

---

### 4. Temporal Workflows (`src/services/workflow/`)

**Purpose**: Orchestrate long-running assessment processes with reliability.

**Key Features**:
- Deterministic workflow execution
- Automatic retries and error handling
- Workflow versioning support
- Activity-based I/O operations
- Complete execution history

**Files**:
- `workflows.py` - Workflow definitions
- `activities.py` - Activity implementations
- `worker.py` - Worker configuration
- `models.py` - Data models
- `temporal_client.py` - Client setup

**Critical Rules**:
- Workflows must be deterministic (no random, no direct I/O)
- All external operations happen in activities
- Use retry policies for transient failures
- Version workflows for production changes

---

### 5. Classification Engine (`src/core/classification/`)

**Purpose**: Analyze and classify user activities into competency areas.

**Key Features**:
- Intent analysis using LLMs
- Content extraction from activities
- Date range extraction
- Multi-label classification

**Files**:
- `intent_analyzer.py` - Intent classification
- `content_extractor.py` - Content parsing
- `date_range_extractor.py` - Temporal information extraction

---

### 6. Data Layer (`src/core/storage/`)

**Purpose**: Persistent storage and data access patterns.

**Technologies**:
- **PostgreSQL**: Primary relational database
- **TimescaleDB**: Time-series analytics extension
- **Redis**: Session management and caching

**Patterns**:
- Async SQLAlchemy for database operations
- Repository pattern for data access
- Pydantic models for validation
- Alembic for schema migrations

**Files**:
- `managers/` - Data access layer (repositories)
- `models/` - Pydantic data models

---

## Data Flow

### Assessment Workflow

```
1. User Activity (Slack)
   │
   ├─→ Slack Socket Handler
   │   └─→ Command Parser
   │
2. Classification
   │
   ├─→ Intent Analyzer (LLM Gateway)
   │   └─→ Multi-label Classifier
   │
3. Temporal Workflow Triggered
   │
   ├─→ Activity: Fetch User History
   ├─→ Activity: Score Competencies
   ├─→ Activity: Analyze Gaps
   └─→ Activity: Generate Recommendations
   │
4. Response Generation
   │
   ├─→ Format Results (Slack Blocks)
   ├─→ Send to User (Threading)
   └─→ Store in Database (TimescaleDB)
```

### LLM Request Flow

```
1. Component needs LLM
   │
   ├─→ LLM Gateway
   │   ├─→ Check Cache (Redis)
   │   │   └─→ Cache Hit? Return cached
   │   │
   │   ├─→ Select Provider (Optimizer)
   │   │   └─→ Based on: cost, latency, availability
   │   │
   │   ├─→ Execute Request
   │   │   ├─→ Primary provider
   │   │   └─→ Failover if needed
   │   │
   │   ├─→ Track Cost
   │   │   └─→ Update budget, check alerts
   │   │
   │   └─→ Cache Response
   │
2. Return to caller
```

---

## Integration Points

### External Services

1. **Slack API**
   - Socket mode for events
   - Web API for responses
   - OAuth2 for authentication

2. **LLM Providers**
   - OpenAI API
   - Anthropic API (Claude)
   - Custom gateway abstraction

3. **Temporal Server**
   - gRPC for workflow execution
   - WebSocket for workflow updates
   - HTTP API for management

### Internal Services

1. **FastAPI Application** → Temporal Workers
2. **Slack Adapter** → Temporal Workflows
3. **LLM Gateway** → All Business Logic
4. **Assessment Engine** → Storage Layer
5. **All Components** → Monitoring/Logging

---

## Scalability Considerations

### Horizontal Scaling

**Stateless Components** (can scale freely):
- FastAPI application servers
- Temporal workers
- Slack event handlers

**Stateful Components** (managed scaling):
- PostgreSQL (read replicas)
- Redis (clustering)
- Temporal server (clustered)

### Performance Targets

- **API Response Time**: <200ms (95th percentile)
- **LLM Response Time**: <2s (95th percentile)
- **Slack Response**: <3s (requirement)
- **Workflow Completion**: <60s for standard assessments
- **Database Queries**: <50ms (95th percentile)

---

## Security Architecture

### Authentication & Authorization

- OAuth2 for Slack integration
- JWT tokens for API access
- Role-based access control (RBAC)
- API key management for LLM providers

### Data Security

- Encryption at rest (database)
- Encryption in transit (TLS)
- Secret management (environment variables)
- PII handling compliance
- Audit logging for sensitive operations

### Network Security

- Rate limiting per user/endpoint
- Input validation (Pydantic)
- SQL injection prevention (parameterized queries)
- XSS prevention (sanitized outputs)

**Documentation**: See [Security Guide](../security/SECURITY_GUIDE.md).

---

## Monitoring & Observability

### Metrics

- Application metrics (Prometheus)
- LLM cost tracking (custom)
- Workflow execution (Temporal UI)
- Database performance (PostgreSQL stats)

### Logging

- Structured logging (JSON)
- Correlation IDs for tracing
- Log aggregation (stdout → collector)
- Error tracking and alerting

### Health Checks

- `/health` - Application health
- `/health/db` - Database connectivity
- `/health/redis` - Cache connectivity
- `/health/temporal` - Workflow engine connectivity

**Documentation**: See [Monitoring Guide](../deployment/MONITORING.md).

---

## Deployment Architecture

### Local Development

```
Docker Compose:
├── app (FastAPI)
├── postgres (Database)
├── redis (Cache)
├── temporal (Workflow engine)
└── temporal-ui (Management interface)
```

### Production (Kubernetes)

```
Kubernetes Cluster:
├── Namespace: reflectai-prod
│   ├── Deployment: api (3+ replicas)
│   ├── Deployment: workers (5+ replicas)
│   ├── Service: postgres (managed)
│   ├── Service: redis (managed)
│   └── Service: temporal (clustered)
├── Ingress: HTTPS/TLS termination
├── ConfigMaps: Application configuration
└── Secrets: API keys, credentials
```

**Documentation**: See [Deployment Guide](../deployment/DEPLOYMENT_GUIDE.md) and [Enterprise Architecture](./ENTERPRISE_ARCH.md).

---

## Technology Stack Summary

| Layer | Technologies |
|-------|-------------|
| **Language** | Python 3.11+ |
| **Web Framework** | FastAPI, Uvicorn, Pydantic |
| **Orchestration** | Temporal |
| **Database** | PostgreSQL, TimescaleDB |
| **Cache** | Redis |
| **LLM** | OpenAI, LiteLLM, custom gateway |
| **Integration** | Slack SDK, OAuth2 |
| **Testing** | Pytest, async support |
| **Quality** | Ruff (linting), MyPy (types) |
| **Deployment** | Docker, Kubernetes, Helm |
| **Monitoring** | Prometheus, Grafana, structured logs |

**Full Details**: See [Technology Stack](./TECHNOLOGY_STACK.md).

---

## Design Patterns

### Architectural Patterns

1. **Gateway Pattern** - LLM gateway for unified provider interface
2. **Repository Pattern** - Data access abstraction
3. **Workflow Pattern** - Temporal for orchestration
4. **Adapter Pattern** - External service integration (Slack)
5. **Strategy Pattern** - Provider selection, caching strategies

### Code Patterns

1. **Dependency Injection** - FastAPI DI system
2. **Async/Await** - All I/O operations
3. **Type Hints** - Full type coverage with MyPy
4. **Pydantic Models** - Data validation and serialization
5. **Structured Logging** - Consistent log format with context

---

## Development Workflow

### Local Development

```bash
# Setup environment
./rai setup all

# Start services
./rai docker up dev

# Run application
./rai run app

# Run tests
./rai test

# Quality checks
./rai check
```

### Code Quality Standards

- **Testing**: 80% minimum coverage
- **Linting**: Ruff with project config
- **Type Checking**: MyPy strict mode
- **Documentation**: Docstrings for public APIs
- **Commits**: Conventional Commits format

**Documentation**: See [Developer Guide](../development/DEVELOPER_GUIDE.md).

---

## Related Documentation

### Architecture Deep Dives
- [Enterprise Architecture](./ENTERPRISE_ARCH.md) - Kubernetes, scaling, production
- [Multi-Agent System](./MULTI_AGENT_SYSTEM.md) - AI agent architecture
- [Model Specification](./MODEL_SPECIFICATION.md) - Data models and schemas
- [Slack Integration Architecture](./SLACK_INTEGRATION_ARCHITECTURE.md) - Slack details
- [Technology Stack](./TECHNOLOGY_STACK.md) - Complete tech stack with justifications

### Development Guides
- [Developer Guide](../development/DEVELOPER_GUIDE.md) - Getting started
- [API Documentation](../development/API_DOCUMENTATION.md) - REST API reference
- [AI Development Guide](../AI_DEVELOPMENT_GUIDE.md) - AI-assisted development

### Operations
- [Deployment Guide](../deployment/DEPLOYMENT_GUIDE.md) - Deployment procedures
- [Operations Manual](../deployment/OPERATIONS_MANUAL.md) - Day-to-day operations
- [Monitoring Guide](../deployment/MONITORING.md) - Monitoring setup

### Standards
- [Security Guide](../security/SECURITY_GUIDE.md) - Security best practices
- [Conventional Commits](../CONVENTIONAL_COMMITS_GUIDE.md) - Commit message format
- [Version Management](../VERSION_MANAGEMENT.md) - Version control workflow

---

## Version History

| Version | Date | Description |
|---------|------|-------------|
| 2.0 | Oct 5, 2025 | Rewritten as concise overview with links to detailed docs |
| 1.0 | Sep 2024 | Initial architecture documentation |

---

**Last Updated**: October 5, 2025
**Status**: Current architecture (v0.1.2-alpha)
**Maintained By**: ReflectAI Development Team
