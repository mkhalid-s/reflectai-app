"""
Workflow model for ReflectAI workflow orchestration

Implements workflow execution tracking with support for:
- Workflow status and stage management
- Input/output data storage in JSONB format
- Error handling and retry tracking
- Temporal workflow integration
- Parent-child workflow relationships
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, UUID, CheckConstraint, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel


class Workflow(BaseModel):
    """Workflow execution tracking and orchestration"""

    __tablename__ = "workflows"
    __table_args__ = (
        # Check constraints from schema
        CheckConstraint(
            "workflow_status IN ('pending', 'running', 'completed', 'failed', 'cancelled', 'paused')",
            name="workflows_status_valid",
        ),
        CheckConstraint("LENGTH(workflow_type) > 0", name="workflows_type_not_empty"),
        # Indexes for performance
        Index("idx_workflows_user_id", "user_id"),
        Index("idx_workflows_status", "workflow_status"),
        Index("idx_workflows_type", "workflow_type"),
        Index(
            "idx_workflows_correlation_id",
            "correlation_id",
            postgresql_where="correlation_id IS NOT NULL",
        ),
        Index(
            "idx_workflows_temporal_id",
            "temporal_workflow_id",
            postgresql_where="temporal_workflow_id IS NOT NULL",
        ),
        Index(
            "idx_workflows_parent_id",
            "parent_workflow_id",
            postgresql_where="parent_workflow_id IS NOT NULL",
        ),
        Index(
            "idx_workflows_started_at",
            "started_at",
        ),
        {"comment": "Workflow execution tracking and orchestration"},
    )

    # Relationships
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, comment="User who initiated the workflow"
    )

    parent_workflow_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="SET NULL"),
        nullable=True,
        comment="Parent workflow for nested workflows",
    )

    # Workflow identification and type
    workflow_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Type of workflow (competency_analysis, report_generation, etc.)",
    )

    workflow_status: Mapped[str] = mapped_column(
        String(20), server_default="pending", nullable=False, comment="Current workflow status"
    )

    # Workflow data
    input_data: Mapped[dict[str, Any]] = mapped_column(
        JSON, server_default="{}", nullable=False, comment="Input parameters and data for workflow"
    )

    output_data: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        server_default="{}",
        nullable=False,
        comment="Output results and artifacts from workflow",
    )

    context_data: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        server_default="{}",
        nullable=False,
        comment="Context and configuration data for workflow execution",
    )

    # Execution state
    stage: Mapped[str] = mapped_column(
        String(50),
        server_default="initial",
        nullable=False,
        comment="Current execution stage within workflow",
    )

    error_count: Mapped[int] = mapped_column(
        Integer,
        server_default="0",
        nullable=False,
        comment="Number of errors encountered during execution",
    )

    last_error: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="Details of most recent error"
    )

    # Correlation and integration
    correlation_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Correlation ID for tracking related workflows/activities",
    )

    temporal_workflow_id: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment="Temporal workflow ID for integration"
    )

    # Timing
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default="now()",
        nullable=False,
        comment="Workflow start timestamp",
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Workflow completion timestamp"
    )

    # Relationships
    user = relationship("User", back_populates="workflows")
    parent_workflow = relationship(
        "Workflow", remote_side="Workflow.id", back_populates="child_workflows"
    )
    child_workflows = relationship(
        "Workflow", back_populates="parent_workflow", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """String representation of workflow"""
        return (
            f"<Workflow("
            f"id={self.id}, "
            f"user_id={self.user_id}, "
            f"type='{self.workflow_type}', "
            f"status='{self.workflow_status}', "
            f"stage='{self.stage}', "
            f"errors={self.error_count}"
            f")>"
        )

    def is_running(self) -> bool:
        """Check if workflow is currently running"""
        return self.workflow_status == "running"

    def is_completed(self) -> bool:
        """Check if workflow completed successfully"""
        return self.workflow_status == "completed"

    def is_failed(self) -> bool:
        """Check if workflow failed"""
        return self.workflow_status == "failed"

    def is_terminal_state(self) -> bool:
        """Check if workflow is in a terminal state"""
        return self.workflow_status in ["completed", "failed", "cancelled"]

    def can_retry(self) -> bool:
        """Check if workflow can be retried"""
        return self.workflow_status in ["failed", "cancelled"] and self.error_count < 3

    def get_duration_seconds(self) -> float | None:
        """Get workflow duration in seconds"""
        if not self.completed_at:
            if self.is_running():
                return (datetime.now(UTC) - self.started_at.replace(tzinfo=None)).total_seconds()
            return None
        return (
            self.completed_at.replace(tzinfo=None) - self.started_at.replace(tzinfo=None)
        ).total_seconds()

    def start_workflow(self) -> None:
        """Mark workflow as started"""
        self.workflow_status = "running"
        self.started_at = datetime.now(UTC)

    def complete_workflow(self, output_data: dict[str, Any] | None = None) -> None:
        """Mark workflow as completed with optional output data"""
        self.workflow_status = "completed"
        self.completed_at = datetime.now(UTC)
        if output_data:
            self.output_data.update(output_data)

    def fail_workflow(self, error_info: dict[str, Any]) -> None:
        """Mark workflow as failed with error information"""
        self.workflow_status = "failed"
        self.completed_at = datetime.now(UTC)
        self.error_count += 1
        self.last_error = error_info

    def pause_workflow(self) -> None:
        """Pause workflow execution"""
        if self.is_running():
            self.workflow_status = "paused"

    def resume_workflow(self) -> None:
        """Resume paused workflow"""
        if self.workflow_status == "paused":
            self.workflow_status = "running"

    def cancel_workflow(self) -> None:
        """Cancel workflow execution"""
        if not self.is_terminal_state():
            self.workflow_status = "cancelled"
            self.completed_at = datetime.now(UTC)

    def update_stage(self, new_stage: str) -> None:
        """Update current execution stage"""
        self.stage = new_stage

    def get_input_value(self, key: str, default: Any = None) -> Any:
        """Get a value from input data"""
        if self.input_data and isinstance(self.input_data, dict):
            return self.input_data.get(key, default)
        return default

    def set_input_value(self, key: str, value: Any) -> None:
        """Set a value in input data"""
        if not isinstance(self.input_data, dict):
            self.input_data = {}
        self.input_data[key] = value

    def get_output_value(self, key: str, default: Any = None) -> Any:
        """Get a value from output data"""
        if self.output_data and isinstance(self.output_data, dict):
            return self.output_data.get(key, default)
        return default

    def set_output_value(self, key: str, value: Any) -> None:
        """Set a value in output data"""
        if not isinstance(self.output_data, dict):
            self.output_data = {}
        self.output_data[key] = value

    def get_context_value(self, key: str, default: Any = None) -> Any:
        """Get a value from context data"""
        if self.context_data and isinstance(self.context_data, dict):
            return self.context_data.get(key, default)
        return default

    def set_context_value(self, key: str, value: Any) -> None:
        """Set a value in context data"""
        if not isinstance(self.context_data, dict):
            self.context_data = {}
        self.context_data[key] = value

    def has_child_workflows(self) -> bool:
        """Check if workflow has child workflows"""
        return len(self.child_workflows) > 0

    def get_child_workflow_statuses(self) -> dict[str, int]:
        """Get count of child workflows by status"""
        statuses = {}
        for child in self.child_workflows:
            status = child.workflow_status
            statuses[status] = statuses.get(status, 0) + 1
        return statuses

    def all_children_completed(self) -> bool:
        """Check if all child workflows are completed"""
        if not self.child_workflows:
            return True
        return all(child.is_terminal_state() for child in self.child_workflows)

    @property
    def summary(self) -> dict[str, Any]:
        """Get workflow summary for API responses"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "workflow_type": self.workflow_type,
            "workflow_status": self.workflow_status,
            "stage": self.stage,
            "error_count": self.error_count,
            "correlation_id": self.correlation_id,
            "temporal_workflow_id": self.temporal_workflow_id,
            "parent_workflow_id": str(self.parent_workflow_id) if self.parent_workflow_id else None,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.get_duration_seconds(),
            "has_children": self.has_child_workflows(),
            "child_statuses": self.get_child_workflow_statuses(),
            "can_retry": self.can_retry(),
            "created_at": self.created_at.isoformat(),
        }
