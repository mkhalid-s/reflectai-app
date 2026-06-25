# Technology Stack & Build System

## Core Technologies

### Language & Framework
- **Python 3.11+**: Primary development language
- **FastAPI**: High-performance async web framework for APIs
- **Pydantic**: Data validation and settings management
- **AsyncIO**: Asynchronous programming for concurrent operations

### AI & Multi-Agent System
- **Temporal.io**: Workflow orchestration for agents (Phase 1)
- **CrewAI**: Future option for complex, dynamic agent collaboration
- **LiteLLM**: LLM integration with multiple providers
- **LangFuse**: LLM observability and monitoring
- **Guardrails AI**: LLM output validation and safety

### Slack Integration
- **slack-bolt**: Modern Slack app framework
- **slack-sdk**: Official Slack SDK for Python

### Database & Storage
- **PostgreSQL**: Primary database (with SQLite fallback for development)
- **SQLAlchemy**: ORM with async support
- **Alembic**: Database migrations
- **Redis**: Caching and session storage

### Infrastructure & Deployment
- **Docker**: Containerization
- **Docker Compose**: Local development orchestration
- **Kubernetes**: Production container orchestration
- **Tilt**: Development environment management

### Monitoring & Observability
- **OpenTelemetry**: Distributed tracing and metrics
- **Prometheus**: Metrics collection
- **Grafana**: Visualization and dashboards
- **Structlog**: Structured logging

## Build System

### Package Management
- **Poetry**: Primary dependency management and packaging
- **pyproject.toml**: Modern Python project configuration
- **requirements.txt**: Fallback compatibility for deployment

### Development Tools
- **Ruff**: Fast linting and formatting (replaces Black, isort, Flake8)
- **MyPy**: Static type checking with strict mode
- **Bandit**: Security vulnerability scanning
- **Safety**: Dependency vulnerability checking
- **Pre-commit**: Git hooks for code quality

### Testing Framework
- **pytest**: Primary testing framework
- **pytest-asyncio**: Async test support
- **pytest-cov**: Coverage reporting
- **Hypothesis**: Property-based testing
- **Factory Boy**: Test data generation

## Common Commands

### Development Setup
```bash
# Install dependencies
make install

# Set up development environment
make setup

# Start development environment
make dev

# Copy environment template
make env-template
```

### Code Quality
```bash
# Run all quality checks
make quality

# Lint and format code
make lint format

# Type checking
make type-check

# Security scanning
make security

# Run pre-commit hooks
make pre-commit-run
```

### Testing
```bash
# Run unit tests
make test

# Run all tests with coverage
make test-all

# Run integration tests
make test-integration

# Run benchmarks
make benchmark
```

### Database Operations
```bash
# Run migrations
make migrate

# Create new migration
make migrate-create MESSAGE="description"

# Reset database (development only)
make db-reset
```

### Docker Operations
```bash
# Start infrastructure services
make docker-up

# Stop services
make docker-down

# View logs
make docker-logs

# Clean up Docker resources
make docker-clean
```

### Environment Management
```bash
# Check configuration
make env-check

# Quick start for new developers
make quick-start

# Open monitoring dashboards
make monitor
```

## Configuration

### Environment Variables
- Configuration managed through `.env` files
- Pydantic Settings for type-safe configuration
- Environment-specific overrides supported
- Secrets management via environment variables

### Deployment Modes
- **Development**: SQLite + memory cache
- **Production**: PostgreSQL + Redis
- **Socket Mode**: WebSocket connection to Slack
- **HTTP Mode**: HTTP endpoints for Slack events