"""
Simple HTTP Metrics Middleware

Provides clean metrics collection without registry conflicts.
Integrates ReflectAI error metrics for comprehensive error tracking.
"""

import time
import uuid
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.shared.error_metrics import ErrorMetricsCollector
from src.shared.exceptions import ReflectAIError
from src.shared.logging import get_logger

from .observability import (
    ActiveRequestTracker,
    set_correlation_id,
    track_error,
    track_request,
)

logger = get_logger(__name__)


class SimpleMetricsMiddleware(BaseHTTPMiddleware):
    """Simple middleware for HTTP request metrics and comprehensive error tracking."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.error_metrics = ErrorMetricsCollector(component="http_middleware")
        logger.info("Simple metrics middleware initialized with error tracking")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate correlation ID
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        set_correlation_id(correlation_id)

        # Track active request
        endpoint = request.url.path
        start_time = time.time()

        with ActiveRequestTracker(endpoint):
            try:
                # Log request start
                logger.info(
                    f"Request started - {correlation_id} - {request.method} {endpoint} from {request.client.host if request.client else 'unknown'}"
                )

                # Process request
                response = await call_next(request)

                # Calculate duration and track metrics
                duration = time.time() - start_time
                track_request(
                    method=request.method,
                    endpoint=endpoint,
                    status_code=response.status_code,
                    duration=duration,
                )

                # Add correlation ID to response
                response.headers["X-Correlation-ID"] = correlation_id

                # Log success
                logger.info(
                    f"Request completed - {correlation_id} - {response.status_code} - {duration:.3f}s"
                )

                return response

            except Exception as e:
                # Track error and duration
                duration = time.time() - start_time

                # Use comprehensive error tracking for ReflectAI errors
                if isinstance(e, ReflectAIError):
                    self.error_metrics.track_error(
                        error=e, handler_type="middleware", processing_duration=duration
                    )
                    # Track user-facing errors
                    if e.user_message:
                        self.error_metrics.track_user_facing_error(
                            error=e, notification_method="http"
                        )
                else:
                    # Fallback to basic error tracking for non-ReflectAI errors
                    track_error(component="http_middleware", error_type=type(e).__name__)

                # Track request metrics
                track_request(
                    method=request.method, endpoint=endpoint, status_code=500, duration=duration
                )

                # Log error
                logger.error(
                    f"Request failed - {correlation_id} - {str(e)} - {duration:.3f}s", exc_info=True
                )

                # Re-raise
                raise
