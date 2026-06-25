"""
Configuration Management Infrastructure for ReflectAI

Streamlined configuration with intelligent Doppler integration:
- Smart Doppler > Environment Variables > Code Defaults
- Zero YAML files, zero secrets in git
- Production-ready with proper fallbacks
"""

from .config_manager import (
    ConfigManager,
    get_config,
    get_config_manager,
    get_configuration_health,
    get_secret,
    get_secrets_manager,  # Merged from SecretsManager
    load_configuration,
)
from .environment_validator import (
    EnvironmentValidationReport,
    EnvironmentValidator,
    ValidationLevel,
    ValidationResult,
    get_environment_validator,
    validate_environment_on_startup,
)

# Main configuration exports (streamlined system)
__all__ = [
    "ConfigManager",
    "get_config_manager",
    "get_secrets_manager",  # Alias to get_config_manager (merged from SecretsManager)
    "load_configuration",
    "get_configuration_health",
    "get_config",
    "get_secret",
    "EnvironmentValidator",
    "ValidationLevel",
    "ValidationResult",
    "EnvironmentValidationReport",
    "get_environment_validator",
    "validate_environment_on_startup",
]
