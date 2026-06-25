"""
Activity Data Models for ReflectAI Storage

Implements Activity data structures for
- Activity data schema with validation and constraints
- Activity metadata and classification support
- TimescaleDB optimized structures
- Data integrity and audit trail support

Provides comprehensive activity data modeling for time-series storage.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import UUID4, BaseModel, Field, validator


class ActivityType(Enum):
    """Standard activity types for classification"""

    TECHNICAL_SKILL = "technical_skill"
    LEADERSHIP = "leadership"
    COMMUNICATION = "communication"
    PROJECT_MANAGEMENT = "project_management"
    PROBLEM_SOLVING = "problem_solving"
    COLLABORATION = "collaboration"
    LEARNING = "learning"
    MENTORING = "mentoring"
    INNOVATION = "innovation"
    CLIENT_INTERACTION = "client_interaction"
    STRATEGIC_PLANNING = "strategic_planning"
    PROCESS_IMPROVEMENT = "process_improvement"
    GENERAL = "general"


class ActivitySource(Enum):
    """Sources of activity data"""

    MANUAL = "manual"
    SLACK = "slack"
    JIRA = "jira"
    GITHUB = "github"
    CALENDAR = "calendar"
    EMAIL = "email"
    SURVEY = "survey"
    SYSTEM = "system"
    AI_DETECTED = "ai_detected"


class ActivityMetadata(BaseModel):
    """Flexible metadata container for activities"""

    # Common metadata fields
    project_id: str | None = Field(None, description="Associated project identifier")
    ticket_id: str | None = Field(None, description="Associated ticket/issue identifier")
    repository: str | None = Field(None, description="Associated repository")
    duration_minutes: int | None = Field(None, description="Activity duration in minutes")
    effort_level: str | None = Field(None, description="Effort level: low/medium/high")
    impact_level: str | None = Field(None, description="Impact level: low/medium/high")

    # Collaboration metadata
    participants: list[str] = Field(default_factory=list, description="Other participants")
    team_size: int | None = Field(None, description="Size of team involved")
    cross_functional: bool = Field(default=False, description="Involves multiple functions")

    # Quality indicators
    complexity_score: float | None = Field(None, ge=0.0, le=1.0, description="Complexity indicator")
    innovation_factor: float | None = Field(
        None, ge=0.0, le=1.0, description="Innovation indicator"
    )
    risk_level: str | None = Field(None, description="Risk level: low/medium/high")

    # Source-specific metadata
    slack_channel: str | None = Field(None, description="Slack channel if from Slack")
    slack_thread_ts: str | None = Field(None, description="Slack thread timestamp")
    jira_key: str | None = Field(None, description="JIRA issue key")
    github_pr_number: int | None = Field(None, description="GitHub PR number")

    # AI processing metadata
    ai_confidence: float | None = Field(
        None, ge=0.0, le=1.0, description="AI classification confidence"
    )
    ai_model_version: str | None = Field(None, description="AI model version used")
    human_verified: bool = Field(default=False, description="Human verification status")

    # Custom fields (flexible container)
    custom_fields: dict[str, Any] = Field(
        default_factory=dict, description="Custom metadata fields"
    )

    @validator("effort_level", "impact_level", "risk_level")
    def validate_level_fields(cls, v):
        if v and v.lower() not in ["low", "medium", "high"]:
            raise ValueError("Level fields must be: low, medium, or high")
        return v.lower() if v else v


class ActivityData(BaseModel):
    """Core activity data model"""

    # Primary identifiers
    activity_id: UUID4 = Field(default_factory=uuid.uuid4, description="Unique activity identifier")
    user_id: UUID4 = Field(..., description="User who performed the activity")
    team_id: UUID4 | None = Field(None, description="Team associated with activity")

    # Temporal data
    timestamp: datetime = Field(..., description="When the activity occurred")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="When record was created"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="When record was last updated"
    )

    # Activity content
    activity_type: ActivityType = Field(..., description="Type/category of activity")
    title: str | None = Field(None, max_length=200, description="Short activity title")
    description: str = Field(..., max_length=5000, description="Detailed activity description")

    # Data quality and provenance
    source: ActivitySource = Field(
        default=ActivitySource.MANUAL, description="Source of activity data"
    )
    confidence_score: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Confidence in activity data"
    )

    # Competency mapping
    competencies: list[str] = Field(default_factory=list, description="Associated competency IDs")
    primary_competency: str | None = Field(None, description="Primary competency demonstrated")

    # Metadata
    metadata: ActivityMetadata = Field(
        default_factory=ActivityMetadata, description="Additional activity metadata"
    )

    # Audit trail
    version: int = Field(default=1, description="Record version for updates")
    created_by: str | None = Field(None, description="Who created this record")
    updated_by: str | None = Field(None, description="Who last updated this record")

    @validator("description")
    def validate_description(cls, v):
        if not v or len(v.strip()) < 10:
            raise ValueError("Description must be at least 10 characters")
        return v.strip()

    @validator("title")
    def validate_title(cls, v):
        if v:
            return v.strip()
        return v

    @validator("competencies")
    def validate_competencies(cls, v):
        # Remove duplicates and empty strings
        return list({comp.strip() for comp in v if comp and comp.strip()})

    @validator("updated_at")
    def validate_updated_at(cls, v, values):
        created_at = values.get("created_at")
        if created_at and v < created_at:
            raise ValueError("updated_at cannot be before created_at")
        return v

    class Config:
        use_enum_values = True
        json_encoders = {datetime: lambda v: v.isoformat(), uuid.UUID: lambda v: str(v)}


class ActivityDataModel(BaseModel):
    """Database model for activity data (matches TimescaleDB schema)"""

    activity_id: str = Field(..., description="Activity UUID as string")
    user_id: str = Field(..., description="User UUID as string")
    team_id: str | None = Field(None, description="Team UUID as string")
    timestamp: datetime = Field(..., description="Activity timestamp")
    activity_type: str = Field(..., description="Activity type")
    title: str | None = Field(None, description="Activity title")
    description: str = Field(..., description="Activity description")
    source: str = Field(..., description="Activity source")
    confidence_score: float = Field(..., description="Confidence score")
    metadata: dict[str, Any] = Field(..., description="Metadata as JSONB")
    competencies: list[str] = Field(..., description="Competency array")
    created_at: datetime = Field(..., description="Created timestamp")
    updated_at: datetime = Field(..., description="Updated timestamp")
    version: int = Field(..., description="Record version")

    @classmethod
    def from_activity_data(cls, activity: ActivityData) -> "ActivityDataModel":
        """Convert ActivityData to database model"""
        return cls(
            activity_id=str(activity.activity_id),
            user_id=str(activity.user_id),
            team_id=str(activity.team_id) if activity.team_id else None,
            timestamp=activity.timestamp,
            activity_type=activity.activity_type.value,
            title=activity.title,
            description=activity.description,
            source=activity.source.value,
            confidence_score=activity.confidence_score,
            metadata={
                **activity.metadata.dict(exclude_none=True),
                "primary_competency": activity.primary_competency,
                "created_by": activity.created_by,
                "updated_by": activity.updated_by,
            },
            competencies=activity.competencies,
            created_at=activity.created_at,
            updated_at=activity.updated_at,
            version=activity.version,
        )

    def to_activity_data(self) -> ActivityData:
        """Convert database model to ActivityData"""

        # Extract metadata
        metadata_dict = self.metadata.copy()
        primary_competency = metadata_dict.pop("primary_competency", None)
        created_by = metadata_dict.pop("created_by", None)
        updated_by = metadata_dict.pop("updated_by", None)

        return ActivityData(
            activity_id=uuid.UUID(self.activity_id),
            user_id=uuid.UUID(self.user_id),
            team_id=uuid.UUID(self.team_id) if self.team_id else None,
            timestamp=self.timestamp,
            activity_type=ActivityType(self.activity_type),
            title=self.title,
            description=self.description,
            source=ActivitySource(self.source),
            confidence_score=self.confidence_score,
            competencies=self.competencies,
            primary_competency=primary_competency,
            metadata=ActivityMetadata(**metadata_dict),
            created_at=self.created_at,
            updated_at=self.updated_at,
            version=self.version,
            created_by=created_by,
            updated_by=updated_by,
        )


class ActivityBatch(BaseModel):
    """Batch of activities for bulk operations"""

    activities: list[ActivityData] = Field(..., description="List of activities")
    batch_id: str | None = Field(None, description="Batch identifier")
    source: ActivitySource = Field(..., description="Common source for all activities")
    processed_at: datetime = Field(
        default_factory=datetime.utcnow, description="When batch was processed"
    )

    @validator("activities")
    def validate_activities(cls, v):
        if len(v) == 0:
            raise ValueError("Batch must contain at least one activity")
        if len(v) > 1000:
            raise ValueError("Batch size cannot exceed 1000 activities")
        return v

    def to_database_models(self) -> list[ActivityDataModel]:
        """Convert batch to database models"""
        return [ActivityDataModel.from_activity_data(activity) for activity in self.activities]


class ActivitySummary(BaseModel):
    """Daily activity summary model"""

    user_id: str = Field(..., description="User identifier")
    date: datetime = Field(..., description="Summary date")
    total_activities: int = Field(default=0, description="Total activities for the day")
    activity_types: dict[str, int] = Field(default_factory=dict, description="Activity type counts")
    competency_activities: dict[str, int] = Field(
        default_factory=dict, description="Competency activity counts"
    )
    avg_confidence_score: float = Field(default=0.0, description="Average confidence score")
    high_confidence_activities: int = Field(default=0, description="High confidence activity count")
    activity_velocity: float = Field(default=0.0, description="Activity velocity trend")
    competency_breadth: int = Field(default=0, description="Unique competencies demonstrated")

    class Config:
        json_encoders = {
            datetime: lambda v: v.date().isoformat() if hasattr(v, "date") else v.isoformat()
        }


class ActivityQuery(BaseModel):
    """Query parameters for activity retrieval"""

    user_id: str | None = Field(None, description="Filter by user ID")
    team_id: str | None = Field(None, description="Filter by team ID")
    activity_types: list[ActivityType] | None = Field(None, description="Filter by activity types")
    competencies: list[str] | None = Field(None, description="Filter by competencies")

    # Time range filters
    start_date: datetime | None = Field(None, description="Start date for time range")
    end_date: datetime | None = Field(None, description="End date for time range")
    days_back: int | None = Field(None, description="Number of days back from now")

    # Quality filters
    min_confidence: float | None = Field(
        None, ge=0.0, le=1.0, description="Minimum confidence score"
    )
    sources: list[ActivitySource] | None = Field(None, description="Filter by sources")

    # Pagination
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum results to return")
    offset: int = Field(default=0, ge=0, description="Results offset for pagination")

    # Ordering
    order_by: str = Field(default="timestamp", description="Field to order by")
    order_direction: str = Field(default="desc", description="Order direction: asc or desc")

    @validator("order_direction")
    def validate_order_direction(cls, v):
        if v.lower() not in ["asc", "desc"]:
            raise ValueError("Order direction must be asc or desc")
        return v.lower()

    @validator("end_date")
    def validate_date_range(cls, v, values):
        start_date = values.get("start_date")
        if start_date and v and v < start_date:
            raise ValueError("end_date must be after start_date")
        return v
