# Makefile for ReflectAI Development
# This Makefile provides compatibility aliases for the unified ./dev CLI
#
# IMPORTANT: All commands now use the unified ./dev CLI tool
# Run './dev help' for full documentation

.PHONY: help install setup lint format type security deps-check test check clean server
.PHONY: setup-redis db-migrate db-reset run docker-up docker-down

# Default target shows help
help:  ## Show help message
	@echo "ReflectAI Development Commands (Makefile Compatibility)"
	@echo "======================================================="
	@echo ""
	@echo "RECOMMENDED: Use './dev' directly for all commands!"
	@echo "Example: ./dev setup all"
	@echo ""
	@echo "Available make targets (for backwards compatibility):"
	@echo ""
	@./dev help

install:  ## Install project dependencies
	@./dev setup deps

setup:  ## Setup development environment
	@./dev setup all

lint:  ## Run code linting with auto-fix
	@./dev check lint

format:  ## Format code
	@./dev check format

type:  ## Run type checking
	@./dev check type

security:  ## Run security scanning
	@./dev check security

test:  ## Run test suite with coverage
	@./dev test-coverage

test-no-cov:  ## Run test suite without coverage
	@./dev test

check:  ## Run full quality check (lint, type, security, tests)
	@./dev check

clean:  ## Clean up generated files and caches
	@./dev clean

server:  ## Start development server with hot reload
	@./dev run app

# Composite targets
dev-setup: install setup  ## Complete development setup
	@echo "✅ Development environment setup complete!"

ci-check: lint-check type security test  ## CI/CD quality checks
	@echo "✅ All CI checks passed!"

# Docker targets (for future use)
docker-build:  ## Build Docker image for development
	@docker build -f docker/Dockerfile.dev -t reflectai:dev .

docker-run:  ## Run application in Docker container
	@docker run -p 8000:8000 --env-file .env reflectai:dev

# Database targets (for future use when Task 6 is implemented)
db-up:  ## Start database services
	@docker-compose up -d postgres redis

db-down:  ## Stop database services  
	@docker-compose down

db-reset:  ## Reset database (drop and recreate)
	@python scripts/dev.py clean
	@docker-compose down -v
	@docker-compose up -d postgres redis
	@sleep 5
	@alembic upgrade head

# Redis Environment Management
setup-redis:  ## Setup full Redis development environment
	@echo "🚀 Setting up complete Redis development environment..."
	@python scripts/setup_redis_dev.py --full-setup --verbose
	@echo "✅ Redis development environment ready!"

setup-redis-minimal:  ## Setup minimal Redis with basic data
	@echo "🚀 Setting up minimal Redis environment..."
	@python scripts/setup_redis_dev.py --seed-data --warm-cache --verbose
	@echo "✅ Minimal Redis environment ready!"

reset-redis:  ## Reset all Redis development data
	@echo "🗑️  Resetting Redis development data..."
	@python scripts/setup_redis_dev.py --reset-development-data --verbose
	@echo "✅ Redis development data reset complete!"

validate-redis:  ## Run comprehensive Redis validation
	@echo "🔍 Running comprehensive Redis validation..."
	@python scripts/validate_redis.py --all --verbose --output validation_results.json
	@echo "✅ Redis validation complete! See validation_results.json for details."

test-redis:  ## Run task processing integration tests
	@echo "⚙️  Running task processing integration tests..."
	@python scripts/test_task_processing.py --integration-test --verbose --output test_results.json
	@echo "✅ Integration tests complete! See test_results.json for details."

health-check:  ## Run Redis health check
	@echo "🏥 Running Redis health check..."
	@./scripts/redis_health_check.sh --detailed --output health_report.json
	@echo "✅ Health check complete! See health_report.json for details."

redis-dev:  ## Start Redis Stack for development
	@echo "🐳 Starting Redis Stack for development..."
	@docker-compose --profile dev --profile redis-stack up -d redis-stack
	@echo "⏳ Waiting for Redis to be ready..."
	@sleep 5
	@./scripts/redis_health_check.sh || true
	@echo "✅ Redis Stack development environment is running!"
	@echo "   - Redis: localhost:6379"
	@echo "   - RedisInsight: http://localhost:8001"

redis-prod:  ## Start Redis in production mode
	@echo "🐳 Starting Redis in production mode..."
	@docker-compose --profile prod --profile redis up -d redis
	@echo "⏳ Waiting for Redis to be ready..."
	@sleep 5
	@./scripts/redis_health_check.sh || true
	@echo "✅ Redis production environment is running!"

redis-stop:  ## Stop Redis containers
	@echo "⏹️  Stopping Redis containers..."
	@docker-compose stop redis redis-stack redis-commander
	@echo "✅ Redis containers stopped!"

monitor-redis:  ## Show Redis monitoring dashboard
	@echo "📊 Redis Monitoring Dashboard"
	@echo "============================="
	@python scripts/setup_redis_dev.py --status
	@echo ""
	@echo "🔗 Access RedisInsight: http://localhost:8001"
	@echo "🔗 Access Redis Commander: http://localhost:8081"

clean-redis:  ## Clean up Redis data and containers
	@echo "🧹 Cleaning up Redis containers and data..."
	@docker-compose down redis redis-stack redis-commander
	@docker volume rm -f $$(docker volume ls -q | grep redis) 2>/dev/null || true
	@echo "✅ Redis cleanup complete!"

# Combined workflows
dev-start: redis-dev setup-redis  ## Start complete Redis development environment
	@echo "🎯 Complete development environment is ready!"
	@echo "Next steps: make validate-redis && make test-redis"

dev-test: validate-redis test-redis  ## Run all Redis tests
	@echo "🧪 All Redis tests completed!"

# Show available targets
.DEFAULT_GOAL := help