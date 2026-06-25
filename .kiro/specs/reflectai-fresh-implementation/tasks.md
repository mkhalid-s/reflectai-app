# ReflectAI Fresh Implementation Tasks - Restructured

## 📋 CRITICAL SPECIFICATIONS REFERENCE

**REQUIRED READING**: Before starting implementation, review these critical specifications:
- **`database-schema.md`** - Complete database schema, ERD, and table definitions (15 tables)
- **`error-handling-standards.md`** - Error handling patterns, exception hierarchy, and user notifications

## 🔄 SIMPLIFIED ARCHITECTURE UPDATE

### **Key Simplification: Doppler + Consul (No Vault)**
- **Doppler**: Handles ALL secrets and application configuration
- **Consul**: Provides service discovery, mesh (mTLS), and dynamic config
- **Benefits**:
  - 30% reduction in infrastructure complexity
  - Single vendor for all secrets/config management
  - Faster deployment and easier maintenance
  - Built-in CA from Consul Connect for mTLS (no PKI complexity)
  - Sufficient security for most applications

### **🎯 PHASE 1 SIMPLIFICATIONS (65% Complexity Reduction)**

#### **Observability: 5→3 Tools (60% Reduction)**
- **REMOVED**: VictoriaMetrics, Tempo, OpenTelemetry complexity
- **KEPT**: Structlog + Prometheus + Grafana
- **UPGRADE PATH**: Add distributed tracing when >3 services

#### **Agents: 4→2 Agents + No CrewAI (75% Reduction)**
- **COMBINED**: Analysis Agent (Data + Competency), Advisor Agent (Career + Synthesis)
- **REMOVED**: CrewAI orchestration complexity
- **UPGRADE PATH**: Split to 4 specialized agents when >500 requests/day

#### **Event Streaming: NATS→Redis Pub/Sub (80% Reduction)**
- **SIMPLIFIED**: Redis pub/sub for low-volume events
- **REMOVED**: JetStream, complex schema registry, dead letter queues
- **UPGRADE PATH**: Move to NATS when >1000 events/hour

#### **Service Mesh: Deferred (100% Reduction)**
- **STATUS**: Completely deferred until multi-service architecture
- **CURRENT**: Direct HTTP calls with basic health checks
- **UPGRADE PATH**: Add Consul Connect when >4 services

#### **Timeline Impact: 80→45 Days (44% Faster Implementation)**

---

## 🚨 CRITICAL IMPLEMENTATION PRINCIPLES

### **CLEAN SLATE APPROACH**
- **NO CODE COEXISTENCE**: Old and new implementations are completely separate
- **FRESH CODEBASE**: Everything rebuilt from scratch using modern patterns
- **DATA MIGRATION ONLY**: Only migrate data and configuration, never code
- **SEPARATE DEPLOYMENT**: New system deployed independently of old system

### **DEPENDENCY-FIRST ORDERING**
- **DIRECTORY STRUCTURE FIRST**: Establish complete directory structure before any code (see directory-structure-specification.md)
- **SECURITY FOUNDATION**: Security built from Phase 1, not added later
- **INFRASTRUCTURE BEFORE SERVICES**: Core infrastructure before application logic
- **TESTING THROUGHOUT**: Testing framework established early and used continuously
- **OBSERVABILITY FROM START**: Monitoring and logging from foundation level

### **DIRECTORY STRUCTURE COMPLIANCE**
- **SPECIFICATION**: All development MUST follow .kiro/specs/reflectai-fresh-implementation/directory-structure-specification.md
- **VALIDATION**: Use directory-validation-checklist.md for simple verification
- **NAMING CONVENTIONS**: Enforce snake_case for Python, kebab-case for configs
- **MODULE BOUNDARIES**: Strict import rules to prevent circular dependencies

---

## Phase 1: Security-First Foundation (Days 1-5)

### 0. Initialize project directory structure
- **PREREQUISITE**: Must be completed before any other development tasks
- **REFERENCE**: Follow .kiro/specs/reflectai-fresh-implementation/directory-structure-specification.md exactly
- Create complete directory tree with all folders as specified
- Set up empty __init__.py files in all Python packages
- Create placeholder README.md in each major directory explaining its purpose
- Set up .gitignore with proper Python, cache, and secret exclusions
- Initialize Poetry project with pyproject.toml
- Create initial module import rules documentation
- **VALIDATION**: Use simple checklist to verify key directories exist (defer complex validation to Phase 2)

### 1. Clean implementation structure and security foundation
- Move current implementation to .backup/[timestamp] (no copying, clean separation)
- **DIRECTORY STRUCTURE**: Verify Task 0 completion with validation checklist
- **ERROR HANDLING FOUNDATION**: Implement error handling standards per `error-handling-standards.md`
- Build entirely new codebase in fresh directory structure following domain-driven design
- **SECURITY FIRST**: Set up Doppler for unified secrets and configuration management
- **OAUTH2 FOUNDATION**: Establish OAuth2/OIDC authentication framework
- Set up core, infrastructure, interfaces, services, and shared modules with consistent error handling
- Create comprehensive test directory structure mirroring source organization

### 2. Unified logging and observability foundation

#### **2a. Structlog Configuration and Setup**
- **REQUIRES**: Task 1 (directory structure) complete
- **Core Structlog Configuration**:
  - Install and configure structlog with JSON formatting for structured, searchable logs
  - Set up log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL with environment-based defaults
  - Configure processors: timestamp (ISO format), log level, logger name, stack traces, exception handling
  - Implement context injection for user_id, team_id, request_id, and agent context
- **Log Output Configuration**:
  - Development: Human-readable console output with colors and formatting
  - Production: JSON structured logs for log aggregation and search
  - Configure log rotation with 100MB file size limit and 30-day retention

#### **2b. Correlation ID Generation and Propagation**
- **Correlation ID Strategy** (Requirement 9.2):
  - Generate UUID4 correlation IDs for each user request from Slack
  - Propagate correlation IDs through all system components using Structlog context
  - Include correlation IDs in all log entries, HTTP headers, and inter-service calls
  - Map Slack thread_ts to correlation IDs for conversation continuity
- **Context Management**:
  - Use contextvars for thread-safe correlation ID storage across async operations
  - Implement middleware for FastAPI to automatically inject/extract correlation IDs
  - Create utility functions for manual correlation ID binding in agent workflows

#### **2c. Structured Logging Schema and Standards**
- **Log Schema Definition** (Requirement 38.8):
  - Standard fields: timestamp, level, logger, correlation_id, user_id, team_id, message
  - Agent fields: agent_type, model_used, tokens_consumed, execution_time, cost_usd
  - Business fields: activity_type, competency_scores, analysis_confidence, workflow_stage
  - Error fields: exception_type, stack_trace, error_context, recovery_action
- **Audit Trail Implementation**:
  - Log all user actions: message_received, analysis_requested, report_generated
  - Log system changes: configuration_updated, model_switched, competency_calculated
  - Include before/after states for data modifications with change attribution
  - Implement separate audit logger with 7-year retention for compliance

#### **2d. Prometheus Metrics Foundation**
- **Basic Metrics Infrastructure** (Requirement 9.4):
  - Set up prometheus_client with custom registry for application metrics
  - Configure metrics export endpoint (/metrics) with authentication
  - Define core application metrics with proper labels and help text
  - Implement metrics collection points in logging middleware and utility functions
- **Essential Metrics Definition**:
  - Response times: request_duration_seconds (histogram with user_id, endpoint labels)
  - Error rates: request_errors_total (counter with status_code, endpoint labels)
  - Concurrent requests: active_requests (gauge with endpoint label)
  - LLM costs: llm_cost_usd_total (counter with model, agent_type labels)
  - Business metrics: competency_calculations_total, reports_generated_total

#### **2e. Integration Patterns and Usage Standards**
- **Logger Factory Pattern**:
  - Create get_logger() factory function that returns configured structlog logger
  - Automatic context injection for user_id, correlation_id from request context
  - Standardized logger naming convention: module_name.component_name
- **Usage Standards for All Subsequent Tasks**:
  - Every module MUST use get_logger(__name__) for consistent logging
  - All async functions MUST preserve correlation context across await boundaries
  - All error handling MUST log exceptions with structured context
  - All business operations MUST log start/completion with execution metrics
- **Performance and Reliability**:
  - Implement async logging to prevent I/O blocking on log writes
  - Set up log buffering with 1-second flush interval for performance
  - Configure log level filtering to reduce noise in production
  - Implement log sampling for high-frequency debug logs (1% sampling rate)

### 3. Simplified configuration and secrets management

#### **3a. Doppler Secrets Management (Primary)**
- **REQUIRES**: Task 2 (logging foundation) complete
- **Doppler Project Setup**:
  - Create Doppler projects: `reflectai-dev`, `reflectai-staging`, `reflectai-prod`
  - Configure environment-specific secret isolation with proper access controls
  - Set up service tokens for automated deployment access
  - Implement branch-based configuration for feature development workflows
- **Secret Categories and Organization**:
  - Database secrets: PostgreSQL connection strings, Redis credentials
  - API secrets: Slack app tokens, signing secrets, LLM provider API keys
  - Infrastructure secrets: Deployment keys, monitoring credentials
  - Application secrets: JWT signing keys, encryption keys, webhook secrets
- **Doppler Integration Implementation**:
  - Install Doppler CLI and Python SDK for application integration
  - Create Pydantic settings classes that automatically load from Doppler
  - Implement secret validation on application startup with fail-fast behavior
  - Set up secret change monitoring and audit logging through Structlog

#### **3b. Consul Configuration Management (Dynamic Config)**
- **Consul Setup for Phase 1**:
  - Deploy single Consul server (3-node cluster deferred until production scale)
  - Configure Consul KV store for non-sensitive dynamic configuration
  - Set up basic service discovery for future multi-service expansion
  - Implement health check definitions for application monitoring
- **Dynamic Configuration Categories**:
  - Feature flags: Enable/disable features without deployment
  - LLM model configurations: Model selection, prompt templates, cost limits
  - Business logic parameters: Competency weights, scoring thresholds
  - Cache configurations: TTL values, eviction policies, warming strategies
- **Hot-Reload Implementation**:
  - Create configuration watcher service that monitors Consul KV changes
  - Implement configuration reload without application restart
  - Add configuration change notifications via Structlog for audit trails
  - Set up configuration validation before applying changes

#### **3c. Environment and Deployment Configuration**
- **Environment-Specific Settings**:
  - Development: SQLite fallback, debug logging, relaxed validation
  - Staging: Production-like PostgreSQL, verbose logging, strict validation
  - Production: Optimized settings, error-only logging, maximum security
- **Configuration Loading Strategy**:
  - Precedence order: Environment variables → Consul KV → Doppler secrets
  - Implement configuration caching to reduce external calls during startup
  - Create configuration health checks to validate all required settings
  - Set up configuration backup and restore procedures for disaster recovery

#### **3d. Security and Compliance Implementation**
- **Secret Security Best Practices**:
  - Enable Doppler secret rotation notifications for manual key updates
  - Implement secret access logging for all Doppler API calls
  - Set up secret usage monitoring and alerting for unusual access patterns
  - Create secret backup strategy using Doppler's export capabilities
- **Configuration Audit and Monitoring**:
  - Log all configuration changes through Structlog with user attribution
  - Monitor configuration drift and unauthorized changes
  - Set up alerts for configuration load failures or validation errors
  - Implement configuration rollback capabilities for emergency recovery
- **Compliance and Documentation**:
  - Document all configuration parameters with descriptions and valid ranges
  - Create configuration change approval workflow for production
  - Maintain configuration schema documentation with Pydantic models
  - Set up regular configuration security audits and access reviews

#### **3e. Application Integration Patterns**
- **Configuration Client Implementation**:
  - Create unified ConfigManager class that abstracts Doppler and Consul access
  - Implement async configuration loading with proper error handling
  - Add configuration caching layer to improve application startup performance
  - Create configuration mock utilities for testing environments
- **Usage Standards for Development Teams**:
  - All configuration MUST use ConfigManager, never direct environment access
  - Secret values MUST never be logged, printed, or exposed in error messages
  - Configuration changes MUST be validated before application startup
  - New configuration parameters MUST include documentation and validation rules
- **Monitoring and Observability**:
  - Track configuration load times and success rates via Prometheus metrics
  - Monitor Doppler API usage and rate limiting to prevent service disruption
  - Set up configuration health dashboards in Grafana
  - Create alerts for configuration service outages or authentication failures

### 4. Development tooling and quality foundation
- Set up Poetry for dependency management and virtual environments
- Replace Flake8, Black, isort with Ruff for 10-100x faster linting
- Configure strict MyPy type checking with comprehensive type annotations
- Set up pre-commit hooks with Ruff, MyPy, Bandit, and Safety
- Implement automated security scanning for dependencies
- Configure Tilt for sub-second rebuilds during development

### 5. Testing framework foundation (Expanded)
- **5a. Core Testing Setup**:
  - Configure pytest with async support and fixtures
  - Set up testcontainers for PostgreSQL, Redis, NATS
  - Create test environment configuration management
  - Implement test isolation and cleanup procedures
  - Configure code coverage targets (>90% for critical paths)
- **5b. Test Data Factories**:
  - UserFactory: Generate users with varied profiles and levels
  - ActivityFactory: Create activities with different classifications
  - CompetencyFactory: Build competency scores with evidence
  - WorkflowFactory: Generate workflow states and transitions
  - EventFactory: Create event streams for testing
- **5c. Mock Infrastructure**:
  - LLM mocks: Predefined responses per prompt pattern
  - Slack API mocks: Event generation and response simulation
  - Temporal workflow mocks: State machine simulation
  - External service mocks: OAuth, email, webhooks
- **5d. Golden Datasets**:
  - Classification dataset: 1000 pre-classified activities
  - Competency dataset: Complete competency progression scenarios
  - Conversation dataset: Multi-turn conversation examples
  - Error dataset: Known error scenarios and edge cases
- **5e. Testing Standards**:
  - Unit tests: <100ms execution time
  - Integration tests: <1s execution time
  - E2E tests: <10s execution time
  - All async code must use pytest-asyncio
  - All external calls must be mocked in unit tests

---

## Phase 2: Core Infrastructure Layer (Days 6-12)

### 6. Database infrastructure setup (Expanded)
- **REQUIRES**: Phase 1 (security, logging, config) complete
- **SPECIFICATION**: See `database-schema.md` for complete schema definitions, ERD, and table relationships
- **6a. PostgreSQL & TimescaleDB Setup**:
  - Deploy PostgreSQL 15+ with TimescaleDB extension
  - Configure connection parameters from Doppler secrets (Task 3a)
  - Set up continuous aggregates for metrics (1min, 5min, 1hr, 1day)
  - Implement hypertable partitioning by time (7-day chunks)
  - Create data retention policies (raw: 30d, 1min: 90d, 1hr: 1yr)
- **6b. Database Schema Implementation (Per database-schema.md)**:
  - **Core Tables**: users, activities (hypertable), competencies, workflows, reports
  - **Time-Series Tables**: competency_history (hypertable), events (hypertable)
  - **Configuration Tables**: user_preferences, user_sessions
  - **Audit Tables**: audit_events (separate database for 7-year retention)
  - **Complete JSONB Structures**: profile_data, classification, metrics, evidence, notification_preferences
- **6c. Index Strategy**:
  - B-tree indexes on foreign keys and timestamps
  - GIN indexes on JSONB columns for fast queries
  - BRIN indexes on time-series data for space efficiency
  - Partial indexes for common query patterns
  - Index usage monitoring and optimization
- **6d. PgBouncer Configuration**:
  - Deploy PgBouncer in transaction pooling mode
  - Configure pool sizes: default=25, reserve=5, max=1000
  - Set up connection limits per user/database
  - Implement health checks and automatic recovery
  - Create monitoring for pool saturation
- **6e. Migration System**:
  - Set up Alembic with async support per `database-schema.md` migration strategy
  - Create baseline migrations for all 15 tables from schema specification
  - Implement migration testing in CI/CD
  - Set up rollback procedures with data preservation
  - Create migration performance monitoring
- **ERROR HANDLING**: Use database error patterns from `error-handling-standards.md`
- **USE STRUCTLOG**: All database operations use established logging with query timing

### 7. Cache infrastructure setup (Expanded)
- **REQUIRES**: Task 6 (database) complete
- **7a. Redis Stack Deployment**:
  - Deploy Redis Stack with modules: JSON, Search, TimeSeries, Graph
  - Configure persistence: RDB snapshots (hourly) + AOF (everysec)
  - Set up memory limits and eviction policy (allkeys-lru)
  - Implement Redis Sentinel for HA (3 nodes)
  - Configure TLS with certificates from Consul Connect CA
- **7b. Cache Manager Implementation**:
  - Create cache key namespaces:
    - user:{user_id} - User profiles and preferences
    - session:{session_id} - Conversation sessions
    - activity:{activity_id} - Activity cache
    - home_tab:{team_id}:{user_id} - Home tab data
    - llm:{prompt_hash} - LLM response cache
  - Implement cache strategies:
    - Write-through for user data
    - Write-behind for analytics
    - Refresh-ahead for frequently accessed
  - Set up TTL policies:
    - Sessions: 24 hours (sliding window)
    - User data: 1 hour
    - LLM responses: 30 minutes
    - Home tab: 1 hour
- **7c. Session Management**:
  - Create session lifecycle:
    - Creation: On first user interaction
    - Updates: On each message (sliding TTL)
    - Expiry: After 24 hours of inactivity
    - Cleanup: Background job every hour
  - Store session data:
    - conversation_history (last 20 messages)
    - current_context (workflow state)
    - user_preferences (cached)
    - thread_mapping (Slack thread IDs)
  - Implement session recovery:
    - Persist critical state to database
    - Rebuild from event history
    - Graceful degradation on cache miss
- **7d. Cache Warming & Optimization**:
  - Implement cache warming on startup
  - Create predictive cache loading
  - Set up cache performance monitoring
  - Build cache analysis dashboards
  - Implement cache size management
- **7e. User-Context-Aware Caching Strategy (CRITICAL)**:
  - **CRITICAL FINDING**: LLM responses vary by user context - naive caching causes incorrect classifications
  - Implement cache safety matrix with user-dependent operations identified
  - Create UserAwareCacheManager with user context in cache keys
  - Never cache classify_text without user level/title in key
  - Safe content-only caching for summarize_text operations
  - Never cache personal competency calculations - always compute fresh
  - Aggressive caching for static lookups (competency matrix, requirements)
  - **INTEGRATION**: Used by all LLM operations to prevent classification errors
- **USE STRUCTLOG**: All cache operations with hit/miss metrics

### 8. Simple event streaming infrastructure (Simplified)

#### **8a. Redis Pub/Sub Setup and Configuration**
- **REQUIRES**: Tasks 6, 7 (database, cache) complete
- **Redis Pub/Sub Infrastructure** (Requirement 14.1):
  - Use existing Redis Stack from Task 7 for lightweight event streaming (<1000 events/hour)
  - Configure Redis pub/sub with connection pooling and automatic reconnection
  - Set up separate Redis database (db=1) for pub/sub to avoid cache interference
  - Implement pub/sub connection health monitoring with automatic failover
- **Event Channel Architecture**:
  - Core channels: `user.activity.completed`, `user.analysis.completed`, `user.report.generated`
  - Cache channels: `cache.user.updated`, `cache.home_tab.refresh`
  - System channels: `slack.event.received`, `workflow.completed`, `error.occurred`
  - Use hierarchical naming: `{domain}.{entity}.{action}` for consistent routing

#### **8b. Event Schema and Validation**
- **Event Schema Definition** (Requirements 14.2, 21.3):
  - Base Event schema: event_id (UUID), timestamp, correlation_id, event_type, payload
  - UserActivityEvent: user_id, team_id, activity_type, activity_data, analysis_results
  - CacheUpdateEvent: cache_key, operation_type, user_id, data_changes
  - SlackEvent: slack_event_id, user_id, channel_id, message_text, event_metadata
  - WorkflowEvent: workflow_id, agent_type, execution_status, results, cost_data
- **Pydantic Model Implementation**:
  - Create strict Pydantic models with field validation and type checking
  - Implement event versioning with backward compatibility (event_version field)
  - Add event payload size validation (<10KB per event for Redis pub/sub efficiency)
  - Include automatic timestamp and correlation_id generation from context

#### **8c. Event Publishing and Correlation**
- **Event Publishing Layer**:
  - Implement EventPublisher class with async Redis pub/sub client
  - Auto-inject correlation_id from Structlog context (Task 2) into all events
  - Include user context (user_id, team_id) extraction from Slack events
  - Implement event publishing with JSON serialization and schema validation
- **Publishing Metrics and Monitoring**:
  - Track publishing metrics: events_published_total, publishing_errors_total, channel_usage
  - Monitor event payload sizes and publishing latency
  - Log all event publishing with structured logging (Task 2 integration)
  - Implement publishing rate limiting (100 events/minute per user) to prevent abuse

#### **8d. Event Subscription and Processing**
- **Subscription Management**:
  - Create EventSubscriber base class with async context manager for connection lifecycle
  - Implement subscription registration with channel pattern matching
  - Support multiple subscribers per channel with load balancing across instances
  - Handle subscription failures with automatic re-subscription and exponential backoff
- **Error Handling and Retry Logic** (Requirement 14.4):
  - Implement exponential backoff retry with 3 attempts max for processing failures
  - Log subscription errors with full context and correlation tracking
  - Dead event logging (no dead letter queues initially) with manual replay capability
  - Circuit breaker pattern deferred until >10% failure rate observed

#### **8e. Essential Deduplication Implementation**
- **Deduplication Strategy** (Requirements 14.2, 14.3):
  - Implement composite key deduplication: `dedup:{event_id}:{timestamp}:{user_id}`
  - Use 5-minute TTL window for deduplication keys in Redis
  - Check deduplication before event processing, skip if duplicate detected
  - Track deduplication metrics: duplicate_events_total, deduplication_rate
- **Slack Event Deduplication**:
  - Special handling for Slack event deduplication using event_id + event_time
  - Handle Slack retry mechanisms by detecting duplicate event signatures
  - Implement user-specific deduplication to prevent cross-user interference
  - Log duplicate detection with structured logging for debugging

#### **8f. Event Processing Integration Points**
- **Home Tab Cache Updates** (Requirement 21.1, 21.3):
  - Subscribe to user.activity.completed → trigger Home Tab cache refresh
  - Subscribe to user.analysis.completed → update activity counters and last analysis date
  - Subscribe to user.report.generated → update report count and last report date
  - Subscribe to user.profile.updated → refresh cached user profile data
- **Monitoring and Health Checks** (Requirement 14.5):
  - Track basic event processing metrics: processing_time, success_rate, error_rate
  - Monitor deduplication effectiveness and false positive rates
  - Implement event processing health checks with Redis connectivity validation
  - Set up alerting for event processing failures or high error rates
- **Integration with Logging Foundation**:
  - All event operations use get_logger() from Task 2 for consistent structured logging
  - Include correlation_id in all event processing logs for request tracing
  - Log event lifecycle: received → validated → processed → completed/failed
  - Implement event audit trail for troubleshooting and system observability

### 9. Simplified observability stack (Right-sized for Phase 1)

#### **9a. Prometheus Setup and Configuration**
- **REQUIRES**: Task 2 (logging foundation) complete
- **Prometheus Deployment** (Requirements 9.2, 36.4):
  - Deploy Prometheus server with 30-day retention for Phase 1 monitoring
  - Configure scrape targets: FastAPI application (/metrics endpoint, 15s interval)
  - Set up service discovery for dynamic target discovery as services scale
  - Implement Prometheus configuration hot-reload for configuration updates
- **Recording Rules and Aggregation**:
  - Create recording rules for frequently queried metrics (error rates, P95/P99 latencies)
  - Define SLI recording rules: availability, latency, throughput, quality
  - Implement rate() and increase() calculations for counter metrics
  - Set up histogram_quantile() rules for latency percentiles

#### **9b. Essential Metrics Collection and Definition**
- **System Performance Metrics** (Requirements 36.3, 32.3):
  - HTTP metrics: `reflectai_request_duration_seconds` (histogram with method, endpoint, status labels)
  - Request counts: `reflectai_requests_total` (counter with endpoint, status_code labels)
  - Concurrent requests: `reflectai_active_requests` (gauge with endpoint label)
  - Database metrics: `reflectai_db_query_duration_seconds`, `reflectai_db_connections_active`
  - Cache metrics: `reflectai_cache_hit_rate`, `reflectai_cache_operations_total`
- **Business and Agent Metrics** (Requirements 32.1, 32.7, 3.7):
  - Agent performance: `reflectai_agent_execution_duration_seconds` (histogram with agent_type label)
  - Agent success: `reflectai_agent_requests_total` (counter with agent_type, status labels)
  - LLM costs: `reflectai_llm_cost_usd_total` (counter with model, agent_type labels)
  - LLM tokens: `reflectai_llm_tokens_consumed_total` (counter with model, agent_type labels)
  - User activity: `reflectai_user_activities_processed_total`, `reflectai_active_users_total`
- **Event Processing Metrics** (Requirement 14.5):
  - Event processing: `reflectai_events_processed_total` (counter with event_type, status labels)
  - Deduplication: `reflectai_events_deduplicated_total`, `reflectai_deduplication_rate`
  - Event latency: `reflectai_event_processing_duration_seconds`

#### **9c. SLI/SLO Definition and Monitoring**
- **Service Level Indicators (Requirements 32.5, 32.6)**:
  - Availability SLI: `(sum(rate(reflectai_requests_total{status!~"5.."}[5m])) / sum(rate(reflectai_requests_total[5m]))) * 100`
  - Latency SLI P99: `histogram_quantile(0.99, rate(reflectai_request_duration_seconds_bucket[5m]))`
  - Agent success rate: `(sum(rate(reflectai_agent_requests_total{status="success"}[5m])) / sum(rate(reflectai_agent_requests_total[5m]))) * 100`
- **Service Level Objectives**:
  - Availability: >99.5% uptime (requirement 29.10)
  - API latency P99: <500ms (requirement 40.1)
  - Home Tab load time: <200ms (requirement 17.2)
  - Agent success rate: >95% (requirement 32.1)
  - Error rate: <5% for critical operations (requirement 32.6)

#### **9d. Grafana Dashboard Implementation**
- **System Health Dashboard** (Requirements 36.5, 32.7):
  - Overview panel: System status, uptime, active users, error rate summary
  - Performance panels: Request latency (P50, P95, P99), throughput, concurrent requests
  - Infrastructure panels: CPU/memory usage, database connections, Redis connectivity
  - Error tracking: Error rate trends, error distribution by endpoint, recent errors
- **Agent Performance Dashboard**:
  - Agent execution metrics: Response times by agent type, success rates, concurrent executions
  - LLM usage analysis: Token consumption, cost tracking, model performance comparison
  - Workflow monitoring: End-to-end processing duration, workflow success rates
  - Cost optimization: Cost per interaction, daily spend tracking, budget alerts
- **Business Metrics Dashboard** (Requirement 32.8):
  - User engagement: Active users, activity processing volume, feature adoption
  - Competency analysis: Analysis completion rates, report generation metrics
  - Home Tab performance: Load times, cache hit rates, user interaction patterns

#### **9e. Alerting Configuration and Rules**
- **Critical Alerts** (Requirement 32.6):
  - System down: `up{job="reflectai"} == 0` → Immediate Slack notification
  - High error rate: `rate(reflectai_requests_total{status=~"5.."}[5m]) / rate(reflectai_requests_total[5m]) > 0.05` → 2min evaluation
  - Database connectivity: `reflectai_db_connections_active == 0` → 1min evaluation
  - Agent failures: `rate(reflectai_agent_requests_total{status="error"}[10m]) / rate(reflectai_agent_requests_total[10m]) > 0.1` → 5min evaluation
- **Performance Alerts**:
  - High latency: `histogram_quantile(0.99, rate(reflectai_request_duration_seconds_bucket[5m])) > 0.5` → 10min evaluation
  - Home Tab slow loading: `histogram_quantile(0.95, rate(reflectai_home_tab_load_duration_seconds_bucket[5m])) > 0.2` → 5min evaluation
  - High LLM costs: `increase(reflectai_llm_cost_usd_total[1d]) > daily_budget_threshold` → Daily evaluation
- **Alert Routing and Notification**:
  - Critical alerts → Slack channel with @here mention
  - Performance alerts → Slack channel without mention
  - Cost alerts → Email to admin + Slack notification
  - Include runbook links and troubleshooting steps in alert messages

#### **9f. Health Checks and Monitoring Integration**
- **Application Health Checks** (Requirements 16.7, 32.5):
  - `/health` endpoint: Basic service health (HTTP 200/503)
  - `/health/detailed` endpoint: Database, Redis, LLM API connectivity checks
  - `/metrics` endpoint: Prometheus metrics exposure with authentication
  - Include dependency health: Database queries, Redis connectivity, LLM API availability
- **Integration with Event System**:
  - Monitor event processing health from Task 8 event streaming
  - Track Home Tab cache update effectiveness
  - Alert on event processing delays or failures
  - Monitor deduplication effectiveness and false positive rates
- **Performance Baseline and Trend Analysis** (Requirement 32.9):
  - Establish baseline metrics during first 30 days of operation
  - Implement trend analysis for capacity planning and scaling decisions
  - Create automated reports for weekly performance review
  - Track progress toward upgrade triggers (>500 requests/day for agent scaling)
  - Medium: Cost spike >2x baseline (Slack)
  - **SIMPLIFIED**: Basic alerting via Grafana (PagerDuty when business grows)
  - Alert fatigue prevention: Basic deduplication
- **9e. Simple Correlation Tracing (No Distributed Tracing Initially)**:
  - Use Structlog correlation IDs for request tracing
  - Implement request ID propagation across service calls
  - **DEFERRED**: Full distributed tracing with Tempo (add when >3 services)
  - **DEFERRED**: Complex trace analysis (add when debugging needs justify)
  - Basic request flow logging with correlation IDs
- **9f. Direct Prometheus Integration (No OpenTelemetry Complexity)**:
  - Use prometheus_client directly in FastAPI application
  - Implement custom metrics collection without OTLP overhead
  - Create business metrics: llm_request_duration, activity_classifications, cache_hits
  - Integrate with Structlog for log/metric correlation using correlation IDs
  - **SIMPLIFIED**: No OTLP collectors, auto-instrumentation complexity
  - **UPGRADE PATH**: Add OpenTelemetry when observability requirements expand
- **EXTEND STRUCTLOG**: All metrics include correlation IDs from logging foundation

### 10. Infrastructure testing and validation
- **REQUIRES**: Tasks 6-9 (all infrastructure) complete
- Create integration tests for database, cache, and NATS connectivity
- Implement infrastructure health check endpoints
- Set up infrastructure performance testing
- Create infrastructure monitoring and alerting validation
- Test disaster recovery and backup procedures
- Validate security configuration and access controls

---

## Phase 3: AI/LLM Foundation (Days 13-18)

### 11. LLM gateway and provider integration (Expanded)
- **REQUIRES**: Phase 2 (infrastructure) complete
- **ERROR HANDLING**: Implement LLM provider error handling and circuit breaker patterns per `error-handling-standards.md`
- **11a. LiteLLM Gateway Setup**:
  - Configure provider credentials from Vault
  - Set up provider priority: OpenAI → Anthropic → Bedrock
  - Implement provider health checks and auto-failover with circuit breaker pattern
  - Configure model aliases for easy switching
  - Set up request queuing and batching
- **11b. Guardrails AI Configuration**:
  - Define output schemas per agent type:
    - Data Analyst: {classification, confidence, evidence}
    - Competency: {score, gaps, recommendations}
    - Career: {opportunities, development_plan, timeline}
    - Synthesizer: {insights, summary, actions}
  - Create validation rules:
    - No PII in responses
    - Confidence scores 0.0-1.0
    - Required fields present
    - JSON format validity
  - Implement failure handling:
    - Retry with clarified prompt (max 2)
    - Fallback to simpler model
    - Return structured error
- **11c. LLMLingua Optimization**:
  - Configure compression levels by prompt type:
    - System prompts: 80% compression
    - User context: 60% compression
    - Examples: 70% compression
  - Set up semantic preservation thresholds
  - Implement compression effectiveness monitoring
  - Create compression bypass for critical prompts
- **11d. Response Caching Layer**:
  - Implement semantic similarity matching (threshold: 0.95)
  - Cache by prompt hash + model + temperature
  - TTL configuration: Intent=30min, Analysis=1hr, Help=24hr
  - Cache invalidation on user data changes
  - Monitor cache effectiveness (target: 30% hit rate)
- **USE STRUCTLOG**: All LLM operations logged with tokens, cost, latency

### 12. Simple prompt management for agents and tools
- **REQUIRES**: Task 11 (LLM gateway) complete
- **File-Based Prompt Templates**:
  - Store prompts as text files in `prompts/agents/` and `prompts/tools/` directories
  - Support environment-specific prompt variations (dev/staging/prod)
  - Use Jinja2 templating for dynamic variable injection (user_name, context, etc.)
  - Implement prompt validation on startup to ensure all required prompts exist
- **Prompt Organization**:
  - Agent prompts: `analysis_agent.txt`, `advisor_agent.txt`
  - Tool prompts: `activity_classifier.txt`, `competency_assessor.txt`, `recommendation_engine.txt`
  - System prompts: `greeting.txt`, `help.txt`, `error_handling.txt`
- **Prompt Loading and Management**:
  - Load all prompts at application startup with caching in memory
  - Support prompt reloading via configuration update (Consul integration from Task 3)
  - Add prompt usage tracking for optimization insights
  - Create prompt testing utilities for validation against golden datasets

### 13. LLM cost optimization and monitoring (Expanded)
- **REQUIRES**: Tasks 11, 12 (LLM gateway, prompts) complete
- **13a. Cost Tracking Infrastructure**:
  - Implement per-request cost calculation based on tokens and model
  - Create cost attribution by user, department, and use case
  - Set up real-time cost aggregation (hourly, daily, monthly)
  - Build cost prediction based on usage patterns
  - Implement cost anomaly detection (>2x standard deviation)
- **13b. Model Selection & Routing Strategy (CRITICAL)**:
  - Implement tiered model selection for 60-75% cost reduction:
    - Tier 1 (Data Analyst): gpt-4o-mini ($0.15/1k tokens, <3s)
    - Tier 2 (Competency Specialist): claude-3-5-haiku ($0.25/1k tokens, <5s)
    - Tier 3 (Career Strategist): gpt-4o ($2.50/1k tokens, <8s)
    - Tier 4 (Insight Synthesizer): gpt-4o with o1-mini escalation (complexity >0.8)
  - Create DynamicModelSelector with complexity-based routing
  - Implement automatic fallback on provider failures
  - Set up A/B testing for model selection effectiveness
  - Track escalation rates (target: <5% to Tier 4)
- **13c. Token Optimization Strategies**:
  - Implement prompt caching for repeated queries (30min TTL)
  - Create semantic deduplication for similar requests
  - Set up response caching by intent category
  - **Batch Processing Implementation**: Process multiple activities in single LLM call
    - Same-user batching with 100ms timeout, max 10 items
    - 30-50% reduction in API calls during peak hours
    - Fallback to individual processing on batch failures
  - Build token usage prediction and pre-optimization
- **13d. Budget Management**:
  - Set up department/user quotas ($X per month)
  - Implement soft limits with warnings at 80%
  - Create hard limits with graceful degradation
  - Build cost allocation and chargeback reports
  - Set up cost optimization recommendations
- **TARGET**: Achieve 60-75% cost reduction vs baseline through optimization

### 14. Practical LLM testing with golden datasets
- **REQUIRES**: Task 5 (testing foundation) and Tasks 11-13 (LLM stack) complete
- **Golden Dataset Testing**:
  - Create test datasets with input/expected output pairs for each agent and tool
  - Activity classification tests: 100 sample activities with expected categories
  - Competency assessment tests: 50 sample activities with expected competency mappings
  - Career advice tests: 25 scenarios with expected recommendation types
- **Response Validation Methods**:
  - Exact match testing for structured outputs (JSON, classifications)
  - Keyword presence testing for text responses (check for required concepts)
  - Confidence threshold testing (ensure responses meet minimum confidence levels)
  - Format validation (ensure JSON responses are valid, required fields present)
- **LLM Testing Utilities**:
  - Mock LLM responses using predefined response maps for unit tests
  - Test prompt construction with variable substitution validation
  - Token counting tests to ensure prompts stay within model limits
  - Cost calculation validation for different model/token combinations

---

## Phase 4: Multi-Agent System Core (Days 19-26)

### 15. Base agent framework
- **REQUIRES**: Phase 3 (AI/LLM foundation) complete
- Create BaseAgent abstract class with comprehensive common functionality
- Implement agent configuration models with Pydantic V2 validation
- Set up agent performance metrics, monitoring, and health checks
- Create agent resource management with concurrent execution limits
- Implement agent lifecycle management (initialization, execution, cleanup)
- **USE STRUCTLOG**: All agent operations use established logging foundation

### 16. Temporal workflow orchestration and batch processing (Expanded - Gap #10)
- **REQUIRES**: Task 15 (base framework) complete
- **16a. Temporal.io Workflow Engine Configuration**:
  - **Temporal Server Deployment**:
    - Deploy Temporal server with PostgreSQL backend (production-grade persistence)
    - Configure High Availability (HA) cluster with 3 frontend instances
    - Set up workflow namespaces with isolation:
      ```yaml
      namespaces:
        - name: reflectai-dev
          retention: 3 days
          archival_enabled: false
        - name: reflectai-staging  
          retention: 7 days
          archival_enabled: true
        - name: reflectai-prod
          retention: 30 days
          archival_enabled: true
          archival_uri: "s3://reflectai-workflow-archive"
      ```
  - **Worker Pool Configuration**:
    - Default workflow workers: 10 concurrent workflows (CPU-bound operations)
    - Agent activity workers: Analysis Agent (8 instances), Advisor Agent (5 instances)
    - Batch processing workers: 15 instances for bulk operations
    - Cron workflow workers: 3 instances for scheduled operations
    - Worker resource limits: 2 CPU cores, 4GB RAM per worker
  - **Advanced Workflow Configuration**:
    - Implement workflow search attributes for operational querying:
      ```python
      search_attributes = {
          "UserId": "keyword",
          "WorkflowType": "keyword", 
          "Priority": "int",
          "BatchId": "keyword",
          "ConversationId": "keyword"
      }
      ```
    - Configure workflow retention policies (completed: 7 days, failed: 30 days, terminated: 1 day)
    - Set up workflow archival to S3 for compliance and audit trails
- **16b. Core Workflow Definitions with Batch Processing**:
  - **Sequential Analysis Workflow**:
    ```python
    @workflow.defn
    class SequentialAnalysisWorkflow:
        @workflow.run
        async def run(self, request: AnalysisRequest) -> AnalysisResult:
            # Activity 1: Analysis Agent processing
            analysis_result = await workflow.execute_activity(
                analyze_activity,
                request,
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(seconds=60),
                    maximum_attempts=3
                )
            )
            
            # Activity 2: Advisor Agent processing  
            advice_result = await workflow.execute_activity(
                provide_advice,
                analysis_result,
                start_to_close_timeout=timedelta(minutes=3),
                retry_policy=RetryPolicy(maximum_attempts=3)
            )
            
            return AnalysisResult(analysis=analysis_result, advice=advice_result)
    ```
  - **Batch Processing Workflow**:
    ```python
    @workflow.defn  
    class BatchAnalysisWorkflow:
        @workflow.run
        async def run(self, batch_request: BatchRequest) -> BatchResult:
            batch_id = workflow.uuid4()
            
            # Process activities in batches of 5 for optimal LLM usage
            batch_size = 5
            results = []
            
            for i in range(0, len(batch_request.activities), batch_size):
                batch = batch_request.activities[i:i + batch_size]
                
                # Parallel processing within batch
                batch_tasks = []
                for activity in batch:
                    task = workflow.execute_activity(
                        batch_analyze_activity,
                        BatchItem(activity=activity, batch_id=batch_id),
                        start_to_close_timeout=timedelta(minutes=5)
                    )
                    batch_tasks.append(task)
                
                # Wait for batch completion
                batch_results = await asyncio.gather(*batch_tasks)
                results.extend(batch_results)
                
                # Progress tracking
                await workflow.execute_activity(
                    update_batch_progress,
                    BatchProgress(
                        batch_id=batch_id,
                        completed=len(results),
                        total=len(batch_request.activities)
                    )
                )
            
            return BatchResult(batch_id=batch_id, results=results)
    ```
  - **Conversation Context Workflow**:
    ```python
    @workflow.defn
    class ConversationWorkflow:
        @workflow.run
        async def run(self, context: ConversationContext) -> ConversationResult:
            # Maintain conversation state
            conversation_state = ConversationState(
                thread_id=context.thread_id,
                user_id=context.user_id,
                messages=[],
                context_summary=""
            )
            
            # Handle conversation flow with context persistence
            while not workflow.await_until(lambda: conversation_state.is_complete):
                message = await workflow.wait_condition(
                    lambda: workflow.get_external_workflow_signal("new_message")
                )
                
                # Process message with context
                response = await workflow.execute_activity(
                    process_conversation_message,
                    ConversationMessage(
                        message=message,
                        context=conversation_state
                    ),
                    start_to_close_timeout=timedelta(minutes=1)
                )
                
                conversation_state.messages.append(response)
                
                # Summarize if conversation gets long (>10 messages)
                if len(conversation_state.messages) > 10:
                    summary = await workflow.execute_activity(
                        summarize_conversation,
                        conversation_state,
                        start_to_close_timeout=timedelta(minutes=2)
                    )
                    conversation_state.context_summary = summary
                    conversation_state.messages = conversation_state.messages[-3:]
            
            return ConversationResult(final_state=conversation_state)
    ```
  - **Workflow Versioning and Migration**:
    - Implement semantic versioning for workflows (v1.0, v1.1, v2.0)
    - Create workflow compatibility matrix for safe upgrades
    - Set up automated workflow migration testing
- **16c. Advanced Activity Implementations**:
  - **Typed Activity Definitions**:
    ```python
    @activity.defn
    async def analyze_activity(request: AnalysisRequest) -> AnalysisResult:
        activity.heartbeat("Starting analysis")
        
        try:
            # Use Analysis Agent with claude-3-5-haiku
            result = await analysis_agent.process(request)
            
            # Cache result for 1 hour
            await cache_activity_result(
                key=f"analysis:{request.user_id}:{hash(request.content)}",
                result=result,
                ttl=3600
            )
            
            activity.heartbeat("Analysis complete")
            return result
            
        except Exception as e:
            activity.logger.error(f"Analysis failed: {e}")
            raise ActivityError(f"Analysis failed: {str(e)}")
    
    @activity.defn
    async def batch_analyze_activity(batch_item: BatchItem) -> BatchAnalysisResult:
        """Process multiple activities in single LLM call for 30-50% cost reduction"""
        activity.heartbeat(f"Processing batch {batch_item.batch_id}")
        
        # Batch multiple activities for single LLM call
        batch_context = f"Analyze these {len(batch_item.activities)} activities together:"
        for i, activity_content in enumerate(batch_item.activities):
            batch_context += f"\n{i+1}. {activity_content}"
        
        result = await analysis_agent.batch_process(batch_context)
        
        activity.heartbeat("Batch analysis complete")
        return BatchAnalysisResult(batch_id=batch_item.batch_id, results=result)
    
    @activity.defn
    async def gather_user_competency_data(request: UserDataRequest) -> UserCompetencyData:
        """Gather comprehensive user data for report generation"""
        activity.heartbeat("Gathering user competency data")
        
        # Collect user activities from specified time period
        activities = await database.get_user_activities(
            user_id=request.user_id,
            start_date=request.time_period.start,
            end_date=request.time_period.end,
            include_classifications=True
        )
        
        # Get current competency scores
        competency_scores = await database.get_competency_scores(request.user_id)
        
        # Calculate trends if requested
        trends = None
        if request.include_trends:
            trends = await calculate_competency_trends(
                user_id=request.user_id,
                time_period=request.time_period
            )
        
        activity.heartbeat("User data gathered")
        return UserCompetencyData(
            user_id=request.user_id,
            activities=activities,
            competency_scores=competency_scores,
            trends=trends,
            career_stage=await get_user_career_stage(request.user_id)
        )
    
    @activity.defn
    async def format_slack_report(request: SlackReportRequest) -> SlackReport:
        """Format competency analysis into rich Slack Block Kit format"""
        activity.heartbeat("Formatting Slack report")
        
        # Use Block Kit builder for consistent formatting
        block_builder = SlackBlockKitBuilder()
        
        # Build comprehensive competency report blocks
        report_blocks = []
        
        # Header section
        report_blocks.extend(block_builder.build_report_header(
            report_type="Competency Analysis",
            user_name=request.analysis.user_name,
            time_period=request.analysis.time_period
        ))
        
        # Competency scores section
        report_blocks.extend(block_builder.build_competency_scores(
            scores=request.analysis.competency_scores,
            trends=request.analysis.trends,
            show_details=request.user_preferences.show_details
        ))
        
        # Activity highlights section
        if request.user_preferences.include_activities:
            report_blocks.extend(block_builder.build_activity_highlights(
                activities=request.analysis.recent_activities[:5],
                classifications=request.analysis.activity_classifications
            ))
        
        # Career insights section
        report_blocks.extend(block_builder.build_career_insights(
            insights=request.insights.recommendations,
            development_areas=request.insights.development_areas,
            strengths=request.insights.strengths
        ))
        
        # Interactive actions section
        report_blocks.extend(block_builder.build_report_actions(
            actions=["view_detailed_pdf", "schedule_follow_up", "set_goals"],
            user_id=request.analysis.user_id
        ))
        
        activity.heartbeat("Slack report formatted")
        return SlackReport(
            blocks=report_blocks,
            thread_id=request.thread_id,
            user_id=request.analysis.user_id,
            report_summary=request.insights.executive_summary
        )
    
    @activity.defn
    async def generate_pdf_report(request: PDFReportRequest) -> PDFReport:
        """Generate professional PDF competency report"""
        activity.heartbeat("Generating PDF report")
        
        try:
            # Initialize PDF generator with template
            pdf_generator = PDFReportGenerator(template=request.template)
            
            # Build report sections
            report_sections = [
                # Executive summary
                pdf_generator.build_executive_summary(
                    insights=request.insights,
                    key_metrics=request.analysis.key_metrics
                ),
                
                # Competency analysis section
                pdf_generator.build_competency_analysis(
                    scores=request.analysis.competency_scores,
                    trends=request.analysis.trends,
                    benchmarks=request.analysis.industry_benchmarks
                ),
                
                # Activity analysis section
                pdf_generator.build_activity_analysis(
                    activities=request.analysis.activities,
                    classifications=request.analysis.activity_classifications,
                    time_distribution=request.analysis.time_distribution
                ),
                
                # Development recommendations
                pdf_generator.build_development_section(
                    recommendations=request.insights.recommendations,
                    action_items=request.insights.action_items,
                    timeline=request.insights.development_timeline
                ),
                
                # Appendix with detailed data
                pdf_generator.build_appendix(
                    raw_data=request.analysis.raw_data,
                    methodology=request.analysis.methodology,
                    data_sources=request.analysis.data_sources
                )
            ]
            
            # Generate PDF with branding
            pdf_path = await pdf_generator.generate_report(
                sections=report_sections,
                branding=request.branding,
                output_dir="/tmp/reports",
                filename=f"competency_report_{request.analysis.user_id}_{datetime.now().strftime('%Y%m%d')}.pdf"
            )
            
            # Upload to secure storage
            secure_url = await upload_report_to_secure_storage(
                file_path=pdf_path,
                user_id=request.analysis.user_id,
                report_type="competency_analysis"
            )
            
            activity.heartbeat("PDF report generated")
            return PDFReport(
                file_path=pdf_path,
                secure_url=secure_url,
                file_size=os.path.getsize(pdf_path),
                page_count=await get_pdf_page_count(pdf_path),
                generated_at=datetime.now()
            )
            
        except Exception as e:
            activity.logger.error(f"PDF generation failed: {e}")
            raise ActivityError(f"PDF generation failed: {str(e)}")
    
    @activity.defn
    async def deliver_report(request: DeliveryRequest) -> DeliveryResult:
        """Deliver report via specified method (Slack message, DM, email, etc.)"""
        activity.heartbeat("Delivering report")
        
        try:
            if request.delivery_method == "slack_thread":
                # Post Slack report to existing thread
                result = await slack_client.post_message(
                    channel=request.thread_id,
                    blocks=request.report.blocks,
                    thread_ts=request.thread_id
                )
                
            elif request.delivery_method == "slack_dm":
                # Send as direct message
                result = await slack_client.post_dm(
                    user_id=request.recipient,
                    blocks=request.report.blocks
                )
                
            elif request.delivery_method == "pdf_download":
                # Provide secure download link
                result = await slack_client.post_message(
                    channel=request.recipient,
                    blocks=build_pdf_download_blocks(
                        pdf_url=request.report.secure_url,
                        file_name=f"Competency_Report_{datetime.now().strftime('%Y-%m-%d')}.pdf"
                    )
                )
                
            elif request.delivery_method == "email":
                # Send PDF via email (future enhancement)
                result = await email_service.send_report_email(
                    recipient=request.recipient,
                    pdf_attachment=request.report.file_path,
                    summary=request.report.report_summary
                )
            
            activity.heartbeat("Report delivered")
            return DeliveryResult(
                status="success",
                delivery_id=result.message_id or result.email_id,
                delivered_at=datetime.now()
            )
            
        except Exception as e:
            activity.logger.error(f"Report delivery failed: {e}")
            return DeliveryResult(
                status="failed",
                error=str(e),
                attempted_at=datetime.now()
            )
    ```
  - **Activity Configuration**:
    - Retry policies: exponential backoff (1s, 2s, 4s, max 3 attempts)
    - Timeouts: Standard activities (30s), LLM calls (60s), batch processing (5min), PDF generation (6min)
    - Heartbeat intervals: Every 10s for long-running activities
    - Result caching: Redis with 1-hour TTL for analysis results, 24-hour TTL for PDF reports
- **16d. Batch Processing Configuration**:
  - **Batch Workflow Triggers**:
    - User-initiated batch: Process multiple activities from single user
    - Scheduled batch: Daily aggregation at 2 AM UTC
    - Volume-based batch: Auto-trigger when queue depth > 20 items
    - Time-based batch: Process accumulated items every 15 minutes
  - **Batch Optimization Strategies**:
    ```python
    class BatchOptimizer:
        def optimize_batch(self, activities: List[Activity]) -> List[BatchGroup]:
            """Optimize batching for cost and performance"""
            
            # Group by user for context optimization
            user_groups = self.group_by_user(activities)
            
            # Group by competency area for LLM efficiency
            competency_groups = self.group_by_competency(user_groups)
            
            # Optimal batch size: 5 activities per LLM call
            optimized_batches = []
            for group in competency_groups:
                for i in range(0, len(group), 5):
                    batch = group[i:i+5]
                    optimized_batches.append(BatchGroup(
                        activities=batch,
                        priority=self.calculate_priority(batch),
                        estimated_cost=self.estimate_cost(batch)
                    ))
            
            return optimized_batches
    ```
  - **Batch Processing Metrics**:
    - Cost reduction: Track 30-50% API call reduction target
    - Processing efficiency: Batch vs individual processing time comparison
    - Error rates: Failed batch recovery and partial completion handling
- **16e. Cron Workflows for Scheduled Operations**:
  - **Daily Aggregation Workflow**:
    ```python
    @workflow.defn
    class DailyAggregationWorkflow:
        @workflow.run  
        async def run(self) -> AggregationResult:
            # Scheduled at 2 AM UTC daily
            date = workflow.now().date()
            
            # Aggregate previous day's activities
            aggregation_tasks = [
                workflow.execute_activity(
                    aggregate_user_activities,
                    AggregationRequest(date=date, type="daily"),
                    schedule_to_close_timeout=timedelta(hours=2)
                ),
                workflow.execute_activity(
                    update_competency_scores,
                    date,
                    schedule_to_close_timeout=timedelta(hours=1)
                ),
                workflow.execute_activity(
                    cleanup_expired_cache,
                    date,
                    schedule_to_close_timeout=timedelta(minutes=30)
                )
            ]
            
            results = await asyncio.gather(*aggregation_tasks)
            return AggregationResult(date=date, results=results)
    ```
  - **Weekly Report Generation Workflow**:
    ```python  
    @workflow.defn
    class WeeklyReportWorkflow:
        @workflow.run
        async def run(self) -> ReportResult:
            # Scheduled every Monday at 8 AM UTC
            week_start = workflow.now().date() - timedelta(days=7)
            
            # Generate reports for all active users
            users = await workflow.execute_activity(get_active_users, week_start)
            
            report_tasks = []
            for user in users:
                task = workflow.execute_activity(
                    generate_weekly_report,
                    WeeklyReportRequest(user_id=user.id, week_start=week_start),
                    schedule_to_close_timeout=timedelta(hours=1)
                )
                report_tasks.append(task)
            
            # Process in batches of 10 users
            batch_size = 10
            for i in range(0, len(report_tasks), batch_size):
                batch = report_tasks[i:i+batch_size]
                await asyncio.gather(*batch)
                
                # Rate limit between batches
                await asyncio.sleep(30)
            
            return ReportResult(week=week_start, reports_generated=len(users))
    ```
  - **Competency Report Generation Workflow**:
    ```python
    @workflow.defn
    class CompetencyReportWorkflow:
        @workflow.run
        async def run(self, request: ReportRequest) -> ReportResult:
            """Generate competency reports in Slack or PDF format"""
            
            # Step 1: Gather comprehensive user data
            user_data = await workflow.execute_activity(
                gather_user_competency_data,
                UserDataRequest(
                    user_id=request.user_id,
                    time_period=request.time_period,
                    include_activities=True,
                    include_trends=True
                ),
                start_to_close_timeout=timedelta(minutes=3)
            )
            
            # Step 2: Run comprehensive analysis workflow
            analysis_result = await workflow.execute_activity(
                run_comprehensive_analysis,
                ComprehensiveAnalysisRequest(
                    user_data=user_data,
                    analysis_type=request.report_type,
                    detail_level=request.detail_level
                ),
                start_to_close_timeout=timedelta(minutes=5)
            )
            
            # Step 3: Generate insights and recommendations
            insights = await workflow.execute_activity(
                generate_career_insights,
                InsightsRequest(
                    analysis_results=analysis_result,
                    user_goals=request.user_goals,
                    career_stage=user_data.career_stage
                ),
                start_to_close_timeout=timedelta(minutes=4)
            )
            
            # Step 4: Format report based on output preference
            if request.output_format == ReportFormat.SLACK:
                report = await workflow.execute_activity(
                    format_slack_report,
                    SlackReportRequest(
                        analysis=analysis_result,
                        insights=insights,
                        user_preferences=request.formatting_options,
                        thread_id=request.thread_id
                    ),
                    start_to_close_timeout=timedelta(minutes=2)
                )
            else:  # PDF format
                report = await workflow.execute_activity(
                    generate_pdf_report,
                    PDFReportRequest(
                        analysis=analysis_result,
                        insights=insights,
                        template=request.pdf_template,
                        branding=request.branding_options
                    ),
                    start_to_close_timeout=timedelta(minutes=6)
                )
            
            # Step 5: Deliver report
            delivery_result = await workflow.execute_activity(
                deliver_report,
                DeliveryRequest(
                    report=report,
                    delivery_method=request.delivery_method,
                    recipient=request.user_id,
                    notification_preferences=request.notifications
                ),
                start_to_close_timeout=timedelta(minutes=2)
            )
            
            return ReportResult(
                report_id=workflow.uuid4(),
                format=request.output_format,
                delivery_status=delivery_result.status,
                generated_at=workflow.now(),
                file_path=report.file_path if hasattr(report, 'file_path') else None
            )
    ```
  - **Batch Report Generation Workflow**:
    ```python
    @workflow.defn
    class BatchReportWorkflow:
        @workflow.run
        async def run(self, batch_request: BatchReportRequest) -> BatchReportResult:
            """Generate reports for multiple users efficiently"""
            
            batch_id = workflow.uuid4()
            results = []
            
            # Process reports in batches of 3 for optimal resource usage
            batch_size = 3
            for i in range(0, len(batch_request.user_requests), batch_size):
                batch = batch_request.user_requests[i:i+batch_size]
                
                # Parallel report generation within batch
                report_tasks = []
                for user_request in batch:
                    # Create individual report workflow for each user
                    task = workflow.execute_child_workflow(
                        CompetencyReportWorkflow.run,
                        user_request,
                        id=f"report_{batch_id}_{user_request.user_id}",
                        task_queue="report-generation",
                        execution_timeout=timedelta(minutes=20)
                    )
                    report_tasks.append(task)
                
                # Wait for batch completion
                batch_results = await asyncio.gather(*report_tasks, return_exceptions=True)
                
                # Handle partial failures gracefully
                for j, result in enumerate(batch_results):
                    if isinstance(result, Exception):
                        results.append(ReportResult(
                            report_id=f"failed_{batch_id}_{batch[j].user_id}",
                            format=batch[j].output_format,
                            delivery_status="failed",
                            error=str(result)
                        ))
                    else:
                        results.append(result)
                
                # Progress tracking and rate limiting
                await workflow.execute_activity(
                    update_batch_report_progress,
                    BatchReportProgress(
                        batch_id=batch_id,
                        completed=len(results),
                        total=len(batch_request.user_requests),
                        current_batch=i // batch_size + 1
                    ),
                    start_to_close_timeout=timedelta(minutes=1)
                )
                
                # Rate limit between batches to avoid overwhelming systems
                if i + batch_size < len(batch_request.user_requests):
                    await asyncio.sleep(30)
            
            return BatchReportResult(
                batch_id=batch_id,
                total_reports=len(results),
                successful_reports=len([r for r in results if r.delivery_status == "success"]),
                failed_reports=len([r for r in results if r.delivery_status == "failed"]),
                results=results
            )
    ```
- **16f. Agent Coordination Through Temporal Activities**:
  - **Direct Activity Coordination** (No CrewAI complexity):
    ```python
    class AgentCoordinator:
        async def coordinate_analysis(self, request: AnalysisRequest) -> CoordinationResult:
            """Coordinate Analysis Agent → Advisor Agent through Temporal state"""
            
            # Step 1: Analysis Agent activity
            analysis = await workflow.execute_activity(
                run_analysis_agent,
                request,
                start_to_close_timeout=timedelta(minutes=2)
            )
            
            # Step 2: Pass results through workflow state (not direct agent communication)
            workflow_state = WorkflowState(
                user_id=request.user_id,
                analysis_results=analysis,
                stage="analysis_complete",
                timestamp=workflow.now()
            )
            
            # Step 3: Advisor Agent activity with analysis context
            advice = await workflow.execute_activity(
                run_advisor_agent, 
                AdvisorRequest(
                    user_id=request.user_id,
                    analysis_context=analysis,
                    workflow_state=workflow_state
                ),
                start_to_close_timeout=timedelta(minutes=3)
            )
            
            return CoordinationResult(analysis=analysis, advice=advice)
    ```
  - **Resource Management and Scaling**:
    - Semaphore-based concurrency: Analysis Agent (8), Advisor Agent (5)
    - Auto-scaling triggers: Queue depth > 15 (scale up), < 5 (scale down) 
    - Resource monitoring: CPU, memory, and response time per agent type
    - Circuit breaker: Stop workflow execution if agent failure rate > 10%
- **16g. Workflow State Management and Recovery**:
  - **Persistent Workflow State Schema**:
    ```python
    @dataclass
    class WorkflowState:
        workflow_id: str
        user_id: str
        conversation_id: Optional[str]
        current_stage: str  # "analysis", "advice", "complete"
        analysis_results: Optional[AnalysisResult]
        conversation_context: Optional[ConversationContext]
        retry_count: int = 0
        created_at: datetime
        updated_at: datetime
        
        def to_temporal_search_attributes(self) -> Dict[str, Any]:
            return {
                "UserId": self.user_id,
                "WorkflowType": self.current_stage,
                "ConversationId": self.conversation_id or "none"
            }
    ```
  - **State Recovery and Continuation**:
    - Automatic workflow continuation after worker restarts
    - State checkpointing after each activity completion
    - Query workflows by user_id for conversation continuity
    - State compression for workflows with large context (>10KB)
- **16h. Simplified Workflow Routing Configuration**:
  - **Rule-Based Routing** (Phase 1 - No LLM complexity):
    ```python
    class WorkflowRouter:
        def route_request(self, intent: UserIntent, context: RequestContext) -> WorkflowType:
            """Simple rule-based routing for Phase 1"""
            
            routing_rules = {
                UserIntent.GREETING: WorkflowType.CONVERSATION,
                UserIntent.HELP_REQUEST: WorkflowType.CONVERSATION, 
                UserIntent.CLASSIFY_ACTIVITY: WorkflowType.SEQUENTIAL_ANALYSIS,
                UserIntent.ANALYZE_AND_STORE: WorkflowType.SEQUENTIAL_ANALYSIS,
                UserIntent.COMPREHENSIVE_ANALYSIS: WorkflowType.SEQUENTIAL_ANALYSIS,
                UserIntent.BATCH_ACTIVITIES: WorkflowType.BATCH_ANALYSIS,
                UserIntent.GENERATE_REPORT: WorkflowType.COMPETENCY_REPORT,
                UserIntent.COMPETENCY_REPORT: WorkflowType.COMPETENCY_REPORT,
                UserIntent.CAREER_ANALYSIS: WorkflowType.COMPETENCY_REPORT
            }
            
            # Route to batch workflow if multiple activities detected
            if len(context.activities) > 1:
                return WorkflowType.BATCH_ANALYSIS
                
            # Route to batch report workflow if multiple users requested
            if hasattr(context, 'multiple_users') and context.multiple_users:
                return WorkflowType.BATCH_REPORT
                
            return routing_rules.get(intent, WorkflowType.SEQUENTIAL_ANALYSIS)
    ```
  - **Fallback and Error Handling**:
    - Default to conversation workflow for unclear intents
    - Implement graceful degradation when agents are unavailable
    - Route to simple analysis if batch processing fails
- **USE STRUCTLOG**: All Temporal operations logged with workflow_id, user_id, activity_type, batch_id

### 17. Simplified agent implementations (Right-sized for Phase 1)
- **REQUIRES**: Tasks 15, 16 (base framework, orchestration) complete
- **17a. Analysis Agent (Combined Data Analyst + Competency Specialist)**:
  - Implement combined activity classification and competency scoring in single LLM call
  - Create metrics extraction with confidence scoring (threshold: 0.7)
  - Use competency scoring algorithm (weights: recency=0.3, frequency=0.4, complexity=0.3)
  - Build skill mapping and gap analysis in unified process
  - Configure concurrent limit: 8 instances (combined capacity)
  - Model: claude-3-5-haiku ($0.25/1k tokens) for cost efficiency
  - Tool access: classification_tools, assessment_tools, storage_tools
  - Performance target: <4s per combined analysis
  - **RATIONALE**: Eliminates agent-to-agent communication overhead, 50% faster
- **17b. Advisor Agent (Combined Career Strategist + Insights Synthesizer)**:
  - Implement career progression analysis with development recommendations
  - Create coherent narrative generation from analysis results
  - Build actionable insights extraction and learning opportunity identification
  - Combine synthesis with strategic advice in single response
  - Configure concurrent limit: 5 instances
  - Model: gpt-4o ($2.50/1k tokens) for higher quality advice
  - Tool access: reporting_tools, career_planning_tools, all tools (read-only)
  - Performance target: <6s per advisory synthesis
  - **RATIONALE**: Natural grouping of advisory functions, eliminates synthesis bottleneck
- **17c. Agent Coordination (Simplified, No CrewAI)**:
  - Use simple Temporal workflow orchestration (remove CrewAI complexity)
  - Implement direct agent-to-agent result passing
  - Create simple routing logic: analysis-first, advisory-on-demand
  - **SIMPLIFIED**: No crew formation, role negotiation, or complex collaboration
  - **SIMPLIFIED**: No agent communication protocols beyond result passing
  - **PERFORMANCE GAIN**: 3-5x faster execution, 75% less overhead
- **17d. Agent Resource Management**:
  - Implement semaphore-based concurrency control per agent type
  - Create agent health monitoring (CPU, memory, latency)
  - Set up simple auto-scaling triggers (queue depth > 10)
  - Build basic agent performance dashboards
  - **INTEGRATION**: Connects to Tool Framework (Task 20)
- **17e. Scaling Strategy & Upgrade Path**:
  - **Phase 1**: 2 agents handle 90% of use cases efficiently
  - **Scale Trigger**: Split agents when volume >500 requests/day
  - **Complexity Trigger**: Add specialized agents when workflow complexity >0.8 on 30% of requests
  - **UPGRADE PATH**: Can easily split combined agents into 4 specialized ones when justified

### 18. Workflow execution patterns (Expanded)
- **REQUIRES**: Tasks 15-17 (complete agent system) complete
- **18a. Execution Pattern Implementation**:
  - Sequential: Single agent, linear flow, 5-min timeout
  - Parallel: Multi-agent concurrent, 10-min timeout
  - Pipeline: Staged with dependencies, 15-min timeout
  - Adaptive: Dynamic pattern selection based on complexity
- **18b. Error Handling & Recovery**:
  - **Agent Failures**:
    - Retry with exponential backoff (1s, 2s, 4s)
    - Fallback to simpler agent/model
    - Partial result handling
  - **Workflow Failures**:
    - Checkpoint recovery from last successful state
    - Compensation actions for cleanup
    - User notification with recovery options
  - **System Failures**:
    - Circuit breakers per service (50% failure rate)
    - Graceful degradation paths
    - Automatic incident creation
- **18c. User-Facing Error Messages**:
  - Template categories:
    - Temporary issue: "I'm having trouble right now. Let me try again..."
    - Partial success: "I completed part of your request. Here's what I found..."
    - Need clarification: "I need more information to help with that..."
    - System limits: "This request is too complex. Let me break it down..."
  - Include recovery actions in every error
  - Maintain conversation context through errors
- **18d. Progress Tracking**:
  - Real-time status updates to Slack
  - Progress indicators for long-running workflows
  - Completion notifications with summaries
  - Workflow history and audit trail
- **18e. State Persistence**:
  - Checkpoint after each agent completion
  - Store state in database with versioning
  - Implement state recovery on restart
  - State compression for large contexts
- **INTEGRATION**: Error patterns used across all agent executions

### 19. Agent system testing
- **REQUIRES**: Task 14 (AI testing) and Tasks 15-18 (agent system) complete
- Implement Temporal workflow testing utilities with state validation
- Create agent performance benchmarking tests with realistic workloads
- Set up multi-agent coordination testing and validation
- Implement agent failure and recovery testing
- Create agent resource utilization and scaling tests
- Set up agent security and access control testing

---

## Phase 5: Tool Framework and Business Logic (Days 27-33)

### 20. Simple agent tools and task processing
- **REQUIRES**: Phase 4 (agent system) complete
- **Analysis Agent Tools**:
  - `activity_classifier`: Classify user activities into competency categories
  - `competency_assessor`: Calculate competency levels from activity history  
  - `database_query`: Fetch user activities and profile data from PostgreSQL
  - `cache_manager`: Store and retrieve frequently accessed data from Redis
- **Advisor Agent Tools**:
  - `recommendation_engine`: Generate career development recommendations
  - `report_generator`: Create PDF reports using templates from Task 35
  - `goal_tracker`: Track and update user development goals
  - `resource_finder`: Find external learning resources and opportunities
- **Tool Implementation Framework**:
  - Create simple Tool base class with execute() method and basic error handling
  - Implement tool registry as simple dictionary mapping tool names to classes
  - Add basic input validation using Pydantic models for tool parameters
  - Set up tool execution logging with performance metrics (execution time, success/failure)
- **Task Processing with Redis Queue**:
  - Use Redis lists as simple task queues for each agent type
  - Implement basic task priority (high/normal) using separate Redis keys
  - Add task deduplication using task hashes to prevent duplicate processing
  - Set up task retry logic with exponential backoff for failed executions
- **Tool Access and Security**:
  - Analysis Agent: Read-only access to user data, can write competency calculations
  - Advisor Agent: Read access to all data, can generate reports and update goals
  - Simple tool authentication using agent identity and basic permission checks
  - Log all tool executions with user context for audit trails
  - **INTEGRATION**: Connects to Agents (Task 17) via execute_tool interface

### 21. Classification and analysis tools

#### **21a. Activity Classification Engine**
- **REQUIRES**: Task 20 (tool framework) complete
- **Simple Classification Approach**:
  - Rule-based classifier: Pattern matching for known activity types using keyword detection and regex patterns
  - LLM-assisted classification: Use Analysis Agent (claude-3-5-haiku) for complex/ambiguous activities
  - Implement fallback strategy: rules → LLM classification via existing Analysis Agent
  - Create classification confidence based on rule match strength and LLM confidence scores
- **Activity Type Taxonomy**:
  - Technical activities: coding, architecture, debugging, testing, deployment
  - Leadership activities: mentoring, planning, decision-making, team meetings
  - Learning activities: training, research, documentation, knowledge sharing
  - Support activities: troubleshooting, customer support, maintenance

#### **21b. Intent Classification and Analysis**
- **LLM-Powered Intent Analysis**:
  - Implement intent classification using Analysis Agent (claude-3-5-haiku) for cost efficiency
  - Support intent types: activity_classification, competency_analysis, career_advice, help_request
  - Create intent confidence scoring with threshold-based routing (>0.7 direct routing, <0.7 clarification)
  - Implement context-aware intent detection using conversation history and user profile
- **Intent Processing Pipeline**:
  - Pre-processing: Text normalization, context injection, user context enrichment
  - Classification: Intent prediction with confidence scoring and alternative suggestions
  - Post-processing: Intent validation, clarification generation, routing decision
  - Monitoring: Track intent accuracy, clarification rates, user satisfaction

#### **21c. Competency Framework Mapping**
- **Dynamic Framework Loading** (Requirement 45.1):
  - Support JSON-based competency framework definitions with versioning
  - Implement framework schema validation using Pydantic models
  - Create framework hot-reloading without service restart for configuration updates
  - Support organization-specific frameworks and custom skill taxonomies
- **Activity-to-Competency Mapping**:
  - Create skill extraction from activity descriptions using Analysis Agent (claude-3-5-haiku)
  - Implement competency matching with keyword matching and predefined competency mappings
  - Build competency hierarchy navigation (skill → competency → level → role)
  - Support multi-competency activities with competency weight distribution based on configuration

#### **21d. Trend Analysis and Progression Tracking**
- **Competency Progression Analysis** (Requirement 45.6):
  - Calculate moving averages for competency scores over configurable time windows
  - Implement growth rate calculations with trend direction detection
  - Create predictive competency trajectories using linear regression and seasonal adjustments
  - Build competency momentum indicators (accelerating, stable, declining)
- **Performance Benchmarking**:
  - Compare user competency progression against peer benchmarks
  - Implement competency velocity calculations (competency growth per time period)
  - Create competency milestone detection and achievement tracking
  - Generate competency progression insights and development recommendations

### 22. Assessment and competency tools

#### **22a. Simple Competency Assessment**
- **REQUIRES**: Task 21 (classification tools) complete
- **Simple Competency Scoring** (Requirements 45.2, 45.4):
  - Count relevant activities for each competency in the last 90 days
  - Apply linear time decay: activities lose value over time (1.0 weight today → 0.0 weight at 90 days)
  - Calculate competency level: Level = min(activity_count * time_weighted_average, 5.0)
  - Set evidence thresholds: Strong (>8 activities), Moderate (4-8), Weak (<4)
- **Activity-Based Evidence Only**:
  - Focus on direct work activities and their competency classifications
  - Use activity frequency and recency as primary indicators
  - Simple competency mapping from activity types to competency areas
  - Store competency scores with last_calculated timestamp for tracking

#### **22b. Competency Level Calculation and Validation**
- **Level Advancement Logic** (Requirement 45.3):
  - Implement competency threshold calculations based on framework definitions
  - Apply time-in-role requirements for level advancement (junior: 0-2 years, mid: 2-5 years, senior: 5+ years)
  - Create competency level validation with peer comparison and historical benchmarks
  - Support custom advancement rules per organization and role type
- **Competency Gap Analysis** (Requirement 45.5):
  - Compare current competency levels against target role requirements
  - Calculate skill gap scores and prioritize development areas
  - Generate competency development roadmaps with actionable next steps
  - Implement skill transferability analysis for career path recommendations

#### **22c. Assessment Quality and Validation**
- **Data Quality Validation** (Requirement 45.10):
  - Implement anomaly detection for unusual competency score changes
  - Validate assessment consistency across similar activities and time periods
  - Flag outliers and inconsistencies for human review and validation
  - Monitor assessment accuracy through feedback loops and correction tracking
- **Peer Review and Approval Workflows** (Requirement 45.7):
  - Create peer review workflows for significant competency level changes
  - Implement manager approval processes for promotional level advancements
  - Support competency assessment challenges and resolution processes
  - Maintain audit trails for all assessment changes and approvals

#### **22d. Competency Prediction and Future Planning**
- **Predictive Competency Modeling**:
  - Implement competency trajectory prediction using statistical analysis of historical progression data
  - Create skill development timeline estimates based on current progress rates and linear extrapolation
  - Predict future competency levels using simple linear regression on historical competency scores
  - Support scenario modeling for different development path choices using statistical projections
- **Career Path Optimization**:
  - Generate optimal learning sequences for target competency achievement
  - Recommend skill development priorities based on career goals and market demand
  - Create personalized development plans with timeline estimates and milestones
  - Integrate with external learning resources and development opportunities

### 23. Storage and data management tools

#### **23a. Activity Data Store and Management**
- **REQUIRES**: Tasks 20-22 (tool framework and business tools) complete
- **Activity Storage Architecture**:
  - Implement time-series optimized storage using TimescaleDB for activity data
  - Create partitioned tables by date and user for efficient querying and archival
  - Set up composite indexes on (user_id, timestamp, activity_type) for fast retrieval
  - Implement data compression for older activity records (>6 months)
- **Activity Data Model and Validation**:
  - Define activity data schema: activity_id, user_id, timestamp, type, description, metadata
  - Create Pydantic models for activity validation with field constraints
  - Implement data integrity constraints: foreign keys, check constraints, not null validations
  - Support activity versioning and update tracking with change audit trails

#### **23b. User Profile Store and Cache Management**
- **User Profile Data Architecture**:
  - Store user profiles in PostgreSQL with normalized data structure
  - Implement intelligent caching in Redis with hierarchical cache keys
  - Create cache warming strategies for active users and cache invalidation on profile updates
  - Support multi-tenant user data with organization-level data isolation
- **Profile Update and Synchronization**:
  - Implement optimistic locking for concurrent profile updates
  - Create profile change detection and delta synchronization with external systems
  - Set up profile data validation and consistency checks across systems
  - Support profile data import/export with data transformation pipelines

#### **23c. Competency Data Store and Historical Tracking**
- **Competency Data Architecture** (Requirements 45.6, 45.8):
  - Store competency scores in TimescaleDB for efficient time-series operations
  - Create competency snapshot tables for point-in-time competency states
  - Implement competency change tracking with before/after values and change attribution
  - Support competency data partitioning by user and time for scalable storage
- **Historical Analysis and Trend Storage**:
  - Create pre-computed competency trend tables for fast dashboard queries
  - Implement moving average calculations and store results for quick retrieval
  - Store competency benchmarks and peer comparison data for relative assessments
  - Create competency milestone tracking with achievement timestamps and evidence

#### **23d. Data Validation and Quality Assurance**
- **Data Integrity and Validation Tools** (Requirement 45.10):
  - Implement data validation pipelines with automated anomaly detection
  - Create data consistency checks across related tables and entities
  - Set up referential integrity validation with orphaned data detection
  - Monitor data quality metrics: completeness, accuracy, consistency, timeliness
- **Data Correction and Cleanup Processes**:
  - Create automated data correction workflows for known data quality issues
  - Implement data deduplication processes for duplicate activity and user records
  - Set up data normalization tools for consistent data formats and values
  - Create data quality dashboards with alerts for data quality degradation

#### **23e. Data Export and Integration Tools**
- **Report Data Export Capabilities**:
  - Create data export tools for PDF report generation with optimized queries
  - Implement data aggregation and summarization for executive dashboards
  - Support data export in multiple formats (JSON, CSV, XML) for external integrations
  - Create data anonymization and pseudonymization tools for external sharing
- **External System Integration**:
  - Implement data synchronization APIs for HRIS and performance management systems
  - Create data validation and transformation pipelines for external data ingestion
  - Set up data reconciliation processes for external data consistency
  - Support real-time data streaming for live dashboard updates

#### **23f. Data Archival and Lifecycle Management**
- **Data Retention and Archival Policies**:
  - Implement configurable data retention policies by data type and organization requirements
  - Create automated data archival processes for old activity data (>2 years)
  - Set up archived data storage in cost-effective cold storage with retrieval capabilities
  - Support legal hold capabilities for litigation and compliance requirements
- **Performance Optimization and Cleanup**:
  - Create database maintenance routines: index rebuilds, statistics updates, vacuum operations
  - Implement automated cleanup of temporary data, cache entries, and log files
  - Set up storage monitoring and alerting for disk usage and performance degradation
  - Create data migration tools for schema changes and system upgrades

### 24. Business logic implementation (Expanded)
- **REQUIRES**: Tasks 20-23 (complete tool framework) complete
- **24a. Competency Calculation Engine**:
  - Implement weighted scoring algorithm:
    - Recency weight: 0.3 (time decay function)
    - Frequency weight: 0.4 (activity count normalization)
    - Complexity weight: 0.3 (task difficulty scoring)
  - Create confidence interval calculation (90% CI using bootstrap)
  - Build trend analysis with moving averages (7-day, 30-day, 90-day)
  - Implement anomaly detection for sudden score changes
  - Set up evidence validation with minimum thresholds (3 activities minimum)
- **24b. Career Progression Engine**:
  - Implement level advancement rules:
    - Junior→Mid: 365 days minimum + competency threshold
    - Mid→Senior: 730 days minimum + competency threshold
    - Senior→Principal: 1095 days minimum + leadership evidence
  - Create promotion readiness scoring (0-100)
  - Build gap analysis with actionable recommendations
  - Implement peer comparison and benchmarking
  - Set up succession planning indicators
- **24c. Skill Assessment Algorithms**:
  - Create skill taxonomy with 4-level hierarchy
  - Implement skill decay modeling (half-life: 180 days)
  - Build skill transferability matrix
  - Create skill demand forecasting
  - Set up skill verification workflows
- **24d. Recommendation Engine**:
  - Implement collaborative filtering for learning recommendations
  - Create content-based filtering using skill gaps
  - Build hybrid recommendation model
  - Set up recommendation explanations ("why this recommendation")
  - Implement feedback loop for recommendation improvement
  - **INTEGRATION**: Used by Career Strategist Agent (Task 17c)

---

## Phase 6: Slack Integration Layer (Days 34-40)

### 25. Slack adapter architecture (Expanded)
- **REQUIRES**: Phase 5 (tools and business logic) complete
- **25a. Slack App Configuration**:
  - Create Slack App manifest with required scopes:
    - Bot: chat:write, app_mentions:read, im:history, channels:history
    - User: None (bot-only implementation)
    - Admin: app_configurations:write (for updates)
  - Configure event subscriptions:
    - message.channels, message.groups, message.im, message.mpim
    - app_mention, app_home_opened, team_join
  - Set up slash commands:
    - /reflect - Main entry point
    - /analyze - Direct analysis request
    - /report - Generate reports
    - /help - Get assistance
  - Configure interactivity & shortcuts
  - Set up OAuth redirect URLs
- **25b. Unified Adapter Implementation**:
  - Create adapter interface abstracting Socket/HTTP modes
  - Implement mode detection from environment variables
  - Build event normalization layer
  - Create response queuing for rate limiting
  - Set up connection health monitoring
- **25c. Authentication Layer**:
  - Socket Mode: App-level token management
  - HTTP Mode: Request signature verification
  - OAuth: User token handling (future)
  - Workspace installation tracking
  - Token refresh and rotation
- **25d. Mode-Specific Handlers**:
  - Socket Mode: WebSocket connection management
  - HTTP Mode: Webhook endpoint configuration
  - Health checks adapted to each mode
  - Graceful shutdown procedures
  - Connection retry logic
- **USE STRUCTLOG**: All Slack operations logged with workspace_id, user_id

### 26. Event handling and deduplication (Expanded)
- **REQUIRES**: Task 25 (Slack adapter) and Task 8 (NATS/Redis) complete
- **26a. Slack Event Processing Pipeline**:
  - Implement event receivers for all Slack event types:
    - message.channels, message.groups, message.im, message.mpim
    - app_mention, app_home_opened, team_join
    - slash commands: /reflect, /analyze, /help, /report
  - Create event normalization layer for consistent processing
  - Set up event priority queuing (slash commands > mentions > messages)
  - Implement event batching for high-volume scenarios
- **26b. Deduplication Integration**:
  - **EXTEND REDIS DEDUPLICATION**: Use deduplication from Task 8e
  - Create Slack-specific dedup keys: slack:{team_id}:{event_id}:{event_time}
  - Implement 3-second acknowledgment window for Slack's retry mechanism
  - Set up deduplication bypass for event replay/recovery
  - Build deduplication metrics dashboard
- **26c. Event-to-NATS Bridge**:
  - Transform Slack events to internal event schema (from Task 8b)
  - Publish events to NATS streams with correlation IDs
  - Implement event enrichment with user context
  - Set up event routing based on intent classification
  - Create event flow tracing from Slack to agents
- **26d. Rate Limiting & Backpressure**:
  - Implement Slack API rate limiting (Web API: 1/sec, Events API: 30k/hr)
  - Create adaptive backoff for rate limit responses (429 errors)
  - Set up request queuing with priority (user messages > system events)
  - Implement circuit breakers for Slack API failures
  - Build rate limit monitoring and alerting
- **INTEGRATION FLOW**: Slack Event → Deduplication (Task 8e) → Redis Pub/Sub (Task 8) → Intent Classification → Temporal Workflow (Task 16)

### 27. Comprehensive conversation context management

#### **27a. Slack Threading Strategy and Lifecycle** (Requirements 22.1-22.12)
- **REQUIRES**: Tasks 25, 26 (Slack foundation) complete
- **Threading Decision Matrix**:
  - Direct Messages: NO threading for simple conversation flow
  - Shared Channels + Greetings: NO threading (simple response)
  - Shared Channels + Analysis/Complex: CREATE thread for organized workflow
  - Follow-up Questions: CONTINUE existing thread when context is related
- **Thread Lifecycle Management**:
  - Create thread ID mapping to conversation_id for context persistence
  - Implement thread expiry detection (Slack 90-day limit) with graceful recovery
  - Handle thread accessibility issues with automatic new thread creation
  - Manage thread-to-conversation context transfer when threads expire

#### **27b. Natural Conversation Context Understanding** (Requirements 13.3, 20.3-20.10)
- **Context Extraction and Intent Analysis**:
  - Detect indirect mentions of work activities in natural conversation
  - Identify competency-related discussions without explicit keywords
  - Recognize follow-up questions related to previous analysis
  - Extract action requests from conversational language
- **Conversation State Tracking**:
  - Maintain conversation history with message timestamps and context
  - Track user's current conversation stage (greeting, analysis, follow-up, closing)
  - Detect conversation topic transitions and context switches  
  - Store conversation sentiment and user engagement level
- **Multi-Turn Conversation Support**:
  - Reference previous messages and analysis results in responses
  - Build conversation memory for coherent multi-message exchanges
  - Handle conversation interruptions and topic resumption
  - Support conversational clarification loops for unclear requests

#### **27c. Redis-Based Context Storage and State Management** (Requirements 29.2, 29.7-29.8)
- **Conversation Context Schema**:
  ```json
  conversation:{thread_id} = {
    "user_id": "U123456",
    "thread_ts": "1640995200.123",
    "conversation_stage": "analysis_in_progress",
    "context_summary": "User discussing recent code review work",
    "message_history": [...],
    "mentioned_activities": [...],
    "pending_actions": [...],
    "agent_state": {...}
  }
  ```
- **Context Storage Strategy**:
  - Use Redis hashes for structured conversation data with 24-hour TTL
  - Implement conversation context indexing by user_id for cross-thread reference
  - Store conversation summaries for quick context retrieval
  - Cache frequent context access patterns for performance

#### **27d. Context Summarization for Long Conversations** (Requirements 29.6, 34.8)
- **Automatic Context Compression**:
  - Trigger summarization when conversation exceeds 20 messages or 4000 tokens
  - Use Analysis Agent (claude-3-5-haiku) to create conversation summaries
  - Preserve key context: user activities mentioned, competency areas, action items
  - Maintain conversation flow continuity through intelligent summarization
- **Context Summarization Strategy**:
  - Keep last 5 messages as full context + summary of earlier messages
  - Extract and preserve mentioned work activities and competency discussions
  - Maintain user's stated goals and preferences throughout conversation
  - Update summary incrementally to avoid re-processing entire conversation

#### **27e. Multi-Agent Conversation Coordination** (Requirements 23.4, 29.7-29.11)
- **Agent Context Sharing**:
  - Pass conversation context to Analysis Agent for activity classification
  - Provide Advisor Agent with conversation history for personalized recommendations
  - Maintain agent handoff state within conversation context
  - Coordinate agent responses within the same thread for coherent flow
- **Temporal Workflow Integration**:
  - Store conversation context in Temporal workflow state for reliability
  - Use conversation_id as workflow correlation ID for context persistence
  - Handle workflow continuation with preserved conversation context
  - Implement conversation state recovery after system restarts or failures
- **Response Coordination**:
  - Ensure agent responses reference previous conversation elements
  - Maintain conversational tone and context consistency across agent responses
  - Handle conversation flow when multiple agents contribute to single thread
  - Provide contextual follow-up suggestions based on conversation history

### 28. Block Kit UI formatting for consistent responses (Expanded)
- **REQUIRES**: Tasks 25-27 (complete Slack integration) complete
- **28a. Standard Block Kit Templates**:
  - **Agent Response Templates**:
    ```json
    // Analysis Agent Response Template
    {
      "blocks": [
        {
          "type": "header",
          "text": {"type": "plain_text", "text": "🔍 Analysis Complete"}
        },
        {
          "type": "section",
          "text": {"type": "mrkdwn", "text": "*Activity Classification Results*"}
        },
        {
          "type": "divider"
        },
        {
          "type": "section",
          "fields": [
            {"type": "mrkdwn", "text": "*Competency Area:*\n{competency}"},
            {"type": "mrkdwn", "text": "*Skill Level:*\n{skill_level}/5"}
          ]
        }
      ]
    }
    ```
  - **Advisor Agent Response Template**:
    ```json
    {
      "blocks": [
        {
          "type": "header", 
          "text": {"type": "plain_text", "text": "💡 Career Guidance"}
        },
        {
          "type": "section",
          "text": {"type": "mrkdwn", "text": "*Development Recommendations*"}
        },
        {
          "type": "rich_text",
          "elements": [{"type": "rich_text_list", "style": "bullet"}]
        }
      ]
    }
    ```
  - **Error/Status Templates**: Consistent error handling and system status updates
  - **Progress Templates**: Real-time workflow progress with progress bars
- **28b. Response Type Categorization**:
  - **Immediate Responses** (Classification, Quick Status):
    - Simple section blocks with consistent emoji indicators
    - Maximum 2-3 blocks for rapid consumption
    - Action buttons for follow-up options
  - **Complex Analysis Responses** (Competency Reports):
    - Header block with analysis type
    - Structured field sections for data presentation
    - Interactive elements for drill-down exploration
    - Summary footer with next action recommendations
  - **Conversation Responses** (Questions, Clarifications):
    - Context section referencing previous messages
    - Button groups for user choice selections
    - Input components for text collection when needed
  - **Error Responses** (System Issues, User Errors):
    - Warning/error header with clear severity indicators
    - Context section explaining the issue
    - Action buttons for resolution steps
- **28c. Interactive Component Specifications**:
  - **Button Actions**:
    ```json
    {
      "type": "actions",
      "elements": [
        {
          "type": "button",
          "text": {"type": "plain_text", "text": "View Full Report"},
          "style": "primary",
          "action_id": "view_full_report",
          "value": "report_id_{report_id}"
        },
        {
          "type": "button", 
          "text": {"type": "plain_text", "text": "Get Recommendations"},
          "style": "danger",
          "action_id": "get_recommendations",
          "value": "user_id_{user_id}"
        }
      ]
    }
    ```
  - **Select Menus** for competency area filtering and skill level selection
  - **Multi-select** components for activity category selection
  - **Radio Button Groups** for report format preferences
  - **Date Pickers** for time period analysis selection
- **28d. Block Kit Builder Service**:
  - **ResponseBuilder Class**:
    ```python
    class SlackBlockKitBuilder:
        def __init__(self):
            self.templates = self.load_block_templates()
            
        def build_agent_response(self, response_type: str, data: dict) -> dict:
            """Build standardized agent response blocks"""
            template = self.templates[response_type]
            return self.populate_template(template, data)
            
        def build_progress_update(self, workflow_id: str, stage: str, progress: float) -> dict:
            """Build workflow progress update blocks"""
            return {
                "blocks": [
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": f"*Workflow Progress:* {stage}"}
                    },
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": self.create_progress_bar(progress)},
                        "accessory": {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "View Details"},
                            "action_id": "workflow_details",
                            "value": workflow_id
                        }
                    }
                ]
            }
            
        def build_error_response(self, error_type: str, context: dict) -> dict:
            """Build consistent error response blocks"""
            severity_emoji = {"warning": "⚠️", "error": "❌", "info": "ℹ️"}
            return self.templates["error_response"].format(
                emoji=severity_emoji[error_type], 
                **context
            )
    ```
  - **Template Management**: File-based templates with Jinja2 rendering
  - **Dynamic Content Population**: Data binding with validation
  - **Accessibility Compliance**: Alt text and screen reader support
- **28e. Consistent Formatting Standards**:
  - **Color Scheme**: Primary (blue), Danger (red), Success (green) consistently applied
  - **Emoji Usage**: Standardized emoji indicators for different content types
    - 🔍 Analysis results
    - 💡 Recommendations  
    - ⚠️ Warnings
    - ❌ Errors
    - ✅ Success
    - 📊 Reports
    - 🎯 Goals
  - **Typography**: Consistent use of bold, italics, and code formatting
  - **Spacing**: Standardized block spacing and divider usage
  - **Action Patterns**: Consistent button positioning and labeling conventions
- **28f. Context-Aware Response Adaptation**:
  - **Thread vs DM Formatting**: Different formatting for threaded vs direct responses
  - **User Role Adaptation**: Manager vs individual contributor response variations  
  - **Conversation Stage Adaptation**: Initial vs follow-up response formatting
  - **Device-Responsive**: Mobile-optimized vs desktop-optimized layouts
- **28g. Real-Time Message Updates**:
  - **Progress Notifications**: Live workflow progress updates using message updates API
  - **Status Changes**: Dynamic status indicator updates
  - **Interactive State Management**: Button state changes based on user actions
  - **Ephemeral Responses**: Temporary responses for intermediate states
- **USE STRUCTLOG**: All Block Kit operations logged with response_type, user_id, template_used

### 29. Slack integration testing
- **REQUIRES**: Tasks 25-28 (complete Slack system) complete
- Set up Slack API interaction testing with VCR cassettes and respx mocking
- Create event deduplication testing and validation
- Implement threading and conversation management testing
- Set up response formatting and interaction testing
- Create Slack app manifest management and drift detection
- Test Socket Mode and HTTP Mode compatibility validation

---

## Phase 7: User Experience and Home Tab (Days 41-46)

### 30. Conversation intelligence
- **REQUIRES**: Phase 6 (Slack integration) complete
- Implement sophisticated LLM-powered intent analysis for user requests
- Create comprehensive conversation context management with thread support
- Set up intelligent conversation history optimization and pruning
- Implement conversation state persistence and cross-session continuity
- Create conversation analytics and user engagement tracking
- **30a. Intelligent Clarification System (CRITICAL)**:
  - Implement IntentAnalyzer with confidence threshold of 0.7
  - Create ClarificationGenerator with contextual response templates
  - Build ConversationContextManager with Redis-based state storage (5min TTL)
  - Set up smart follow-up questions per intent category
  - Target: <20% requests need clarification, 95% resolution after clarification
  - **INTEGRATION**: Reduces user friction and improves experience quality
- **USE STRUCTLOG**: All conversation operations use established logging

### 31. Greeting and help system
- **REQUIRES**: Task 30 (conversation intelligence) complete
- Create advanced greeting pattern recognition and intent classification
- Implement contextual responses based on user history and interaction patterns
- Set up comprehensive personalized onboarding for new users
- Create interactive help system with examples and contextual assistance
- Implement user capability overview personalized by role and department
- Set up greeting response effectiveness monitoring and optimization

### 32. Home Tab architecture and implementation

#### **32a. Home Tab UI Components**
- **REQUIRES**: Tasks 30, 31 (conversation and help systems) complete
- **Static Information Section**:
  - Bot capabilities overview with feature highlights
  - Getting started guide with example commands
  - Quick help section with common questions and answers
  - Version information and last updated timestamp
- **User Profile Section** (from cache only):
  - User display name, role/department, and team information
  - Current competency level and last analysis date
  - Recent activity summary (last 7 days) with activity count
  - Progress indicators and completion streaks

#### **32b. Interactive Features**
- **Quick Action Buttons**:
  - "Analyze Recent Work" → Triggers batch analysis workflow
  - "Get Career Advice" → Opens guided career planning conversation
  - "View My Progress" → Displays competency trends and growth
  - "Help & Support" → Opens comprehensive help system
- **Smart Recommendations**:
  - Personalized tips based on user activity patterns
  - Suggested competency areas for development
  - Upcoming review reminders and development goals
  - Context-aware next steps based on recent interactions

#### **32c. Performance and Reliability**
- **Ultra-Fast Loading (Sub-200ms Target)**:
  - Pre-render static content at application startup
  - Use only cached data from Redis (no database queries during render)
  - Implement progressive loading for dynamic content
  - Set up CDN-style caching for static assets and images
- **Graceful Degradation**:
  - Display bot information and getting started guide when cache unavailable
  - Show generic recommendations when user data is missing
  - Implement retry logic for failed cache reads with exponential backoff
  - Provide clear error messages with actionable recovery steps

#### **32d. Home Tab State Management**
- **USE REDIS CACHE**: Build on cache infrastructure from Task 7
- **Cache-First Architecture**:
  - Never query database during Home Tab rendering
  - Use background workers to populate cache from user activities
  - Implement cache warming for active users
  - Set up cache invalidation on user data updates

### 33. Home Tab cache management (Expanded)
- **REQUIRES**: Task 32 (Home Tab) and Task 8 (Redis events) complete

#### **33a. Cache Architecture and Data Models**
- **Cache Key Structure**:
  - Design hierarchical cache keys: `home_tab:{team_id}:{user_id}:{version}`
  - Implement user profile cache: `user_profile:{user_id}:{last_updated}`
  - Create activity summary cache: `activity_summary:{user_id}:{date_range}`
  - Set up recommendations cache: `recommendations:{user_id}:{context}`
- **Cache Data Schema**:
  - Define Pydantic models for Home Tab data structures
  - Create versioned cache schemas for backward compatibility
  - Implement cache validation and data integrity checks
  - Set up cache serialization with JSON and compression

#### **33b. Redis Event-Driven Cache Updates**
- **REDIS PUB/SUB INTEGRATION**: Subscribe to Redis events from Task 8:
  - Channel: `user.activity.completed` → Update activity counters and recent work
  - Channel: `user.analysis.completed` → Refresh last analysis date and recommendations
  - Channel: `user.competency.updated` → Update competency levels and progress indicators
  - Channel: `user.report.generated` → Add latest report information to profile
- **Cache Update Strategies**:
  - Implement write-through caching for immediate consistency
  - Set up background cache refresh for expensive computations
  - Create cache warming for frequently accessed user data
  - Implement cache invalidation patterns for stale data removal
    - user.report.generated → Update report count
    - user.profile.updated → Refresh user info
  - Implement event handlers with error recovery
  - Create event-to-cache mapping configuration
  - Set up event replay for cache reconstruction
- **33c. Background Cache Workers**:
  - Deploy cache refresh workers (3 instances)
  - Implement debouncing (max 1 update per 5 min per user)
  - Create priority queuing (active users first)
  - Set up batch cache warming during low-traffic periods
  - Build worker health monitoring
- **33d. Cache Performance Optimization**:
  - Implement cache preloading for frequent users
  - Create cache hit rate monitoring (target: >95%)
  - Set up cache miss analysis and optimization
  - Build cache size management with LRU eviction
  - Implement cache performance dashboards
- **INTEGRATION FLOW**: User Activity → Redis Pub/Sub Event (Task 8) → Cache Worker → Redis Update → Home Tab Load (<200ms)

### 34. User experience testing
- **REQUIRES**: Tasks 30-33 (complete UX system) complete
- Create user journey testing for conversation flows
- Implement Home Tab performance testing and validation
- Set up user onboarding effectiveness testing
- Create accessibility testing and validation
- Implement user engagement tracking and analytics testing
- Set up A/B testing framework for UX improvements

---

## Phase 8: Advanced Features and Reporting (Days 47-53)

### 35. PDF report system implementation

#### **35a. PDF Report Engine and Template Management**
- **REQUIRES**: Phase 7 (user experience) complete
- **PDF Generation Engine**:
  - Implement PDF generation using WeasyPrint or ReportLab for high-quality output
  - Set up HTML-to-PDF conversion pipeline with CSS styling support
  - Create PDF optimization for file size and loading performance
  - Implement asynchronous PDF generation to avoid blocking user interactions
- **Template Architecture**:
  - Create structured template directory: `templates/reports/{template_type}/{version}/`
  - Support multiple template types: competency reports, career development plans, team analysis, executive summaries
  - Implement Jinja2 template engine for dynamic content insertion
  - Set up template inheritance for consistent branding and layout

#### **35b. Report Data Aggregation and Processing**
- **Competency Report Data Pipeline**:
  - Aggregate user activities from TimescaleDB within specified date ranges
  - Calculate competency scores using weighted algorithms from Task 24a
  - Generate competency trend analysis with period-over-period comparisons
  - Extract key achievements, skills demonstrated, and areas for improvement
- **Career Development Report Data**:
  - Analyze skill gap analysis against target roles and competency levels
  - Generate personalized development recommendations based on user history
  - Create career progression timeline with milestones and achievements
  - Calculate competency growth rates and predictive career trajectory

#### **35c. Template Variables and Content Generation**
- **Dynamic Content Variables**:
  - User profile variables: `{{user.name}}`, `{{user.role}}`, `{{user.department}}`
  - Competency data: `{{competencies.current_level}}`, `{{competencies.growth_rate}}`
  - Time-based data: `{{period.start_date}}`, `{{period.activities_count}}`
  - Analysis results: `{{analysis.top_skills}}`, `{{analysis.recommendations}}`
- **Content Intelligence**:
  - Use Advisor Agent (gpt-4o) to generate executive summaries and insights
  - Create contextual recommendations based on competency analysis
  - Generate action items and development goals personalized to user
  - Implement content optimization for different audience levels (individual, manager, executive)

#### **35d. Report Customization and Branding**
- **Organization Branding Support**:
  - Allow custom logos, colors, fonts, and styling per organization
  - Implement CSS-based theming system for consistent branding
  - Support for multiple organization templates in multi-tenant deployments
  - Create brand asset management with secure file storage
- **Template Versioning and Management**:
  - Implement semantic versioning for templates (v1.0.0, v1.1.0)
  - Support hot-swapping of templates without system restart
  - Create template validation pipeline to ensure required variables exist
  - Implement rollback capabilities for template deployment failures

#### **35e. Report Generation Workflow and Delivery**
- **Report Generation Process**:
  - Implement user-triggered report generation via Slack commands
  - Support scheduled report generation via Temporal cron workflows
  - Create batch report generation for multiple users or teams
  - Set up progress tracking and user notifications during generation
- **Report Delivery and Access**:
  - Deliver PDF reports as Slack attachments with file preview
  - Implement secure report storage with expiration policies (90 days default)
  - Create report sharing capabilities with permission controls
  - Set up report download tracking and access logging for audit
- **Performance and Scalability**:
  - Implement report generation queue to handle concurrent requests
  - Set up PDF caching for identical report parameters (24-hour TTL)
  - Create report generation rate limiting (5 reports per user per day)
  - Monitor report generation performance and optimize for sub-30s generation time

### 36. Date range and period management for reports

#### **36a. Flexible Date Range Parsing and Processing**
- **REQUIRES**: Task 35 (report system) complete
- **Natural Language Date Processing**:
  - Support relative formats: "last 30 days", "this quarter", "last month", "year-to-date"
  - Handle absolute formats: "2024-01-01 to 2024-03-31", "January 2024", "Q1 2024"  
  - Parse conversational date expressions: "since January", "last quarter", "past 6 months"
  - Implement date range validation with clear error messages for invalid ranges
- **Intelligent Date Defaults**:
  - Competency reports: Default to last 90 days for comprehensive analysis
  - Career development plans: Default to last year for trend visibility
  - Executive summaries: Default to current quarter for business alignment
  - Team analysis: Default to last 6 months for meaningful team insights

#### **36b. Timezone and User Preference Management**
- **Timezone Handling**:
  - Use user's Slack timezone for all date calculations and displays
  - Handle timezone conversions for multi-timezone team reports
  - Display clear timezone information in report headers and summaries
  - Support daylight saving time transitions accurately
- **User Preference Storage**:
  - Remember user's preferred date ranges per report type in Redis cache
  - Store frequently used custom date ranges for quick selection
  - Implement preference inheritance (team defaults → organization defaults)
  - Allow users to reset preferences to system defaults

#### **36c. Assessment Period Configuration**
- **Organizational Assessment Cycles**:
  - Support configurable assessment periods: quarterly, semi-annual, annual, custom
  - Allow custom period boundaries aligned with fiscal/review calendars  
  - Enable multiple overlapping periods for different organizational units
  - Provide assessment period templates for common organizational patterns
- **Period Progress and Notifications**:
  - Show progress within current assessment periods with time remaining
  - Generate reminders for upcoming assessment period deadlines
  - Create assessment period transition handling with historical context
  - Support period-based report scheduling and automation

#### **36d. Period Comparison and Trend Analysis**  
- **Comparative Analytics**:
  - Implement period-over-period comparisons (current vs previous quarter)
  - Support year-over-year analysis for annual competency reviews
  - Create rolling period comparisons for trend identification
  - Generate comparative insights highlighting growth and regression areas
- **Data Availability and Validation**:
  - Warn users when requested periods have insufficient data for analysis
  - Provide data availability indicators for different time ranges
  - Suggest alternative date ranges when data is sparse
  - Handle incomplete periods gracefully with partial data indicators

### 37. Batch processing and scheduled operations
- **REQUIRES**: Tasks 35, 36 (reporting system) complete
- Implement Daily Batch Agents for activity aggregation and competency updates
- Create Weekly Report Agents for automated report generation and distribution
- Build Data Cleanup Agents for archiving and database optimization
- **USE TEMPORAL**: Set up Temporal.io cron workflows from Task 16
- Implement configurable batch processing with parallel execution
- Create batch operation monitoring and failure recovery

### 38. Slack notification and alert system (Expanded - Gap #11)
- **REQUIRES**: Tasks 25-28 (Slack integration) and Task 16 (Temporal workflows) complete
- **38a. Core Slack Notification Infrastructure**:
  - **Notification Event System**:
    ```python
    class SlackNotificationEvent:
        event_id: str
        user_id: str
        notification_type: str  # "workflow_progress", "analysis_complete", "error", "reminder"
        priority: str  # "high", "medium", "low"
        channel_context: str  # "thread", "dm", "channel"
        thread_ts: Optional[str]
        message_data: dict
        scheduled_for: Optional[datetime]
        retry_count: int = 0
        created_at: datetime
    ```
  - **Notification Queue Management**:
    - Use Redis pub/sub for real-time notification delivery
    - Implement priority queuing: high (immediate), medium (5s delay), low (30s delay)
    - Set up notification deduplication to prevent spam
    - Create notification batching for bulk updates
  - **Notification Templates**:
    ```python
    NOTIFICATION_TEMPLATES = {
        "workflow_started": {
            "emoji": "🔄",
            "title": "Analysis Started",
            "message": "I'm analyzing your {activity_type} now..."
        },
        "analysis_progress": {
            "emoji": "⏳", 
            "title": "Analysis in Progress",
            "message": "Processing step {current_step} of {total_steps}..."
        },
        "analysis_complete": {
            "emoji": "✅",
            "title": "Analysis Complete",
            "message": "Your competency analysis is ready!"
        },
        "error_occurred": {
            "emoji": "❌",
            "title": "Processing Error", 
            "message": "I encountered an issue: {error_summary}"
        },
        "follow_up_reminder": {
            "emoji": "💡",
            "title": "Follow-up Available",
            "message": "Ready for next steps on your {analysis_type}?"
        }
    }
    ```
- **38b. Thread-Based Notification Management**:
  - **Thread Context Tracking**:
    ```python
    class ThreadNotificationManager:
        async def send_thread_notification(self, thread_id: str, notification: SlackNotificationEvent):
            """Send notification within existing conversation thread"""
            
            # Get thread context for appropriate messaging
            thread_context = await self.get_thread_context(thread_id)
            
            # Format notification for thread context
            blocks = self.format_thread_notification(
                notification=notification,
                context=thread_context,
                show_progress=True
            )
            
            # Send as threaded reply
            return await slack_client.post_message(
                channel=thread_context.channel_id,
                thread_ts=thread_id,
                blocks=blocks,
                unfurl_links=False
            )
    ```
  - **Progress Notifications in Threads**:
    - Real-time workflow progress updates using message updates API
    - Step-by-step analysis progress with estimated completion time
    - Interactive progress bars using Block Kit components
    - Contextual next-step recommendations when workflow completes
  - **Thread State Management**:
    - Track notification state per thread to avoid duplicates
    - Update existing progress messages instead of creating new ones
    - Handle thread expiration and cleanup of old notifications
- **38c. Direct Message Notification System**:
  - **Proactive DM Notifications**:
    ```python
    class DMNotificationService:
        async def send_proactive_dm(self, user_id: str, notification_type: str, data: dict):
            """Send proactive direct message notifications"""
            
            # Check user DM preferences
            user_prefs = await self.get_user_notification_preferences(user_id)
            
            if not user_prefs.allow_proactive_dms:
                return self.queue_for_next_interaction(user_id, notification_type, data)
            
            # Format DM notification
            blocks = self.format_dm_notification(
                notification_type=notification_type,
                data=data,
                user_preferences=user_prefs
            )
            
            return await slack_client.post_dm(
                user_id=user_id,
                blocks=blocks
            )
    ```
  - **DM Notification Triggers**:
    - Daily competency score updates (configurable time)
    - Weekly progress summaries with trend analysis
    - Milestone achievements and goal completions
    - Deadline reminders for development actions
    - System alerts for account or data issues
  - **User Preference Management**:
    ```python
    class UserNotificationPreferences:
        user_id: str
        allow_proactive_dms: bool = True
        preferred_dm_time: time = time(9, 0)  # 9 AM local time
        frequency_limits: dict = {
            "daily_updates": 1,
            "weekly_summaries": 1, 
            "milestone_alerts": 5,
            "error_notifications": 3
        }
        quiet_hours: Tuple[time, time] = (time(18, 0), time(8, 0))  # 6 PM to 8 AM
        timezone: str = "UTC"
    ```
- **38d. Interactive Notification Components**:
  - **Action-Rich Notifications**:
    ```python
    def build_interactive_notification(self, notification: SlackNotificationEvent) -> List[dict]:
        """Build interactive notification with action buttons"""
        
        base_blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{notification.emoji} *{notification.title}*\n{notification.message}"
                }
            }
        ]
        
        # Add contextual action buttons based on notification type
        if notification.notification_type == "analysis_complete":
            base_blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "View Full Report"},
                        "style": "primary",
                        "action_id": "view_full_report",
                        "value": notification.message_data.get("report_id")
                    },
                    {
                        "type": "button", 
                        "text": {"type": "plain_text", "text": "Get PDF"},
                        "action_id": "generate_pdf_report",
                        "value": notification.user_id
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Ask Questions"},
                        "action_id": "start_follow_up",
                        "value": notification.message_data.get("analysis_id")
                    }
                ]
            })
        
        return base_blocks
    ```
  - **Notification Action Handlers**:
    - Quick action buttons for common responses
    - Inline feedback collection for notification quality
    - Smart follow-up suggestions based on user behavior
    - Dismissal options with feedback capture
  - **Interactive Progress Components**:
    - Live updating progress bars with workflow stages
    - Clickable workflow stages for detailed status
    - Cancel/pause options for long-running operations
- **38e. Alert and Error Notification System**:
  - **Error Classification and Routing**:
    ```python
    class ErrorNotificationRouter:
        def route_error_notification(self, error: SystemError, context: dict) -> NotificationPlan:
            """Route error notifications based on severity and context"""
            
            if error.severity == "critical":
                return NotificationPlan(
                    channels=["user_dm", "admin_channel"],
                    priority="high",
                    retry_policy="immediate",
                    escalation_timer=300  # 5 minutes
                )
            elif error.severity == "warning":
                return NotificationPlan(
                    channels=["thread_reply"],
                    priority="medium", 
                    retry_policy="standard",
                    include_recovery_actions=True
                )
            else:  # informational
                return NotificationPlan(
                    channels=["thread_reply"],
                    priority="low",
                    batch_with_similar=True
                )
    ```
  - **System Alert Types**:
    - Workflow failures with recovery suggestions
    - LLM rate limit warnings with delay estimates
    - Data processing errors with retry options
    - Integration failures with fallback recommendations
    - Performance degradation alerts
  - **User-Friendly Error Messages**:
    - Convert technical errors to user-friendly explanations
    - Provide actionable next steps for error resolution
    - Include estimated resolution time when available
    - Offer alternative approaches when primary method fails
- **38f. Notification Analytics and Monitoring**:
  - **Notification Metrics Collection**:
    ```python
    class NotificationMetrics:
        def track_notification_delivery(self, notification: SlackNotificationEvent, result: DeliveryResult):
            """Track notification delivery success and user engagement"""
            
            metrics = {
                "notification_type": notification.notification_type,
                "delivery_channel": notification.channel_context,
                "delivery_status": result.status,
                "delivery_latency_ms": result.delivery_time_ms,
                "user_interaction": result.user_clicked,
                "user_dismissed": result.user_dismissed
            }
            
            self.prometheus_client.increment("slack_notifications_sent", metrics)
            if result.user_clicked:
                self.prometheus_client.increment("slack_notifications_engaged", metrics)
    ```
  - **Delivery Success Tracking**:
    - Monitor notification delivery rates per type
    - Track user engagement with interactive notifications
    - Measure notification-to-action conversion rates
    - Identify optimal notification timing patterns
  - **User Experience Monitoring**:
    - Track notification frequency per user to prevent spam
    - Monitor user feedback on notification quality
    - Measure response time improvements from notifications
    - Analyze notification abandonment patterns
- **38g. Smart Notification Scheduling**:
  - **Intelligent Timing**:
    ```python
    class SmartNotificationScheduler:
        async def schedule_optimal_notification(self, user_id: str, notification: SlackNotificationEvent):
            """Schedule notification for optimal user engagement"""
            
            # Get user's historical engagement patterns
            engagement_patterns = await self.get_user_engagement_patterns(user_id)
            
            # Determine optimal delivery time
            if notification.priority == "high":
                # Send immediately for high priority
                return await self.send_immediate_notification(notification)
            
            # Schedule for optimal engagement time
            optimal_time = self.calculate_optimal_delivery_time(
                user_patterns=engagement_patterns,
                notification_type=notification.notification_type,
                current_time=datetime.now()
            )
            
            return await self.schedule_notification(notification, optimal_time)
    ```
  - **Batch Notification Management**:
    - Group similar notifications to reduce noise
    - Smart digest creation for multiple updates
    - Respect user quiet hours and preferences
    - Adaptive scheduling based on user responsiveness
- **38h. Integration with Temporal Workflows**:
  - **Workflow-Driven Notifications**:
    ```python
    # Integration with existing Temporal workflows from Task 16
    
    @activity.defn
    async def send_workflow_notification(notification_request: WorkflowNotificationRequest):
        """Send notification as part of Temporal workflow"""
        
        notification_service = SlackNotificationService()
        
        notification = SlackNotificationEvent(
            event_id=workflow.uuid4(),
            user_id=notification_request.user_id,
            notification_type=notification_request.type,
            priority=notification_request.priority,
            channel_context=notification_request.context,
            thread_ts=notification_request.thread_id,
            message_data=notification_request.data
        )
        
        return await notification_service.send_notification(notification)
    ```
  - **Workflow Progress Notifications**:
    - Integrate notification sending into existing workflow activities
    - Update progress notifications as workflows advance
    - Send completion notifications with results
    - Handle workflow failure notifications with recovery options
- **USE STRUCTLOG**: All notification operations logged with notification_id, user_id, channel_type, delivery_status

### 39. Advanced features testing
- **REQUIRES**: Tasks 35-38 (complete advanced features) complete
- Create comprehensive reporting system testing
- Implement batch processing and scheduled operations testing
- Set up notification and delivery system testing
- Create performance testing for report generation
- Implement data integrity testing for batch operations
- Set up end-to-end workflow testing

---

## Phase 9: Performance and Scaling (Days 54-59)

### 39.6. Performance Baseline Establishment (NEW)
- **REQUIRES**: All core components operational
- **39.6a. Baseline Metrics Collection**:
  - Current system performance (if accessible)
  - Industry benchmarks for similar systems
  - Expected performance targets from requirements
  - Create performance test scenarios
  - Document baseline measurements
- **39.6b. Performance Test Suite**:
  - Load tests: 1, 10, 50, 100, 200 concurrent users
  - Stress tests: Find breaking points
  - Soak tests: 24-hour sustained load
  - Spike tests: Sudden traffic increases
  - Volume tests: Large data processing
- **39.6c. Key Performance Indicators**:
  - Response times: P50, P95, P99
  - Throughput: Requests per second
  - Error rates: By error type
  - Resource utilization: CPU, memory, network
  - Business metrics: User actions per minute
- **39.6d. Performance Regression Detection**:
  - Automated performance tests in CI/CD
  - Performance budget enforcement
  - Regression alerting thresholds
  - Performance trend analysis
  - Root cause analysis tools

### 40. Database performance optimization
- **REQUIRES**: All previous phases using database complete
- Optimize TimescaleDB queries with advanced indexing strategies
- Enhance PgBouncer configuration for optimal connection pooling
- Set up comprehensive database query optimization and performance tuning
- Create database performance monitoring and automated optimization
- Implement database sharding and read replicas for horizontal scaling
- Set up database backup optimization and disaster recovery

### 41. Application performance tuning
- **REQUIRES**: Complete application stack from previous phases
- Implement Pydantic V2 optimizations for faster serialization
- Set up Redis Stack optimizations for caching performance
- Optimize LLM token usage with compression and intelligent prompting
- Create comprehensive performance benchmarking and regression testing
- Implement application-level caching strategies and monitoring
- Set up performance profiling and bottleneck identification

### 42. Auto-scaling and resource management
- **REQUIRES**: Tasks 40, 41 (performance optimization) complete
- Implement intelligent auto-scaling based on queue depth and utilization
- Create predictive scaling using historical usage patterns
- Set up resource limits and cost control mechanisms with budget alerting
- Implement horizontal scaling for Temporal workers and agent capacity
- Create scaling policies with configurable parameters and cooldown periods
- Set up capacity planning and resource optimization recommendations

### 43. Performance testing and validation
- **REQUIRES**: Tasks 40-42 (complete performance system) complete
- Implement comprehensive load testing for 100+ concurrent users
- Create performance benchmarking for all critical system components
- Set up database performance testing with realistic time-series data
- Validate auto-scaling effectiveness and resource utilization
- Create continuous performance monitoring and regression detection
- Test system capacity under realistic production conditions

---

## Phase 9.4: Contract Testing & API Standards (Days 53-54)

### 39.4. Contract Testing Framework (NEW)
- **REQUIRES**: Phase 9 complete
- **39.4a. API Contract Definition**:
  - Define OpenAPI schemas for all endpoints
  - Create AsyncAPI schemas for event contracts
  - Implement JSON Schema for data models
  - Set up schema versioning strategy
  - Build backward compatibility checks
- **39.4b. Contract Testing Setup**:
  - Implement Pact for consumer-driven contracts
  - Create provider verification tests
  - Set up contract publishing to Pact Broker
  - Implement breaking change detection
  - Build contract compatibility matrix
- **39.4c. Integration Contract Tests**:
  - Agent-to-Tool contracts
  - Workflow-to-Agent contracts
  - Service-to-Database contracts
  - Event publisher-subscriber contracts
  - External API contracts
- **39.4d. Contract Monitoring**:
  - Runtime contract validation
  - Contract drift detection
  - Version compatibility tracking
  - Consumer usage analytics
  - Deprecation timeline management

---

## Phase 9.5: API Management Layer (Days 54-56)

### 39.5. API Gateway and Management (NEW)
- **REQUIRES**: Phase 9 (performance optimization) complete
- **39.5a. API Gateway Setup**:
  - Deploy Kong/Envoy as API gateway with basic service discovery (defer Consul Connect until service mesh phase)
  - Configure request routing and load balancing
  - Implement request/response transformation
  - Set up API versioning strategy (path-based: /v1/, /v2/)
  - Create API deprecation workflows
- **39.5b. Rate Limiting & Throttling**:
  - Implement tiered rate limits (free: 100/hr, pro: 1000/hr, enterprise: unlimited)
  - Create per-endpoint rate limiting configuration
  - Set up distributed rate limiting using Redis
  - Implement adaptive throttling based on system load
  - Build rate limit headers (X-RateLimit-Limit, X-RateLimit-Remaining)
- **39.5c. API Authentication & Authorization**:
  - Implement multiple auth methods (OAuth2, API keys, JWT)
  - Create API key management system with rotation
  - Set up scope-based authorization (read, write, admin)
  - Implement API key analytics and usage tracking
  - Build developer portal for API key self-service
- **39.5d. API Documentation & Discovery**:
  - Generate OpenAPI 3.0 specifications automatically
  - Create interactive API documentation (Swagger UI)
  - Implement API change detection and notifications
  - Set up API mocking for development
  - Build SDK generation for Python, TypeScript, Go
- **39.5e. API Monitoring & Analytics**:
  - Track API metrics (requests, latency, errors by endpoint)
  - Create API usage dashboards per client
  - Implement API cost attribution and billing
  - Set up API performance SLAs and alerting
  - **INTEGRATION**: Connects to all service endpoints via basic DNS/load balancer (upgrade to Consul when service mesh is implemented)

---

## Phase 10: Security Hardening (Days 60-65)

### 44. Advanced security implementation

#### **44a. Authentication and Authorization Framework**
- **REQUIRES**: Complete application stack from previous phases
- **OAuth2 + JWT Implementation**:
  - Implement OAuth2 flow with Slack as primary identity provider
  - Create JWT token generation, validation, and refresh mechanisms
  - Set up user session management with Redis for secure session storage
  - Implement role-based access control (RBAC) with user permissions
- **API Security**:
  - Add request signature verification for Slack events (HTTP mode)
  - Implement API rate limiting and throttling per user/organization
  - Create API key management for internal service authentication
  - Set up CORS policies and security headers (HSTS, CSP, X-Frame-Options)

#### **44b. Comprehensive Audit Trail Implementation**
- **EXTEND DOPPLER**: Enhance Doppler secret management from Task 3
- **Audit Logging Framework**:
  - Create structured audit event schema with user, action, resource, timestamp
  - Implement audit event generation for all user actions and system changes
  - Set up audit log storage in separate audit database (PostgreSQL)
  - Create audit log retention policies (7 years for compliance)
- **Security Event Tracking**:
  - Track authentication attempts, authorization failures, data access
  - Log all LLM interactions with user context and content classification
  - Monitor admin actions, configuration changes, and privilege escalations
  - Implement real-time security event correlation and alerting

#### **44c. Data Encryption and Protection**
- **Encryption at Rest**:
  - Enable PostgreSQL transparent data encryption (TDE) for all databases
  - Implement Redis encryption with TLS for cache and session data
  - Encrypt audit logs and backup files with AES-256
  - Set up encrypted file storage for PDF reports and documents
- **Encryption in Transit**:
  - Enforce TLS 1.3 for all HTTP communications (Slack, LLM APIs)
  - Implement certificate management with automatic renewal
  - Set up mutual TLS (mTLS) for internal service communication preparation
  - Secure WebSocket connections for Slack Socket Mode with TLS

#### **44d. Security Monitoring and Incident Response**
- **Security Monitoring**:
  - Implement security event monitoring with Prometheus metrics
  - Create security dashboards in Grafana for threat detection
  - Set up automated security alerting for suspicious activities
  - Monitor for LLM prompt injection attempts and data exfiltration
- **Incident Response**:
  - Create automated security incident response procedures
  - Implement security event escalation and notification workflows
  - Set up automated account lockout for repeated authentication failures
  - Create security incident documentation and post-mortem procedures

### 45. ~~Service mesh implementation~~ (DEFERRED TO FUTURE PHASE)
- **STATUS**: Deferred until multi-service architecture justifies complexity
- **RATIONALE**: Single service deployment doesn't require service mesh overhead
- **CURRENT APPROACH**: Direct HTTP calls with simple load balancing
- **UPGRADE TRIGGERS**: 
  - Service count >4 with complex inter-service communication
  - Security requirements mandate mTLS for all internal communication
  - Traffic management needs (canary, blue-green) become business critical
  - Service discovery complexity exceeds simple DNS/load balancer capabilities
- **TEMPORARY IMPLEMENTATION**:
  - Use direct service calls with httpx client and connection pooling
  - Implement basic circuit breakers at application level if needed
  - Use simple health check endpoints (/health) for load balancer integration
  - **INTEGRATION**: Leverage existing Consul from Task 3c for basic service discovery when needed
- **MIGRATION PATH**: Can easily add Consul Connect later without architectural changes

### 46. Data protection and privacy

#### **46a. GDPR and Privacy Compliance Framework**
- **REQUIRES**: Task 44 (security foundation) complete
- **Data Subject Rights Implementation**:
  - Create data export functionality for user data portability (GDPR Article 20)
  - Implement data deletion procedures for "right to be forgotten" (GDPR Article 17)
  - Set up data access requests for transparency (GDPR Article 15)
  - Create data rectification procedures for accuracy (GDPR Article 16)
- **Privacy by Design**:
  - Implement data minimization principles in all data collection
  - Set up consent management for data processing activities
  - Create privacy notice generation and user consent tracking
  - Implement privacy impact assessment (PIA) procedures

#### **46b. Data Classification and Protection**
- **EXTEND PII REDACTION**: Build on logging foundation from Task 2
- **Sensitive Data Detection**:
  - Implement automated PII detection in user inputs and LLM responses
  - Set up data classification levels (Public, Internal, Confidential, Restricted)
  - Create content scanning for sensitive information in competency data
  - Implement automated redaction of sensitive data in logs and outputs
- **Data Loss Prevention (DLP)**:
  - Set up DLP rules for sensitive data in LLM inputs and outputs
  - Monitor for data exfiltration attempts through unusual access patterns
  - Implement data access controls based on user roles and data classification
  - Create alerts for bulk data access or unusual download patterns

#### **46c. Data Retention and Lifecycle Management**
- **Automated Data Retention**:
  - Create retention policies for user activities (5 years), audit logs (7 years)
  - Set up automated data archival for inactive users after 2 years
  - Implement secure data deletion for expired retention periods
  - Create data backup and recovery procedures with encryption
- **Data Anonymization and Pseudonymization**:
  - Set up data anonymization pipelines for analytics and testing
  - Implement pseudonymization for user identifiers in analytics
  - Create synthetic data generation for development and testing
  - Set up data masking for non-production environments

### 47. Security testing and validation
- **REQUIRES**: Tasks 44-46 (complete security system) complete
- Implement automated security testing with Bandit and Safety integration
- **EXTEND GARAK**: Build on LLM security testing from Task 14
- Create authentication and authorization testing for all access controls
- Implement data protection testing for encryption and privacy compliance
- Set up penetration testing and security audit procedures
- Create compliance testing for GDPR and data protection regulations

---

## Phase 11: Production Deployment (Days 66-70)

### 48. Containerization and orchestration
- **REQUIRES**: Complete application stack ready for deployment
- Create optimized multi-stage Docker images with security scanning
- Set up comprehensive Kubernetes manifests with Helm charts
- Implement GitOps with ArgoCD for automated continuous deployment
- Create deployment scripts, health checks, and validation procedures
- **DIRECT SERVICE COMMUNICATION**: Deploy with basic health checks and direct HTTP service calls
- Set up Infrastructure as Code with Terraform for cloud resources

### 49. CI/CD pipeline implementation
- **REQUIRES**: Task 48 (containerization) complete
- Create comprehensive GitHub Actions pipeline with quality gates
- Implement automated testing pipeline with unit, integration, security tests
- Set up automated deployment pipeline with staging and production environments
- Create automated rollback procedures and deployment validation
- Implement code quality gates with coverage requirements
- Set up automated performance testing and regression detection

### 50. Production monitoring and alerting
- **REQUIRES**: Tasks 48, 49 (deployment infrastructure) complete
- **EXTEND OBSERVABILITY**: Build on foundation from Tasks 2, 9
- Define SLIs, SLOs, and error budgets for production systems
- Implement Grafana alerting with actionable thresholds and on-call routing
- Set up burn-rate dashboards and weekly review workflows
- Configure observability retention policies and cost controls
- Create production runbooks and incident response procedures

### 51. Production readiness validation
- **REQUIRES**: Tasks 48-50 (complete production system) complete
- Complete comprehensive system integration testing
- Validate all security requirements and compliance standards
- Test disaster recovery and business continuity procedures
- Conduct final performance validation under production load
- Validate all monitoring, alerting, and incident response procedures
- Create production deployment checklist and sign-off procedures

---

## Phase 12: Data Migration and Go-Live (Days 71-75)

### 52. Data migration preparation
- **REQUIRES**: Phase 11 (production deployment) complete
- **DATA ONLY**: Extract data from existing system (NO CODE MIGRATION)
- Create data transformation scripts for new schema structure
- Set up data validation and integrity checking procedures
- Create migration rollback procedures and data recovery mechanisms
- Test data migration in staging environment with production data copy
- **USE STRUCTLOG**: All migration operations use established logging

### 53. Configuration migration
- **REQUIRES**: Task 52 (data migration prep) complete
- **CONFIG ONLY**: Transfer environment variables to new Doppler-based system
- **RECREATE OAUTH2**: Set up fresh OAuth2 integration (no token preservation)
- **RECREATE TEMPLATES**: Build new templates from scratch
- Migrate user preferences and system settings to new format
- Validate configuration completeness and correctness
- Test configuration in staging environment

### 54. Production data migration
- **REQUIRES**: Tasks 52, 53 (migration preparation) complete
- Execute production data migration with zero-downtime procedures
- Validate data integrity and completeness in production
- Test all business processes with migrated data
- Validate user authentication and authorization with new system
- Monitor system performance with production data load
- Create post-migration validation reports

### 55. System validation and acceptance
- **REQUIRES**: Task 54 (production migration) complete
- **VALIDATE NEW SYSTEM**: Test that new system provides same business functionality
- Validate Socket Mode and HTTP Mode compatibility
- Verify performance improvements meet targets (3-5x faster)
- Conduct comprehensive user acceptance testing
- Validate all user journeys and business processes
- Create system acceptance documentation and sign-off

---

## Phase 13: Documentation and Knowledge Transfer (Days 76-80)

### 56. Technical documentation
- **REQUIRES**: Complete system implementation and validation
- Create comprehensive API documentation with examples and schemas
- Write detailed deployment and operations guides for all environments
- Document multi-agent system configuration and troubleshooting procedures
- Create monitoring and alerting setup guides with dashboard configurations
- Write disaster recovery and business continuity documentation
- Create architecture decision records and technical debt documentation

### 57. Operational documentation
- **REQUIRES**: Task 56 (technical documentation) complete
- Write user guides and training materials for system administrators
- Create troubleshooting guides and common issue resolution procedures
- Document maintenance procedures and update processes
- Create support procedures and escalation paths
- Write performance optimization guides and capacity planning procedures
- Create security incident response and compliance procedures

### 58. Knowledge transfer and training
- **REQUIRES**: Tasks 56, 57 (complete documentation) complete
- Prepare developer onboarding and training materials
- Create system architecture presentations and walkthroughs
- Set up hands-on training sessions for operations team
- Create video tutorials and interactive documentation
- Establish mentoring and support procedures for new team members
- Document future enhancement opportunities and roadmap

### 59. Final validation and handover
- **REQUIRES**: Tasks 56-58 (complete documentation and training) complete
- Conduct final system performance validation
- Validate 60-75% LLM cost reduction targets with real usage data
- Confirm 3-5x overall performance improvements with benchmarking
- Complete final security assessment and compliance validation
- Create production support procedures and monitoring validation
- Execute formal system handover and acceptance procedures

---

## 📋 IMPLEMENTATION READINESS CHECKLIST

### **Pre-Implementation Validation**
- [ ] All task dependencies clearly defined
- [ ] Integration points documented
- [ ] Error handling patterns established
- [ ] Testing strategies defined
- [ ] Performance targets specified
- [ ] Security requirements mapped
- [ ] Monitoring metrics defined
- [ ] Data schemas finalized

### **Simplified Phase Completion Gates**
- [ ] Phase 1: Security and configuration operational (Doppler + Consul only)
- [ ] Phase 2: Simplified infrastructure stable (Prometheus + Redis + PostgreSQL)
- [ ] Phase 3: LLM gateway functional with tiered model selection
- [ ] Phase 4: 2-agent system tested (Analysis + Advisor agents)
- [ ] Phase 5: Business logic validated with simplified tools
- [ ] Phase 6: Slack integration working with Redis pub/sub events
- [ ] Phase 7: User experience optimized with basic clarification system
- [ ] Phase 8: Advanced features complete (PDF reports + batch processing)
- [ ] Phase 9: Performance optimized and baseline established
- [ ] Phase 10: Security hardened (no service mesh initially)
- [ ] Phase 11: Production deployed with direct service communication
- [ ] Phase 12: Data migrated and system validated

### **Deferred Complexity (Add When Justified)**
- [ ] Service mesh implementation (when >4 services)
- [ ] Full distributed tracing (when >3 services)
- [ ] 4-agent specialization (when >500 requests/day)
- [ ] NATS JetStream (when >1000 events/hour)
- [ ] Complex observability stack (when operational needs demand)

---

## 🎯 SUCCESS CRITERIA

### **Technical Validation**
- ✅ 3-5x performance improvement validated
- ✅ 60-75% LLM cost reduction achieved
- ✅ Sub-200ms Home Tab load times
- ✅ 100+ concurrent user capacity
- ✅ 99.9% uptime target met

### **Implementation Quality**
- ✅ Zero code migration (data only)
- ✅ Consistent Structlog usage throughout
- ✅ Security-first architecture validated
- ✅ Complete test coverage achieved
- ✅ Production monitoring operational

### **Business Continuity**
- ✅ All existing functionality preserved
- ✅ User experience maintained/improved
- ✅ Data integrity validated
- ✅ Compliance requirements met
- ✅ Team knowledge transfer complete

---

## 🔗 CRITICAL INTEGRATION POINTS

### **Simplified Event Flow Integration**
```
Slack Event → Task 26 (Deduplication) → Task 8e (Redis Dedup) → Task 8 (Redis Pub/Sub) 
→ Task 21 (Intent Classification) → Task 16f (Workflow Router) → Task 16 (Temporal)
→ Task 17 (2 Simplified Agents) → Task 20 (Tools) → Response Generation → Slack
```

### **Configuration Flow**
```
Environment Variables → Task 3b (Doppler) → Task 3c (Consul)
→ Application Startup → Hot Reload via Consul Watch
(Vault removed for simplicity)
```

### **Cache Update Flow**
```
User Activity → Task 8 (Redis Pub/Sub Event) → Task 33b (Cache Worker) 
→ Task 7 (Redis Cache) → Task 33 (Home Tab Cache) → <200ms Load Time
```

### **Simplified Multi-Agent Orchestration Flow**
```
Request → Task 16f (Router) → Task 16b (Simple Workflow Selection)
→ Task 16a (Temporal) → Task 17 (Analysis + Advisor Agents) → Task 20 (Tool Execution)
→ Task 24 (Business Logic) → Direct Response (No Synthesis Agent) → Slack Response
```

### **Direct Service Communication (No Service Mesh)**
```
Service Startup → Basic Health Checks → Direct HTTP Calls
→ Simple Load Balancer → Service Communication
(Service mesh deferred until multi-service deployment)
```

### **Simplified Observability Integration**
```
Task 2 (Structlog) + Task 9 (Prometheus Direct) → Correlation IDs
→ Task 50 (Grafana) → Basic Dashboards → Slack Alerts
(OpenTelemetry/PagerDuty complexity removed)
```

### **Database Schema Dependencies**
- Task 6 must define schemas used by:
  - Task 17 (Agent data storage)
  - Task 23 (Activity/User/Competency stores)
  - Task 24 (Business logic calculations)
- All database credentials managed by Doppler (Task 3a)

### **Testing Dependencies**
- Task 5 (Test framework) provides foundation for:
  - Task 10 (Infrastructure tests)
  - Task 14 (AI/LLM tests)
  - Task 19 (Agent tests)
  - Task 29 (Slack tests)
  - All use shared factories and mocks
- Test environment configs managed by Doppler branches

### **Critical Version Alignments**
- Pydantic V2 across all services (Tasks 3, 8, 20, 24)
- Structlog correlation IDs propagated everywhere
- Consul Connect for all service communication
- Redis Stack for all caching needs
- Temporal for all workflow orchestration