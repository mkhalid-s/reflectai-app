# Multi-stage Dockerfile for ReflectAI Platform
# Optimized for both development and production builds with PDM

# ===============================================================================
# Build Arguments
# ===============================================================================
ARG PYTHON_VERSION=3.11
ARG PDM_VERSION=2.20.1
ARG NODE_VERSION=18

# ===============================================================================
# Stage 1: Base Python Image
# ===============================================================================
FROM python:${PYTHON_VERSION}-slim AS base

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100

# ===============================================================================
# Stage 2: Build Dependencies
# ===============================================================================
FROM base AS builder
ARG PDM_VERSION

# Install system dependencies for building (minimal set)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Install PDM and its runtime compatibility dependency.
RUN pip install six pdm==${PDM_VERSION}

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml pdm.lock* ./

# Install dependencies
RUN pdm config venv.in_project true && \
    pdm install --prod --no-self

# ===============================================================================
# Stage 3: Development Image
# ===============================================================================
FROM base AS development
ARG PDM_VERSION

# Install development tools + WeasyPrint dependencies (PDF generation)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    vim \
    cron \
    postgresql-client \
    libpq-dev \
    redis-tools \
    netcat-openbsd \
    procps \
    ca-certificates \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Copy and install Zscaler root certificate (for corporate proxy)
# This is optional - if cert doesn't exist, build continues without it
# Note: COPY will fail if no .crt files exist, so we create a dummy .keep file
COPY docker/certs/ /tmp/certs/
RUN if [ -f /tmp/certs/*.crt ]; then \
        cp /tmp/certs/*.crt /usr/local/share/ca-certificates/ && \
        update-ca-certificates; \
    fi && \
    rm -rf /tmp/certs

# Install PDM for development

WORKDIR /app

# Copy dependency files
COPY pyproject.toml pdm.lock* ./

# Install all dependencies (including dev)
RUN pip install --upgrade pip setuptools wheel && \
    pip install six pdm==${PDM_VERSION} && \
    pdm config venv.in_project true && \
    pdm install --no-self

# Copy application code
COPY . .

# Create directories
RUN mkdir -p /app/data /app/logs /app/reports /app/cache /app/.venv

# Development health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8090/health || exit 1

# Expose ports
EXPOSE 3000 8080 8090 9090

# Development entry point
CMD ["pdm", "run", "uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "3000", "--reload"]

# ===============================================================================
# Stage 4: Testing Image
# ===============================================================================
FROM development AS testing

# Install test dependencies
RUN pdm install --group test

# Run tests
CMD ["pdm", "run", "pytest", "-v", "--cov=src", "--cov-report=term-missing"]

# ===============================================================================
# Stage 5: Production Image
# ===============================================================================
FROM base AS production

# Install runtime dependencies + WeasyPrint for PDF generation
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* \
    && apt-get clean \
    && apt-get autoclean

# Create non-root user
RUN groupadd -r appgroup && \
    useradd -r -g appgroup -u 1000 appuser && \
    mkdir -p /app && \
    chown -R appuser:appgroup /app

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv

# Copy application code
COPY --chown=appuser:appgroup . .

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/reports /app/cache && \
    chown -R appuser:appgroup /app

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app:$PYTHONPATH"

# Switch to non-root user
USER appuser

# Production health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD curl -f http://localhost:8090/health/ready || exit 1

# Expose ports
EXPOSE 3000 8080 8090

# Production entry point with proper signal handling
ENTRYPOINT ["/app/.venv/bin/uvicorn"]
CMD ["src.app:app", "--host", "0.0.0.0", "--port", "3000", "--workers", "4"]

# ===============================================================================
# Stage 6: Lightweight Production (Alpine-based)
# ===============================================================================
FROM python:${PYTHON_VERSION}-alpine AS production-alpine

# Install runtime dependencies
RUN apk add --no-cache \
    curl \
    postgresql-client \
    libpq

# Create non-root user
RUN addgroup -S appgroup && \
    adduser -S appuser -G appgroup -u 1000

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv

# Copy application code
COPY --chown=appuser:appgroup . .

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/reports /app/cache && \
    chown -R appuser:appgroup /app

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app:$PYTHONPATH"

# Switch to non-root user
USER appuser

# Alpine health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD curl -f http://localhost:8090/health/ready || exit 1

# Expose ports
EXPOSE 3000 8080 8090

# Alpine entry point
ENTRYPOINT ["/app/.venv/bin/uvicorn"]
CMD ["src.app:app", "--host", "0.0.0.0", "--port", "3000", "--workers", "2"]