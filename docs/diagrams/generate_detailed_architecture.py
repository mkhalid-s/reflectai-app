"""
Generate COMPREHENSIVE ReflectAI System Architecture Diagram
with all implementation details, file names, ports, and data flows.

This creates a highly detailed visual architecture showing:
- All 176 Python files organized by layer
- Exact component file names
- Port numbers and protocols
- Redis key patterns
- Database tables (9 + 3 hypertables)
- 8 workflows with 20+ activities
- Complete data flows
"""

from diagrams import Cluster, Diagram, Edge
from diagrams.aws.storage import S3
from diagrams.onprem.client import Users
from diagrams.onprem.compute import Server
from diagrams.onprem.database import PostgreSQL
from diagrams.onprem.inmemory import Redis
from diagrams.onprem.monitoring import Prometheus, Grafana
from diagrams.onprem.network import Nginx
from diagrams.programming.framework import Fastapi
from diagrams.programming.language import Python

# Enhanced diagram attributes for detailed view
graph_attr = {
    "fontsize": "16",
    "bgcolor": "white",
    "pad": "1.0",
    "ranksep": "2.0",
    "nodesep": "1.0",
    "concentrate": "false",
    "compound": "true",
}

node_attr = {
    "fontsize": "10",
    "height": "0.8",
    "width": "2.2",
    "fixedsize": "false",
}

edge_attr = {
    "fontsize": "8",
    "minlen": "1",
}

with Diagram(
    "ReflectAI Platform - Comprehensive System Architecture\nv0.1.2-alpha | 176 Python Files | 5 Architectural Layers",
    filename="reflectai_detailed_architecture",
    outformat="png",
    show=False,
    direction="TB",
    graph_attr=graph_attr,
    node_attr=node_attr,
    edge_attr=edge_attr,
):

    # ========================================================================
    # EXTERNAL INTERFACES LAYER
    # ========================================================================
    with Cluster("🌐 EXTERNAL INTERFACES"):
        slack_users = Users("Slack Users\n(Primary Interface)\n\nSocket Mode\nReal-time Events")
        api_clients = Server("API Clients\nREST/HTTP")
        web_users = Users("Web Users\n(Future)")

    # ========================================================================
    # APPLICATION LAYER - FASTAPI
    # ========================================================================
    with Cluster("📱 APPLICATION LAYER - FastAPI (Async/Await)"):
        with Cluster("HTTP Server"):
            fastapi_main = Fastapi("FastAPI + Uvicorn\n\nPort 3000: Main App\nPort 8080: Prometheus\nPort 8090: Health")

        with Cluster("Interface Adapters (src/interfaces/slack/) - 14 files"):
            slack_socket = Python("socket_handler.py\n\nSocket Mode Handler\nEvent Deduplication\nACK < 3 seconds")

            slack_handlers = Python("handlers.py\n\nSlackEventHandlers\nSlackCommandHandlers\nDedup Integration")

            slack_conv = Python("conversation_manager.py\n\nConversation State\nContext Mgmt\nIntent Routing")

            slack_commands = Python("slash_commands.py\n\n/analyze\n/report\n/summary\n/goal\n/help")

            slack_blocks = Python("block_builder.py\n\nSlack Block Kit\nUI Components\nInteractive Msgs")

        with Cluster("Middleware"):
            auth_mw = Python("auth_middleware.py\nOAuth2\nSession Validation")
            error_mw = Python("error_middleware.py\nError Handling\nCorrelation IDs")
            rate_mw = Python("rate_limiter.py\nRate Limiting\n100/sec global")

    # ========================================================================
    # BUSINESS LOGIC LAYER
    # ========================================================================
    with Cluster("🧠 BUSINESS LOGIC LAYER (src/core/) - 68 files"):

        # Core Engines
        with Cluster("Core Engines"):
            with Cluster("LLM Gateway (src/core/llm/) - 11 files"):
                llm_gateway = Python("gateway.py\n\nMulti-Provider Router\nFailover Logic")
                llm_cost = Python("cost_tracker.py\n\nBudget: $50/day\nAlert: 80%\nSlack Notify")
                llm_cache = Python("cache.py +\nredis_cache_backend.py\n\nDistributed Cache\nTTL: 30m-24h")
                llm_providers = Python("providers.py +\nenterprise_gateway_client.py\n\nEnterpriseGateway (OAuth2)\nOpenAI\nAnthropic")
                llm_optimizer = Python("optimizer.py\n\nModel Selection\nCost Optimization")
                llm_guardrails = Python("guardrails.py\n\nOutput Validation\nSafety Checks")

            with Cluster("Classification (src/core/classification/) - 7 files"):
                intent_analyzer = Python("intent_analyzer.py\n\nIntent Detection\n7 Intent Types\nPattern+LLM")
                activity_classifier = Python("activity_classifier.py\n\n6 Activity Types\nCode Review\nDeployment\nTesting")
                competency_mapper = Python("competency_mapper.py\n\nActivity→Competency\nFramework Loading\nJSON-based")

            with Cluster("Assessment (src/core/assessment/) - 8 files"):
                competency_assessor = Python("competency_assessor.py\n\nMain Engine\nScoring 0-5\nEvidence Level")
                gap_analyzer = Python("gap_analyzer.py\n\n1040+ lines\nPromotion Ready\n4 Gap Severities")
                level_calc = Python("level_calculator.py\n\nLevel Mapping\nAdvancement\nRequirements")
                activity_scorer = Python("scoring/\nactivity_scorer.py\n\nTime Decay\nQuality Weight\nRecency Bonus")

        # Business Services
        with Cluster("Business Services (src/core/business/) - 4 files"):
            career_engine = Python("Career Path Engine\n\nGap Analysis\nPromotion Detect\nDev Plan (12mo)")
            analytics_engine = Python("Analytics Engine\n\nData Aggregation\nMetrics Calc\nTrend Analysis")
            reporting_engine = Python("Reporting Engine\n\nData Collection\nFormatting\nPDF Prep")
            notification_engine = Python("Notification Engine\n\nSlack Delivery\nEmail (Future)\nEvent-driven")

        # Conversation Management
        with Cluster("Conversation (src/core/conversation/) - 5 files"):
            conv_intelligence = Python("intelligence.py\n\nIntent Analysis\nContext Update\nClarification Gen")
            context_manager = Python("context_manager.py\n\nRedis Storage\n24h TTL\nCleanup Logic")
            clarification_gen = Python("clarification_generator.py\n\nSmart Prompts\nContext-aware\nUser-friendly")

        # AI Agents
        with Cluster("AI Agents (src/services/agents/) - 6 files"):
            advisor_agent = Python("advisor_agent.py\n\nGoal Tracking\nReport Gen\nResource Finding")
            analysis_agent = Python("analysis_agent.py\n\nDB Queries\nData Analysis\nInsights")
            chat_agent = Python("chat_responder.py\n\nConversation\nNatural Lang\nContext-aware")

    # ========================================================================
    # WORKFLOW ORCHESTRATION LAYER - TEMPORAL
    # ========================================================================
    with Cluster("⚙️ WORKFLOW ORCHESTRATION - Temporal (src/services/workflow/) - 7 files"):
        with Cluster("Temporal Server"):
            temporal_server = Server("Temporal Server v1.22.0\n\nPort 7233 (gRPC)\nPort 8088 (Web UI)\n\nWorkflow State: PostgreSQL\nTask Queues: In-Memory\nHistory: Persistent")

        with Cluster("8 Workflows (workflows.py)"):
            wf1 = Python("Sequential\nAnalysis\n\n5-8 min\n4 activities")
            wf2 = Python("Parallel\nAnalysis\n\n3-5 min\n3 activities")
            wf3 = Python("Report\nGeneration\n\n5-6 min\n7 activities")
            wf4 = Python("Career\nPath\n\n15-30s\n8 activities")
            wf5 = Python("Batch\nProcessing\n\n2-10 min\nbatch size 10")
            wf6 = Python("Inline\nAnalysis\n\n2 min\n4 activities")
            wf7 = Python("Quick\nSummary\n\n30-60s\n3 activities")
            wf8 = Python("Conversation\nFlow\n\n2-3 min\n3 activities")

        with Cluster("Workers (worker.py)"):
            worker_main = Python("Main Worker Container\n\nTask Queues:\n• competency-tasks\n• report-tasks\n• analysis-tasks\n• notification-tasks\n\nConcurrency:\n5 workflows\n10 activities")
            worker_embedded = Python("Embedded Worker\n\nUrgent Tasks Only\n2 workflows")

        with Cluster("20+ Activities (activities.py)"):
            act_analysis = Python("Analysis:\n• analyze_activity\n• assess_competency\n• generate_advice\n• synthesize_insights")
            act_reports = Python("Reports:\n• aggregate_data\n• generate_pdf\n• save_to_db\n• upload_slack\n• send_notification")
            act_inline = Python("Inline:\n• analyze_inline\n• assess_content\n• format_report\n• deliver_report")

    # ========================================================================
    # INFRASTRUCTURE LAYER
    # ========================================================================
    with Cluster("🏗️ INFRASTRUCTURE (src/infrastructure/) - 46 files"):

        with Cluster("Database (database/) - 20 files"):
            db_manager = PostgreSQL("db_manager.py\n\nAsync SQLAlchemy\nasyncpg driver\nConnection Pool: 20\nMax: 100")

            with Cluster("Repositories - 8 files"):
                repo_user = Python("user_repository.py\nCRUD + Analytics")
                repo_activity = Python("activity_repository.py\nQuery + Aggregation")
                repo_competency = Python("competency_repository.py\nScores + History")
                repo_report = Python("report_repository.py\n40+ query methods")

        with Cluster("Cache (cache/) - 3 files"):
            redis_manager = Redis("redis_manager.py\n\nredis.asyncio\nConnection Pool: 50\nPipeline Support\nPub/Sub")
            memory_cache = Python("memory_cache.py\n\nFallback Cache\nLRU Eviction\nThread-safe")

        with Cluster("Monitoring (monitoring/) - 6 files"):
            prometheus = Prometheus("Prometheus\nMetrics\n\nPort 8080\n\nreflectai_*\nmetrics")
            health_monitor = Python("health_monitor.py\n\n12-Point Checks\nPort 8090\n/health\n/ready")
            correlation = Python("correlation_middleware.py\n\nRequest Tracking\nX-Correlation-ID\nDistributed Tracing")

        with Cluster("Events (events/) - 4 files"):
            event_dedup = Python("event_deduplicator.py\n\n536 lines\nRedis-backed\nComposite Keys\nTTL: 1h\n\nStrategies:\n• Strict\n• Content Hash\n• Composite (default)\n• Temporal")
            event_bus = Python("event_bus.py\nredis_event_bus.py\n\nPub/Sub\nEvent Types\nHandlers")

        with Cluster("Config & Security (config/, security/) - 6 files"):
            config_mgr = Python("config_manager.py\n\nPydantic Settings\nEnv Validation\nDoppler Integration")
            secrets_mgr = Python("secrets_manager.py\n\nDoppler SDK\nSecret Rotation\nSecure Access")
            session_mgr = Python("session_manager.py\n\nSession Types:\nUser: 1h\nAPI: 24h\nAdmin: 30m")
            rate_limiter = Python("rate_limiter.py\n\nEndpoint Limits\nUser Quotas\n2x auth multiplier")

    # ========================================================================
    # SHARED UTILITIES LAYER
    # ========================================================================
    with Cluster("🛠️ SHARED UTILITIES (src/shared/) - 6 files | ✅ PRODUCTION READY"):
        shared_exceptions = Python("exceptions.py\n\nReflectAIError\nDatabaseError\nLLMProviderError\nSlackAPIError\nValidationError")
        shared_handlers = Python("error_handlers.py\n\nRetry (exp backoff)\nCircuit Breaker\nAsync Context Mgmt")
        shared_logging = Python("logging.py\n\nstructlog\nCorrelation IDs\nJSON format\nAsync-safe")
        shared_metrics = Python("error_metrics.py\n\nPrometheus\nError tracking\nHandler duration\nCircuit state")

    # ========================================================================
    # DATA STORAGE LAYER
    # ========================================================================
    with Cluster("💾 DATA STORAGE LAYER"):

        with Cluster("PostgreSQL 15 + TimescaleDB 2.14"):
            with Cluster("Standard Tables"):
                db_users = PostgreSQL("users\n\nslack_user_id (PK)\nemail (unique)\nprofile_data (JSONB)\nlast_activity_at\ntimezone")

                db_competencies = PostgreSQL("competencies\n\nuser_id + competency_id\ncurrent_level (0-5)\ntarget_level\nevidence_count\ntrend_direction\nconfidence_interval")

                db_reports = PostgreSQL("reports\n\nuser_id\nreport_type\nformat (pdf/slack)\nstatus\ncontent (JSONB)\nfile_path\nexpires_at (30d)")

                db_sessions = PostgreSQL("user_sessions\n\nsession_token\nuser_id\nexpires_at\nis_active\nlast_activity_at")

                db_workflows = PostgreSQL("workflows\n\nworkflow_type\ntemporal_workflow_id\nstatus\ninput_data (JSONB)\noutput_data (JSONB)\ncorrelation_id")

                db_preferences = PostgreSQL("user_preferences\n\nuser_id\npreference_key\npreference_value\ncategory")

            with Cluster("TimescaleDB Hypertables (Time-series)"):
                db_activities = PostgreSQL("activities\n(Hypertable)\n\nPartition: timestamp\n\nuser_id\ncontent\nactivity_type\ncompetency_areas[]\nmetrics (JSONB)\nconfidence_score\nprocessing_status")

                db_comp_history = PostgreSQL("competency_history\n(Hypertable)\n\nPartition: timestamp\n\nuser_id\ncompetency_id\nlevel_value\nevidence_count\nactivity_id\nchange_reason")

                db_events = PostgreSQL("events\n(Hypertable)\n\nPartition: timestamp\n\nevent_type\nevent_source\nuser_id\nevent_data (JSONB)\nprocessing_status")

        with Cluster("Redis 7/8 Cache"):
            redis_main = Redis("Redis 7.4.6→8.0.5\n\nPort: 6379\nMemory: 512MB\nPolicy: allkeys-lru\nPersistence: AOF\n\nKeys (12+ patterns):\n━━━━━━━━━━━━━━━━━━━\nllm_cache:* (24h)\nconversation_context:* (24h)\nsession:* (1-24h)\nevent_dedup:* (1h)\nrate_limit:* (1m)\nactivity_cache:* (5m)\ncompetency:* (15m)\nworkflow_status:* (1h)\nfeature_flag:*\nconfig:*")

        with Cluster("File Storage"):
            file_storage = S3("File System\n\nreports/output/\n\nPDF Reports\n30-day TTL\nAuto-cleanup")

    # ========================================================================
    # EXTERNAL SYSTEMS
    # ========================================================================
    with Cluster("🌍 EXTERNAL SYSTEMS"):
        with Cluster("Slack Platform"):
            slack_api = Server("Slack API\n\nSocket Mode\nWebSocket\nEvents API\nFiles API\nBlock Kit")

        with Cluster("LLM Providers (via LiteLLM 1.0)"):
            enterprise_gateway = Server("EnterpriseGateway\n(Primary)\n\nOAuth2\nEnterprise LLM\nTenant Isolation")
            openai_provider = Server("OpenAI\n(Failover)\n\nGPT-4 Turbo\nGPT-3.5 Turbo\nAPI Key Auth")
            anthropic_provider = Server("Anthropic\n(Failover)\n\nClaude 3.5\nHaiku/Sonnet\nAPI Key Auth")

        doppler_secrets = Server("Doppler\n\nSecrets Management\nAPI Keys\nCredentials\nConfig Sync")

        with Cluster("Monitoring Stack (Future)"):
            grafana = Grafana("Grafana\n\nDashboards\nAlerts\nVisualization")

    # ========================================================================
    # DATA FLOW CONNECTIONS
    # ========================================================================

    # External to App Layer
    slack_users >> Edge(label="WebSocket\nSocket Mode\nEvents", color="blue") >> slack_socket
    api_clients >> Edge(label="HTTP/JSON\nREST API", color="green") >> fastapi_main

    # App Layer Internal
    slack_socket >> Edge(label="Parse &\nDedup", color="blue") >> slack_handlers
    slack_handlers >> Edge(label="Route", color="blue") >> slack_conv
    slack_handlers >> Edge(label="Commands", color="blue") >> slack_commands
    fastapi_main >> Edge(label="Middleware", color="gray", style="dashed") >> auth_mw
    fastapi_main >> Edge(label="Middleware", color="gray", style="dashed") >> error_mw
    fastapi_main >> Edge(label="Middleware", color="gray", style="dashed") >> rate_mw

    # App to Business Logic
    slack_conv >> Edge(label="Analyze\nIntent", color="orange") >> conv_intelligence
    slack_conv >> Edge(label="Classify", color="orange") >> intent_analyzer
    slack_commands >> Edge(label="Trigger\nAnalysis", color="orange") >> competency_assessor

    # Business Logic Internal Flows
    conv_intelligence >> Edge(label="Load/Save\nContext", color="purple") >> context_manager
    intent_analyzer >> Edge(label="Map to\nCompetency", color="orange") >> competency_mapper
    competency_mapper >> Edge(label="Score\nActivity", color="orange") >> activity_classifier
    activity_classifier >> Edge(label="Assess", color="orange") >> competency_assessor
    competency_assessor >> Edge(label="Find\nGaps", color="orange") >> gap_analyzer
    gap_analyzer >> Edge(label="Career\nAnalysis", color="orange") >> career_engine
    competency_assessor >> Edge(label="Report\nData", color="orange") >> reporting_engine

    # LLM Gateway Integration
    conv_intelligence >> Edge(label="Summarize\nContext", color="red") >> llm_gateway
    intent_analyzer >> Edge(label="Classify\n(fallback)", color="red") >> llm_gateway
    activity_classifier >> Edge(label="Classify\nActivity", color="red") >> llm_gateway
    reporting_engine >> Edge(label="Generate\nSummary", color="red") >> llm_gateway
    advisor_agent >> Edge(label="Generate\nRecommendations", color="red") >> llm_gateway

    # LLM Gateway Internal
    llm_gateway >> Edge(label="Track\nCost", color="red", style="dashed") >> llm_cost
    llm_gateway >> Edge(label="Check\nCache", color="red", style="dashed") >> llm_cache
    llm_gateway >> Edge(label="Select\nProvider", color="red", style="dashed") >> llm_optimizer
    llm_gateway >> Edge(label="Validate", color="red", style="dashed") >> llm_guardrails

    # Business Logic to Workflows
    conv_intelligence >> Edge(label="Start\nWorkflow", color="purple") >> temporal_server
    competency_assessor >> Edge(label="Trigger\nAssessment", color="purple") >> wf1
    reporting_engine >> Edge(label="Trigger\nReport", color="purple") >> wf3
    career_engine >> Edge(label="Trigger\nCareer", color="purple") >> wf4

    # Temporal Orchestration
    temporal_server >> Edge(label="Distribute\nTasks", color="purple") >> worker_main
    temporal_server >> Edge(label="Urgent\nTasks", color="purple") >> worker_embedded

    worker_main >> Edge(label="Execute", color="purple") >> act_analysis
    worker_main >> Edge(label="Execute", color="purple") >> act_reports
    worker_main >> Edge(label="Execute", color="purple") >> act_inline

    # Activities to Data & External
    act_analysis >> Edge(label="Query", color="brown") >> db_activities
    act_analysis >> Edge(label="Query", color="brown") >> db_competencies
    act_reports >> Edge(label="Generate", color="red") >> llm_providers
    act_reports >> Edge(label="Save PDF", color="brown") >> file_storage
    act_reports >> Edge(label="Create", color="brown") >> db_reports
    act_inline >> Edge(label="Notify", color="blue") >> slack_api

    # Infrastructure Connections
    context_manager >> Edge(label="conversation:*\nTTL: 24h", color="darkred") >> redis_manager
    llm_cache >> Edge(label="llm_cache:*\nTTL: 30m-24h", color="darkred") >> redis_manager
    slack_handlers >> Edge(label="event_dedup:*\nTTL: 1h", color="darkred") >> event_dedup
    event_dedup >> Edge(label="Store\nComposite Key", color="darkred") >> redis_manager
    session_mgr >> Edge(label="session:*\nTTL: 1-24h", color="darkred") >> redis_manager

    # Redis Manager to Cache
    redis_manager >> Edge(label="Connection\nPool: 50", color="darkred") >> redis_main
    redis_manager >> Edge(label="Fallback", color="gray", style="dashed") >> memory_cache

    # Database Connections
    db_manager >> Edge(label="Async\nPool: 20", color="brown") >> db_users
    db_manager >> Edge(label="Async\nPool: 20", color="brown") >> db_activities
    db_manager >> Edge(label="Async\nPool: 20", color="brown") >> db_competencies
    db_manager >> Edge(label="Async\nPool: 20", color="brown") >> db_comp_history
    db_manager >> Edge(label="Async\nPool: 20", color="brown") >> db_reports
    db_manager >> Edge(label="Async\nPool: 20", color="brown") >> db_workflows

    # LLM Providers
    llm_providers >> Edge(label="Primary\nOAuth2", color="red") >> enterprise_gateway
    llm_providers >> Edge(label="Failover\nAPI Key", color="red") >> openai_provider
    llm_providers >> Edge(label="Failover\nAPI Key", color="red") >> anthropic_provider

    # Slack Integration
    slack_socket >> Edge(label="Events &\nMessages", color="blue") >> slack_api
    slack_blocks >> Edge(label="Send\nBlocks", color="blue") >> slack_api
    act_reports >> Edge(label="Upload\nPDF", color="blue") >> slack_api
    notification_engine >> Edge(label="Send\nNotifications", color="blue") >> slack_api

    # Configuration & Secrets
    secrets_mgr >> Edge(label="Pull Secrets\nat Startup", color="green") >> doppler_secrets
    config_mgr >> Edge(label="Load", color="green", style="dashed") >> secrets_mgr

    # Monitoring
    shared_metrics >> Edge(label="Export", color="gray", style="dashed") >> prometheus
    prometheus >> Edge(label="Scrape", color="gray", style="dashed") >> grafana
    shared_logging >> Edge(label="All Logs", color="gray", style="dotted") >> fastapi_main
    correlation >> Edge(label="Track IDs", color="gray", style="dotted") >> shared_logging

    # Temporal State Persistence
    temporal_server >> Edge(label="Workflow\nState &\nHistory", color="purple") >> db_workflows

    # Error Handling Integration
    shared_handlers >> Edge(label="Metrics", color="gray", style="dashed") >> shared_metrics
    shared_exceptions >> Edge(label="Raise", color="gray", style="dashed") >> shared_handlers

print("✅ Detailed architecture diagram generated: reflectai_detailed_architecture.png")
print("   Includes: 176 files, 5 layers, 12+ Redis keys, 9+ DB tables, 8 workflows, 20+ activities")
