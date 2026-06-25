"""
Smart Environment-Based Configuration for ReflectAI
Intelligent approach: Doppler > Environment Variables > Code Defaults

Streamlined configuration system with:
- Zero YAML files
- Intelligent Doppler integration
- Environment variable fallback
- Code-based defaults
- Production security
"""

import os
from datetime import datetime
from typing import Any

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    requests = None
    REQUESTS_AVAILABLE = False

try:
    from dopplersdk import DopplerSDK

    DOPPLER_SDK_AVAILABLE = True
except ImportError:
    DOPPLER_SDK_AVAILABLE = False

from src.shared import ReflectAIError, get_logger
from src.version import get_base_version

logger = get_logger(__name__)


class SmartEnvLoader:
    """
    Intelligent environment variable loader with Doppler integration.
    Priority: Doppler > Environment Variables > Defaults
    """

    def __init__(self) -> None:
        self._doppler_available = False
        self._doppler_secrets: dict[str, str] = {}
        self._load_doppler()

    def _load_doppler(self) -> None:
        """Load secrets from Doppler using SDK first, then REST API fallback."""
        doppler_token = os.getenv("DOPPLER_TOKEN")
        if not doppler_token:
            logger.debug(
                "No DOPPLER_TOKEN found - using environment variables only"
            )
            return

        # Try SDK approach first
        if DOPPLER_SDK_AVAILABLE:
            try:
                logger.info(
                    "DOPPLER_TOKEN found - trying Doppler SDK approach"
                )

                # Initialize Doppler SDK
                doppler = DopplerSDK()
                doppler.set_access_token(doppler_token)

                # Get all secrets using SDK
                project = os.getenv("DOPPLER_PROJECT", "reflectai")
                config = os.getenv("DOPPLER_CONFIG", "dev")

                secrets_response = doppler.secrets.list(
                    project=project,
                    config=config,
                )

                if hasattr(secrets_response, "secrets"):
                    # SDK returns secrets as dictionaries
                    self._doppler_secrets = {
                        key: (
                            secret["computed"]
                            if isinstance(secret, dict)
                            else secret
                        )
                        for key, secret in secrets_response.secrets.items()
                    }
                    self._doppler_available = True
                    logger.info(
                        f"Successfully loaded {len(self._doppler_secrets)} "
                        f"secrets from Doppler SDK"
                    )
                    return

            except Exception as e:
                logger.warning(
                    f"Doppler SDK failed: {e} - trying REST API fallback"
                )

        # Fallback to REST API approach
        if REQUESTS_AVAILABLE:
            try:
                logger.info("Trying Doppler REST API approach")

                # Make API call to get all secrets
                url = "https://api.doppler.com/v3/configs/config/secrets"
                headers = {
                    "Authorization": f"Bearer {doppler_token}",
                    "Accept": "application/json",
                }

                # Always specify project and config for REST API
                params = {
                    "project": os.getenv("DOPPLER_PROJECT", "reflectai"),
                    "config": os.getenv("DOPPLER_CONFIG", "dev"),
                }

                logger.debug(f"Doppler API call with params: {params}")

                response = requests.get(
                    url, headers=headers, params=params, timeout=10
                )

                if response.status_code == 200:
                    secrets_data = response.json()
                    self._doppler_secrets = {
                        key: value["computed"]
                        for key, value in secrets_data.get(
                            "secrets", {}
                        ).items()
                    }
                    self._doppler_available = True
                    logger.info(
                        f"Successfully loaded {len(self._doppler_secrets)} "
                        f"secrets from Doppler REST API"
                    )
                else:
                    logger.warning(
                        f"Doppler REST API error: {response.status_code} - "
                        f"{response.text}"
                    )

            except Exception as e:
                logger.warning(
                    f"Failed to load from Doppler REST API: {e} - "
                    f"falling back to environment variables"
                )
        else:
            logger.warning(
                "No requests library available - "
                "falling back to environment variables"
            )

    def get(self, key: str, default: str | None = None, required: bool = False) -> str | None:
        """Get configuration value with intelligent priority."""
        value = None

        # =============================================================================
        # DOCKER INFRASTRUCTURE OVERRIDE PATTERN
        # =============================================================================
        # Why: In Docker environments, services use container names (e.g., 'postgres',
        #      'redis', 'temporal') instead of 'localhost'. Doppler config typically
        #      contains localhost values for local development.
        #
        # Solution: For infrastructure connection variables, environment variables
        #           (from docker-compose.yml) take precedence over Doppler secrets.
        #
        # When: This only applies to these specific infrastructure connection keys.
        #       All other configuration follows normal precedence: Doppler > env vars.
        #
        # Example: DATABASE_URL in Doppler = postgresql://user:pass@localhost:5432/db
        #          DATABASE_URL in Docker   = postgresql://user:pass@postgres:5432/db
        #          Docker env var wins for this specific key.
        # =============================================================================
        docker_infrastructure_keys = {
            "TEMPORAL_HOST", "DATABASE_URL", "REDIS_URL",
            "REDIS_HOST", "POSTGRES_HOST"
        }

        # 1. For Docker infrastructure keys, check environment variables FIRST
        if key in docker_infrastructure_keys and key in os.environ:
            value = os.environ[key]
            logger.debug(f"Config '{key}' loaded from environment variable (Docker override)")

        # 2. Try Doppler
        elif self._doppler_available and key in self._doppler_secrets:
            value = self._doppler_secrets[key]
            logger.debug(f"Config '{key}' loaded from Doppler")

        # 3. Fallback to environment variable
        elif key in os.environ:
            value = os.environ[key]
            logger.debug(f"Config '{key}' loaded from environment variable")

        # 4. Use default
        else:
            value = default
            if value is not None:
                logger.debug(f"Config '{key}' using default value")

        # Handle required fields
        if required and not value:
            raise ValueError(
                f"Required configuration '{key}' not found in Doppler or environment variables. "
                f"Please set {key} in Doppler or your .env file."
            )

        return value

    def get_bool(self, key: str, default: bool = False, required: bool = False) -> bool:
        """Get boolean configuration value."""
        value = self.get(key, str(default).lower(), required)
        if value is None:
            return default
        return str(value).lower() in ("true", "1", "yes", "on")

    def get_int(self, key: str, default: int = 0, required: bool = False) -> int:
        """Get integer configuration value."""
        value = self.get(key, str(default), required)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            logger.warning(
                f"Config '{key}' value '{value}' is not a valid integer, using default {default}"
            )
            return default

    def get_float(self, key: str, default: float = 0.0, required: bool = False) -> float:
        """Get float configuration value."""
        value = self.get(key, str(default), required)
        if value is None:
            return default
        try:
            return float(value)
        except ValueError:
            logger.warning(
                f"Config '{key}' value '{value}' is not a valid float, using default {default}"
            )
            return default

    def is_doppler_available(self) -> bool:
        """Check if Doppler is available and working."""
        return self._doppler_available

    def get_source_info(self) -> dict[str, Any]:
        """Get information about configuration sources."""
        return {
            "doppler_available": self._doppler_available,
            "doppler_secrets_count": len(self._doppler_secrets) if self._doppler_available else 0,
            "environment_vars_count": len(os.environ),
            "doppler_token_present": bool(os.getenv("DOPPLER_TOKEN")),
        }


# Global smart environment loader
_smart_env: SmartEnvLoader | None = None


def get_smart_env() -> SmartEnvLoader:
    """Get global smart environment loader instance."""
    global _smart_env
    if _smart_env is None:
        _smart_env = SmartEnvLoader()
    return _smart_env


# Configuration classes with code-based defaults
class ApplicationConfig:
    """Application configuration with smart Doppler + environment loading."""

    def __init__(self) -> None:
        env = get_smart_env()
        self.name = env.get("APP_NAME", "reflectai")
        # Use centralized version from src/version.py (reads from pyproject.toml)
        self.version = get_base_version()
        self.debug = env.get_bool("DEBUG", False)
        self.log_level = (env.get("LOG_LEVEL", "INFO") or "INFO").upper()
        self.environment = env.get("ENVIRONMENT", "development")


class DatabaseConfig:
    """Database configuration with smart Doppler + environment loading and fail-fast validation."""

    def __init__(self) -> None:
        env = get_smart_env()

        # CRITICAL: Either/Or pattern for database connection
        # Option 1: DATABASE_URL (preferred - simpler, single config)
        # Option 2: Individual components (DB_HOST + DB_PORT + DB_NAME + DB_USER + DB_PASSWORD)
        self.url = env.get("DATABASE_URL")

        # Parse connection details from URL if provided, otherwise build from parts
        if self.url:
            # Parse DATABASE_URL to extract individual components
            # Format: postgresql://username:password@host:port/database
            from urllib.parse import urlparse
            parsed = urlparse(self.url)
            self.host = parsed.hostname or "localhost"
            self.port = parsed.port or 5432
            self.name = parsed.path.lstrip('/') or "reflectai"
            self.username = parsed.username or "reflectai_user"
            self.password = parsed.password or ""
        else:
            # Build URL from individual components - all required if URL not provided
            # Fail-fast: if DATABASE_URL not provided, ALL components must be present
            self.host = env.get("DB_HOST", required=True)
            self.port = env.get_int("DB_PORT", required=True)
            self.name = env.get("DB_NAME", required=True)
            self.username = env.get("DB_USER", required=True)
            self.password = env.get("DB_PASSWORD", required=True)
            self.url = f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.name}"

        # Pool settings with defaults (optional)
        self.pool_size = env.get_int("DB_POOL_SIZE", 5)
        self.max_overflow = env.get_int("DB_MAX_OVERFLOW", 10)
        self.echo_sql = env.get_bool("DB_ECHO_SQL", False)

        # Connection timeouts (optional)
        self.connect_timeout = env.get_int("DB_CONNECT_TIMEOUT", 30)
        self.query_timeout = env.get_int("DB_QUERY_TIMEOUT", 60)


class MonitoringConfig:
    """Monitoring configuration with smart Doppler + environment loading."""

    def __init__(self) -> None:
        env = get_smart_env()
        self.metrics_enabled = env.get_bool("METRICS_ENABLED", True)
        self.metrics_port = env.get_int("METRICS_PORT", 8080)
        self.health_check_enabled = env.get_bool("HEALTH_CHECK_ENABLED", True)
        self.health_check_port = env.get_int("HEALTH_CHECK_PORT", 8090)
        self.correlation_id_enabled = env.get_bool("CORRELATION_ID_ENABLED", True)
        self.json_logs = env.get_bool("JSON_LOGS", False)
        self.log_rotation_mb = env.get_int("LOG_ROTATION_MB", 100)
        self.log_retention_days = env.get_int("LOG_RETENTION_DAYS", 30)


class TemporalConfig:
    """Temporal workflow configuration with smart Doppler + environment loading."""

    def __init__(self) -> None:
        env = get_smart_env()
        # CRITICAL: Temporal connection required for workflow orchestration
        self.host = env.get("TEMPORAL_HOST", required=True)
        self.port = env.get_int("TEMPORAL_PORT", required=True)
        self.namespace = env.get("TEMPORAL_NAMESPACE", required=True)
        # Optional fields with defaults
        self.task_queue = env.get("TEMPORAL_TASK_QUEUE", "reflectai-queue")
        self.tls_enabled = env.get_bool("TEMPORAL_TLS_ENABLED", False)
        self.run_local_server = env.get_bool("TEMPORAL_RUN_LOCAL", True)
        self.prometheus_enabled = env.get_bool("TEMPORAL_PROMETHEUS_ENABLED", True)
        self.log_level = env.get("TEMPORAL_LOG_LEVEL", "INFO")


class EnterpriseGatewayConfig:
    """EnterpriseGateway LLM Gateway configuration - corporate LLM access."""

    def __init__(self) -> None:
        env = get_smart_env()
        # CRITICAL: All EnterpriseGateway fields required for corporate LLM gateway access
        self.base_url = env.get("LLM_GATEWAY_BASE_URL", required=True)
        self.client_id = env.get("LLM_GATEWAY_CLIENT_ID", required=True)
        self.client_secret = env.get("LLM_GATEWAY_CLIENT_SECRET", required=True)
        self.token_url = env.get("LLM_GATEWAY_TOKEN_URL", required=True)
        self.tenant = env.get("LLM_GATEWAY_TENANT", required=True)
        self.star = env.get("LLM_GATEWAY_STAR", required=True)
        # Optional OAuth scope
        self.oauth_scope = env.get("LLM_GATEWAY_OAUTH_SCOPE", "default")


class SlackConfig:
    """Slack integration configuration."""

    def __init__(self) -> None:
        env = get_smart_env()
        # CRITICAL: All Slack credentials required for bot operation
        self.bot_token = env.get("SLACK_BOT_TOKEN", required=True)
        self.app_token = env.get("SLACK_APP_TOKEN", required=True)
        self.signing_secret = env.get("SLACK_SIGNING_SECRET", required=True)
        # OAuth disabled - using simple bot token authentication for development
        self.client_id = None
        self.client_secret = None
        # Optional configuration
        self.rate_limit_retries = env.get_int("SLACK_RATE_LIMIT_RETRIES", 3)


class SecurityConfig:
    """Security and encryption configuration."""

    def __init__(self) -> None:
        env = get_smart_env()
        # CRITICAL: All security keys required for production operation
        self.jwt_secret_key = env.get("JWT_SECRET_KEY", required=True)
        self.encryption_key = env.get("ENCRYPTION_KEY", required=True)
        self.api_secret_key = env.get("API_SECRET_KEY", required=True)
        self.audit_encryption_key = env.get("AUDIT_ENCRYPTION_KEY", required=True)


class CacheConfig:
    """Cache configuration with smart Doppler + environment loading."""

    def __init__(self) -> None:
        env = get_smart_env()
        self.type = env.get("CACHE_TYPE", "redis")

        # CRITICAL: Either/Or pattern for Redis connection
        # Option 1: REDIS_URL (preferred - simpler, single config)
        # Option 2: Individual components (REDIS_HOST + REDIS_PORT + REDIS_PASSWORD)
        self.redis_url = env.get("REDIS_URL")

        if not self.redis_url:
            # Build URL from individual components - all required if URL not provided
            host = env.get("REDIS_HOST", required=True)
            port = env.get_int("REDIS_PORT", required=True)
            password = env.get("REDIS_PASSWORD", required=True)
            db = env.get_int("REDIS_DB", 0)  # DB is optional, defaults to 0

            # Build URL with password (required in production)
            self.redis_url = f"redis://:{password}@{host}:{port}/{db}"

        # Optional cache settings
        self.memory_max_size = env.get_int("CACHE_MEMORY_MAX_SIZE", 1000)
        self.default_ttl = env.get_int("CACHE_DEFAULT_TTL", 3600)
        self.enabled = env.get_bool("CACHE_ENABLED", True)


class ReflectAIConfig:
    """Main application configuration with fail-fast validation."""

    def __init__(self) -> None:
        self.app = ApplicationConfig()
        self.database = DatabaseConfig()
        self.monitoring = MonitoringConfig()
        self.temporal = TemporalConfig()
        self.cache = CacheConfig()

        # New specialized configs with fail-fast validation
        self.enterprise_gateway = EnterpriseGatewayConfig()
        self.slack = SlackConfig()
        self.security = SecurityConfig()

        # Metadata
        smart_env = get_smart_env()
        source_info = smart_env.get_source_info()
        if source_info["doppler_available"]:
            self.config_source = "doppler+env_vars+code_defaults"
        else:
            self.config_source = "env_vars+code_defaults"
        self.loaded_at = datetime.now()


class ConfigManager:
    """
    Ultra-simple configuration manager.
    No YAML files, no complexity - just environment variables and code defaults.
    """

    def __init__(self) -> None:
        self._config: ReflectAIConfig | None = None
        logger.info(
            "Initializing simple configuration manager with environment "
            "variables and code defaults"
        )

    def load_configuration(self, environment: str = None) -> ReflectAIConfig:
        """Load configuration using smart Doppler + environment variables."""
        try:
            # Set environment if provided
            if environment:
                os.environ["ENVIRONMENT"] = environment

            # Get smart env info for logging
            smart_env = get_smart_env()
            source_info = smart_env.get_source_info()

            logger.info(
                "Loading configuration with intelligent Doppler + environment integration",
                extra={
                    "environment": smart_env.get("ENVIRONMENT", "development"),
                    "doppler_available": source_info["doppler_available"],
                    "doppler_secrets_count": source_info["doppler_secrets_count"],
                },
            )

            # Create configuration - smart env loading handles Doppler priority
            self._config = ReflectAIConfig()

            logger.info(
                "Configuration loaded successfully",
                extra={
                    "environment": self._config.app.environment,
                    "source": self._config.config_source,
                    "doppler_used": source_info["doppler_available"],
                },
            )

            return self._config

        except Exception as e:
            logger.error("Failed to load configuration", extra={"error": str(e)}, exc_info=True)
            raise ReflectAIError(
                message="Configuration loading failed",
                error_code="CONFIG_LOAD_ERROR",
                severity="HIGH",
                category="SYSTEM",
            ) from e

    def get_config(self) -> ReflectAIConfig:
        """Get current configuration."""
        if self._config is None:
            self._config = self.load_configuration()
        return self._config

    async def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key using dot notation."""
        try:
            config = self.get_config()

            # Handle dot notation (e.g., "database.host")
            if "." in key:
                parts = key.split(".")
                current = config
                for part in parts:
                    if hasattr(current, part):
                        current = getattr(current, part)
                    else:
                        return default
                return current
            else:
                return getattr(config, key, default)

        except Exception as e:
            logger.warning(f"Failed to get config key '{key}': {e}")
            return default

    def get_secret(self, key: str, default: Any = None, required: bool = False) -> Any:
        """
        Get secret with Doppler priority (merged from SecretsManager).

        Priority:
        1. Docker infrastructure override (DATABASE_URL, REDIS_URL, TEMPORAL_HOST)
        2. Doppler secrets
        3. Environment variables
        4. Default value

        Args:
            key: Secret key name
            default: Default value if not found
            required: Raise error if missing

        Returns:
            Secret value

        Raises:
            ReflectAIError: If required secret is missing
        """
        # Docker infrastructure override pattern
        docker_infrastructure_keys = {
            "DATABASE_URL", "REDIS_URL", "TEMPORAL_HOST",
            "REDIS_HOST", "POSTGRES_HOST"
        }

        if key in docker_infrastructure_keys:
            env_value = os.getenv(key)
            if env_value is not None:
                logger.debug(f"Retrieved secret from environment (Docker override): {key}")
                return env_value

        # Use SmartEnvLoader which has Doppler integration
        smart_env = get_smart_env()
        value = smart_env.get(key, default)

        if required and value is None:
            raise ReflectAIError(
                message=f"Required secret missing: {key}",
                error_code="SECRET_MISSING",
                severity="HIGH",
                category="CONFIGURATION",
            )

        return value

    def get_slack_secrets(self) -> dict[str, str]:
        """Get Slack integration secrets."""
        return {
            "bot_token": self.get_secret("SLACK_BOT_TOKEN", required=True),
            "signing_secret": self.get_secret("SLACK_SIGNING_SECRET", required=True),
            "app_token": self.get_secret("SLACK_APP_TOKEN", required=False),
        }

    def get_health_status(self) -> dict[str, Any]:
        """Get health status of configuration system."""
        smart_env = get_smart_env()
        source_info = smart_env.get_source_info()

        return {
            "config_loaded": self._config is not None,
            "environment": self._config.app.environment if self._config else "unknown",
            "loaded_at": self._config.loaded_at.isoformat() if self._config else None,
            "config_source": self._config.config_source if self._config else "unknown",
            "doppler_enabled": source_info["doppler_token_present"],
            "doppler_available": source_info["doppler_available"],
            "doppler_secrets_count": source_info["doppler_secrets_count"],
        }


# Global configuration manager instance
_config_manager: ConfigManager | None = None


def get_config_manager() -> ConfigManager:
    """Get global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def load_configuration(environment: str = None) -> ReflectAIConfig:
    """Load application configuration."""
    return get_config_manager().load_configuration(environment)


def get_configuration_health() -> dict[str, Any]:
    """Get health status of configuration system."""
    return get_config_manager().get_health_status()


# Async convenience functions
async def get_config(key: str, default: Any = None) -> Any:
    """Convenience function to get configuration value."""
    config_manager = get_config_manager()
    return await config_manager.get(key, default)


async def get_secret(key: str, default: Any = None) -> Any:
    """Convenience function to get secret configuration value."""
    config_manager = get_config_manager()
    return config_manager.get_secret(key, default)


# Alias for SecretsManager compatibility
def get_secrets_manager() -> ConfigManager:
    """
    Get configuration manager (merged from SecretsManager).
    This maintains API compatibility after merge.
    """
    return get_config_manager()
