"""
Correlation ID middleware for HTTP requests.

Provides automatic correlation ID generation/propagation for all HTTP requests,
integrating with the logging context for end-to-end request tracing.
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from src.infrastructure.monitoring.simple.correlation_manager import (
    extract_correlation_from_headers,
    get_or_create_correlation_id,
)
from src.shared.logging import LoggingContext, get_logger

logger = get_logger(__name__)


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to generate/propagate correlation IDs for HTTP requests.

    Features:
    - Extracts correlation ID from request headers (if present)
    - Generates new correlation ID (if not present)
    - Adds correlation ID to response headers
    - Sets up logging context for the request
    - Stores correlation ID in request state for handlers to access

    The correlation ID follows the request through the entire system,
    appearing in all logs and being returned in response headers.
    """

    async def dispatch(self, request: Request, call_next):
        """Process request with correlation ID."""

        # Extract correlation ID from request headers or generate new one
        correlation_id = extract_correlation_from_headers(dict(request.headers))
        if not correlation_id:
            correlation_id = get_or_create_correlation_id()

        # Set up logging context with correlation ID
        # This ensures all logs within this request include the correlation ID
        with LoggingContext(correlation_id=correlation_id):
            # Store correlation ID in request state for handlers to access
            request.state.correlation_id = correlation_id

            logger.debug(
                "Processing request with correlation ID",
                correlation_id=correlation_id,
                method=request.method,
                path=request.url.path,
            )

            # Process the request
            response = await call_next(request)

            # Add correlation ID to response headers for client tracking
            response.headers["X-Correlation-ID"] = correlation_id
            response.headers["X-Request-ID"] = correlation_id  # Alternative header name

            return response
