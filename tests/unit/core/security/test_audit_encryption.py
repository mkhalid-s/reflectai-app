"""
Tests for Audit Trail Encryption

Verifies that sensitive data in audit logs is properly encrypted
using AES-256 (Fernet) encryption.
"""

import os

import pytest

from src.core.security.audit_trail import (
    AuditAction,
    AuditEvent,
    AuditLevel,
    AuditLogger,
    AuditTrailManager,
)


@pytest.fixture
def audit_logger():
    """Create audit logger for testing."""
    return AuditLogger(redis_client=None, enable_encryption=True)


@pytest.fixture
def audit_manager():
    """Create audit trail manager for testing."""
    return AuditTrailManager(redis_client=None)


@pytest.fixture
def encryption_key():
    """Set up test encryption key."""
    from cryptography.fernet import Fernet

    # Generate test key
    test_key = Fernet.generate_key().decode()

    # Set in environment
    original_key = os.environ.get("AUDIT_ENCRYPTION_KEY")
    os.environ["AUDIT_ENCRYPTION_KEY"] = test_key

    yield test_key

    # Restore original
    if original_key:
        os.environ["AUDIT_ENCRYPTION_KEY"] = original_key
    else:
        os.environ.pop("AUDIT_ENCRYPTION_KEY", None)


@pytest.mark.asyncio
async def test_encrypt_sensitive_fields(audit_logger, encryption_key):
    """Test encryption of sensitive fields in audit data."""
    # Arrange
    sensitive_data = {
        "password": "secret_password_123",
        "api_key": "sk-1234567890abcdef",
        "normal_field": "not_sensitive",
        "ssn": "123-45-6789",
    }

    # Act
    encrypted = await audit_logger._encrypt_sensitive_data(sensitive_data)

    # Assert - sensitive fields should be encrypted
    assert encrypted["password"]["_encrypted"] is True
    assert encrypted["api_key"]["_encrypted"] is True
    assert encrypted["ssn"]["_encrypted"] is True

    # Normal field should not be encrypted
    assert encrypted["normal_field"] == "not_sensitive"

    # Values should be different from original
    assert encrypted["password"]["_value"] != "secret_password_123"
    assert encrypted["api_key"]["_value"] != "sk-1234567890abcdef"


@pytest.mark.asyncio
async def test_decrypt_sensitive_fields(audit_logger, encryption_key):
    """Test decryption of encrypted audit data."""
    # Arrange
    original_data = {
        "password": "secret_password_123",
        "api_key": "sk-1234567890abcdef",
        "normal_field": "not_sensitive",
    }

    # Act - Encrypt then decrypt
    encrypted = await audit_logger._encrypt_sensitive_data(original_data)
    decrypted = await audit_logger._decrypt_sensitive_data(encrypted)

    # Assert - decrypted should match original
    assert decrypted["password"] == "secret_password_123"
    assert decrypted["api_key"] == "sk-1234567890abcdef"
    assert decrypted["normal_field"] == "not_sensitive"


@pytest.mark.asyncio
async def test_nested_encryption(audit_logger, encryption_key):
    """Test encryption of nested dictionaries."""
    # Arrange
    nested_data = {
        "user": {
            "username": "john_doe",
            "password": "secret_pass",
            "email": "john@example.com",
        },
        "metadata": {"normal": "value"},
    }

    # Act
    encrypted = await audit_logger._encrypt_sensitive_data(nested_data)

    # Assert
    assert encrypted["user"]["password"]["_encrypted"] is True
    assert encrypted["user"]["email"]["_encrypted"] is True
    assert encrypted["user"]["username"] == "john_doe"
    assert encrypted["metadata"]["normal"] == "value"


@pytest.mark.asyncio
async def test_encryption_with_list_values(audit_logger, encryption_key):
    """Test encryption of data containing lists."""
    # Arrange
    list_data = {
        "tokens": [
            {"token": "secret_token_1", "name": "token1"},
            {"token": "secret_token_2", "name": "token2"},
        ],
        "normal_list": ["item1", "item2"],
    }

    # Act
    encrypted = await audit_logger._encrypt_sensitive_data(list_data)

    # Assert
    assert encrypted["tokens"][0]["token"]["_encrypted"] is True
    assert encrypted["tokens"][1]["token"]["_encrypted"] is True
    assert encrypted["tokens"][0]["name"] == "token1"
    assert encrypted["normal_list"] == ["item1", "item2"]


@pytest.mark.asyncio
async def test_encryption_without_key():
    """Test encryption fallback when no key is configured."""
    from unittest.mock import MagicMock, patch

    # Arrange - Remove encryption key
    original_key = os.environ.get("AUDIT_ENCRYPTION_KEY")
    os.environ.pop("AUDIT_ENCRYPTION_KEY", None)

    # Mock secrets manager to return None
    mock_secrets = MagicMock()
    mock_secrets.get_secret.return_value = None

    with patch(
        "src.infrastructure.config.secrets_manager.get_secrets_manager", return_value=mock_secrets
    ):
        # Create audit logger AFTER removing key
        audit_logger = AuditLogger(redis_client=None, enable_encryption=True)

        sensitive_data = {"password": "secret", "api_key": "key123"}

        # Act
        encrypted = await audit_logger._encrypt_sensitive_data(sensitive_data)

        # Assert - Should use placeholder encryption
        assert encrypted["password"] == "***ENCRYPTED***"
        assert encrypted["api_key"] == "***ENCRYPTED***"

    # Restore key
    if original_key:
        os.environ["AUDIT_ENCRYPTION_KEY"] = original_key


@pytest.mark.asyncio
async def test_audit_event_encryption_integration(audit_logger, encryption_key):
    """Test encryption integration in full audit event logging."""
    # Arrange
    event = AuditEvent(
        action=AuditAction.USER_LOGIN,
        level=AuditLevel.INFO,
        user_id="user123",
        details={
            "password": "user_password",
            "session_token": "session_abc123",
            "ip_address": "192.168.1.1",
            "device": "Chrome",
        },
    )

    # Act - Log event (which triggers encryption)
    event_id = await audit_logger.log_event(event)

    # Assert
    assert event_id is not None
    # Verify details were encrypted
    assert event.details["password"]["_encrypted"] is True
    assert event.details["session_token"]["_encrypted"] is True
    assert event.details["ip_address"]["_encrypted"] is True
    assert event.details["device"] == "Chrome"  # Not sensitive


@pytest.mark.asyncio
async def test_verify_encryption_status(audit_manager, encryption_key):
    """Test encryption status verification."""
    # Act
    status = await audit_manager.verify_encryption_status()

    # Assert
    assert status["encryption_enabled"] is True
    assert status["status"] == "healthy"
    assert status["algorithm"] == "fernet_aes256"
    assert "key_source" in status


@pytest.mark.asyncio
async def test_verify_encryption_status_no_key(audit_manager):
    """Test encryption status verification when no key configured."""
    from unittest.mock import MagicMock, patch

    # Arrange - Remove encryption key
    original_key = os.environ.get("AUDIT_ENCRYPTION_KEY")
    os.environ.pop("AUDIT_ENCRYPTION_KEY", None)

    # Mock secrets manager to return None
    mock_secrets = MagicMock()
    mock_secrets.get_secret.return_value = None

    with patch(
        "src.infrastructure.config.secrets_manager.get_secrets_manager", return_value=mock_secrets
    ):
        # Act
        status = await audit_manager.verify_encryption_status()

        # Assert
        assert status["encryption_enabled"] is False
        assert status["status"] == "warning"
        assert "No encryption key configured" in status["message"]

    # Restore key
    if original_key:
        os.environ["AUDIT_ENCRYPTION_KEY"] = original_key


@pytest.mark.asyncio
async def test_authorized_decryption(audit_manager, encryption_key):
    """Test authorized decryption of audit data."""
    # Arrange

    # First encrypt properly
    original_data = {"password": "secret_pass", "normal_field": "visible"}
    encrypted = await audit_manager.logger._encrypt_sensitive_data(original_data)

    # Act - Authorized decryption
    decrypted = await audit_manager.decrypt_audit_data(encrypted, authorized_user_id="admin_user")

    # Assert
    assert decrypted["password"] == "secret_pass"
    assert decrypted["normal_field"] == "visible"


@pytest.mark.asyncio
async def test_multiple_sensitive_fields():
    """Test all defined sensitive field types are encrypted."""
    # Arrange
    audit_logger = AuditLogger(enable_encryption=True)

    from cryptography.fernet import Fernet

    test_key = Fernet.generate_key().decode()
    os.environ["AUDIT_ENCRYPTION_KEY"] = test_key

    # Test data with all sensitive field types
    all_sensitive = {
        "password": "pass123",
        "ssn": "123-45-6789",
        "credit_card": "4111111111111111",
        "api_key": "sk-abc123",
        "token": "bearer_token",
        "email": "user@example.com",
        "phone": "+1234567890",
        "ip_address": "192.168.1.1",
        "normal": "not_sensitive",
    }

    # Act
    encrypted = await audit_logger._encrypt_sensitive_data(all_sensitive)

    # Assert - All sensitive fields encrypted
    sensitive_fields = [
        "password",
        "ssn",
        "credit_card",
        "api_key",
        "token",
        "email",
        "phone",
        "ip_address",
    ]

    for field in sensitive_fields:
        assert encrypted[field]["_encrypted"] is True, f"Field {field} should be encrypted"

    assert encrypted["normal"] == "not_sensitive"

    # Cleanup
    os.environ.pop("AUDIT_ENCRYPTION_KEY", None)


@pytest.mark.asyncio
async def test_encryption_roundtrip_preserves_data_types():
    """Test encryption/decryption preserves all data types."""
    # Arrange
    audit_logger = AuditLogger(enable_encryption=True)

    from cryptography.fernet import Fernet

    test_key = Fernet.generate_key().decode()
    os.environ["AUDIT_ENCRYPTION_KEY"] = test_key

    test_data = {
        "string_field": "normal_string",
        "int_field": 42,
        "float_field": 3.14,
        "bool_field": True,
        "none_field": None,
        "list_field": [1, 2, 3],
        "dict_field": {"nested": "value"},
        "password": "encrypted_value",
    }

    # Act
    encrypted = await audit_logger._encrypt_sensitive_data(test_data)
    decrypted = await audit_logger._decrypt_sensitive_data(encrypted)

    # Assert - Non-sensitive fields preserve types
    assert decrypted["string_field"] == "normal_string"
    assert decrypted["int_field"] == 42
    assert decrypted["float_field"] == 3.14
    assert decrypted["bool_field"] is True
    assert decrypted["none_field"] is None
    assert decrypted["list_field"] == [1, 2, 3]
    assert decrypted["dict_field"] == {"nested": "value"}

    # Sensitive field decrypted correctly
    assert decrypted["password"] == "encrypted_value"

    # Cleanup
    os.environ.pop("AUDIT_ENCRYPTION_KEY", None)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
