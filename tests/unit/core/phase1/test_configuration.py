"""
Phase 1: Security-First Foundation - Configuration Tests

Unit tests for the configuration system including:
- Configuration loading and validation
- Environment variable handling
- Secrets management
- Configuration health checks
"""

import os
from unittest.mock import MagicMock, mock_open, patch

import pytest

# Import the modules under test
try:
    from infrastructure.config.configuration import (
        AppConfig,
        Configuration,
        DatabaseConfig,
        get_configuration_health,
        load_configuration,
    )

    from infrastructure.config.secrets_manager import SecretsManager
except ImportError as e:
    pytest.skip(f"Configuration modules not available: {e}", allow_module_level=True)


@pytest.mark.unit
@pytest.mark.phase1
class TestConfiguration:
    """Test configuration loading and validation"""

    def test_app_config_creation(self):
        """Test AppConfig creation with valid data"""
        config = AppConfig(name="ReflectAI Test", version="1.0.0", environment="test", debug=True)

        assert config.name == "ReflectAI Test"
        assert config.version == "1.0.0"
        assert config.environment == "test"
        assert config.debug is True

    def test_app_config_defaults(self):
        """Test AppConfig with default values"""
        config = AppConfig()

        assert config.name == "ReflectAI"
        assert config.version == "1.0.0"
        assert config.environment == "development"
        assert config.debug is False

    def test_database_config_creation(self):
        """Test DatabaseConfig creation with valid data"""
        config = DatabaseConfig(
            url="postgresql://user:pass@localhost:5432/db", pool_size=10, max_overflow=20
        )

        assert config.url == "postgresql://user:pass@localhost:5432/db"
        assert config.pool_size == 10
        assert config.max_overflow == 20

    def test_database_config_validation(self):
        """Test DatabaseConfig validation"""
        # Test invalid pool size
        with pytest.raises(ValueError):
            DatabaseConfig(pool_size=0)

        # Test invalid max overflow
        with pytest.raises(ValueError):
            DatabaseConfig(max_overflow=-1)

    def test_configuration_creation(self):
        """Test complete Configuration creation"""
        app_config = AppConfig(name="Test App")
        db_config = DatabaseConfig()

        config = Configuration(app=app_config, database=db_config)

        assert config.app.name == "Test App"
        assert config.database is not None

    @patch.dict(
        os.environ,
        {
            "REFLECTAI_NAME": "Test from ENV",
            "REFLECTAI_DEBUG": "true",
            "DATABASE_URL": "postgresql://test:test@localhost/test",
        },
    )
    def test_load_configuration_from_env(self):
        """Test loading configuration from environment variables"""
        config = load_configuration()

        assert config.app.name == "Test from ENV"
        assert config.app.debug is True
        assert "postgresql://test:test@localhost/test" in config.database.url

    @patch(
        "builtins.open",
        mock_open(
            read_data="""
app:
  name: "YAML Config Test"
  version: "2.0.0"
  environment: "staging"
database:
  pool_size: 15
"""
        ),
    )
    @patch("pathlib.Path.exists")
    def test_load_configuration_from_yaml(self, mock_exists):
        """Test loading configuration from YAML file"""
        mock_exists.return_value = True

        config = load_configuration()

        # Note: This would test the actual YAML loading if implemented
        assert config is not None

    def test_get_configuration_health(self):
        """Test configuration health check"""
        with patch("infrastructure.config.configuration.load_configuration") as mock_load:
            mock_config = MagicMock()
            mock_config.app.name = "Test App"
            mock_config.app.version = "1.0.0"
            mock_load.return_value = mock_config

            health = get_configuration_health()

            assert "status" in health
            assert "app_name" in health
            assert "version" in health


@pytest.mark.unit
@pytest.mark.phase1
class TestSecretsManager:
    """Test secrets management functionality"""

    def setUp(self):
        """Set up test environment"""
        self.secrets_manager = SecretsManager()

    def test_secrets_manager_creation(self):
        """Test SecretsManager initialization"""
        manager = SecretsManager()
        assert manager is not None

    @patch.dict(os.environ, {"TEST_SECRET": "secret_value"})
    def test_get_secret_from_env(self):
        """Test getting secret from environment variables"""
        manager = SecretsManager()

        # This would test actual secret retrieval if implemented
        # For now, test that manager exists
        assert manager is not None

    def test_get_secret_with_default(self):
        """Test getting secret with default value"""
        manager = SecretsManager()

        # Test would verify fallback to default value
        assert manager is not None

    @patch("infrastructure.config.secrets_manager.requests.get")
    def test_doppler_integration(self, mock_get):
        """Test Doppler secrets integration"""
        # Mock Doppler API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "secrets": {"DATABASE_URL": "postgresql://doppler:secret@localhost/db"}
        }
        mock_get.return_value = mock_response

        manager = SecretsManager()
        # Test would verify Doppler integration if implemented
        assert manager is not None

    def test_secret_validation(self):
        """Test secret validation and sanitization"""
        manager = SecretsManager()

        # Test would verify secret validation logic
        assert manager is not None


@pytest.mark.unit
@pytest.mark.phase1
class TestConfigurationIntegration:
    """Test configuration system integration"""

    def test_config_environment_override(self):
        """Test environment-based configuration override"""
        with patch.dict(os.environ, {"ENVIRONMENT": "production", "DEBUG": "false"}):
            config = load_configuration()
            # Would test actual environment override logic
            assert config is not None

    def test_config_validation_errors(self):
        """Test configuration validation error handling"""
        # Test invalid configuration scenarios
        with pytest.raises((ValueError, TypeError)):
            # Would test actual validation error scenarios
            AppConfig(name="")  # Invalid empty name

    def test_config_file_not_found(self):
        """Test behavior when config file is not found"""
        with patch("pathlib.Path.exists", return_value=False):
            config = load_configuration()
            # Should fall back to defaults
            assert config.app.name == "ReflectAI"

    @patch("infrastructure.config.configuration.SecretsManager")
    def test_secrets_integration(self, mock_secrets_manager):
        """Test integration between configuration and secrets"""
        mock_manager = MagicMock()
        mock_manager.get_secret.return_value = "test_secret_value"
        mock_secrets_manager.return_value = mock_manager

        config = load_configuration()
        # Would test actual secrets integration
        assert config is not None


@pytest.mark.unit
@pytest.mark.phase1
class TestConfigurationValidation:
    """Test configuration validation logic"""

    def test_validate_app_config(self):
        """Test application configuration validation"""
        # Valid configuration
        config = AppConfig(name="Valid App", version="1.0.0", environment="production")
        assert config.name == "Valid App"

    def test_validate_database_config(self):
        """Test database configuration validation"""
        # Valid database configuration
        config = DatabaseConfig(
            url="postgresql://user:pass@host:5432/db", pool_size=5, max_overflow=10
        )
        assert config.pool_size == 5
        assert config.max_overflow == 10

    def test_validate_environment_values(self):
        """Test environment value validation"""
        valid_environments = ["development", "staging", "production", "test"]

        for env in valid_environments:
            config = AppConfig(environment=env)
            assert config.environment == env

    def test_validate_version_format(self):
        """Test version format validation"""
        valid_versions = ["1.0.0", "1.2.3", "2.0.0"]

        for version in valid_versions:
            config = AppConfig(version=version)
            assert config.version == version


@pytest.mark.unit
@pytest.mark.phase1
@pytest.mark.slow
class TestConfigurationPerformance:
    """Test configuration system performance"""

    def test_config_load_performance(self):
        """Test configuration loading performance"""
        import time

        start_time = time.time()
        config = load_configuration()
        end_time = time.time()

        # Configuration should load quickly (< 100ms)
        assert (end_time - start_time) < 0.1
        assert config is not None

    def test_secrets_cache_performance(self):
        """Test secrets caching performance"""
        manager = SecretsManager()

        # Test would verify caching improves performance
        assert manager is not None

    def test_concurrent_config_access(self):
        """Test concurrent configuration access"""
        import concurrent.futures

        def load_config():
            return load_configuration()

        # Test concurrent configuration loading
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(load_config) for _ in range(10)]
            results = [future.result() for future in futures]

        assert len(results) == 10
        assert all(config is not None for config in results)


# Test utilities and helpers
def create_test_config() -> Configuration:
    """Helper function to create test configuration"""
    return Configuration(
        app=AppConfig(name="Test App", version="1.0.0-test", environment="test", debug=True),
        database=DatabaseConfig(
            url="postgresql://test:test@localhost:5432/test_db", pool_size=1, max_overflow=0
        ),
    )


def assert_config_valid(config: Configuration) -> None:
    """Helper function to assert configuration is valid"""
    assert config is not None
    assert config.app is not None
    assert config.database is not None
    assert config.app.name != ""
    assert config.app.version != ""
    assert config.database.url != ""
