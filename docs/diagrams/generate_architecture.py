"""
Generate comprehensive ReflectAI system architecture diagram.

This script creates a detailed visual architecture diagram showing all layers,
components, and data flows in the ReflectAI platform.
"""

from diagrams import Cluster, Diagram, Edge
from diagrams.onprem.client import Users
from diagrams.onprem.compute import Server
from diagrams.onprem.database import PostgreSQL
from diagrams.onprem.inmemory import Redis
from diagrams.programming.framework import Fastapi
from diagrams.programming.language import Python

# Set diagram attributes for better layout
graph_attr = {
    "fontsize": "14",
    "bgcolor": "white",
    "pad": "0.5",
    "ranksep": "1.2",
    "nodesep": "0.8",
}

node_attr = {
    "fontsize": "11",
    "height": "1.0",
    "width": "1.8",
}

edge_attr = {
    "fontsize": "9",
}

with Diagram(
    "ReflectAI Platform - Complete System Architecture",
    filename="reflectai_complete_architecture",
    outformat="png",
    show=False,
    direction="TB",
    graph_attr=graph_attr,
    node_attr=node_attr,
    edge_attr=edge_attr,
):

    # External Interfaces
    with Cluster("External Interfaces"):
        slack_users = Users("Slack Users\n(Primary Interface)")
        api_clients = Server("API Clients")

    # Application Layer
    with Cluster("Application Layer - FastAPI"):
        with Cluster("HTTP Server (3000, 8080, 8090)"):
            fastapi = Fastapi("FastAPI + Uvicorn")

        with Cluster("Adapters"):
            slack_adapter = Python("Slack Adapter\nEvent Dedup")
            api_routes = Python("API Routes")
            auth = Python("Auth OAuth2")

    # Business Logic Layer
    with Cluster("Business Logic Layer"):
        with Cluster("Core Engines"):
            llm_gateway = Python("LLM Gateway\nLiteLLM\n\nEnterpriseGateway+OpenAI\nAnthropic\n\nFailover\nCost Track\nCache")

            classification = Python("Classification\n\nIntent\nActivity\nCompetency")

            assessment = Python("Assessment\n\nScoring 1-5\nGap Analysis\nLevels")

        with Cluster("Business Services"):
            career = Python("Career Path")
            reporting = Python("Reporting\nPDF Engine")
            notification = Python("Notification")

        with Cluster("Conversation"):
            conv_intel = Python("Conversation\nIntelligence\n\nCompaction\n20→5+summary")
            context_mgr = Python("Context Mgr\nRedis 24h")

    # Workflow Orchestration
    with Cluster("Workflow Orchestration - Temporal"):
        temporal_server = Server("Temporal Server\n7233, 8088\n\nState Store\nTask Queues\nRetry Logic")

        with Cluster("Workflows"):
            wf_assessment = Python("Assessment\n8-15s")
            wf_report = Python("Report Gen\n5-6 min")
            wf_career = Python("Career Path\n15-30s")

        with Cluster("Workers"):
            worker_main = Python("Main Worker\n\nQueues:\ncompetency\nreport\nanalysis")
            worker_embedded = Python("Embedded\nWorkers")

    # Infrastructure Layer
    with Cluster("Infrastructure"):
        with Cluster("Config & Security"):
            config = Python("Config\nPydantic")
            secrets = Python("Secrets\nDoppler")
            security = Python("Security\nAuth/Audit")

        with Cluster("Observability"):
            logging = Python("Logging\nstructlog")
            metrics = Python("Prometheus\n8080")
            health = Python("Health\n12-point\n8090")

        redis_mgr = Python("Redis Manager\nredis.asyncio")

    # Data Storage Layer
    with Cluster("Data Storage"):
        with Cluster("PostgreSQL 15 + TimescaleDB"):
            db_users = PostgreSQL("users")
            db_activities = PostgreSQL("activities")
            db_competencies = PostgreSQL("competencies\n0-5 scores")
            db_comp_history = PostgreSQL("competency_history\nTimescaleDB")
            db_reports = PostgreSQL("reports\n30d TTL")

        redis_cache = Redis("Redis 7/8\n6379\n512MB LRU\n\nKeys:\nsession:*\nconversation:*\nllm:cache:*\nevent_dedup:*\nrate_limit:*")

        file_storage = Server("File System\nPDF Reports")

    # External Systems
    with Cluster("External Systems"):
        slack_api = Server("Slack API\nSocket Mode")

        with Cluster("LLM Providers"):
            enterprise_gateway = Server("EnterpriseGateway")
            openai = Server("OpenAI")
            anthropic = Server("Anthropic")

        doppler = Server("Doppler")

    # Data Flow Connections
    slack_users >> Edge(label="Events") >> slack_adapter
    api_clients >> Edge(label="HTTP") >> api_routes

    slack_adapter >> Edge(label="Dedup") >> conv_intel
    conv_intel >> classification >> assessment
    assessment >> career >> reporting

    conv_intel >> Edge(label="Summarize") >> llm_gateway
    classification >> Edge(label="Classify") >> llm_gateway
    reporting >> Edge(label="Generate") >> llm_gateway

    context_mgr >> Edge(label="24h") >> redis_mgr

    conv_intel >> Edge(label="Start") >> temporal_server
    temporal_server >> worker_main >> db_activities
    worker_main >> llm_gateway
    worker_main >> file_storage
    worker_main >> slack_api

    llm_gateway >> Edge(label="Primary") >> enterprise_gateway
    llm_gateway >> Edge(label="Failover") >> openai
    llm_gateway >> Edge(label="Failover") >> anthropic

    llm_gateway >> Edge(label="Cache 24h") >> redis_mgr
    redis_mgr >> redis_cache

    slack_adapter >> Edge(label="session") >> redis_mgr
    slack_adapter >> Edge(label="dedup 1h") >> redis_mgr

    secrets >> doppler
    slack_adapter >> slack_api

    temporal_server >> db_users

print("✅ Architecture diagram generated: docs/diagrams/reflectai_complete_architecture.png")
