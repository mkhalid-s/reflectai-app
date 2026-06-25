"""
Competency models for ReflectAI competency tracking

Implements competency scoring and history tracking with support for:
- Current competency levels and targets
- Evidence-based scoring with confidence intervals
- Trend analysis and change tracking
- TimescaleDB hypertable for competency history
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import (
    ARRAY,
    DECIMAL,
    UUID,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel, TimescaleModel


class Competency(BaseModel):
    """Current competency levels and metadata for users"""

    __tablename__ = "competencies"
    __table_args__ = (
        # Foreign key constraints
        # Check constraints from schema
        CheckConstraint(
            "current_level >= 0 AND current_level <= 5", name="competencies_current_level_valid"
        ),
        CheckConstraint(
            "target_level IS NULL OR (target_level >= 0 AND target_level <= 5)",
            name="competencies_target_level_valid",
        ),
        CheckConstraint(
            "trend_direction IN ('improving', 'stable', 'declining')",
            name="competencies_trend_direction_valid",
        ),
        # Unique constraint
        CheckConstraint(
            "user_id IS NOT NULL AND competency_id IS NOT NULL",
            name="competencies_user_competency_unique",
        ),
        # Indexes for performance
        Index("idx_competencies_user_id", "user_id"),
        Index("idx_competencies_competency_id", "competency_id"),
        Index("idx_competencies_current_level", "current_level"),
        Index("idx_competencies_trend", "trend_direction", "trend_strength"),
        Index("idx_competencies_last_calculated", "last_calculated_at"),
        {"comment": "Current competency levels and scoring for users"},
    )

    # Relationships
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, comment="Reference to user"
    )

    # Competency identification
    competency_id: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="Unique identifier for competency type"
    )

    competency_name: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="Human-readable competency name"
    )

    # Current scoring
    current_level: Mapped[Decimal] = mapped_column(
        DECIMAL(3, 2), nullable=False, comment="Current competency level (0-5 scale)"
    )

    target_level: Mapped[Decimal | None] = mapped_column(
        DECIMAL(3, 2), nullable=True, comment="Target competency level for development"
    )

    # Evidence tracking
    evidence_count: Mapped[int] = mapped_column(
        Integer,
        server_default="0",
        nullable=False,
        comment="Number of evidence instances supporting this level",
    )

    last_evidence_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Date of most recent evidence"
    )

    # Confidence and reliability
    confidence_interval: Mapped[list[Decimal] | None] = mapped_column(
        ARRAY(DECIMAL(3, 2)), nullable=True, comment="Confidence interval [lower, upper] bounds"
    )

    # Trend analysis
    trend_direction: Mapped[str] = mapped_column(
        String(20),
        server_default="stable",
        nullable=False,
        comment="Trend direction: improving, stable, declining",
    )

    trend_strength: Mapped[Decimal] = mapped_column(
        DECIMAL(3, 2), server_default="0", nullable=False, comment="Strength of trend (0-1 scale)"
    )

    # Calculation metadata
    last_calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default="now()",
        nullable=False,
        comment="When competency was last calculated",
    )

    # Relationships
    user = relationship("User", back_populates="competencies")
    history = relationship(
        "CompetencyHistory",
        back_populates="competency",
        cascade="all, delete-orphan",
        order_by="CompetencyHistory.timestamp.desc()",
    )

    def __repr__(self) -> str:
        """String representation of competency"""
        return (
            f"<Competency("
            f"id={self.id}, "
            f"user_id={self.user_id}, "
            f"competency='{self.competency_id}', "
            f"level={self.current_level}, "
            f"trend='{self.trend_direction}', "
            f"evidence={self.evidence_count}"
            f")>"
        )

    def get_level_description(self) -> str:
        """Get human-readable level description"""
        level = float(self.current_level)
        if level < 1.0:
            return "Novice"
        elif level < 2.0:
            return "Beginner"
        elif level < 3.0:
            return "Intermediate"
        elif level < 4.0:
            return "Advanced"
        else:
            return "Expert"

    def get_confidence_range(self) -> tuple[float, float]:
        """Get confidence interval as tuple"""
        if self.confidence_interval and len(self.confidence_interval) >= 2:
            return (float(self.confidence_interval[0]), float(self.confidence_interval[1]))
        # Default to +/- 0.5 if no confidence interval
        level = float(self.current_level)
        return (max(0.0, level - 0.5), min(5.0, level + 0.5))

    def is_improving(self) -> bool:
        """Check if competency is improving"""
        return self.trend_direction == "improving"

    def is_declining(self) -> bool:
        """Check if competency is declining"""
        return self.trend_direction == "declining"

    def needs_attention(self) -> bool:
        """Check if competency needs attention (declining or low evidence)"""
        return (
            self.is_declining()
            or self.evidence_count < 3
            or (
                self.last_evidence_date
                and (datetime.now(UTC) - self.last_evidence_date.replace(tzinfo=None)).days > 30
            )
        )

    def progress_to_target(self) -> float | None:
        """Calculate progress toward target level (0-1 scale)"""
        if not self.target_level:
            return None

        target = float(self.target_level)
        current = float(self.current_level)

        if target <= current:
            return 1.0  # Already at or above target

        # Assume starting from 0, calculate progress
        return current / target if target > 0 else 0.0

    @property
    def summary(self) -> dict[str, Any]:
        """Get competency summary for API responses"""
        confidence_low, confidence_high = self.get_confidence_range()

        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "competency_id": self.competency_id,
            "competency_name": self.competency_name,
            "current_level": float(self.current_level),
            "level_description": self.get_level_description(),
            "target_level": float(self.target_level) if self.target_level else None,
            "evidence_count": self.evidence_count,
            "confidence_range": [confidence_low, confidence_high],
            "trend_direction": self.trend_direction,
            "trend_strength": float(self.trend_strength),
            "last_evidence_date": self.last_evidence_date.isoformat()
            if self.last_evidence_date
            else None,
            "last_calculated_at": self.last_calculated_at.isoformat(),
            "needs_attention": self.needs_attention(),
            "progress_to_target": self.progress_to_target(),
        }


class CompetencyHistory(TimescaleModel):
    """Historical competency level changes for trend analysis"""

    __tablename__ = "competency_history"
    __table_args__ = (
        # Check constraints from schema
        CheckConstraint(
            "level_value >= 0 AND level_value <= 5", name="competency_history_level_valid"
        ),
        CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="competency_history_confidence_valid",
        ),
        # Indexes optimized for TimescaleDB time-series queries
        Index(
            "idx_competency_history_user_competency_time",
            "user_id",
            "competency_id",
            "timestamp",
        ),
        Index(
            "idx_competency_history_activity_id",
            "activity_id",
            postgresql_where="activity_id IS NOT NULL",
        ),
        {"comment": "TimescaleDB hypertable for competency level history and trend analysis"},
    )

    # Relationships
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, comment="Reference to user"
    )

    activity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("activities.id", ondelete="SET NULL"),
        nullable=True,
        comment="Activity that triggered this competency change",
    )

    # Competency data
    competency_id: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="Competency identifier"
    )

    level_value: Mapped[Decimal] = mapped_column(
        DECIMAL(3, 2), nullable=False, comment="Competency level at this point in time"
    )

    evidence_count: Mapped[int] = mapped_column(
        Integer, server_default="0", nullable=False, comment="Evidence count at time of change"
    )

    confidence_score: Mapped[Decimal | None] = mapped_column(
        DECIMAL(3, 2), nullable=True, comment="Confidence in this level assessment"
    )

    # Change metadata
    change_reason: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Reason for competency level change"
    )

    # Relationships
    user = relationship("User")
    activity = relationship("Activity", back_populates="competency_history")
    competency = relationship(
        "Competency",
        back_populates="history",
        foreign_keys=[user_id, competency_id],
        primaryjoin="and_(CompetencyHistory.user_id == Competency.user_id, "
        "CompetencyHistory.competency_id == Competency.competency_id)",
    )

    def __repr__(self) -> str:
        """String representation of competency history entry"""
        return (
            f"<CompetencyHistory("
            f"id={self.id}, "
            f"user_id={self.user_id}, "
            f"competency='{self.competency_id}', "
            f"level={self.level_value}, "
            f"reason='{self.change_reason}', "
            f"timestamp={self.timestamp}"
            f")>"
        )

    def get_level_change(self, previous_entry: Optional["CompetencyHistory"]) -> Decimal | None:
        """Calculate level change from previous entry"""
        if not previous_entry:
            return None
        return self.level_value - previous_entry.level_value

    def is_improvement(self, previous_entry: Optional["CompetencyHistory"]) -> bool | None:
        """Check if this represents an improvement"""
        change = self.get_level_change(previous_entry)
        return change > 0 if change is not None else None

    def get_change_magnitude(self, previous_entry: Optional["CompetencyHistory"]) -> str | None:
        """Get magnitude of change (minor, moderate, major)"""
        change = self.get_level_change(previous_entry)
        if change is None:
            return None

        abs_change = abs(float(change))
        if abs_change < 0.25:
            return "minor"
        elif abs_change < 0.75:
            return "moderate"
        else:
            return "major"

    @property
    def summary(self) -> dict[str, Any]:
        """Get history entry summary for API responses"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "competency_id": self.competency_id,
            "level_value": float(self.level_value),
            "evidence_count": self.evidence_count,
            "confidence_score": float(self.confidence_score) if self.confidence_score else None,
            "change_reason": self.change_reason,
            "activity_id": str(self.activity_id) if self.activity_id else None,
            "timestamp": self.timestamp.isoformat(),
        }
