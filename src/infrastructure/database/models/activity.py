"""
Activity model for ReflectAI TimescaleDB hypertable

Implements activity tracking and analysis with support for:
- TimescaleDB hypertable for time-series data
- JSONB fields for flexible metadata storage
- Activity classification and competency mapping
- Workflow integration and correlation tracking
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import ARRAY, DECIMAL, JSON, UUID, CheckConstraint, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import TimescaleModel


class Activity(TimescaleModel):
    """Activity model for TimescaleDB hypertable storing user activities"""

    __tablename__ = "activities"
    __table_args__ = (
        # Check constraints from schema
        CheckConstraint("LENGTH(content) > 0", name="activities_content_not_empty"),
        CheckConstraint(
            "processing_status IN ('pending', 'processing', 'complete', 'failed', 'archived')",
            name="activities_processing_status_valid",
        ),
        CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="activities_confidence_valid",
        ),
        # Indexes optimized for TimescaleDB
        Index("idx_activities_user_id_timestamp", "user_id", "timestamp"),
        Index("idx_activities_type_timestamp", "activity_type", "timestamp"),
        Index("idx_activities_status", "processing_status"),
        Index(
            "idx_activities_workflow_id", "workflow_id", postgresql_where="workflow_id IS NOT NULL"
        ),
        Index(
            "idx_activities_correlation_id",
            "correlation_id",
            postgresql_where="correlation_id IS NOT NULL",
        ),
        Index("idx_activities_thread_ts", "thread_ts", postgresql_where="thread_ts IS NOT NULL"),
        Index("idx_activities_classification_gin", "classification", postgresql_using="gin"),
        Index("idx_activities_metrics_gin", "metrics", postgresql_using="gin"),
        Index("idx_activities_competency_areas_gin", "competency_areas", postgresql_using="gin"),
        {"comment": "TimescaleDB hypertable for user activity tracking and analysis"},
    )

    # Relationships
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, comment="Reference to user who performed the activity"
    )

    # Core activity data
    content: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Activity content (message, code, etc.)"
    )

    activity_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Type of activity (message, code_review, deployment, etc.)",
    )

    source: Mapped[str] = mapped_column(
        String(50),
        server_default="slack",
        nullable=False,
        comment="Source system where activity originated",
    )

    # Analysis and classification
    classification: Mapped[dict[str, Any]] = mapped_column(
        JSON, server_default="{}", nullable=False, comment="AI classification results and metadata"
    )

    metrics: Mapped[dict[str, Any]] = mapped_column(
        JSON, server_default="{}", nullable=False, comment="Calculated metrics and scores"
    )

    # Processing status
    processing_status: Mapped[str] = mapped_column(
        String(20), server_default="pending", nullable=False, comment="Current processing status"
    )

    confidence_score: Mapped[Decimal | None] = mapped_column(
        DECIMAL(3, 2), nullable=True, comment="Confidence score for analysis (0-1)"
    )

    evidence: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        server_default="{}",
        nullable=False,
        comment="Evidence supporting analysis and classification",
    )

    # Competency mapping
    competency_areas: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True, comment="Array of competency areas demonstrated"
    )

    # Workflow integration
    workflow_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, comment="Optional workflow that processed this activity"
    )

    correlation_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Correlation ID for tracking related activities"
    )

    # Slack-specific metadata
    thread_ts: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="Slack thread timestamp for message threading"
    )

    channel_id: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="Slack channel ID where activity occurred"
    )

    # Additional timestamp for created_at (different from partitioning timestamp)
    created_at: Mapped[datetime] = mapped_column(
        "created_at", server_default="now()", nullable=False, comment="Activity creation timestamp"
    )

    updated_at: Mapped[datetime] = mapped_column(
        "updated_at",
        server_default="now()",
        onupdate="now()",
        nullable=False,
        comment="Activity last update timestamp",
    )

    # Relationships
    user = relationship("User", back_populates="activities")
    competency_history = relationship(
        "CompetencyHistory", back_populates="activity", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """String representation of activity"""
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return (
            f"<Activity("
            f"id={self.id}, "
            f"user_id={self.user_id}, "
            f"type='{self.activity_type}', "
            f"status='{self.processing_status}', "
            f"content='{content_preview}', "
            f"timestamp={self.timestamp}"
            f")>"
        )

    def get_competency_count(self) -> int:
        """Get count of competency areas demonstrated"""
        return len(self.competency_areas) if self.competency_areas else 0

    def has_competency(self, competency_id: str) -> bool:
        """Check if activity demonstrates specific competency"""
        return self.competency_areas is not None and competency_id in self.competency_areas

    def add_competency(self, competency_id: str) -> None:
        """Add a competency area to this activity"""
        if self.competency_areas is None:
            self.competency_areas = []
        if competency_id not in self.competency_areas:
            self.competency_areas.append(competency_id)

    def get_classification_value(self, key: str, default: Any = None) -> Any:
        """Get a value from classification data"""
        if self.classification and isinstance(self.classification, dict):
            return self.classification.get(key, default)
        return default

    def set_classification_value(self, key: str, value: Any) -> None:
        """Set a value in classification data"""
        if not isinstance(self.classification, dict):
            self.classification = {}
        self.classification[key] = value

    def get_metric_value(self, key: str, default: Any = None) -> Any:
        """Get a value from metrics data"""
        if self.metrics and isinstance(self.metrics, dict):
            return self.metrics.get(key, default)
        return default

    def set_metric_value(self, key: str, value: Any) -> None:
        """Set a value in metrics data"""
        if not isinstance(self.metrics, dict):
            self.metrics = {}
        self.metrics[key] = value

    def mark_processed(self, confidence: float | None = None) -> None:
        """Mark activity as processed with optional confidence score"""
        self.processing_status = "complete"
        if confidence is not None:
            self.confidence_score = Decimal(str(confidence))

    def mark_failed(self, error_info: dict[str, Any] | None = None) -> None:
        """Mark activity as failed with optional error information"""
        self.processing_status = "failed"
        if error_info:
            self.set_classification_value("error", error_info)

    def get_age_seconds(self) -> float:
        """Get age of activity in seconds"""
        return (datetime.now(UTC) - self.timestamp.replace(tzinfo=None)).total_seconds()

    def is_recent(self, hours: int = 24) -> bool:
        """Check if activity is recent (within specified hours)"""
        age_hours = self.get_age_seconds() / 3600
        return age_hours <= hours

    @property
    def summary(self) -> dict[str, Any]:
        """Get activity summary for API responses"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "content_preview": self.content[:100] + "..."
            if len(self.content) > 100
            else self.content,
            "activity_type": self.activity_type,
            "source": self.source,
            "processing_status": self.processing_status,
            "confidence_score": float(self.confidence_score) if self.confidence_score else None,
            "competency_count": self.get_competency_count(),
            "competency_areas": self.competency_areas or [],
            "timestamp": self.timestamp.isoformat(),
            "created_at": self.created_at.isoformat(),
            "is_recent": self.is_recent(),
        }
