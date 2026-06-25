"""
ReflectAI FastAPI Application
Production Security-First Foundation with API endpoints

This module provides the FastAPI application with health checks,
configuration endpoints, and foundation for future features.
"""

import asyncio
import os
import random
import sys
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.conversation.intelligence import ConversationIntelligence
from src.core.llm import LLMRequest, ModelTier, get_llm_gateway
from src.core.workflows.workflow_router import get_workflow_router
from src.infrastructure.cache.redis_manager import get_redis_manager
from src.infrastructure.config import (
    get_config_manager,
    get_configuration_health,
    load_configuration,
)
from src.infrastructure.config.environment_validator import validate_environment_on_startup
from src.infrastructure.config import get_secrets_manager
from src.infrastructure.database.db_manager import get_database_health, get_database_manager
from src.infrastructure.events import EventType, SlackEvent, UserActivityEvent, get_event_bus
from src.infrastructure.events.handlers import initialize_event_handlers
from src.infrastructure.monitoring import get_metrics_health, start_metrics_server
from src.infrastructure.monitoring.observability import (
    set_application_info,
    update_component_health,
)
from src.infrastructure.monitoring.correlation_middleware import CorrelationIDMiddleware
from src.infrastructure.monitoring.simple_middleware import SimpleMetricsMiddleware
from src.infrastructure.security.rate_limiter import (
    ENDPOINT_RATE_LIMITS,
    RateLimitConfig,
    RateLimitMiddleware,
)
from src.interfaces.slack.conversation_manager import ConversationManager
from src.interfaces.slack.enhanced_home_tab import EnhancedHomeTabManager
from src.interfaces.slack.socket_handler import SlackSocketModeHandler
from src.interfaces.slack.workflow_integration import SlackWorkflowIntegration
from src.services.workflow.models import WorkflowRequest, WorkflowStatus, WorkflowType
from src.services.workflow.temporal_client import get_temporal_client
from src.services.workflow.workflows import SequentialAnalysisWorkflow
from src.shared.logging import configure_logging, get_logger
from src.version import get_short_version, get_version_info

# Configure logging with environment variable
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
configure_logging(log_level=log_level)
logger = get_logger(__name__)

# Load configuration at module level
try:
    config_manager = get_config_manager()
    app_config = config_manager.get_config()
    secrets_manager = get_secrets_manager()
except Exception as e:
    logger.error(f"❌ Failed to load configuration: {e}", exc_info=True)
    logger.error("Application cannot start without valid configuration")
    logger.error("Please check your .env file and ensure all required variables are set")
    sys.exit(1)


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    version: str
    environment: str
    checks: dict[str, Any]


class ReadinessResponse(BaseModel):
    """Readiness check response model."""

    ready: bool
    timestamp: datetime
    checks: dict[str, dict[str, Any]]
    failed_checks: list[str]


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str
    detail: str
    request_id: str = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global app_config

    logger.info("🚀 Starting ReflectAI FastAPI Application")

    try:
        # Load configuration
        app_config = load_configuration()
        logger.info(f"Configuration loaded - environment: {app_config.app.environment}")

        # Validate environment before proceeding
        logger.info("Starting environment validation...")
        validation_report = await validate_environment_on_startup(
            environment=app_config.app.environment,
            raise_on_failure=True,
            print_report=True,  # Show detailed validation report for debugging
        )

        if validation_report.overall_status == "passed":
            logger.info("✅ Environment validation passed")
        elif validation_report.overall_status == "warnings":
            logger.warning(
                f"⚠️  Environment validation passed with {validation_report.warning_checks_count} warnings"
            )
        else:
            logger.error("❌ Environment validation failed - startup aborted")
            raise RuntimeError("Environment validation failed")

        # Start metrics server if enabled
        if app_config.monitoring.metrics_enabled:
            start_metrics_server(port=app_config.monitoring.metrics_port)
            logger.info(f"Metrics server started on port {app_config.monitoring.metrics_port}")

        # Initialize database with retry logic
        db_manager = get_database_manager()
        max_retries = 5
        base_delay = 2.0  # seconds

        for attempt in range(max_retries):
            try:
                logger.info(f"Initializing database (attempt {attempt + 1}/{max_retries})...")
                await db_manager.initialize()
                logger.info("✅ Database initialized")
                break  # Success - exit retry loop
            except Exception as e:
                if attempt == max_retries - 1:
                    # Last attempt failed
                    logger.error(f"Database initialization failed after {max_retries} attempts: {e}")
                    raise
                # Calculate backoff delay with jitter
                delay = base_delay * (2 ** attempt)
                jitter = delay * 0.1
                wait_time = delay + random.uniform(-jitter, jitter)
                logger.warning(
                    f"Database initialization failed, retrying in {wait_time:.1f}s...",
                    extra={"error": str(e), "attempt": attempt + 1, "max_retries": max_retries}
                )
                await asyncio.sleep(wait_time)

        # Initialize Redis manager ONCE at startup with memory fallback
        # This replaces the old CacheManager - RedisManager is now the unified cache layer
        from src.infrastructure.cache.redis_manager import initialize_redis

        redis_manager = await initialize_redis()
        if redis_manager._using_fallback:
            logger.warning("⚠️  Redis unavailable - using in-memory cache fallback")
        else:
            logger.info("✅ Redis manager initialized")

        # Initialize event system
        await initialize_event_handlers()
        logger.info("✅ Event system initialized")

        # Initialize LLM gateway
        llm_gateway = get_llm_gateway()
        logger.info("✅ LLM gateway initialized")

        # Initialize report generation engines
        from src.core.business.reporting_engine import ReportingEngine
        from src.services.reporting.pdf_report_engine import PDFReportEngine

        # Use already-initialized Redis manager
        redis_manager = get_redis_manager()

        # Initialize PDF report engine
        pdf_report_engine = PDFReportEngine(
            redis_manager=redis_manager,
            template_dir="templates/reports",
            output_dir="reports/output",
        )

        # Initialize reporting engine
        reporting_engine = ReportingEngine()

        # Store in app state for access by activities
        app.state.pdf_report_engine = pdf_report_engine
        app.state.reporting_engine = reporting_engine

        logger.info("✅ Report engines initialized")

        # Initialize Temporal workflow system
        # Note: get_temporal_client is already imported at module level (line 58)
        from src.services.workflow.worker import start_temporal_worker

        # Initialize Temporal client
        _ = await get_temporal_client()
        logger.info("✅ Temporal client initialized")

        # Start Temporal worker in background
        _ = await start_temporal_worker()
        logger.info("✅ Temporal worker started")

        # Initialize Slack integration components
        try:
            # Use config system for Slack configuration
            slack_mode = "socket"  # Default mode from config
            slack_secrets = secrets_manager.get_slack_secrets() if secrets_manager else {}

            # Only initialize if Slack tokens are available
            if slack_secrets.get("bot_token") and slack_secrets.get("signing_secret"):
                # Use already-initialized Redis manager
                redis_manager = get_redis_manager()

                # Initialize conversation intelligence
                conversation_intelligence = ConversationIntelligence(redis_client=redis_manager.redis_client)

                # Initialize enhanced home tab with connected Redis client
                home_tab_manager = EnhancedHomeTabManager(redis_client=redis_manager.redis_client)
                await home_tab_manager.initialize()

                # Initialize workflow router for Slack-Temporal integration
                workflow_router = await get_workflow_router()
                logger.info("✅ Workflow router initialized")

                # Initialize Slack workflow integration (bridge to Temporal)
                from src.interfaces.slack.app import get_slack_app

                slack_app = await get_slack_app(mode=slack_mode)

                slack_workflow_integration = SlackWorkflowIntegration(
                    slack_app=slack_app,
                    workflow_router=workflow_router,
                    dedup_service=None,  # Will auto-initialize
                    redis_manager=redis_manager,
                )
                await slack_workflow_integration.initialize()
                logger.info("✅ Slack workflow integration initialized")

                # Initialize conversation manager with workflow router
                conversation_manager = ConversationManager(
                    redis_client=redis_manager.redis_client,  # Use raw Redis client, not manager
                    conversation_intelligence=conversation_intelligence,
                    home_tab_manager=home_tab_manager,
                    workflow_router=workflow_router,  # Connect to workflow system
                )

                # Initialize Slack handler
                global slack_handler
                slack_handler = SlackSocketModeHandler(
                    redis_client=redis_manager.redis_client,  # Use raw Redis client, not manager
                    conversation_manager=conversation_manager,
                )

                # Start Slack handler in background for Socket Mode
                if slack_mode == "socket" and slack_secrets.get("app_token"):
                    # Note: asyncio already imported at module level (line 9)
                    asyncio.create_task(slack_handler.start())
                    logger.info(f"✅ Slack integration initialized in {slack_mode} mode")
                else:
                    logger.info(
                        f"✅ Slack integration initialized for {slack_mode} mode (HTTP endpoints ready)"
                    )

            else:
                logger.warning("⚠️  Slack tokens not configured - Slack integration disabled")

        except Exception as e:
            logger.error(f"❌ Slack integration initialization failed: {str(e)}")
            # Don't fail startup for Slack integration issues
            pass

        # Set application metrics
        set_application_info(
            version=app_config.app.version,
            environment=app_config.app.environment,
            phase="production" if app_config.app.environment == "production" else "development",
        )

        # Update health status
        update_component_health("database", True)
        update_component_health("cache", True)
        update_component_health("events", True)
        update_component_health("llm_gateway", True)
        update_component_health("temporal_client", True)
        update_component_health("temporal_worker", True)
        update_component_health("slack_integration", slack_handler is not None)

        logger.info("✅ Application startup complete")

        yield  # Application runs here

    except Exception as e:
        logger.error(f"Startup failed: {str(e)}", exc_info=True)
        raise
    finally:
        # ====================================================================
        # Graceful Shutdown Sequence
        # ====================================================================
        logger.info("🔄 Starting graceful shutdown...")

        # 1. Stop Temporal worker
        try:
            from src.services.workflow.worker import stop_temporal_worker

            await stop_temporal_worker()
            logger.info("✅ Temporal worker stopped")
        except Exception as e:
            logger.error(f"Error stopping Temporal worker: {e}")

        # 2. Close database connections
        try:
            logger.info("Closing database connections...")
            db_manager = get_database_manager()
            await db_manager.close()
            logger.info("✅ Database connections closed")
        except Exception as e:
            logger.error(f"Error closing database: {e}", exc_info=True)

        # 3. Close Redis connections
        try:
            logger.info("Closing Redis connections...")
            redis_manager = get_redis_manager()
            await redis_manager.close()
            logger.info("✅ Redis connections closed")
        except Exception as e:
            logger.error(f"Error closing Redis: {e}", exc_info=True)

        # 4. Close Temporal client
        try:
            logger.info("Closing Temporal client...")
            temporal_client = await get_temporal_client()
            if temporal_client:
                await temporal_client.cleanup()
            logger.info("✅ Temporal client closed")
        except Exception as e:
            logger.error(f"Error closing Temporal client: {e}", exc_info=True)

        # 5. Stop event bus
        try:
            logger.info("Stopping event bus...")
            event_bus = get_event_bus()
            await event_bus.stop()
            logger.info("✅ Event bus stopped")
        except Exception as e:
            logger.error(f"Error stopping event bus: {e}", exc_info=True)

        logger.info("🛑 Graceful shutdown complete")


# Create FastAPI app with security configurations
app = FastAPI(
    title="ReflectAI API",
    description="AI-powered competency analysis system",
    version=get_short_version(),
    lifespan=lifespan,
    # Security: Disable automatic docs in production
    docs_url="/docs" if app_config and app_config.app.environment != "production" else None,
    redoc_url="/redoc" if app_config and app_config.app.environment != "production" else None,
)

# Security Middleware Configuration

# 1. Request Size Limits - Prevent large payload attacks


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to limit request body size."""

    def __init__(self, app, max_size: int = 10 * 1024 * 1024):  # 10MB default
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(self, request: Request, call_next):
        # Check Content-Length header
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                if size > self.max_size:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": "Request Entity Too Large",
                            "detail": f"Request body exceeds maximum size of {self.max_size} bytes",
                            "max_size": self.max_size,
                        },
                    )
            except ValueError:
                pass

        # For chunked transfer encoding, we need to check during reading
        # This is handled by setting client_max_size in uvicorn

        response = await call_next(request)
        return response


# 2. Add observability and security middleware in order of priority

# Correlation ID middleware (must be first to set context for all requests)
app.add_middleware(CorrelationIDMiddleware)

# Request size limiting (10MB for general, 50MB for file uploads)
max_request_size = 10 * 1024 * 1024  # Default from config
app.add_middleware(RequestSizeLimitMiddleware, max_size=max_request_size)

# Trusted host validation (prevent host header attacks)
allowed_hosts = ["*"]  # Default to allow all in development
if allowed_hosts != ["*"]:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

# Rate limiting with Redis backend
rate_limit_config = RateLimitConfig(
    requests_per_second=10,  # Default from config
    requests_per_minute=100,  # Default from config
    requests_per_hour=1000,  # Default from config
    burst_size=20,  # Default from config
    endpoint_limits=ENDPOINT_RATE_LIMITS,
    authenticated_multiplier=2.0,
    use_redis=True,  # Use Redis by default
    include_headers=True,
    exempt_paths=["/health", "/metrics", "/docs", "/openapi.json", "/redoc"],
)
app.add_middleware(RateLimitMiddleware, config=rate_limit_config)

# Monitoring middleware (after security middleware)
app.add_middleware(SimpleMetricsMiddleware)


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "HTTP Error", "detail": exc.detail, "status_code": exc.status_code},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error", "detail": "An unexpected error occurred"},
    )


# Health check endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Basic health check endpoint."""
    global app_config

    if not app_config:
        raise HTTPException(status_code=503, detail="Application not initialized")

    return HealthResponse(
        status="healthy",
        version=app_config.app.version,
        environment=app_config.app.environment,
        checks={
            "config": "ok",
            "metrics": "ok" if app_config.monitoring.metrics_enabled else "disabled",
        },
    )


@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with component status."""
    global app_config

    if not app_config:
        raise HTTPException(status_code=503, detail="Application not initialized")

    health_status = {
        "status": "healthy",
        "version": app_config.app.version,
        "environment": app_config.app.environment,
        "components": {
            "configuration": get_configuration_health(),
            "metrics": get_metrics_health()
            if app_config.monitoring.metrics_enabled
            else {"status": "disabled"},
            "database": await get_database_health(),
            "cache": await get_redis_manager().health_check(),
        },
    }

    # Check if any component is unhealthy
    for _component, status in health_status["components"].items():
        if isinstance(status, dict) and status.get("status") == "unhealthy":
            health_status["status"] = "degraded"
            break

    return health_status


@app.get("/ready", response_model=ReadinessResponse)
async def readiness_check():
    """
    Readiness probe - checks if application can handle requests.

    Returns 200 if ready, 503 if not ready.
    Checks all critical dependencies: database, redis, temporal, config.
    """
    checks = {}
    failed = []

    # Check 1: Configuration loaded
    if app_config:
        checks["config"] = {"status": "ready", "message": "Configuration loaded"}
    else:
        checks["config"] = {"status": "not_ready", "error": "Config not loaded"}
        failed.append("config")

    # Check 2: Database connectivity
    try:
        db_health = await get_database_health()
        if db_health.get("status") == "healthy":
            checks["database"] = {"status": "ready", "message": "Connected"}
        else:
            checks["database"] = {"status": "not_ready", "error": db_health.get("error", "Unhealthy")}
            failed.append("database")
    except Exception as e:
        checks["database"] = {"status": "not_ready", "error": str(e)}
        failed.append("database")

    # Check 3: Redis connectivity
    try:
        cache_health = await get_redis_manager().health_check()
        if cache_health.get("status") == "healthy":
            checks["redis"] = {"status": "ready", "message": "Connected"}
        else:
            checks["redis"] = {"status": "not_ready", "error": cache_health.get("error", "Unhealthy")}
            failed.append("redis")
    except Exception as e:
        checks["redis"] = {"status": "not_ready", "error": str(e)}
        failed.append("redis")

    # Check 4: Temporal connectivity (optional, don't fail if not available)
    try:
        temporal_client = await get_temporal_client()
        if temporal_client and hasattr(temporal_client, "workflow_service"):
            checks["temporal"] = {"status": "ready", "message": "Connected"}
        else:
            checks["temporal"] = {"status": "degraded", "message": "Client not fully initialized"}
    except Exception as e:
        checks["temporal"] = {"status": "degraded", "error": str(e)}
        # Note: Not adding to failed list - temporal is optional for basic requests

    # Overall readiness
    is_ready = len(failed) == 0

    response_data = ReadinessResponse(
        ready=is_ready,
        timestamp=datetime.now(UTC),
        checks=checks,
        failed_checks=failed
    )

    # Return 503 if not ready, 200 if ready
    status_code = 200 if is_ready else 503

    return JSONResponse(
        status_code=status_code,
        content=response_data.model_dump(mode='json')  # mode='json' serializes datetime to ISO string
    )


# Configuration endpoints
@app.get("/config")
async def get_configuration():
    """Get current application configuration (non-sensitive only)."""
    global app_config

    if not app_config:
        raise HTTPException(status_code=503, detail="Application not initialized")

    # Return non-sensitive configuration
    return {
        "app": {
            "name": app_config.app.name,
            "version": app_config.app.version,
            "environment": app_config.app.environment,
            "phase": app_config.app.phase,
        },
        "features": {
            "simplified_agents": app_config.features.simplified_agents,
            "redis_pubsub": app_config.features.redis_pubsub,
            "simple_observability": app_config.features.simple_observability,
            "doppler_config": app_config.features.doppler_config,
        },
        "monitoring": {
            "metrics_enabled": app_config.monitoring.metrics_enabled,
            "metrics_port": app_config.monitoring.metrics_port,
        },
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    version_info = get_version_info()
    return {
        "name": "ReflectAI API",
        "version": version_info["version"],
        "build_date": version_info["build_date"],
        "git_commit": version_info["git_commit"],
        "git_branch": version_info["git_branch"],
        "status": "operational",
        "environment": app_config.app.environment if app_config else "development",
        "endpoints": {
            "health": "/health",
            "detailed_health": "/health/detailed",
            "configuration": "/config",
            "version": "/version",
            "metrics": "/metrics (Prometheus)",
            "documentation": "/docs"
            if app_config and app_config.app.environment != "production"
            else "Disabled in production",
        },
    }


@app.get("/version")
async def get_version():
    """Get detailed version information."""
    return get_version_info()


# Database endpoints
@app.post("/api/v1/users")
async def create_user(user_data: dict):
    """Create a new user in the database."""
    try:
        db = get_database_manager()
        user_id = await db.insert_user(user_data)
        return {"status": "success", "user_id": user_id}
    except Exception as e:
        logger.error(f"Failed to create user: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/api/v1/activities")
async def create_activity(activity_data: dict):
    """Create a new activity in the database."""
    try:
        db = get_database_manager()
        activity_id = await db.insert_activity(activity_data)
        return {"status": "success", "activity_id": activity_id}
    except Exception as e:
        logger.error(f"Failed to create activity: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/v1/users/{user_id}/activities")
async def get_user_activities(user_id: str, limit: int = 100):
    """Get activities for a user."""
    try:
        db = get_database_manager()
        activities = await db.get_user_activities(user_id, limit)
        return {"user_id": user_id, "activities": activities, "count": len(activities)}
    except Exception as e:
        logger.error(f"Failed to get activities: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# Cache endpoints
@app.post("/api/v1/cache/{key}")
async def set_cache(key: str, value: dict, ttl: int = 3600):
    """Set a value in cache with optional TTL."""
    try:
        redis_manager = get_redis_manager()
        success = await redis_manager.set("api", key, value, ttl_override=ttl)
        return {"status": "success" if success else "failed", "key": key}
    except Exception as e:
        logger.error(f"Cache set failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/v1/cache/{key}")
async def get_cache(key: str):
    """Get a value from cache."""
    try:
        redis_manager = get_redis_manager()
        value = await redis_manager.get("api", key)
        return {"key": key, "value": value, "found": value is not None}
    except Exception as e:
        logger.error(f"Cache get failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.delete("/api/v1/cache/{key}")
async def delete_cache(key: str):
    """Delete a value from cache."""
    try:
        redis_manager = get_redis_manager()
        success = await redis_manager.delete("api", key)
        return {"status": "success" if success else "not_found", "key": key}
    except Exception as e:
        logger.error(f"Cache delete failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# Event system endpoints
@app.post("/api/v1/events/publish")
async def publish_event(event_data: dict):
    """Publish an event to the event bus."""
    import uuid

    try:
        event_bus = get_event_bus()

        # Create appropriate event based on type
        event_type = event_data.get("event_type", "custom")
        correlation_id = event_data.get("correlation_id", str(uuid.uuid4()))

        if event_type == "slack.message":
            event = SlackEvent(
                event_type=EventType.SLACK_MESSAGE_RECEIVED,
                correlation_id=correlation_id,
                team_id=event_data.get("team_id", ""),
                user_id=event_data.get("user_id", ""),
                channel_id=event_data.get("channel_id", ""),
                text=event_data.get("text", ""),
                event_ts=event_data.get("event_ts", str(datetime.now(UTC).timestamp())),
            )
        elif event_type == "user.activity":
            event = UserActivityEvent(
                event_type=EventType.USER_ACTIVITY_CREATED,
                correlation_id=correlation_id,
                user_id=event_data.get("user_id", ""),
                team_id=event_data.get("team_id", ""),
                activity_type=event_data.get("activity_type", ""),
                activity_data=event_data.get("activity_data", {}),
            )
        else:
            # Generic event
            from infrastructure.events.event_bus import Event

            event = Event(name=event_type, data=event_data, correlation_id=correlation_id)

        subscribers = await event_bus.publish(event)

        return {"status": "success", "correlation_id": correlation_id, "subscribers": subscribers}
    except Exception as e:
        logger.error(f"Failed to publish event: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/v1/events/stats")
async def get_event_stats():
    """Get event bus statistics."""
    try:
        event_bus = get_event_bus()
        stats = event_bus.get_stats()
        return {"status": "success", "stats": stats}
    except Exception as e:
        logger.error(f"Failed to get event stats: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# LLM Gateway endpoints
@app.post("/api/v1/llm/generate")
async def generate_llm_response(request_data: dict):
    """Generate LLM response via gateway."""
    import uuid

    try:
        llm_gateway = get_llm_gateway()

        # Create LLM request
        messages = request_data.get("messages", [])
        if not messages and request_data.get("prompt"):
            messages = [{"role": "user", "content": request_data["prompt"]}]

        llm_request = LLMRequest(
            messages=messages,
            model_tier=ModelTier(request_data.get("model_tier", "standard")),
            user_id=request_data.get("user_id", "anonymous"),
            request_id=request_data.get("request_id", str(uuid.uuid4())),
            correlation_id=request_data.get("correlation_id", str(uuid.uuid4())),
            max_tokens=request_data.get("max_tokens"),
            temperature=request_data.get("temperature", 0.7),
            system_prompt=request_data.get("system_prompt"),
            context=request_data.get("context", {}),
            cache_strategy=request_data.get("cache_strategy", "default"),
            retry_attempts=request_data.get("retry_attempts", 2),
            timeout_seconds=request_data.get("timeout_seconds", 30),
        )

        # Generate response
        response = await llm_gateway.generate(llm_request)

        return {"status": "success", "response": response.to_dict()}

    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/v1/llm/health")
async def llm_health_check():
    """Check LLM gateway health."""
    try:
        llm_gateway = get_llm_gateway()
        health = await llm_gateway.health_check()
        return {"status": "success", "health": health}
    except Exception as e:
        logger.error(f"LLM health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/v1/llm/usage")
async def llm_usage_stats():
    """Get LLM usage statistics."""
    try:
        llm_gateway = get_llm_gateway()
        stats = llm_gateway.get_usage_stats()
        return {"status": "success", "usage": stats}
    except Exception as e:
        logger.error(f"LLM usage stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# Workflow endpoints
@app.post("/api/v1/workflows/start")
async def start_workflow(request: dict):
    """Start a new workflow execution."""
    try:
        # Parse workflow type
        workflow_type_str = request.get("workflow_type", "sequential_analysis")
        workflow_type = WorkflowType[workflow_type_str.upper()]

        # Create workflow request
        workflow_request = WorkflowRequest(
            workflow_type=workflow_type,
            user_id=request.get("user_id", "test-user"),
            team_id=request.get("team_id", "test-team"),
            correlation_id=request.get("correlation_id", str(datetime.now().timestamp())),
            input_data=request.get("input_data", {}),
            conversation_id=request.get("conversation_id"),
            thread_ts=request.get("thread_ts"),
            batch_items=request.get("batch_items"),
            priority=request.get("priority", 0),
            timeout_seconds=request.get("timeout_seconds", 300),
        )

        # Start workflow using Temporal client
        temporal_client = await get_temporal_client()

        # Map workflow type to workflow class
        workflow_class_map = {
            WorkflowType.SEQUENTIAL_ANALYSIS: SequentialAnalysisWorkflow,
            # Add other workflow mappings as needed
        }

        workflow_class = workflow_class_map.get(workflow_type, SequentialAnalysisWorkflow)
        response = await temporal_client.start_workflow(workflow_class, workflow_request)

        return {
            "status": "success",
            "workflow_id": response.workflow_id,
            "workflow_status": response.status.value,
            "message": f"Workflow {response.workflow_id} started",
        }

    except KeyError as e:
        raise HTTPException(
            status_code=400, detail=f"Invalid workflow type: {workflow_type_str}"
        ) from e
    except Exception as e:
        logger.error(f"Failed to start workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/v1/workflows/{workflow_id}/status")
async def get_workflow_status(workflow_id: str):
    """Get the status of a workflow execution."""
    try:
        temporal_client = await get_temporal_client()
        response = await temporal_client.get_workflow_status(workflow_id)

        if not response:
            raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")

        return {
            "status": "success",
            "workflow_id": response.workflow_id,
            "workflow_type": response.workflow_type.value,
            "workflow_status": response.status.value,
            "result": response.result,
            "error": response.error,
            "activities_completed": response.activities_completed,
            "activities_failed": response.activities_failed,
            "duration_ms": response.duration_ms,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow status: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.delete("/api/v1/workflows/{workflow_id}/cancel")
async def cancel_workflow(workflow_id: str):
    """Cancel a running workflow."""
    try:
        temporal_client = await get_temporal_client()
        cancelled = await temporal_client.cancel_workflow(workflow_id)

        if not cancelled:
            raise HTTPException(
                status_code=404, detail=f"Workflow {workflow_id} not found or already completed"
            )

        return {
            "status": "success",
            "workflow_id": workflow_id,
            "message": f"Workflow {workflow_id} cancelled",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/v1/workflows")
async def list_workflows(
    user_id: str = None, workflow_type: str = None, status: str = None, limit: int = 20
):
    """List workflows with optional filtering."""
    try:
        temporal_client = await get_temporal_client()

        # Parse optional filters
        wf_type = WorkflowType[workflow_type.upper()] if workflow_type else None
        wf_status = WorkflowStatus[status.upper()] if status else None

        # Get workflows
        workflows = await temporal_client.list_workflows(
            user_id=user_id, workflow_type=wf_type, status=wf_status, limit=limit
        )

        return {
            "status": "success",
            "workflows": [
                {
                    "workflow_id": wf.workflow_id,
                    "workflow_type": wf.workflow_type.value,
                    "status": wf.status.value,
                    "user_id": wf.user_id,
                    "team_id": wf.team_id,
                    "duration_ms": wf.duration_ms,
                }
                for wf in workflows
            ],
            "count": len(workflows),
        }

    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"Invalid filter value: {str(e)}") from e
    except Exception as e:
        logger.error(f"Failed to list workflows: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/v1/workflows/metrics")
async def get_workflow_metrics():
    """Get Temporal workflow metrics."""
    try:
        from src.services.workflow.worker import get_temporal_worker

        temporal_worker = await get_temporal_worker()
        worker_status = temporal_worker.get_status()

        return {
            "status": "success",
            "metrics": {
                "worker_status": worker_status,
                "temporal_version": "1.22.0",  # From docker-compose
                "system": "temporal",
            },
        }

    except Exception as e:
        logger.error(f"Failed to get Temporal metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# Slack Integration endpoints
slack_handler = None  # Global handler for dual mode support


@app.post("/api/v1/slack/events")
async def slack_events(request: Request):
    """Slack events endpoint for HTTP Mode."""
    global slack_handler

    if not slack_handler:
        raise HTTPException(status_code=503, detail="Slack integration not initialized")

    try:
        # Get the Slack app from handler for HTTP mode processing
        slack_app = await slack_handler.get_app_for_http_mode()

        # Process the request through Slack Bolt framework
        from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler

        app_handler = AsyncSlackRequestHandler(slack_app)
        return await app_handler.handle(request)

    except Exception as e:
        logger.error(f"Slack event processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Event processing failed") from e


@app.post("/api/v1/slack/interactive")
async def slack_interactive(request: Request):
    """Slack interactive components endpoint for HTTP Mode."""
    global slack_handler

    if not slack_handler:
        raise HTTPException(status_code=503, detail="Slack integration not initialized")

    try:
        # Get the Slack app from handler for HTTP mode processing
        slack_app = await slack_handler.get_app_for_http_mode()

        # Process the request through Slack Bolt framework
        from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler

        app_handler = AsyncSlackRequestHandler(slack_app)
        return await app_handler.handle(request)

    except Exception as e:
        logger.error(f"Slack interactive processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Interactive processing failed") from e


@app.post("/api/v1/slack/commands")
async def slack_commands(request: Request):
    """Slack slash commands endpoint for HTTP Mode."""
    global slack_handler

    if not slack_handler:
        raise HTTPException(status_code=503, detail="Slack integration not initialized")

    try:
        # Get the Slack app from handler for HTTP mode processing
        slack_app = await slack_handler.get_app_for_http_mode()

        # Process the request through Slack Bolt framework
        from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler

        app_handler = AsyncSlackRequestHandler(slack_app)
        return await app_handler.handle(request)

    except Exception as e:
        logger.error(f"Slack command processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Command processing failed") from e


@app.get("/api/v1/slack/health")
async def slack_health():
    """Slack integration health check."""
    global slack_handler

    if not slack_handler:
        return {"status": "not_initialized", "mode": "none"}

    try:
        health_status = await slack_handler.health_check()
        return health_status
    except Exception as e:
        return {"status": "error", "error": str(e)}


# Activity Analysis endpoint (implemented)
@app.post("/api/v1/analyze")
async def analyze_activity(request: dict):
    """Activity analysis endpoint integrated with conversation intelligence."""
    try:
        # Get conversation intelligence system
        if slack_handler:
            conversation_manager = slack_handler.conversation_manager

            # Use conversation intelligence for analysis
            intent_result = await conversation_manager.conversation_intelligence.analyze_message(
                message=request.get("text", ""),
                user_id=request.get("user_id", "api_user"),
                thread_id=request.get("thread_id"),
                conversation_history=request.get("context", []),
            )

            return {
                "status": "success",
                "analysis": {
                    "intent_type": intent_result.intent_type,
                    "confidence": intent_result.confidence,
                    "needs_clarification": intent_result.needs_clarification,
                    "clarification_message": intent_result.clarification_message,
                    "extracted_entities": intent_result.extracted_entities,
                    "context_summary": intent_result.context_summary,
                },
            }
        else:
            return {
                "status": "service_unavailable",
                "message": "Analysis service not available - Slack integration not initialized",
            }

    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ===============================================================================
# CLI/Standalone Entry Point (from main.py functionality)
# ===============================================================================


async def initialize_standalone_application():
    """Initialize application for standalone/CLI mode (from main.py)."""
    from src.infrastructure.config import get_configuration_health, load_configuration
    from src.infrastructure.monitoring import start_metrics_server
    from src.shared.logging import get_logger

    logger = get_logger(__name__)
    logger.info("🚀 Starting ReflectAI (Standalone Mode)")

    try:
        # Load configuration
        config = load_configuration()
        logger.info(f"Configuration loaded successfully - environment: {config.app.environment}")

        # Start metrics server if enabled
        if config.monitoring.metrics_enabled:
            start_metrics_server(port=config.monitoring.metrics_port)
            logger.info(f"Metrics server started on port {config.monitoring.metrics_port}")

        # Log configuration health
        health = get_configuration_health()
        logger.info(f"Application initialized successfully - health: {health}")

        return config

    except Exception as e:
        logger.error(f"Failed to initialize application: {str(e)}", exc_info=True)
        raise


async def main():
    """Main application entry point for CLI/standalone mode."""
    import asyncio

    from src.shared.logging import configure_logging, get_logger

    try:
        # Configure logging first
        configure_logging()
        logger = get_logger(__name__)

        # Initialize application
        config = await initialize_standalone_application()

        logger.info(f"🎯 ReflectAI Platform Application - {config.app.environment}")

        # Keep application running
        logger.info("Application ready - Press Ctrl+C to stop")
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutdown signal received")

    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"Application startup failed: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        logger = get_logger(__name__)
        logger.info("🛑 ReflectAI application shutdown complete")
