# Project Structure & Organization

## Root Directory Structure

```
reflectai/
├── src/                    # Main application source code
├── tests/                  # Test suite with comprehensive coverage
├── config/                 # Configuration files (YAML-based)
├── data/                   # Data files and database
├── docs/                   # Comprehensive documentation
├── deployment/             # Deployment configurations
├── scripts/                # Utility and management scripts
├── tools/                  # Development and operational tools
├── templates/              # HTML/CSS templates for reports
└── examples/               # Usage examples and samples
```

## Source Code Organization (`src/`)

### Core Application Structure
```
src/
├── __init__.py
├── main.py                 # Application entry point
├── agent/                  # LangGraph agent implementation
├── bot/                    # Slack bot integration
├── config/                 # Configuration management
├── database/               # Database models and operations
├── health/                 # Health check endpoints
├── llm/                    # LLM client implementations
├── utils/                  # Shared utilities
├── core/                   # Business logic and domain models
├── infrastructure/         # Infrastructure concerns
├── interfaces/             # External interface adapters
├── services/               # Application services
└── shared/                 # Shared components across modules
```

### Detailed Module Structure

#### Core Business Logic (`src/core/`)
- `agents/` - Multi-agent system components
- `business/` - Business logic and domain rules
- `models/` - Domain models and data structures
- `tools/` - Agent tools and capabilities
- `workflows/` - Business process workflows

#### Infrastructure Layer (`src/infrastructure/`)
- `cache/` - Caching implementations
- `config/` - Configuration management system
- `database/` - Database infrastructure
- `messaging/` - Event messaging systems
- `monitoring/` - Observability and metrics
- `security/` - Security implementations

#### Interface Layer (`src/interfaces/`)
- `api/` - REST API endpoints
- `slack/` - Slack integration adapters
- `webhooks/` - Webhook handlers

#### Services Layer (`src/services/`)
- `activity/` - Activity tracking services
- `analysis/` - Analysis and processing services
- `notification/` - Notification services
- `reporting/` - Report generation services
- `user/` - User management services

## Configuration Structure (`config/`)

```
config/
├── base.yaml               # Base configuration
├── agents/                 # Agent-specific configurations
├── environments/           # Environment-specific settings
├── tools/                  # Tool configurations
└── workflows/              # Workflow definitions
```

## Testing Structure (`tests/`)

```
tests/
├── conftest.py            # Global test configuration
├── fixtures/              # Test data and fixtures
├── unit/                  # Unit tests (mirror src/ structure)
├── integration/           # Integration tests
├── e2e/                   # End-to-end tests
├── benchmarks/            # Performance benchmarks
└── mocks/                 # Mock implementations
```

## Deployment Structure (`deployment/`)

```
deployment/
├── docker/                # Docker configurations
├── kubernetes/            # Kubernetes manifests
├── terraform/             # Infrastructure as code
└── scripts/               # Deployment scripts
```

## Architecture Patterns

### Layered Architecture
- **Interfaces**: External communication (Slack, API, webhooks)
- **Services**: Application logic and orchestration
- **Core**: Business logic and domain models
- **Infrastructure**: Technical concerns (database, cache, messaging)

### Dependency Injection
- Configuration-driven dependency injection
- Interface-based abstractions
- Factory patterns for component creation

### Event-Driven Design
- Async/await patterns throughout
- Event-driven communication between components
- Message queuing for decoupled processing

### Multi-Agent Architecture
- Agent-based processing with CrewAI
- Tool-based agent capabilities
- Workflow orchestration for complex tasks

## File Naming Conventions

### Python Files
- `snake_case` for all Python files and modules
- `__init__.py` files for package initialization
- Test files: `test_*.py` or `*_test.py`

### Configuration Files
- YAML format for configuration: `*.yaml`
- Environment files: `.env`, `.env.template`
- Docker files: `Dockerfile`, `docker-compose.yml`

### Documentation
- Markdown format: `*.md`
- Numbered documentation: `01-TITLE.md`
- README files in each major directory

## Import Conventions

### Absolute Imports
- Always use absolute imports from `src/`
- Example: `from src.config.settings import settings`

### Module Organization
- Group imports: standard library, third-party, local
- Use `from` imports for specific functions/classes
- Avoid wildcard imports (`from module import *`)

### Circular Import Prevention
- Careful dependency management
- Use of factory patterns where needed
- Late imports when necessary

## Code Organization Principles

### Single Responsibility
- Each module has a clear, single purpose
- Separation of concerns between layers
- Small, focused functions and classes

### Interface Segregation
- Small, focused interfaces
- Protocol-based typing where appropriate
- Clear boundaries between components

### Dependency Inversion
- Depend on abstractions, not concretions
- Configuration-driven implementations
- Pluggable components via interfaces

## Data Flow Patterns

### Request Processing
1. Interface layer receives request
2. Service layer orchestrates processing
3. Core layer applies business logic
4. Infrastructure layer handles persistence
5. Response flows back through layers

### Agent Workflows
1. Message classification and routing
2. Agent selection (single vs multi-agent)
3. Tool execution and data gathering
4. Analysis and synthesis
5. Response generation and delivery