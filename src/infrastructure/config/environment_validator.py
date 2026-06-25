"""
Environment Validation for ReflectAI

Comprehensive environment validation system that checks all required
configurations, dependencies, and services before application startup.

Features:
- Configuration validation
- Secret availability verification
- Service connectivity checks
- Dependency validation
- Environment-specific requirements
"""

import asyncio
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from src.shared import ErrorCategory, ErrorSeverity, ReflectAIError, get_logger

from .config_manager import ReflectAIConfig, get_config_manager
from .config_manager import get_secrets_manager

logger = get_logger(__name__)


class ValidationLevel(str, Enum):
    """Validation severity levels."""

    CRITICAL = "critical"  # Must pass or app won't start
    WARNING = "warning"  # Can fail but app will start with degraded functionality
    INFO = "info"  # Informational only


@dataclass
class ValidationResult:
    """Result of an individual validation check."""

    check_name: str
    status: str  # "passed", "failed", "skipped"
    level: ValidationLevel
    message: str
    details: dict[str, Any] | None = None
    recovery_suggestions: list[str] | None = None


@dataclass
class EnvironmentValidationReport:
    """Complete environment validation report."""

    environment: str
    overall_status: str  # "passed", "failed", "warnings"
    critical_checks: list[ValidationResult]
    warning_checks: list[ValidationResult]
    info_checks: list[ValidationResult]
    total_checks: int
    passed_checks: int
    failed_checks: int
    warning_checks_count: int
    validation_time_seconds: float


class EnvironmentValidator:
    """
    Comprehensive environment validation system.

    Validates all aspects of the application environment:
    - Configuration files and values
    - Required environment variables
    - Service connectivity
    - Dependencies and versions
    - Security requirements
    """

    def __init__(self, config: ReflectAIConfig | None = None):
        """Initialize environment validator."""
        self.config = config or get_config_manager().get_config()
        self.secrets_manager = get_secrets_manager()
        self.checks: list[ValidationResult] = []

    async def validate_environment(self, environment: str = None) -> EnvironmentValidationReport:
        """
        Run comprehensive environment validation.

        Args:
            environment: Environment name to validate

        Returns:
            Validation report with all check results
        """
        start_time = asyncio.get_event_loop().time()
        environment = environment or self.config.app.environment
        self.checks = []

        logger.info(f"Starting environment validation for: {environment}")

        # Run all validation checks
        await self._validate_basic_environment()
        await self._validate_configuration()
        await self._validate_secrets()
        await self._validate_dependencies()
        await self._validate_services()
        await self._validate_database()
        await self._validate_cache()
        await self._validate_security()
        await self._validate_monitoring()
        await self._validate_environment_specific()

        # Generate report
        validation_time = asyncio.get_event_loop().time() - start_time
        report = self._generate_report(environment, validation_time)

        # Log results
        if report.overall_status == "failed":
            logger.error(
                f"Environment validation FAILED for {environment}",
                extra={
                    "environment": environment,
                    "total_checks": report.total_checks,
                    "failed_checks": report.failed_checks,
                    "critical_failures": len(
                        [
                            c
                            for c in self.checks
                            if c.level == ValidationLevel.CRITICAL and c.status == "failed"
                        ]
                    ),
                },
            )
        elif report.overall_status == "warnings":
            logger.warning(
                f"Environment validation passed with WARNINGS for {environment}",
                extra={
                    "environment": environment,
                    "total_checks": report.total_checks,
                    "warning_checks": report.warning_checks_count,
                },
            )
        else:
            logger.info(
                f"Environment validation PASSED for {environment}",
                extra={
                    "environment": environment,
                    "total_checks": report.total_checks,
                    "validation_time": f"{validation_time:.2f}s",
                },
            )

        return report

    async def _validate_basic_environment(self):
        """Validate basic environment setup."""
        # Check Python version
        import sys

        python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        if sys.version_info < (3, 11):  # noqa: UP036
            self._add_check(
                "python_version",
                "failed",
                ValidationLevel.CRITICAL,
                f"Python {python_version} not supported. Requires Python 3.11+",
                recovery_suggestions=["Upgrade to Python 3.11 or higher"],
            )
        else:
            self._add_check(
                "python_version",
                "passed",
                ValidationLevel.INFO,
                f"Python version {python_version} is supported",
            )

        # Check working directory and permissions
        try:
            current_dir = Path.cwd()
            if not current_dir.exists():
                self._add_check(
                    "working_directory",
                    "failed",
                    ValidationLevel.CRITICAL,
                    f"Working directory does not exist: {current_dir}",
                )
            elif not os.access(current_dir, os.R_OK | os.W_OK):
                self._add_check(
                    "working_directory",
                    "failed",
                    ValidationLevel.CRITICAL,
                    f"Insufficient permissions for working directory: {current_dir}",
                    recovery_suggestions=[
                        "Check file permissions",
                        "Run with appropriate user privileges",
                    ],
                )
            else:
                self._add_check(
                    "working_directory",
                    "passed",
                    ValidationLevel.INFO,
                    f"Working directory accessible: {current_dir}",
                )
        except Exception as e:
            self._add_check(
                "working_directory",
                "failed",
                ValidationLevel.CRITICAL,
                f"Error checking working directory: {str(e)}",
            )

        # Check required directories
        required_dirs = ["src", "config", "logs"]
        for dir_name in required_dirs:
            dir_path = Path(dir_name)
            if not dir_path.exists():
                if dir_name == "logs":
                    # Create logs directory if it doesn't exist
                    try:
                        dir_path.mkdir(exist_ok=True)
                        self._add_check(
                            f"directory_{dir_name}",
                            "passed",
                            ValidationLevel.WARNING,
                            f"Created missing directory: {dir_path}",
                        )
                    except Exception as e:
                        self._add_check(
                            f"directory_{dir_name}",
                            "failed",
                            ValidationLevel.WARNING,
                            f"Cannot create directory {dir_path}: {str(e)}",
                        )
                else:
                    level = (
                        ValidationLevel.CRITICAL if dir_name == "src" else ValidationLevel.WARNING
                    )
                    self._add_check(
                        f"directory_{dir_name}",
                        "failed",
                        level,
                        f"Required directory missing: {dir_path}",
                    )
            else:
                self._add_check(
                    f"directory_{dir_name}",
                    "passed",
                    ValidationLevel.INFO,
                    f"Directory exists: {dir_path}",
                )

    async def _validate_configuration(self):
        """Validate application configuration."""
        try:
            # Check if configuration loads without errors
            config = self.config

            self._add_check(
                "config_load",
                "passed",
                ValidationLevel.CRITICAL,
                "Configuration loaded successfully",
            )

            # Validate environment setting
            env = config.app.environment
            valid_environments = ["development", "staging", "production"]
            if env not in valid_environments:
                self._add_check(
                    "config_environment",
                    "failed",
                    ValidationLevel.WARNING,
                    f"Unexpected environment: {env}. Expected one of: {valid_environments}",
                )
            else:
                self._add_check(
                    "config_environment",
                    "passed",
                    ValidationLevel.INFO,
                    f"Environment set to: {env}",
                )

            # Validate log level
            log_level = config.app.log_level
            valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            if log_level not in valid_levels:
                self._add_check(
                    "config_log_level",
                    "failed",
                    ValidationLevel.WARNING,
                    f"Invalid log level: {log_level}. Expected one of: {valid_levels}",
                )
            else:
                self._add_check(
                    "config_log_level",
                    "passed",
                    ValidationLevel.INFO,
                    f"Log level set to: {log_level}",
                )

        except Exception as e:
            self._add_check(
                "config_load",
                "failed",
                ValidationLevel.CRITICAL,
                f"Configuration loading failed: {str(e)}",
                recovery_suggestions=[
                    "Check configuration file syntax",
                    "Verify environment variables are set",
                    "Review configuration schema",
                ],
            )

    async def _validate_secrets(self):
        """Validate secrets and sensitive configuration."""
        try:
            # ConfigManager is already initialized (no initialize() method needed)
            # Verify it's working by checking if we can access config
            try:
                _ = self.secrets_manager.get_secret("DOPPLER_TOKEN", required=False)
                self._add_check(
                    "secrets_manager",
                    "passed",
                    ValidationLevel.CRITICAL,
                    "Secrets manager (ConfigManager) is operational",
                )
            except Exception as e:
                self._add_check(
                    "secrets_manager",
                    "failed",
                    ValidationLevel.CRITICAL,
                    f"Secrets manager access failed: {str(e)}",
                    recovery_suggestions=[
                        "Check ConfigManager initialization",
                        "Verify Doppler configuration",
                        "Check environment variables",
                    ],
                )
                return

            # Check critical secrets (Either/Or pattern aware)
            # Database: Either DATABASE_URL OR individual components
            database_url = self.secrets_manager.get_secret("DATABASE_URL", required=False)
            db_components = all([
                self.secrets_manager.get_secret("DB_HOST", required=False),
                self.secrets_manager.get_secret("DB_PORT", required=False),
                self.secrets_manager.get_secret("DB_NAME", required=False),
                self.secrets_manager.get_secret("DB_USER", required=False),
                self.secrets_manager.get_secret("DB_PASSWORD", required=False),
            ])

            if database_url or db_components:
                self._add_check(
                    "secret_database_config",
                    "passed",
                    ValidationLevel.CRITICAL,
                    "Database configuration is available (URL or components)",
                )
            else:
                self._add_check(
                    "secret_database_config",
                    "failed",
                    ValidationLevel.CRITICAL,
                    "Database configuration missing: need DATABASE_URL or (DB_HOST+DB_PORT+DB_NAME+DB_USER+DB_PASSWORD)",
                    recovery_suggestions=[
                        "Set DATABASE_URL in Doppler/environment",
                        "OR set all DB_* components (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)",
                    ],
                )

            # Redis: Either REDIS_URL OR individual components
            redis_url = self.secrets_manager.get_secret("REDIS_URL", required=False)
            redis_components = all([
                self.secrets_manager.get_secret("REDIS_HOST", required=False),
                self.secrets_manager.get_secret("REDIS_PORT", required=False),
                self.secrets_manager.get_secret("REDIS_PASSWORD", required=False),
            ])

            if redis_url or redis_components:
                self._add_check(
                    "secret_redis_config",
                    "passed",
                    ValidationLevel.CRITICAL,
                    "Redis configuration is available (URL or components)",
                )
            else:
                self._add_check(
                    "secret_redis_config",
                    "failed",
                    ValidationLevel.CRITICAL,
                    "Redis configuration missing: need REDIS_URL or (REDIS_HOST+REDIS_PORT+REDIS_PASSWORD)",
                    recovery_suggestions=[
                        "Set REDIS_URL in Doppler/environment",
                        "OR set all REDIS_* components (REDIS_HOST, REDIS_PORT, REDIS_PASSWORD)",
                    ],
                )

            # Other critical secrets
            other_critical_secrets = ["JWT_SECRET_KEY", "ENCRYPTION_KEY"]

            for secret_name in other_critical_secrets:
                try:
                    value = self.secrets_manager.get_secret(secret_name, required=False)
                    if value:
                        self._add_check(
                            f"secret_{secret_name.lower()}",
                            "passed",
                            ValidationLevel.CRITICAL,
                            f"Secret {secret_name} is available",
                        )
                    else:
                        self._add_check(
                            f"secret_{secret_name.lower()}",
                            "failed",
                            ValidationLevel.CRITICAL,
                            f"Critical secret missing: {secret_name}",
                            recovery_suggestions=[
                                f"Set {secret_name} environment variable",
                                "Configure Doppler secrets",
                                "Check secrets configuration",
                            ],
                        )
                except Exception as e:
                    self._add_check(
                        f"secret_{secret_name.lower()}",
                        "failed",
                        ValidationLevel.CRITICAL,
                        f"Error accessing secret {secret_name}: {str(e)}",
                    )

            # Note: Removed validate_required_secrets() call as ConfigManager doesn't have this method
            # All critical secrets are already validated above (lines 342-372)

        except Exception as e:
            self._add_check(
                "secrets_manager",
                "failed",
                ValidationLevel.CRITICAL,
                f"Secrets manager initialization failed: {str(e)}",
                recovery_suggestions=[
                    "Check Doppler configuration",
                    "Verify environment variables",
                    "Check network connectivity to secrets service",
                ],
            )

    async def _validate_dependencies(self):
        """Validate required dependencies."""
        critical_imports = [
            ("fastapi", "FastAPI web framework"),
            ("sqlalchemy", "Database ORM"),
            ("redis", "Redis client"),
            ("prometheus_client", "Metrics collection"),
            ("structlog", "Structured logging"),
        ]

        optional_imports = [
            ("temporalio", "Temporal workflows"),
            # ("guardrails", "AI output validation"),
            ("slack_sdk", "Slack integration"),
            # ("openai", "OpenAI API client"),
            # Note: anthropic SDK not needed - Claude accessed via EnterpriseGateway/Bedrock
        ]

        for module_name, description in critical_imports:
            try:
                __import__(module_name)
                self._add_check(
                    f"import_{module_name}",
                    "passed",
                    ValidationLevel.CRITICAL,
                    f"Critical dependency available: {description}",
                )
            except ImportError:
                self._add_check(
                    f"import_{module_name}",
                    "failed",
                    ValidationLevel.CRITICAL,
                    f"Critical dependency missing: {description}",
                    recovery_suggestions=[f"Install {module_name}: pip install {module_name}"],
                )

        for module_name, description in optional_imports:
            try:
                __import__(module_name)
                self._add_check(
                    f"import_{module_name}",
                    "passed",
                    ValidationLevel.INFO,
                    f"Optional dependency available: {description}",
                )
            except ImportError:
                self._add_check(
                    f"import_{module_name}",
                    "failed",
                    ValidationLevel.WARNING,
                    f"Optional dependency missing: {description}",
                    recovery_suggestions=[f"Install {module_name}: pip install {module_name}"],
                )

    async def _validate_services(self):
        """Validate external service connectivity."""
        # This would typically test connections to external services
        # For now, we'll do basic checks that don't require actual connections

        self._add_check(
            "services_check",
            "passed",
            ValidationLevel.INFO,
            "Service connectivity checks completed (placeholder implementation)",
        )

    async def _validate_database(self):
        """Validate database configuration and connectivity."""
        try:
            db_config = self.config.database

            # Validate database URL format
            db_url = db_config.url
            if not db_url or not db_url.startswith(("postgresql://", "sqlite://", "mysql://")):
                self._add_check(
                    "database_url",
                    "failed",
                    ValidationLevel.CRITICAL,
                    f"Invalid database URL format: {db_url}",
                    recovery_suggestions=[
                        "Set DATABASE_URL environment variable",
                        "Use format: postgresql://user:pass@host:port/db",
                    ],
                )
            else:
                self._add_check(
                    "database_url", "passed", ValidationLevel.INFO, "Database URL format is valid"
                )

            # Validate pool settings
            if db_config.pool_size < 1 or db_config.pool_size > 50:
                self._add_check(
                    "database_pool_size",
                    "failed",
                    ValidationLevel.WARNING,
                    f"Database pool size out of recommended range: {db_config.pool_size}",
                )
            else:
                self._add_check(
                    "database_pool_size",
                    "passed",
                    ValidationLevel.INFO,
                    f"Database pool size is appropriate: {db_config.pool_size}",
                )

        except Exception as e:
            self._add_check(
                "database_config",
                "failed",
                ValidationLevel.CRITICAL,
                f"Database configuration error: {str(e)}",
            )

    async def _validate_cache(self):
        """Validate cache configuration."""
        try:
            cache_config = self.config.cache

            # Validate cache type
            if cache_config.type not in ["redis", "memory"]:
                self._add_check(
                    "cache_type",
                    "failed",
                    ValidationLevel.WARNING,
                    f"Unsupported cache type: {cache_config.type}",
                )
            else:
                self._add_check(
                    "cache_type",
                    "passed",
                    ValidationLevel.INFO,
                    f"Cache type is valid: {cache_config.type}",
                )

            # Validate Redis URL if using Redis (soft validation - syntax only)
            if cache_config.type == "redis":
                redis_url = cache_config.redis_url
                if not redis_url or not (redis_url.startswith("redis://") or redis_url.startswith("rediss://")):
                    self._add_check(
                        "cache_redis_url",
                        "failed",
                        ValidationLevel.WARNING,
                        f"Redis URL format looks invalid: {redis_url}",
                        recovery_suggestions=["Check REDIS_URL format (should start with redis:// or rediss://)"],
                    )
                else:
                    self._add_check(
                        "cache_redis_url",
                        "passed",
                        ValidationLevel.INFO,
                        "Redis URL format is valid",
                    )

        except Exception as e:
            self._add_check(
                "cache_config",
                "failed",
                ValidationLevel.WARNING,
                f"Cache configuration error: {str(e)}",
            )

    async def _validate_security(self):
        """Validate security configuration."""
        try:
            # Check JWT secret strength (warning only for development)
            jwt_secret = self.secrets_manager.get_secret("JWT_SECRET_KEY", required=False)
            if jwt_secret:
                if len(jwt_secret) < 32:
                    self._add_check(
                        "jwt_secret_strength",
                        "failed",
                        ValidationLevel.WARNING,
                        "JWT secret is too short (minimum 32 characters recommended)",
                        recovery_suggestions=["Generate a longer JWT secret for production"],
                    )
                else:
                    self._add_check(
                        "jwt_secret_strength",
                        "passed",
                        ValidationLevel.INFO,
                        "JWT secret meets minimum length requirements",
                    )

            # Check encryption key
            encryption_key = self.secrets_manager.get_secret("ENCRYPTION_KEY", required=False)
            if encryption_key:
                # Basic validation - should be base64 encoded
                try:
                    import base64

                    decoded = base64.b64decode(encryption_key)
                    if len(decoded) >= 32:  # At least 256 bits
                        self._add_check(
                            "encryption_key_strength",
                            "passed",
                            ValidationLevel.INFO,
                            "Encryption key meets security requirements",
                        )
                    else:
                        self._add_check(
                            "encryption_key_strength",
                            "failed",
                            ValidationLevel.CRITICAL,
                            "Encryption key is too weak (minimum 256 bits)",
                        )
                except Exception:
                    self._add_check(
                        "encryption_key_format",
                        "failed",
                        ValidationLevel.WARNING,
                        "Encryption key is not valid base64 format",
                    )

        except Exception as e:
            self._add_check(
                "security_config",
                "failed",
                ValidationLevel.WARNING,
                f"Security validation error: {str(e)}",
            )

    async def _validate_monitoring(self):
        """Validate monitoring and observability configuration."""
        try:
            monitoring_config = self.config.monitoring

            if monitoring_config.metrics_enabled:
                self._add_check(
                    "monitoring_metrics",
                    "passed",
                    ValidationLevel.INFO,
                    "Metrics collection is enabled",
                )
            else:
                self._add_check(
                    "monitoring_metrics",
                    "failed",
                    ValidationLevel.WARNING,
                    "Metrics collection is disabled",
                    recovery_suggestions=["Enable metrics in configuration"],
                )

        except Exception as e:
            self._add_check(
                "monitoring_config",
                "failed",
                ValidationLevel.WARNING,
                f"Monitoring configuration error: {str(e)}",
            )

    async def _validate_environment_specific(self):
        """Validate environment-specific requirements."""
        environment = self.config.app.environment

        if environment == "production":
            # Production-specific validations
            if self.config.app.debug:
                self._add_check(
                    "production_debug",
                    "failed",
                    ValidationLevel.CRITICAL,
                    "Debug mode is enabled in production",
                    recovery_suggestions=["Set DEBUG=False for production"],
                )
            else:
                self._add_check(
                    "production_debug",
                    "passed",
                    ValidationLevel.INFO,
                    "Debug mode is disabled in production",
                )

            # Check for production secrets
            # Note: ANTHROPIC_API_KEY not needed - Claude accessed via EnterpriseGateway/Bedrock
            # Note: OPENAI_API_KEY not needed - GPT models accessed via EnterpriseGateway
            required_prod_secrets = ["SLACK_BOT_TOKEN"]
            for secret in required_prod_secrets:
                value = self.secrets_manager.get_secret(secret, required=False)
                if not value:
                    self._add_check(
                        f"production_{secret.lower()}",
                        "failed",
                        ValidationLevel.WARNING,
                        f"Production secret missing: {secret}",
                    )

        elif environment == "development":
            # Development-specific validations
            self._add_check(
                "development_setup",
                "passed",
                ValidationLevel.INFO,
                "Development environment configured",
            )

    def _add_check(
        self,
        check_name: str,
        status: str,
        level: ValidationLevel,
        message: str,
        details: dict[str, Any] | None = None,
        recovery_suggestions: list[str] | None = None,
    ):
        """Add a validation check result."""
        result = ValidationResult(
            check_name=check_name,
            status=status,
            level=level,
            message=message,
            details=details,
            recovery_suggestions=recovery_suggestions,
        )
        self.checks.append(result)

    def _generate_report(
        self, environment: str, validation_time: float
    ) -> EnvironmentValidationReport:
        """Generate validation report from check results."""
        critical_checks = [c for c in self.checks if c.level == ValidationLevel.CRITICAL]
        warning_checks = [c for c in self.checks if c.level == ValidationLevel.WARNING]
        info_checks = [c for c in self.checks if c.level == ValidationLevel.INFO]

        total_checks = len(self.checks)
        passed_checks = len([c for c in self.checks if c.status == "passed"])
        failed_checks = len([c for c in self.checks if c.status == "failed"])
        warning_checks_count = len(
            [c for c in self.checks if c.status == "failed" and c.level == ValidationLevel.WARNING]
        )

        # Determine overall status
        critical_failures = len([c for c in critical_checks if c.status == "failed"])
        if critical_failures > 0:
            overall_status = "failed"
        elif warning_checks_count > 0:
            overall_status = "warnings"
        else:
            overall_status = "passed"

        return EnvironmentValidationReport(
            environment=environment,
            overall_status=overall_status,
            critical_checks=critical_checks,
            warning_checks=warning_checks,
            info_checks=info_checks,
            total_checks=total_checks,
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            warning_checks_count=warning_checks_count,
            validation_time_seconds=validation_time,
        )

    def print_report(self, report: EnvironmentValidationReport):
        """Log and optionally print validation report."""
        # Always log to structured logs
        logger.info(
            "Environment validation completed",
            extra={
                "environment": report.environment.upper(),
                "overall_status": report.overall_status.upper(),
                "total_checks": report.total_checks,
                "passed_checks": report.passed_checks,
                "failed_checks": report.failed_checks,
                "warnings": report.warning_checks_count,
                "validation_time_seconds": report.validation_time_seconds,
            }
        )

        # Log critical failures
        failed_critical = [c for c in report.critical_checks if c.status == "failed"]
        for check in failed_critical:
            logger.error(
                f"Critical validation failure: {check.check_name}",
                extra={
                    "check_name": check.check_name,
                    "message": check.message,
                    "recovery_suggestions": check.recovery_suggestions,
                }
            )

        # Log warnings
        failed_warnings = [c for c in report.warning_checks if c.status == "failed"]
        for check in failed_warnings:
            logger.warning(
                f"Validation warning: {check.check_name}",
                extra={
                    "check_name": check.check_name,
                    "message": check.message,
                }
            )

        # For CLI/interactive use, also print to console
        if os.getenv("INTERACTIVE_MODE", "false").lower() == "true":
            print(f"\n{'=' * 60}")
            print(f"ENVIRONMENT VALIDATION REPORT - {report.environment.upper()}")
            print(f"{'=' * 60}")
            print(f"Overall Status: {report.overall_status.upper()}")
            print(f"Total Checks: {report.total_checks}")
            print(f"Passed: {report.passed_checks}")
            print(f"Failed: {report.failed_checks}")
            print(f"Warnings: {report.warning_checks_count}")
            print(f"Validation Time: {report.validation_time_seconds:.2f}s")

            # Show failed critical checks first
            if failed_critical:
                print(f"\n❌ CRITICAL FAILURES ({len(failed_critical)}):")
                for check in failed_critical:
                    print(f"  • {check.check_name}: {check.message}")
                    if check.recovery_suggestions:
                        for suggestion in check.recovery_suggestions:
                            print(f"    → {suggestion}")

            # Show warnings
            if failed_warnings:
                print(f"\n⚠️  WARNINGS ({len(failed_warnings)}):")
                for check in failed_warnings:
                    print(f"  • {check.check_name}: {check.message}")

            # Show successful checks summary
            passed_checks = [c for c in self.checks if c.status == "passed"]
            if passed_checks:
                print(f"\n✅ PASSED CHECKS ({len(passed_checks)}):")
                for check in passed_checks:
                    print(f"  • {check.check_name}: {check.message}")

            print(f"\n{'=' * 60}\n")


# Global validator instance
_environment_validator: EnvironmentValidator | None = None


def get_environment_validator(config: ReflectAIConfig | None = None) -> EnvironmentValidator:
    """Get or create global environment validator instance."""
    global _environment_validator
    if _environment_validator is None:
        _environment_validator = EnvironmentValidator(config)
    return _environment_validator


async def validate_environment_on_startup(
    environment: str = None, raise_on_failure: bool = True, print_report: bool = True
) -> EnvironmentValidationReport:
    """
    Validate environment on application startup.

    Args:
        environment: Environment name to validate
        raise_on_failure: Whether to raise exception on validation failure
        print_report: Whether to print validation report to console

    Returns:
        Validation report

    Raises:
        ReflectAIError: If validation fails and raise_on_failure is True
    """
    validator = get_environment_validator()
    report = await validator.validate_environment(environment)

    if print_report:
        validator.print_report(report)

    if report.overall_status == "failed" and raise_on_failure:
        failed_critical = [c for c in report.critical_checks if c.status == "failed"]
        error_details = {
            "environment": environment,
            "total_checks": report.total_checks,
            "failed_checks": report.failed_checks,
            "critical_failures": len(failed_critical),
        }

        recovery_suggestions = []
        for check in failed_critical:
            if check.recovery_suggestions:
                recovery_suggestions.extend(check.recovery_suggestions)

        raise ReflectAIError(
            message=f"Environment validation failed for {environment} environment",
            error_code="ENVIRONMENT_VALIDATION_FAILED",
            category=ErrorCategory.CONFIGURATION_ERROR,
            severity=ErrorSeverity.CRITICAL,
            context=error_details,
            recovery_suggestions=recovery_suggestions[:10],  # Limit suggestions
        )

    return report
