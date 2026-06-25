"""
Event models for ReflectAI system tracking and audit

Implements event tracking with support for:
- System events in TimescaleDB hypertable
- Audit events for compliance tracking
- Event correlation and metadata storage
- Processing status tracking
- JSONB fields for flexible event data
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, UUID, CheckConstraint, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import TimescaleModel


class Event(TimescaleModel):
    """System events in TimescaleDB hypertable for high-frequency event tracking"""

    __tablename__ = "events"
    __table_args__ = (
        # Check constraints from schema
        CheckConstraint("LENGTH(event_type) > 0", name="events_type_not_empty"),
        CheckConstraint("LENGTH(event_source) > 0", name="events_source_not_empty"),
        CheckConstraint(
            "processing_status IN ('pending', 'processing', 'processed', 'failed', 'skipped')",
            name="events_processing_status_valid",
        ),
        # Indexes optimized for TimescaleDB time-series queries
        Index(
            "idx_events_type_timestamp",
            "event_type",
            "timestamp",
        ),
        Index(
            "idx_events_user_id_timestamp",
            "user_id",
            "timestamp",
            postgresql_where="user_id IS NOT NULL",
        ),
        Index(
            "idx_events_correlation_id",
            "correlation_id",
            postgresql_where="correlation_id IS NOT NULL",
        ),
        Index("idx_events_status", "processing_status"),
        Index("idx_events_event_data_gin", "event_data", postgresql_using="gin"),
        {"comment": "TimescaleDB hypertable for high-frequency system event tracking"},
    )

    # Event identification
    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Type of event (user_action, system_event, integration_event, etc.)",
    )

    event_source: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="Source system or component that generated the event"
    )

    # Relationships
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User associated with the event (if applicable)",
    )

    # Event correlation
    correlation_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Correlation ID for tracking related events"
    )

    # Event data
    event_data: Mapped[dict[str, Any]] = mapped_column(
        JSON, server_default="{}", nullable=False, comment="Event-specific data and payload"
    )

    event_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON, server_default="{}", nullable=False, comment="Additional metadata about the event"
    )

    # Processing status
    processing_status: Mapped[str] = mapped_column(
        String(20), server_default="pending", nullable=False, comment="Event processing status"
    )

    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="When event processing completed"
    )

    # Relationships
    user = relationship("User")

    def __repr__(self) -> str:
        """String representation of event"""
        return (
            f"<Event("
            f"id={self.id}, "
            f"type='{self.event_type}', "
            f"source='{self.event_source}', "
            f"user_id={self.user_id}, "
            f"status='{self.processing_status}', "
            f"timestamp={self.timestamp}"
            f")>"
        )

    def is_pending(self) -> bool:
        """Check if event is pending processing"""
        return self.processing_status == "pending"

    def is_processing(self) -> bool:
        """Check if event is currently being processed"""
        return self.processing_status == "processing"

    def is_processed(self) -> bool:
        """Check if event has been processed"""
        return self.processing_status == "processed"

    def is_failed(self) -> bool:
        """Check if event processing failed"""
        return self.processing_status == "failed"

    def is_skipped(self) -> bool:
        """Check if event was skipped"""
        return self.processing_status == "skipped"

    def start_processing(self) -> None:
        """Mark event as being processed"""
        self.processing_status = "processing"

    def complete_processing(self) -> None:
        """Mark event processing as completed"""
        self.processing_status = "processed"
        self.processed_at = datetime.now(UTC)

    def fail_processing(self, error_info: dict[str, Any]) -> None:
        """Mark event processing as failed"""
        self.processing_status = "failed"
        self.processed_at = datetime.now(UTC)
        self.set_metadata_value("error", error_info)

    def skip_processing(self, reason: str) -> None:
        """Mark event as skipped"""
        self.processing_status = "skipped"
        self.processed_at = datetime.now(UTC)
        self.set_metadata_value("skip_reason", reason)

    def get_event_data_value(self, key: str, default: Any = None) -> Any:
        """Get a value from event_data"""
        if self.event_data and isinstance(self.event_data, dict):
            return self.event_data.get(key, default)
        return default

    def set_event_data_value(self, key: str, value: Any) -> None:
        """Set a value in event_data"""
        if not isinstance(self.event_data, dict):
            self.event_data = {}
        self.event_data[key] = value

    def get_metadata_value(self, key: str, default: Any = None) -> Any:
        """Get a value from metadata"""
        if self.metadata and isinstance(self.metadata, dict):
            return self.metadata.get(key, default)
        return default

    def set_metadata_value(self, key: str, value: Any) -> None:
        """Set a value in metadata"""
        if not isinstance(self.metadata, dict):
            self.metadata = {}
        self.metadata[key] = value

    def get_processing_duration(self) -> float | None:
        """Get processing duration in seconds"""
        if not self.processed_at:
            return None
        return (
            self.processed_at.replace(tzinfo=None) - self.timestamp.replace(tzinfo=None)
        ).total_seconds()

    def get_age_seconds(self) -> float:
        """Get event age in seconds"""
        return (datetime.now(UTC) - self.timestamp.replace(tzinfo=None)).total_seconds()

    def is_recent(self, hours: int = 1) -> bool:
        """Check if event is recent"""
        age_hours = self.get_age_seconds() / 3600
        return age_hours <= hours

    @property
    def summary(self) -> dict[str, Any]:
        """Get event summary for API responses"""
        return {
            "id": str(self.id),
            "event_type": self.event_type,
            "event_source": self.event_source,
            "user_id": str(self.user_id) if self.user_id else None,
            "correlation_id": self.correlation_id,
            "processing_status": self.processing_status,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "processing_duration": self.get_processing_duration(),
            "age_seconds": self.get_age_seconds(),
            "timestamp": self.timestamp.isoformat(),
            "is_recent": self.is_recent(),
        }


class AuditEvent(TimescaleModel):
    """Audit events for compliance and security tracking"""

    __tablename__ = "audit_events"
    __table_args__ = (
        # Check constraints from schema
        CheckConstraint(
            "action IN ('CREATE', 'UPDATE', 'DELETE', 'SELECT', 'LOGIN', 'LOGOUT')",
            name="audit_events_action_valid",
        ),
        # Indexes optimized for TimescaleDB and audit queries
        Index(
            "idx_audit_events_timestamp",
            "timestamp",
        ),
        Index("idx_audit_events_user_id", "user_id", postgresql_where="user_id IS NOT NULL"),
        Index(
            "idx_audit_events_table_record",
            "table_name",
            "record_id",
            postgresql_where="table_name IS NOT NULL",
        ),
        Index("idx_audit_events_action", "action"),
        {"comment": "TimescaleDB hypertable for audit events and compliance tracking"},
    )

    # Event identification
    event_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="Type of audit event"
    )

    # Database change tracking
    table_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Table name for database change events"
    )

    record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, comment="Record ID for database change events"
    )

    # User and action
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, comment="User who performed the action"
    )

    action: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="Action performed (CREATE, UPDATE, DELETE, etc.)"
    )

    # Change tracking
    old_values: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="Previous values for UPDATE/DELETE operations"
    )

    new_values: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="New values for CREATE/UPDATE operations"
    )

    # Context and metadata
    change_context: Mapped[dict[str, Any]] = mapped_column(
        JSON, server_default="{}", nullable=False, comment="Context information about the change"
    )

    client_info: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        server_default="{}",
        nullable=False,
        comment="Client information (IP, user agent, etc.)",
    )

    def __repr__(self) -> str:
        """String representation of audit event"""
        return (
            f"<AuditEvent("
            f"id={self.id}, "
            f"type='{self.event_type}', "
            f"action='{self.action}', "
            f"user_id={self.user_id}, "
            f"table='{self.table_name}', "
            f"timestamp={self.timestamp}"
            f")>"
        )

    def is_data_change(self) -> bool:
        """Check if this is a data change event"""
        return self.action in ["CREATE", "UPDATE", "DELETE"]

    def is_access_event(self) -> bool:
        """Check if this is an access/authentication event"""
        return self.action in ["LOGIN", "LOGOUT", "SELECT"]

    def has_data_changes(self) -> bool:
        """Check if event contains actual data changes"""
        return bool(self.old_values or self.new_values)

    def get_changed_fields(self) -> set:
        """Get set of fields that were changed"""
        changed = set()

        if self.old_values and self.new_values:
            # For updates, compare old and new values
            old_keys = set(self.old_values.keys()) if isinstance(self.old_values, dict) else set()
            new_keys = set(self.new_values.keys()) if isinstance(self.new_values, dict) else set()
            all_keys = old_keys | new_keys

            for key in all_keys:
                old_val = self.old_values.get(key) if self.old_values else None
                new_val = self.new_values.get(key) if self.new_values else None
                if old_val != new_val:
                    changed.add(key)
        elif self.new_values:
            # For creates, all new values are "changed"
            changed.update(self.new_values.keys() if isinstance(self.new_values, dict) else [])
        elif self.old_values:
            # For deletes, all old values are "changed"
            changed.update(self.old_values.keys() if isinstance(self.old_values, dict) else [])

        return changed

    def get_field_change(self, field_name: str) -> dict[str, Any]:
        """Get before/after values for a specific field"""
        old_val = None
        new_val = None

        if self.old_values and isinstance(self.old_values, dict):
            old_val = self.old_values.get(field_name)

        if self.new_values and isinstance(self.new_values, dict):
            new_val = self.new_values.get(field_name)

        return {
            "field": field_name,
            "old_value": old_val,
            "new_value": new_val,
            "changed": old_val != new_val,
        }

    def get_context_value(self, key: str, default: Any = None) -> Any:
        """Get a value from change_context"""
        if self.change_context and isinstance(self.change_context, dict):
            return self.change_context.get(key, default)
        return default

    def set_context_value(self, key: str, value: Any) -> None:
        """Set a value in change_context"""
        if not isinstance(self.change_context, dict):
            self.change_context = {}
        self.change_context[key] = value

    def get_client_info_value(self, key: str, default: Any = None) -> Any:
        """Get a value from client_info"""
        if self.client_info and isinstance(self.client_info, dict):
            return self.client_info.get(key, default)
        return default

    def set_client_info_value(self, key: str, value: Any) -> None:
        """Set a value in client_info"""
        if not isinstance(self.client_info, dict):
            self.client_info = {}
        self.client_info[key] = value

    def get_client_ip(self) -> str | None:
        """Get client IP address"""
        return self.get_client_info_value("ip_address")

    def get_user_agent(self) -> str | None:
        """Get client user agent"""
        return self.get_client_info_value("user_agent")

    @property
    def summary(self) -> dict[str, Any]:
        """Get audit event summary for API responses"""
        return {
            "id": str(self.id),
            "event_type": self.event_type,
            "action": self.action,
            "user_id": str(self.user_id) if self.user_id else None,
            "table_name": self.table_name,
            "record_id": str(self.record_id) if self.record_id else None,
            "changed_fields": list(self.get_changed_fields()),
            "has_data_changes": self.has_data_changes(),
            "is_data_change": self.is_data_change(),
            "is_access_event": self.is_access_event(),
            "client_ip": self.get_client_ip(),
            "timestamp": self.timestamp.isoformat(),
        }
