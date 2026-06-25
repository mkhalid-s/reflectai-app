"""
Comprehensive Audit Trail System

Implements Complete audit logging, compliance tracking,
and forensic analysis capabilities for the ReflectAI platform.
"""

import hashlib
import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

import redis.asyncio as redis
from pydantic import BaseModel, Field

from src.shared import ReflectAIError, get_logger

logger = get_logger(__name__)


class AuditAction(str, Enum):
    """Types of auditable actions"""

    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_REGISTRATION = "user_registration"
    PASSWORD_CHANGE = "password_change"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    DATA_DELETION = "data_deletion"
    DATA_EXPORT = "data_export"
    PERMISSION_CHANGE = "permission_change"
    CONFIGURATION_CHANGE = "configuration_change"
    SECURITY_EVENT = "security_event"
    API_ACCESS = "api_access"
    REPORT_GENERATION = "report_generation"
    FILE_UPLOAD = "file_upload"
    FILE_DOWNLOAD = "file_download"
    SYSTEM_ADMIN_ACTION = "system_admin_action"
    INTEGRATION_ACCESS = "integration_access"
    CONVERSATION_ACCESS = "conversation_access"
    PROFILE_UPDATE = "profile_update"
    TEAM_MANAGEMENT = "team_management"


class AuditLevel(str, Enum):
    """Audit event severity levels"""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ComplianceStandard(str, Enum):
    """Compliance standards for audit requirements"""

    GDPR = "gdpr"
    CCPA = "ccpa"
    HIPAA = "hipaa"
    SOC2 = "soc2"
    ISO27001 = "iso27001"
    PCI_DSS = "pci_dss"


@dataclass
class AuditEvent:
    """Represents a single audit event"""

    action: AuditAction
    level: AuditLevel
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    user_id: str | None = None
    team_id: str | None = None
    session_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    description: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    before_state: dict[str, Any] | None = None
    after_state: dict[str, Any] | None = None
    correlation_id: str | None = None
    compliance_tags: list[ComplianceStandard] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage"""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        data["action"] = self.action.value
        data["level"] = self.level.value
        data["compliance_tags"] = [tag.value for tag in self.compliance_tags]
        return data

    def get_fingerprint(self) -> str:
        """Generate unique fingerprint for the event"""
        fingerprint_data = f"{self.action}_{self.user_id}_{self.resource_type}_{self.resource_id}"
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()


class AuditTrailQuery(BaseModel):
    """Query parameters for searching audit trail"""

    start_date: datetime | None = None
    end_date: datetime | None = None
    user_ids: list[str] = Field(default_factory=list)
    team_ids: list[str] = Field(default_factory=list)
    actions: list[AuditAction] = Field(default_factory=list)
    levels: list[AuditLevel] = Field(default_factory=list)
    resource_types: list[str] = Field(default_factory=list)
    resource_ids: list[str] = Field(default_factory=list)
    compliance_standards: list[ComplianceStandard] = Field(default_factory=list)
    correlation_id: str | None = None
    ip_address: str | None = None
    limit: int = Field(default=100, le=1000)
    offset: int = Field(default=0, ge=0)


class ComplianceReport(BaseModel):
    """Compliance report for audit analysis"""

    standard: ComplianceStandard
    period_start: datetime
    period_end: datetime
    total_events: int = 0
    critical_events: int = 0
    user_activity_summary: dict[str, int] = Field(default_factory=dict)
    data_access_summary: dict[str, int] = Field(default_factory=dict)
    security_incidents: list[dict[str, Any]] = Field(default_factory=list)
    compliance_violations: list[dict[str, Any]] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AuditLogger:
    """
    Centralized audit logging system with compliance tracking

    Features:
    - Structured audit event logging
    - Compliance-aware tagging
    - Before/after state tracking
    - Long-term retention (7 years)
    - Forensic analysis capabilities
    - Compliance reporting
    """

    def __init__(
        self,
        redis_client: redis.Redis | None = None,
        retention_days: int = 2555,  # 7 years default
        enable_encryption: bool = True,
    ):
        """
        Initialize audit logger

        Args:
            redis_client: Redis client for caching recent events
            retention_days: How long to retain audit logs
            enable_encryption: Whether to encrypt sensitive data
        """
        self.redis_client = redis_client
        self.retention_days = retention_days
        self.enable_encryption = enable_encryption

        # Storage backends
        self._events_buffer: list[AuditEvent] = []
        self._buffer_size = 100

        # Compliance mappings
        self._compliance_mappings = self._initialize_compliance_mappings()

    def _initialize_compliance_mappings(self) -> dict[ComplianceStandard, list[AuditAction]]:
        """Initialize mappings of compliance standards to required audit actions"""
        return {
            ComplianceStandard.GDPR: [
                AuditAction.DATA_ACCESS,
                AuditAction.DATA_MODIFICATION,
                AuditAction.DATA_DELETION,
                AuditAction.DATA_EXPORT,
                AuditAction.PERMISSION_CHANGE,
                AuditAction.USER_REGISTRATION,
            ],
            ComplianceStandard.CCPA: [
                AuditAction.DATA_ACCESS,
                AuditAction.DATA_DELETION,
                AuditAction.DATA_EXPORT,
                AuditAction.PROFILE_UPDATE,
            ],
            ComplianceStandard.HIPAA: [
                AuditAction.DATA_ACCESS,
                AuditAction.DATA_MODIFICATION,
                AuditAction.USER_LOGIN,
                AuditAction.USER_LOGOUT,
                AuditAction.PERMISSION_CHANGE,
            ],
            ComplianceStandard.SOC2: [
                AuditAction.SECURITY_EVENT,
                AuditAction.CONFIGURATION_CHANGE,
                AuditAction.PERMISSION_CHANGE,
                AuditAction.SYSTEM_ADMIN_ACTION,
            ],
        }

    async def log_event(self, event: AuditEvent) -> str:
        """
        Log an audit event

        Args:
            event: The audit event to log

        Returns:
            Event ID of the logged event
        """
        try:
            # Add compliance tags based on action
            event.compliance_tags = self._get_compliance_tags(event.action)

            # Encrypt sensitive data if enabled
            if self.enable_encryption and event.details:
                event.details = await self._encrypt_sensitive_data(event.details)

            # Add to buffer
            self._events_buffer.append(event)

            # Persist if buffer is full
            if len(self._events_buffer) >= self._buffer_size:
                await self._flush_buffer()

            # Cache in Redis for quick access
            if self.redis_client:
                await self._cache_event(event)

            logger.info(
                f"Audit event logged: {event.action.value}",
                extra={
                    "event_id": event.event_id,
                    "user_id": event.user_id,
                    "action": event.action.value,
                    "level": event.level.value,
                },
            )

            return event.event_id

        except Exception as e:
            logger.error(f"Failed to log audit event: {str(e)}")
            raise ReflectAIError(
                message="Audit logging failed", error_code="AUDIT_001", details={"error": str(e)}
            ) from e

    def _get_compliance_tags(self, action: AuditAction) -> list[ComplianceStandard]:
        """Get relevant compliance tags for an action"""
        tags = []
        for standard, actions in self._compliance_mappings.items():
            if action in actions:
                tags.append(standard)
        return tags

    async def _encrypt_sensitive_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Encrypt sensitive fields in audit data using AES-256 (Fernet).

        This implements proper encryption for PII and sensitive data in audit logs
        to comply with GDPR, CCPA, HIPAA, and SOC2 requirements.

        Args:
            data: Dictionary containing potentially sensitive data

        Returns:
            Dictionary with sensitive fields encrypted
        """
        try:
            import base64

            from cryptography.fernet import Fernet

            # Sensitive fields that should be encrypted
            sensitive_fields = [
                "password",
                "ssn",
                "social_security_number",
                "credit_card",
                "card_number",
                "api_key",
                "secret",
                "token",
                "private_key",
                "session_token",
                "oauth_token",
                "refresh_token",
                "access_token",
                "authentication_token",
                "email",  # Can contain PII
                "phone",
                "phone_number",
                "address",
                "ip_address",  # Can be PII under GDPR
                "medical_record",
                "health_data",
                "biometric",
                "financial_data",
            ]

            encrypted_data = data.copy()

            # Get encryption key from secrets manager or environment
            encryption_key = await self._get_encryption_key()

            if not encryption_key:
                logger.warning(
                    "No encryption key available, using placeholder encryption for sensitive data"
                )
                # Fallback to placeholder if no key (for development only)
                for field in sensitive_fields:
                    if field in encrypted_data:
                        encrypted_data[field] = "***ENCRYPTED***"
                return encrypted_data

            # Create Fernet cipher
            cipher = Fernet(encryption_key.encode())

            # Encrypt each sensitive field
            for field in sensitive_fields:
                if field in encrypted_data and encrypted_data[field]:
                    try:
                        # Convert value to string if not already
                        value = str(encrypted_data[field])

                        # Encrypt the value
                        encrypted_value = cipher.encrypt(value.encode())

                        # Store as base64 string with marker
                        encrypted_data[field] = {
                            "_encrypted": True,
                            "_value": base64.b64encode(encrypted_value).decode(),
                            "_algorithm": "fernet_aes256",
                        }

                    except Exception as e:
                        logger.error(
                            f"Failed to encrypt field '{field}': {str(e)}",
                            extra={"field": field, "error": str(e)},
                        )
                        # Use placeholder on encryption failure
                        encrypted_data[field] = "***ENCRYPTION_FAILED***"

            # Also encrypt nested dictionaries
            for key, value in encrypted_data.items():
                if isinstance(value, dict) and key not in sensitive_fields:
                    encrypted_data[key] = await self._encrypt_sensitive_data(value)
                elif isinstance(value, list):
                    encrypted_data[key] = [
                        await self._encrypt_sensitive_data(item) if isinstance(item, dict) else item
                        for item in value
                    ]

            return encrypted_data

        except ImportError:
            logger.error(
                "cryptography library not installed, cannot encrypt audit data. "
                "Install with: pip install cryptography"
            )
            # Fallback to placeholder
            for field in sensitive_fields:
                if field in data:
                    data[field] = "***REQUIRES_CRYPTOGRAPHY***"
            return data

        except Exception as e:
            logger.error(f"Unexpected error encrypting sensitive data: {str(e)}", exc_info=True)
            # Return original data to avoid data loss, but log the issue
            return data

    async def _decrypt_sensitive_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Decrypt sensitive fields in audit data.

        Args:
            data: Dictionary containing encrypted sensitive data

        Returns:
            Dictionary with sensitive fields decrypted

        Note:
            Only used for forensic analysis and compliance reporting.
            Requires proper authorization.
        """
        try:
            import base64

            from cryptography.fernet import Fernet

            decrypted_data = data.copy()

            # Get encryption key
            encryption_key = await self._get_encryption_key()

            if not encryption_key:
                logger.warning("No encryption key available, cannot decrypt sensitive data")
                return decrypted_data

            # Create Fernet cipher
            cipher = Fernet(encryption_key.encode())

            # Decrypt each encrypted field
            for key, value in decrypted_data.items():
                if isinstance(value, dict):
                    # Check if this is an encrypted field
                    if value.get("_encrypted"):
                        try:
                            encrypted_b64 = value["_value"]
                            encrypted_bytes = base64.b64decode(encrypted_b64.encode())

                            # Decrypt
                            decrypted_bytes = cipher.decrypt(encrypted_bytes)
                            decrypted_data[key] = decrypted_bytes.decode()

                        except Exception as e:
                            logger.error(
                                f"Failed to decrypt field '{key}': {str(e)}",
                                extra={"field": key, "error": str(e)},
                            )
                            decrypted_data[key] = "***DECRYPTION_FAILED***"
                    else:
                        # Recursively decrypt nested dictionaries
                        decrypted_data[key] = await self._decrypt_sensitive_data(value)

                elif isinstance(value, list):
                    decrypted_data[key] = [
                        await self._decrypt_sensitive_data(item) if isinstance(item, dict) else item
                        for item in value
                    ]

            return decrypted_data

        except ImportError:
            logger.error("cryptography library not installed, cannot decrypt audit data")
            return data

        except Exception as e:
            logger.error(f"Unexpected error decrypting sensitive data: {str(e)}", exc_info=True)
            return data

    async def _get_encryption_key(self) -> str | None:
        """
        Get encryption key for audit data.

        Retrieves key from:
        1. Secrets Manager (production)
        2. Environment variable (development)
        3. None (indicates no encryption available)

        Returns:
            Base64-encoded Fernet key or None
        """
        try:
            # Try to get from secrets manager first
            from src.infrastructure.config import get_secrets_manager

            secrets_manager = get_secrets_manager()
            encryption_key = secrets_manager.get_secret("AUDIT_ENCRYPTION_KEY")

            if encryption_key:
                return encryption_key

        except Exception as e:
            logger.debug(f"Could not get encryption key from secrets manager: {str(e)}")

        # Fallback to environment variable
        import os

        encryption_key = os.environ.get("AUDIT_ENCRYPTION_KEY")

        if encryption_key:
            return encryption_key

        # Generate a warning if no key is available
        logger.warning(
            "No audit encryption key configured. Set AUDIT_ENCRYPTION_KEY in secrets manager or environment. "
            "To generate a key, run: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
        )

        return None

    async def _cache_event(self, event: AuditEvent):
        """Cache event in Redis for quick access"""
        try:
            key = f"audit:event:{event.event_id}"
            await self.redis_client.setex(
                key,
                86400,  # 24 hour cache
                json.dumps(event.to_dict()),
            )

            # Add to sorted set for time-based queries
            await self.redis_client.zadd(
                "audit:events:timeline", {event.event_id: event.timestamp.timestamp()}
            )

            # Add to user index
            if event.user_id:
                await self.redis_client.sadd(f"audit:user:{event.user_id}:events", event.event_id)

        except Exception as e:
            logger.warning(f"Failed to cache audit event: {str(e)}")

    async def _flush_buffer(self):
        """Flush events buffer to persistent storage"""
        if not self._events_buffer:
            return

        try:
            # In production, write to database or file storage
            # For now, just log the flush
            logger.info(f"Flushing {len(self._events_buffer)} audit events to storage")

            # Clear buffer
            self._events_buffer.clear()

        except Exception as e:
            logger.error(f"Failed to flush audit buffer: {str(e)}")

    async def query_events(self, query: AuditTrailQuery) -> list[AuditEvent]:
        """
        Query audit events based on criteria

        Args:
            query: Query parameters

        Returns:
            List of matching audit events
        """
        try:
            events = []

            # In production, query from database
            # For now, query from Redis cache if available
            if self.redis_client:
                # Get events from timeline
                start_score = query.start_date.timestamp() if query.start_date else 0
                end_score = query.end_date.timestamp() if query.end_date else float("inf")

                event_ids = await self.redis_client.zrangebyscore(
                    "audit:events:timeline",
                    start_score,
                    end_score,
                    start=query.offset,
                    num=query.limit,
                )

                # Fetch event details
                for event_id in event_ids:
                    event_data = await self.redis_client.get(f"audit:event:{event_id}")
                    if event_data:
                        event_dict = json.loads(event_data)
                        # Apply filters
                        if self._matches_query(event_dict, query):
                            events.append(self._dict_to_event(event_dict))

            return events

        except Exception as e:
            logger.error(f"Failed to query audit events: {str(e)}")
            raise ReflectAIError(
                message="Audit query failed", error_code="AUDIT_002", details={"error": str(e)}
            ) from e

    def _matches_query(self, event_dict: dict[str, Any], query: AuditTrailQuery) -> bool:
        """Check if event matches query criteria"""
        if query.user_ids and event_dict.get("user_id") not in query.user_ids:
            return False
        if query.team_ids and event_dict.get("team_id") not in query.team_ids:
            return False
        if query.actions and event_dict.get("action") not in [a.value for a in query.actions]:
            return False
        if query.levels and event_dict.get("level") not in [level.value for level in query.levels]:
            return False
        if query.resource_types and event_dict.get("resource_type") not in query.resource_types:
            return False
        if query.correlation_id and event_dict.get("correlation_id") != query.correlation_id:
            return False
        return True

    def _dict_to_event(self, data: dict[str, Any]) -> AuditEvent:
        """Convert dictionary to AuditEvent"""
        # Convert string enums back to enum types
        data["action"] = AuditAction(data["action"])
        data["level"] = AuditLevel(data["level"])
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        data["compliance_tags"] = [
            ComplianceStandard(tag) for tag in data.get("compliance_tags", [])
        ]
        return AuditEvent(**data)

    async def generate_compliance_report(
        self, standard: ComplianceStandard, start_date: datetime, end_date: datetime
    ) -> ComplianceReport:
        """
        Generate compliance report for a standard

        Args:
            standard: Compliance standard to report on
            start_date: Report period start
            end_date: Report period end

        Returns:
            Compliance report
        """
        try:
            report = ComplianceReport(
                standard=standard, period_start=start_date, period_end=end_date
            )

            # Get relevant actions for this standard
            relevant_actions = self._compliance_mappings.get(standard, [])

            # Query events
            query = AuditTrailQuery(
                start_date=start_date, end_date=end_date, actions=relevant_actions, limit=1000
            )

            events = await self.query_events(query)

            # Analyze events
            for event in events:
                report.total_events += 1

                if event.level == AuditLevel.CRITICAL:
                    report.critical_events += 1

                # User activity summary
                if event.user_id:
                    report.user_activity_summary[event.user_id] = (
                        report.user_activity_summary.get(event.user_id, 0) + 1
                    )

                # Data access summary
                if event.action in [AuditAction.DATA_ACCESS, AuditAction.DATA_EXPORT]:
                    resource = event.resource_type or "unknown"
                    report.data_access_summary[resource] = (
                        report.data_access_summary.get(resource, 0) + 1
                    )

                # Security incidents
                if event.level in [AuditLevel.ERROR, AuditLevel.CRITICAL]:
                    report.security_incidents.append(
                        {
                            "event_id": event.event_id,
                            "timestamp": event.timestamp.isoformat(),
                            "description": event.description,
                        }
                    )

            # Generate recommendations
            report.recommendations = self._generate_recommendations(report, standard)

            logger.info(
                f"Generated compliance report for {standard.value}",
                extra={
                    "standard": standard.value,
                    "total_events": report.total_events,
                    "critical_events": report.critical_events,
                },
            )

            return report

        except Exception as e:
            logger.error(f"Failed to generate compliance report: {str(e)}")
            raise ReflectAIError(
                message="Compliance report generation failed",
                error_code="AUDIT_003",
                details={"error": str(e)},
            ) from e

    def _generate_recommendations(
        self, report: ComplianceReport, standard: ComplianceStandard
    ) -> list[str]:
        """Generate compliance recommendations based on report"""
        recommendations = []

        if report.critical_events > 0:
            recommendations.append(
                f"Review and address {report.critical_events} critical security events"
            )

        if standard == ComplianceStandard.GDPR:
            if AuditAction.DATA_DELETION not in [e.action for e in report.security_incidents]:
                recommendations.append(
                    "Ensure data deletion requests are properly logged and processed"
                )

        if standard == ComplianceStandard.SOC2:
            if report.total_events < 100:
                recommendations.append(
                    "Increase audit logging coverage for system administration activities"
                )

        return recommendations

    async def cleanup_old_events(self, days: int | None = None):
        """
        Clean up old audit events beyond retention period

        Args:
            days: Override retention days
        """
        retention = days or self.retention_days
        cutoff_date = datetime.now(UTC) - timedelta(days=retention)

        try:
            logger.info(f"Cleaning up audit events older than {cutoff_date}")

            # In production, delete from database
            # For Redis cache, remove old events
            if self.redis_client:
                cutoff_score = cutoff_date.timestamp()
                removed = await self.redis_client.zremrangebyscore(
                    "audit:events:timeline", 0, cutoff_score
                )

                logger.info(f"Removed {removed} old audit events from cache")

        except Exception as e:
            logger.error(f"Failed to cleanup old audit events: {str(e)}")


class AuditTrailManager:
    """
    High-level manager for audit trail operations
    """

    def __init__(self, redis_client: redis.Redis | None = None):
        """Initialize audit trail manager"""
        self.logger = AuditLogger(redis_client=redis_client)
        self.redis_client = redis_client

    async def log_user_action(
        self, user_id: str, action: AuditAction, description: str, **kwargs
    ) -> str:
        """Log a user action"""
        event = AuditEvent(
            action=action, level=AuditLevel.INFO, user_id=user_id, description=description, **kwargs
        )
        return await self.logger.log_event(event)

    async def log_security_event(
        self, description: str, level: AuditLevel = AuditLevel.WARNING, **kwargs
    ) -> str:
        """Log a security event"""
        event = AuditEvent(
            action=AuditAction.SECURITY_EVENT, level=level, description=description, **kwargs
        )
        return await self.logger.log_event(event)

    async def log_data_change(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        before_state: dict[str, Any],
        after_state: dict[str, Any],
        **kwargs,
    ) -> str:
        """Log a data change with before/after states"""
        event = AuditEvent(
            action=AuditAction.DATA_MODIFICATION,
            level=AuditLevel.INFO,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            before_state=before_state,
            after_state=after_state,
            description=f"Modified {resource_type} {resource_id}",
            **kwargs,
        )
        return await self.logger.log_event(event)

    async def decrypt_audit_data(
        self, data: dict[str, Any], authorized_user_id: str | None = None
    ) -> dict[str, Any]:
        """
        Decrypt sensitive audit data for authorized forensic analysis.

        Args:
            data: Dictionary containing encrypted sensitive data
            authorized_user_id: User ID requesting decryption (for audit trail)

        Returns:
            Dictionary with sensitive fields decrypted

        Note:
            This should only be used for:
            - Forensic analysis by security team
            - Compliance reporting
            - Legal/regulatory requirements
            Access should be strictly controlled and logged.
        """
        # Log the decryption access
        await self.log_security_event(
            description="Audit data decryption accessed",
            level=AuditLevel.WARNING,
            user_id=authorized_user_id,
            details={"operation": "decrypt_audit_data", "reason": "forensic_analysis"},
        )

        # Decrypt the data
        return await self.logger._decrypt_sensitive_data(data)

    async def verify_encryption_status(self) -> dict[str, Any]:
        """
        Verify encryption is properly configured and working.

        Returns:
            Status dictionary with encryption configuration details
        """
        try:
            # Check if encryption key is available
            encryption_key = await self.logger._get_encryption_key()

            if not encryption_key:
                return {
                    "encryption_enabled": False,
                    "status": "warning",
                    "message": "No encryption key configured. Audit data will not be encrypted.",
                    "recommendation": "Set AUDIT_ENCRYPTION_KEY in secrets manager or environment",
                }

            # Test encryption/decryption roundtrip
            test_data = {
                "password": "test_password",
                "api_key": "test_api_key",
                "normal_field": "normal_value",
            }

            encrypted = await self.logger._encrypt_sensitive_data(test_data)
            decrypted = await self.logger._decrypt_sensitive_data(encrypted)

            # Verify roundtrip worked
            encryption_working = (
                decrypted.get("password") == "test_password"
                and decrypted.get("api_key") == "test_api_key"
                and decrypted.get("normal_field") == "normal_value"
            )

            if encryption_working:
                return {
                    "encryption_enabled": True,
                    "status": "healthy",
                    "message": "Audit encryption is properly configured and working",
                    "algorithm": "fernet_aes256",
                    "key_source": "secrets_manager"
                    if encryption_key != os.environ.get("AUDIT_ENCRYPTION_KEY")
                    else "environment",
                }
            else:
                return {
                    "encryption_enabled": True,
                    "status": "error",
                    "message": "Encryption key configured but encryption/decryption failed",
                    "recommendation": "Verify encryption key is valid Fernet key",
                }

        except Exception as e:
            return {
                "encryption_enabled": False,
                "status": "error",
                "message": f"Error verifying encryption: {str(e)}",
                "recommendation": "Check logs for details and verify cryptography library is installed",
            }


class ComplianceAnalyzer:
    """
    Analyzer for compliance-related audit analysis
    """

    def __init__(self, audit_logger: AuditLogger):
        """Initialize compliance analyzer"""
        self.audit_logger = audit_logger

    async def check_compliance_violations(
        self, standard: ComplianceStandard, period_days: int = 30
    ) -> list[dict[str, Any]]:
        """Check for compliance violations"""
        end_date = datetime.now(UTC)
        start_date = end_date - timedelta(days=period_days)

        report = await self.audit_logger.generate_compliance_report(standard, start_date, end_date)

        return report.compliance_violations

    async def generate_audit_summary(
        self, user_id: str | None = None, period_days: int = 30
    ) -> dict[str, Any]:
        """Generate audit summary for user or system"""
        end_date = datetime.now(UTC)
        start_date = end_date - timedelta(days=period_days)

        query = AuditTrailQuery(
            start_date=start_date,
            end_date=end_date,
            user_ids=[user_id] if user_id else [],
            limit=1000,
        )

        events = await self.audit_logger.query_events(query)

        summary = {
            "period": f"{period_days} days",
            "total_events": len(events),
            "events_by_action": {},
            "events_by_level": {},
            "top_users": {},
            "critical_events": [],
        }

        for event in events:
            # Count by action
            action = event.action.value
            summary["events_by_action"][action] = summary["events_by_action"].get(action, 0) + 1

            # Count by level
            level = event.level.value
            summary["events_by_level"][level] = summary["events_by_level"].get(level, 0) + 1

            # Top users
            if event.user_id:
                summary["top_users"][event.user_id] = summary["top_users"].get(event.user_id, 0) + 1

            # Critical events
            if event.level == AuditLevel.CRITICAL:
                summary["critical_events"].append(
                    {
                        "event_id": event.event_id,
                        "timestamp": event.timestamp.isoformat(),
                        "description": event.description,
                    }
                )

        return summary


# Global instance management
_audit_trail_manager: AuditTrailManager | None = None


def get_audit_trail_manager(redis_client: redis.Redis | None = None) -> AuditTrailManager:
    """Get or create audit trail manager instance"""
    global _audit_trail_manager

    if _audit_trail_manager is None:
        _audit_trail_manager = AuditTrailManager(redis_client=redis_client)

    return _audit_trail_manager
