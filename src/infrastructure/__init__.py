"""
Infrastructure Layer for ReflectAI

Provides core infrastructure services including:
- Configuration Management (Doppler integration)
- Database Infrastructure (PostgreSQL 15)
- Security and Authentication
- Monitoring and Observability
- Caching (Redis)

Implements foundational infrastructure for ReflectAI platform.

Note: Workflow orchestration (Temporal) is provided by src.services.workflow
"""

# Configuration Management
from .config import (
    ConfigManager,
    EnvironmentValidationReport,
    EnvironmentValidator,
    ValidationLevel,
    ValidationResult,
    get_config_manager,
    get_configuration_health,
    get_environment_validator,
    get_secrets_manager,  # Now returns ConfigManager (merged)
    load_configuration,
    validate_environment_on_startup,
)

# Database Infrastructure
from .database.db_manager import (
    get_database_manager,
    initialize_database,
)

__all__ = [
    # Configuration Management
    "ConfigManager",
    "get_config_manager",
    "get_secrets_manager",  # Alias to get_config_manager (merged)
    "load_configuration",
    "get_configuration_health",
    "EnvironmentValidator",
    "ValidationLevel",
    "ValidationResult",
    "EnvironmentValidationReport",
    "get_environment_validator",
    "validate_environment_on_startup",
    # Database Infrastructure
    "get_database_manager",
    "initialize_database",
]
