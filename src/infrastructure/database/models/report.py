"""
Report model for ReflectAI report generation and delivery

Implements report generation tracking with support for:
- Multiple report formats (Slack, PDF, JSON, CSV)
- Report parameters and content storage
- File metadata and storage tracking
- Delivery status and metadata
- Report expiration and lifecycle management
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    UUID,
    BigInteger,
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel


class Report(BaseModel):
    """Report generation and delivery tracking"""

    __tablename__ = "reports"
    __table_args__ = (
        # Foreign key constraints
        # Check constraints from schema
        CheckConstraint("format IN ('slack', 'pdf', 'json', 'csv')", name="reports_format_valid"),
        CheckConstraint(
            "status IN ('pending', 'generating', 'ready', 'delivered', 'failed', 'expired')",
            name="reports_status_valid",
        ),
        CheckConstraint(
            "delivery_status IS NULL OR delivery_status IN ('pending', 'sent', 'failed', 'acknowledged')",
            name="reports_delivery_status_valid",
        ),
        # Indexes for performance
        Index("idx_reports_user_id", "user_id"),
        Index("idx_reports_type", "report_type"),
        Index("idx_reports_status", "status"),
        Index(
            "idx_reports_generated_at",
            "generated_at",
        ),
        Index("idx_reports_expires_at", "expires_at", postgresql_where="expires_at IS NOT NULL"),
        {"comment": "Report generation and delivery tracking"},
    )

    # Relationships
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, comment="User who requested the report"
    )

    # Report identification and type
    report_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Type of report (competency_summary, activity_analysis, etc.)",
    )

    title: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="Human-readable report title"
    )

    # Format and status
    format: Mapped[str] = mapped_column(
        String(20), server_default="slack", nullable=False, comment="Report output format"
    )

    status: Mapped[str] = mapped_column(
        String(20),
        server_default="pending",
        nullable=False,
        comment="Current report generation status",
    )

    # Report data
    parameters: Mapped[dict[str, Any]] = mapped_column(
        JSON, server_default="{}", nullable=False, comment="Parameters used to generate report"
    )

    content: Mapped[dict[str, Any]] = mapped_column(
        JSON, server_default="{}", nullable=False, comment="Report content and structured data"
    )

    # File metadata (for PDF, CSV reports)
    file_path: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="Path to generated file (if applicable)"
    )

    file_size_bytes: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, comment="File size in bytes"
    )

    page_count: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Number of pages (for PDF reports)"
    )

    # Delivery tracking
    delivery_method: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="How report was delivered (slack_message, email, download)",
    )

    delivery_status: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="Status of report delivery"
    )

    delivery_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        server_default="{}",
        nullable=False,
        comment="Delivery-specific metadata and tracking info",
    )

    # Timing
    generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="When report generation completed"
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="When report expires and can be cleaned up"
    )

    # Relationships
    user = relationship("User", back_populates="reports")

    def __repr__(self) -> str:
        """String representation of report"""
        return (
            f"<Report("
            f"id={self.id}, "
            f"user_id={self.user_id}, "
            f"type='{self.report_type}', "
            f"format='{self.format}', "
            f"status='{self.status}', "
            f"title='{self.title[:30]}...'"
            f")>"
        )

    def is_pending(self) -> bool:
        """Check if report is pending generation"""
        return self.status == "pending"

    def is_generating(self) -> bool:
        """Check if report is currently generating"""
        return self.status == "generating"

    def is_ready(self) -> bool:
        """Check if report is ready for delivery"""
        return self.status == "ready"

    def is_delivered(self) -> bool:
        """Check if report has been delivered"""
        return self.status == "delivered"

    def is_failed(self) -> bool:
        """Check if report generation failed"""
        return self.status == "failed"

    def is_expired(self) -> bool:
        """Check if report has expired"""
        return self.status == "expired" or (
            self.expires_at and datetime.now(UTC) > self.expires_at.replace(tzinfo=None)
        )

    def has_file(self) -> bool:
        """Check if report has an associated file"""
        return bool(self.file_path)

    def get_generation_duration(self) -> float | None:
        """Get report generation duration in seconds"""
        if not self.generated_at:
            return None
        return (
            self.generated_at.replace(tzinfo=None) - self.created_at.replace(tzinfo=None)
        ).total_seconds()

    def start_generation(self) -> None:
        """Mark report generation as started"""
        self.status = "generating"

    def complete_generation(self, content_data: dict[str, Any] | None = None) -> None:
        """Mark report generation as completed"""
        self.status = "ready"
        self.generated_at = datetime.now(UTC)
        if content_data:
            self.content.update(content_data)

    def fail_generation(self, error_info: dict[str, Any]) -> None:
        """Mark report generation as failed"""
        self.status = "failed"
        self.content["error"] = error_info

    def mark_delivered(
        self, delivery_method: str, delivery_metadata: dict[str, Any] | None = None
    ) -> None:
        """Mark report as delivered"""
        self.status = "delivered"
        self.delivery_method = delivery_method
        self.delivery_status = "sent"
        if delivery_metadata:
            self.delivery_metadata.update(delivery_metadata)

    def mark_expired(self) -> None:
        """Mark report as expired"""
        self.status = "expired"

    def set_file_info(self, file_path: str, file_size: int, page_count: int | None = None) -> None:
        """Set file metadata for report"""
        self.file_path = file_path
        self.file_size_bytes = file_size
        if page_count is not None:
            self.page_count = page_count

    def get_parameter_value(self, key: str, default: Any = None) -> Any:
        """Get a parameter value"""
        if self.parameters and isinstance(self.parameters, dict):
            return self.parameters.get(key, default)
        return default

    def set_parameter_value(self, key: str, value: Any) -> None:
        """Set a parameter value"""
        if not isinstance(self.parameters, dict):
            self.parameters = {}
        self.parameters[key] = value

    def get_content_value(self, key: str, default: Any = None) -> Any:
        """Get a content value"""
        if self.content and isinstance(self.content, dict):
            return self.content.get(key, default)
        return default

    def set_content_value(self, key: str, value: Any) -> None:
        """Set a content value"""
        if not isinstance(self.content, dict):
            self.content = {}
        self.content[key] = value

    def get_delivery_metadata_value(self, key: str, default: Any = None) -> Any:
        """Get a delivery metadata value"""
        if self.delivery_metadata and isinstance(self.delivery_metadata, dict):
            return self.delivery_metadata.get(key, default)
        return default

    def set_delivery_metadata_value(self, key: str, value: Any) -> None:
        """Set a delivery metadata value"""
        if not isinstance(self.delivery_metadata, dict):
            self.delivery_metadata = {}
        self.delivery_metadata[key] = value

    def get_file_size_mb(self) -> float | None:
        """Get file size in megabytes"""
        if self.file_size_bytes is None:
            return None
        return round(self.file_size_bytes / (1024 * 1024), 2)

    def should_expire(self, days: int = 30) -> bool:
        """Check if report should be expired based on age"""
        if self.is_expired():
            return True
        age_days = (datetime.now(UTC) - self.created_at.replace(tzinfo=None)).days
        return age_days >= days

    def get_expiration_info(self) -> dict[str, Any]:
        """Get report expiration information"""
        return {
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_expired": self.is_expired(),
            "should_expire": self.should_expire(),
            "age_days": (datetime.now(UTC) - self.created_at.replace(tzinfo=None)).days,
        }

    @property
    def summary(self) -> dict[str, Any]:
        """Get report summary for API responses"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "report_type": self.report_type,
            "title": self.title,
            "format": self.format,
            "status": self.status,
            "delivery_method": self.delivery_method,
            "delivery_status": self.delivery_status,
            "has_file": self.has_file(),
            "file_size_mb": self.get_file_size_mb(),
            "page_count": self.page_count,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "generation_duration": self.get_generation_duration(),
            "expiration_info": self.get_expiration_info(),
            "created_at": self.created_at.isoformat(),
        }
