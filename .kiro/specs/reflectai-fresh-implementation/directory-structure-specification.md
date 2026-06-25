# ReflectAI Directory Structure Specification

## 📁 Complete Directory Structure & File Organization

### 🎯 Directory Structure Principles

1. **Phase 1 Design**: Start with simplified versions, expand when metrics justify
2. **Domain-Driven Design**: Organize by business domain, not technical layers
3. **Clear Separation**: Infrastructure, business logic, and interfaces separated
4. **Consistent Naming**: Snake_case for Python files, kebab-case for configs
5. **Module Independence**: Each module self-contained with clear interfaces
6. **Future-Ready**: Structure supports both current simplified architecture and future complexity

### 📊 Phase 1 vs Future Structure Strategy

#### **Phase 1 Implementation Pattern**
```
module/
├── simple/          # Phase 1 implementation (use first)
├── complex/         # Future implementation (upgrade trigger documented)
└── common/          # Shared utilities
```

#### **Upgrade Triggers Documentation**
Each `complex/` directory includes `README.md` with specific triggers:
- **Agent Specialization**: >500 requests/day
- **Full Observability**: >3 services or complex debugging needs
- **NATS JetStream**: >1000 events/hour
- **Service Mesh**: >4 services with complex communication

## 📂 Root Level Structure

```
reflectai/
├── .backup/                          # Timestamped backups of old system
│   └── 2024_09_04_123456/          # Format: YYYY_MM_DD_HHMMSS
│       ├── src/                     # Old source code
│       ├── config/                  # Old configurations
│       └── data/                    # Old data files
│
├── .kiro/                           # Kiro IDE specifications
│   └── specs/
│       └── reflectai-fresh-implementation/
│           ├── requirements.md
│           ├── design.md
│           ├── tasks.md
│           └── directory-structure-specification.md
│
├── docs/                            # Project documentation
│   ├── api/                         # API documentation
│   ├── architecture/                # Architecture diagrams
│   ├── deployment/                  # Deployment guides
│   └── user-guides/                 # User documentation
│
├── config/                          # Configuration management
├── src/                             # Source code
├── tests/                           # Test suite
├── deployment/                      # Deployment configurations
├── tools/                           # Development tools
├── data/                           # Data files
├── scripts/                        # Utility scripts
└── templates/                      # Templates (PDF, email, etc.)
```

## 📁 Detailed Source Code Structure

### `/src` Directory Organization

```
src/
├── __init__.py
├── main.py                          # Application entry point
├── version.py                       # Version management
│
├── core/                            # Core business domain
│   ├── __init__.py
│   ├── agents/                      # Multi-agent system
│   ├── tools/                       # Tool framework
│   ├── workflows/                   # Temporal workflows
│   ├── models/                      # Domain models
│   └── business/                    # Business logic
│
├── infrastructure/                  # Technical infrastructure
│   ├── __init__.py
│   ├── database/                    # Database layer
│   ├── cache/                       # Caching layer
│   ├── messaging/                   # Event streaming (simplified)
│   ├── communication/               # Service communication
│   ├── config/                      # Config management
│   ├── monitoring/                  # Observability (simplified)
│   └── security/                    # Security components
│
├── interfaces/                      # External interfaces
│   ├── __init__.py
│   ├── slack/                       # Slack integration
│   ├── api/                         # REST API
│   └── webhooks/                    # Webhook handlers
│
├── services/                        # Application services
│   ├── __init__.py
│   ├── user/                        # User management
│   ├── activity/                    # Activity processing
│   ├── analysis/                    # Analysis services
│   ├── reporting/                   # Report generation
│   └── notification/                # Notifications
│
└── shared/                          # Shared utilities
    ├── __init__.py
    ├── auth/                        # Authentication
    ├── llm/                         # LLM gateway with model selection
    ├── utils/                       # Utilities
    └── constants/                   # Constants
```

## 🗂️ Module-Specific File Organization

### Core Domain Modules

#### `/src/core/agents/` - Simplified Multi-Agent System (Phase 1)
```
agents/
├── __init__.py
├── base/
│   ├── __init__.py
│   ├── base_agent.py               # Abstract base agent class
│   ├── agent_config.py             # Agent configuration models
│   ├── agent_metrics.py            # Performance metrics
│   ├── agent_context.py            # Context management
│   └── prompt_manager.py           # Dynamic prompt construction
│
├── combined/                       # Phase 1: 2 combined agents (Task 17)
│   ├── __init__.py
│   ├── analysis_agent.py           # Combined: Data Analyst + Competency Specialist
│   └── advisor_agent.py            # Combined: Career Strategist + Insights Synthesizer
│
├── specialized/                    # FUTURE: 4 specialized agents
│   ├── __init__.py
│   ├── README.md                   # Upgrade trigger: >500 requests/day
│   ├── data_analyst_agent.py       # Future: split from analysis_agent
│   ├── competency_specialist_agent.py  # Future: split from analysis_agent
│   ├── career_strategist_agent.py  # Future: split from advisor_agent
│   └── insights_synthesizer_agent.py   # Future: split from advisor_agent
│
├── conversation/
│   ├── __init__.py
│   ├── conversation_manager.py     # Conversation state management
│   ├── greeting_manager.py         # Greeting handling
│   ├── intent_classifier.py        # Intent classification (Task 30a)
│   ├── clarification_generator.py  # NEW: Intelligent clarification (Task 30a)
│   └── error_handler.py            # Error recovery
│
└── orchestration/
    ├── __init__.py
    ├── simple_orchestrator.py       # Phase 1: Core Temporal workflows
    ├── workflow_router.py           # Simple routing logic
    ├── temporal_workflows.py        # Temporal integration
    ├── resource_manager.py          # Resource limits
    ├── state_manager.py             # Workflow state
    └── crew_coordinator.py          # FUTURE: CrewAI when agents split
```

#### `/src/core/tools/` - Tool Framework
```
tools/
├── __init__.py
├── framework/
│   ├── __init__.py
│   ├── tool_framework.py           # Main framework
│   ├── base_tool.py                # Abstract base tool
│   ├── tool_registry.py            # Tool registration
│   ├── tool_discovery.py           # Tool discovery
│   ├── access_control.py           # RBAC for tools
│   └── performance_monitor.py      # Tool metrics
│
├── classification/
│   ├── __init__.py
│   ├── activity_classifier_tool.py
│   ├── intent_classifier_tool.py
│   ├── competency_mapper_tool.py
│   └── complexity_analyzer_tool.py
│
├── assessment/
│   ├── __init__.py
│   ├── competency_assessor_tool.py
│   ├── gap_analyzer_tool.py
│   ├── skill_mapper_tool.py
│   └── level_calculator_tool.py
│
├── storage/
│   ├── __init__.py
│   ├── activity_store_tool.py
│   ├── user_profile_store_tool.py
│   ├── competency_store_tool.py
│   └── cache_manager_tool.py
│
└── reporting/
    ├── __init__.py
    ├── progress_reporter_tool.py
    ├── trend_analyzer_tool.py
    ├── recommendation_engine_tool.py
    └── pdf_generator_tool.py
```

#### `/src/core/workflows/` - Temporal Workflows
```
workflows/
├── __init__.py
├── analysis/
│   ├── __init__.py
│   ├── simple_analysis_workflow.py
│   ├── complex_analysis_workflow.py
│   ├── comprehensive_analysis_workflow.py
│   └── workflow_activities.py
│
├── batch/
│   ├── __init__.py
│   ├── daily_batch_workflow.py
│   ├── weekly_report_workflow.py
│   ├── monthly_cleanup_workflow.py
│   └── batch_activities.py
│
└── conversation/
    ├── __init__.py
    ├── greeting_workflow.py
    ├── help_workflow.py
    ├── onboarding_workflow.py
    └── conversation_activities.py
```

### Infrastructure Modules

#### `/src/infrastructure/database/` - Database Layer
```
database/
├── __init__.py
├── connections/
│   ├── __init__.py
│   ├── postgres_client.py          # PostgreSQL connection
│   ├── pgbouncer_pool.py          # Connection pooling
│   └── timescale_client.py        # TimescaleDB features
│
├── repositories/
│   ├── __init__.py
│   ├── user_repository.py
│   ├── activity_repository.py
│   ├── competency_repository.py
│   └── base_repository.py
│
├── models/
│   ├── __init__.py
│   ├── user_model.py
│   ├── activity_model.py
│   ├── competency_model.py
│   └── base_model.py
│
└── migrations/
    ├── alembic.ini
    ├── env.py
    └── versions/
        ├── 001_initial_schema.py
        ├── 002_add_timescale.py
        └── 003_add_indexes.py
```

#### `/src/infrastructure/cache/` - Caching Layer with User-Context Awareness
```
cache/
├── __init__.py
├── redis_client.py                 # Redis connection
├── cache_manager.py                # Basic cache operations
├── user_aware_cache.py             # NEW: User-context-aware caching (Task 7e)
├── session_store.py                # Session management
├── strategies/
│   ├── __init__.py
│   ├── ttl_strategy.py            # TTL-based caching
│   ├── lru_strategy.py            # LRU eviction
│   ├── write_through_strategy.py  # Write-through cache
│   └── context_aware_strategy.py  # NEW: User context caching strategy
│
└── keys/
    ├── __init__.py
    ├── key_generator.py            # Key generation
    ├── key_patterns.py             # Key patterns
    ├── namespace_manager.py        # Namespace management
    └── safety_matrix.py            # NEW: Cache safety rules for user-dependent ops
```

#### `/src/infrastructure/messaging/` - Simplified Event Streaming (Task 8)
```
messaging/
├── __init__.py
├── simple/                         # Phase 1: Redis pub/sub approach
│   ├── __init__.py
│   ├── redis_pubsub.py             # Redis pub/sub client
│   ├── simple_events.py            # Basic event types
│   ├── event_publisher.py          # Event publishing
│   ├── event_subscriber.py         # Event subscription
│   └── event_deduplication.py      # TTL-based deduplication
│
├── complex/                        # FUTURE: NATS JetStream (>1000 events/hour)
│   ├── __init__.py
│   ├── README.md                   # Upgrade trigger documentation
│   ├── nats_client.py              # NATS JetStream client
│   ├── jetstream_manager.py        # Stream management
│   ├── schema_registry.py          # Event schema management
│   └── dead_letter_handler.py      # Dead letter queue handling
│
└── common/
    ├── __init__.py
    ├── event_models.py              # Pydantic event schemas
    ├── correlation_ids.py           # Event correlation
    └── event_metrics.py             # Basic event metrics
```

#### `/src/infrastructure/monitoring/` - Simplified Observability Stack (Task 9)
```
monitoring/
├── __init__.py
├── simple/                         # Phase 1: 3-tool stack (Structlog + Prometheus + Grafana)
│   ├── __init__.py
│   ├── prometheus_client.py        # Direct Prometheus integration
│   ├── metrics_collector.py        # Business metrics collection
│   ├── grafana_dashboards.py       # Dashboard definitions
│   ├── correlation_manager.py      # Simple correlation IDs
│   └── slack_alerter.py            # Basic Slack alerting
│
├── complex/                        # FUTURE: Full observability (>3 services)
│   ├── __init__.py
│   ├── README.md                   # Upgrade trigger documentation
│   ├── opentelemetry_setup.py      # OpenTelemetry OTLP setup
│   ├── tempo_client.py             # Distributed tracing storage
│   ├── victoria_metrics_client.py  # Advanced metrics platform
│   └── pagerduty_alerter.py        # Production alerting
│
└── common/
    ├── __init__.py
    ├── health_checker.py            # Health check utilities
    ├── metrics_registry.py          # Metrics definition registry
    └── alert_manager.py             # Alert management utilities
```

#### `/src/infrastructure/communication/` - Service Communication (Task 45 Deferred)
```
communication/
├── __init__.py
├── simple/                         # Phase 1: Direct HTTP communication
│   ├── __init__.py
│   ├── http_client.py              # HTTP client with connection pooling
│   ├── health_checker.py           # Basic health checks
│   ├── circuit_breaker.py          # Application-level circuit breaking
│   └── load_balancer.py            # Simple load balancing
│
├── service_mesh/                   # FUTURE: Service mesh (>4 services)
│   ├── __init__.py
│   ├── README.md                   # Upgrade trigger: >4 services
│   ├── consul_connect_manager.py   # Consul Connect integration
│   ├── mtls_certificate_manager.py # mTLS certificate management
│   ├── traffic_policy_manager.py   # Traffic management policies
│   └── service_topology.py         # Service dependency mapping
│
└── discovery/
    ├── __init__.py
    ├── simple_discovery.py          # Environment/DNS-based discovery
    └── consul_discovery.py          # FUTURE: Consul service discovery
```

### Shared Modules

#### `/src/shared/llm/` - LLM Gateway with Model Selection (Task 13b)
```
llm/
├── __init__.py
├── gateway/
│   ├── __init__.py
│   ├── llm_client.py               # Unified LLM client interface
│   ├── provider_manager.py         # Multi-provider support
│   ├── retry_handler.py            # Retry logic with exponential backoff
│   └── circuit_breaker.py          # Circuit breaker for LLM calls
│
├── model_selection/                # NEW: Tiered model selection (Task 13b)
│   ├── __init__.py
│   ├── dynamic_selector.py         # Model selection based on complexity
│   ├── cost_tracker.py             # Cost tracking and budgeting
│   ├── performance_monitor.py      # Model performance tracking
│   └── usage_tracker.py            # Usage patterns and optimization
│
├── batch_processing/               # NEW: Batch processing (Task 13c)
│   ├── __init__.py
│   ├── batch_classifier.py         # Batch activity classification
│   ├── batch_queue.py              # Batching queue management
│   ├── prompt_builder.py           # Batch prompt construction
│   └── batch_metrics.py            # Batch processing effectiveness
│
├── optimization/
│   ├── __init__.py
│   ├── prompt_optimizer.py         # Prompt optimization and caching
│   ├── token_optimizer.py          # Token usage optimization
│   ├── response_cache.py           # Response caching with user context
│   └── compression.py              # Response compression utilities
│
└── models/
    ├── __init__.py
    ├── model_config.py              # Model configuration definitions
    ├── request_models.py            # Request/response models
    ├── cost_models.py               # Cost calculation models
    └── performance_models.py        # Performance tracking models
```

### Interface Modules

#### `/src/interfaces/slack/` - Slack Integration
```
slack/
├── __init__.py
├── adapters/
│   ├── __init__.py
│   ├── unified_adapter.py         # Mode-agnostic adapter
│   ├── socket_mode_handler.py     # Socket Mode
│   ├── http_mode_handler.py       # HTTP Mode
│   └── mode_selector.py           # Mode selection logic
│
├── handlers/
│   ├── __init__.py
│   ├── message_handler.py         # Message events
│   ├── app_mention_handler.py     # Mention events
│   ├── slash_command_handler.py   # Slash commands
│   ├── interaction_handler.py     # Interactive components
│   └── event_router.py            # Event routing
│
├── threading/
│   ├── __init__.py
│   ├── thread_manager.py          # Thread management
│   ├── conversation_tracker.py    # Conversation tracking
│   ├── context_manager.py         # Thread context
│   └── thread_optimizer.py        # Performance optimization
│
├── home_tab/
│   ├── __init__.py
│   ├── home_tab_builder.py        # Home Tab UI
│   ├── cache_manager.py           # Pre-computed cache
│   ├── background_updater.py      # Async updates
│   └── fallback_content.py        # Fallback UI
│
├── formatting/
│   ├── __init__.py
│   ├── block_kit_builder.py       # Block Kit components
│   ├── response_formatter.py      # Response formatting
│   ├── interactive_builder.py     # Interactive elements
│   ├── markdown_formatter.py      # Markdown formatting
│   └── accessibility_helper.py    # Accessibility
│
└── deduplication/
    ├── __init__.py
    ├── deduplicator.py            # Event deduplication
    ├── event_processor.py         # Event processing
    ├── retry_handler.py           # Retry logic
    └── event_cache.py             # Event caching
```

## 📁 Configuration Structure

### `/config` Directory
```
config/
├── environments/
│   ├── development.yaml
│   ├── staging.yaml
│   ├── production.yaml
│   └── testing.yaml
│
├── agents/
│   ├── core/                       # Phase 1: 2 combined agents
│   │   ├── analysis_agent.yaml     # Data Analyst + Competency combined
│   │   └── advisor_agent.yaml      # Career + Synthesis combined
│   └── specialized/                # FUTURE: 4 specialized agents
│       ├── data_analyst.yaml
│       ├── competency_specialist.yaml
│       ├── career_strategist.yaml
│       └── insights_synthesizer.yaml
│
├── tools/
│   ├── classification_tools.yaml
│   ├── assessment_tools.yaml
│   ├── storage_tools.yaml
│   └── reporting_tools.yaml
│
├── workflows/
│   ├── simple_analysis.yaml
│   ├── complex_analysis.yaml
│   ├── batch_processing.yaml
│   └── conversation_flows.yaml
│
├── infrastructure/
│   ├── database.yaml
│   ├── cache.yaml
│   ├── messaging/
│   │   ├── redis_pubsub.yaml       # Phase 1: Simple Redis pub/sub
│   │   └── nats_jetstream.yaml     # FUTURE: Complex event streaming
│   ├── monitoring/
│   │   ├── simple_stack.yaml       # Phase 1: Prometheus + Grafana
│   │   └── full_stack.yaml         # FUTURE: Full observability
│   └── communication/
│       ├── direct_http.yaml        # Phase 1: Direct service calls
│       └── service_mesh.yaml       # FUTURE: Consul Connect
│
└── security/
    ├── vault.yaml
    ├── oauth2.yaml
    ├── rbac.yaml
    └── encryption.yaml
```

## 📁 Test Structure

### `/tests` Directory
```
tests/
├── __init__.py
├── conftest.py                     # Global test configuration
├── pytest.ini                      # Pytest configuration
├── .coveragerc                     # Coverage configuration
│
├── unit/                           # Unit tests (mirrors src/)
│   ├── core/
│   ├── infrastructure/
│   ├── interfaces/
│   ├── services/
│   └── shared/
│
├── integration/                    # Integration tests
│   ├── workflows/
│   ├── slack/
│   ├── database/
│   ├── ai/
│   └── cache/
│
├── e2e/                           # End-to-end tests
│   ├── user_journeys/
│   ├── performance/
│   ├── security/
│   └── business/
│
├── fixtures/                      # Test data
│   ├── competency_data/
│   ├── user_profiles/
│   ├── slack_events/
│   ├── llm_responses/
│   └── vcr_cassettes/
│
├── mocks/                         # Test mocks
│   ├── llm_mocks.py
│   ├── agent_mocks.py
│   ├── temporal_mocks.py
│   ├── slack_mocks.py
│   └── database_mocks.py
│
└── benchmarks/                    # Performance tests
    ├── classification_benchmark.py
    ├── agent_benchmark.py
    ├── database_benchmark.py
    └── cache_benchmark.py
```

## 📝 File Naming Conventions

### Python Files
```python
# Module files
module_name.py                     # Snake_case for all Python files

# Class-containing files
user_repository.py                 # Named after primary class
competency_service.py              # Service suffix for services
activity_model.py                  # Model suffix for models

# Test files
test_module_name.py                # test_ prefix for test files
test_user_service.py
test_integration_workflow.py

# Configuration files
config.yaml                        # YAML for configuration
settings.py                        # Python for dynamic config
```

### Configuration Files
```yaml
# Environment configs
development.yaml
staging.yaml
production.yaml

# Component configs
{component_name}.yaml              # Kebab-case or snake_case
database-config.yaml
cache_config.yaml
```

### Documentation Files
```markdown
README.md                          # Standard readme
ARCHITECTURE.md                    # Architecture documentation
API_REFERENCE.md                   # API documentation
DEPLOYMENT_GUIDE.md                # Deployment guide
```

## 🏗️ Module Organization Patterns

### 1. Domain Module Pattern
```python
# Each domain module follows this structure
domain_module/
├── __init__.py                    # Public API exports
├── models.py                      # Domain models
├── services.py                    # Business logic
├── repositories.py                # Data access
├── exceptions.py                  # Domain exceptions
└── validators.py                  # Domain validation
```

### 2. Service Module Pattern
```python
# Service modules follow this pattern
service_module/
├── __init__.py
├── {service}_service.py           # Main service class
├── {service}_repository.py        # Data access
├── {service}_validator.py         # Input validation
├── {service}_transformer.py       # Data transformation
└── {service}_exceptions.py        # Service exceptions
```

### 3. Interface Module Pattern
```python
# Interface modules follow this pattern
interface_module/
├── __init__.py
├── handlers/                      # Request handlers
├── validators/                    # Input validation
├── formatters/                    # Output formatting
├── middleware/                    # Middleware components
└── exceptions/                    # Interface exceptions
```

## 📦 Package Dependencies

### Module Import Rules
```python
# Core modules can only import from:
- core.*
- shared.*

# Infrastructure modules can import from:
- infrastructure.*
- shared.*

# Interface modules can import from:
- core.*
- infrastructure.*
- services.*
- shared.*

# Services can import from:
- core.*
- infrastructure.*
- services.* (other services)
- shared.*

# Shared modules should not import from other modules
```

## 🔧 Special Directories

### `/data` Directory
```
data/
├── competency_frameworks/
│   ├── standard_matrix.json
│   ├── custom_frameworks/
│   └── level_mappings.json
│
├── prompt_templates/
│   ├── agents/
│   │   ├── data_analyst/
│   │   ├── competency_specialist/
│   │   ├── career_strategist/
│   │   └── insights_synthesizer/
│   └── versions/
│
└── reference_data/
    ├── skills_taxonomy.json
    ├── career_paths.json
    └── learning_resources.json
```

### `/templates` Directory
```
templates/
├── pdf/
│   ├── competency_report/
│   │   ├── template.html
│   │   ├── styles.css
│   │   └── assets/
│   ├── career_plan/
│   └── team_analysis/
│
├── email/
│   ├── notification/
│   ├── report_delivery/
│   └── reminders/
│
└── slack/
    ├── blocks/
    ├── messages/
    └── home_tab/
```

### `/scripts` Directory
```
scripts/
├── setup/
│   ├── install_dependencies.sh
│   ├── setup_database.py
│   ├── configure_vault.py
│   └── initialize_cache.py
│
├── migration/
│   ├── backup_current.py
│   ├── migrate_data.py
│   ├── validate_migration.py
│   └── rollback.py
│
├── maintenance/
│   ├── cleanup_logs.py
│   ├── optimize_database.py
│   ├── refresh_cache.py
│   └── archive_data.py
│
└── development/
    ├── generate_test_data.py
    ├── seed_database.py
    ├── run_local_stack.sh
    └── debug_workflow.py
```

## 🎯 Key Principles

1. **Clear Separation**: Business logic, infrastructure, and interfaces are clearly separated
2. **Domain Focus**: Organize by business domain, not technical concerns
3. **Testability**: Test structure mirrors source structure
4. **Discoverability**: Consistent naming makes files easy to find
5. **Modularity**: Each module is self-contained with clear interfaces
6. **Scalability**: Structure supports growth without reorganization

## 📋 Implementation Checklist

- [ ] Create root directory structure
- [ ] Set up core domain modules
- [ ] Implement infrastructure modules
- [ ] Create interface modules
- [ ] Set up service modules
- [ ] Configure shared utilities
- [ ] Create test structure
- [ ] Set up configuration files
- [ ] Create data directories
- [ ] Set up template directories
- [ ] Create utility scripts
- [ ] Document module interfaces
- [ ] Set up import rules
- [ ] Create __init__.py files with exports
- [ ] Set up development tools