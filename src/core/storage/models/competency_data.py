"""
Competency Data Models for ReflectAI Storage

Implements competency assessment data structures with:
- Competency score tracking with historical data
- Competency snapshots and milestones
- Trend analysis and progression tracking
- Integration with TimescaleDB for time-series optimization

Provides comprehensive competency modeling for career development.
"""

import uuid
from datetime import datetime
from enum import Enum

from pydantic import UUID4, BaseModel, Field, validator

# Import canonical CompetencyLevel from assessment module
from src.core.assessment.level_calculator import CompetencyLevel


class CompetencyCategory(Enum):
    """Categories of competencies"""

    TECHNICAL = "technical"
    LEADERSHIP = "leadership"
    COMMUNICATION = "communication"
    PROBLEM_SOLVING = "problem_solving"
    COLLABORATION = "collaboration"
    INNOVATION = "innovation"
    PROJECT_MANAGEMENT = "project_management"
    STRATEGIC_THINKING = "strategic_thinking"
    CUSTOMER_FOCUS = "customer_focus"
    BUSINESS_ACUMEN = "business_acumen"


class TrendDirection(Enum):
    """Trend direction indicators"""

    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"
    VOLATILE = "volatile"


class CompetencyMilestone(BaseModel):
    """Milestone in competency development"""

    milestone_id: UUID4 = Field(default_factory=uuid.uuid4, description="Milestone identifier")
    competency_name: str = Field(..., description="Competency name")
    level_achieved: CompetencyLevel = Field(..., description="Level achieved")
    achieved_date: datetime = Field(..., description="Date achieved")
    evidence: list[str] = Field(default_factory=list, description="Supporting evidence")
    verified_by: UUID4 | None = Field(None, description="Verified by user/system")
    notes: str | None = Field(None, description="Additional notes")


class CompetencyTrend(BaseModel):
    """Trend analysis for a competency"""

    competency_name: str = Field(..., description="Competency name")
    direction: TrendDirection = Field(..., description="Trend direction")

    # Trend metrics
    change_rate: float = Field(..., description="Rate of change (% per month)")
    volatility: float = Field(..., ge=0.0, le=1.0, description="Score volatility")
    consistency: float = Field(..., ge=0.0, le=1.0, description="Performance consistency")

    # Time windows
    short_term_trend: TrendDirection = Field(..., description="30-day trend")
    medium_term_trend: TrendDirection = Field(..., description="90-day trend")
    long_term_trend: TrendDirection = Field(..., description="365-day trend")

    # Predictions
    projected_level: CompetencyLevel | None = Field(None, description="Projected level in 6 months")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Prediction confidence")

    # Analysis period
    analysis_start: datetime = Field(..., description="Start of analysis period")
    analysis_end: datetime = Field(..., description="End of analysis period")
    data_points: int = Field(..., description="Number of data points analyzed")


class CompetencySnapshot(BaseModel):
    """Point-in-time snapshot of all competencies"""

    snapshot_id: UUID4 = Field(default_factory=uuid.uuid4, description="Snapshot identifier")
    user_id: UUID4 = Field(..., description="User identifier")
    snapshot_date: datetime = Field(
        default_factory=datetime.utcnow, description="Snapshot timestamp"
    )

    # Competency scores
    competencies: dict[str, float] = Field(..., description="Competency name to score mapping")

    # Aggregate metrics
    overall_score: float = Field(..., ge=0.0, le=1.0, description="Overall competency score")
    top_competencies: list[str] = Field(default_factory=list, description="Top 5 competencies")
    growth_areas: list[str] = Field(default_factory=list, description="Areas for improvement")

    # Comparison metrics
    team_percentile: float | None = Field(
        None, ge=0.0, le=100.0, description="Percentile within team"
    )
    org_percentile: float | None = Field(
        None, ge=0.0, le=100.0, description="Percentile within organization"
    )

    # Metadata
    assessment_method: str = Field(default="ai_analysis", description="How snapshot was generated")
    confidence_level: float = Field(..., ge=0.0, le=1.0, description="Overall confidence")
    notes: str | None = Field(None, description="Additional notes")


class CompetencyScore(BaseModel):
    """Individual competency score with detailed metrics"""

    # Identifiers
    score_id: UUID4 = Field(default_factory=uuid.uuid4, description="Score record identifier")
    user_id: UUID4 = Field(..., description="User identifier")
    competency_name: str = Field(..., description="Competency name")
    category: CompetencyCategory = Field(..., description="Competency category")

    # Score details
    current_score: float = Field(..., ge=0.0, le=1.0, description="Current score (0-1)")
    current_level: CompetencyLevel = Field(..., description="Current proficiency level")
    previous_score: float | None = Field(None, ge=0.0, le=1.0, description="Previous score")
    score_change: float | None = Field(None, description="Change from previous score")

    # Evidence and validation
    evidence_count: int = Field(default=0, description="Number of evidence items")
    evidence_sources: list[str] = Field(default_factory=list, description="Sources of evidence")
    last_demonstrated: datetime | None = Field(None, description="Last demonstration date")
    assessment_date: datetime = Field(
        default_factory=datetime.utcnow, description="Assessment date"
    )

    # Statistical metrics
    confidence: float = Field(..., ge=0.0, le=1.0, description="Score confidence")
    variance: float = Field(default=0.0, ge=0.0, description="Score variance")
    stability: float = Field(default=1.0, ge=0.0, le=1.0, description="Score stability")

    # Components breakdown (if applicable)
    sub_scores: dict[str, float] = Field(default_factory=dict, description="Sub-component scores")

    # Benchmarking
    team_average: float | None = Field(None, ge=0.0, le=1.0, description="Team average score")
    org_average: float | None = Field(None, ge=0.0, le=1.0, description="Organization average")
    industry_benchmark: float | None = Field(None, ge=0.0, le=1.0, description="Industry benchmark")

    # Metadata
    calculated_by: str = Field(default="system", description="Calculation source")
    algorithm_version: str = Field(default="v1.0", description="Algorithm version used")
    is_verified: bool = Field(default=False, description="Human verification status")

    @validator("current_level")
    def validate_level_consistency(cls, v, values):
        """Ensure level is consistent with score"""
        if "current_score" in values:
            score = values["current_score"]
            expected_level = cls._score_to_level(score)
            if v != expected_level:
                return expected_level
        return v

    @staticmethod
    def _score_to_level(score: float) -> CompetencyLevel:
        """Convert numeric score to competency level

        Uses canonical 5-level scale from assessment.level_calculator:
        - NOVICE: < 0.2
        - DEVELOPING: 0.2 - 0.4
        - PROFICIENT: 0.4 - 0.6
        - ADVANCED: 0.6 - 0.8
        - EXPERT: >= 0.8
        """
        if score < 0.2:
            return CompetencyLevel.NOVICE
        elif score < 0.4:
            return CompetencyLevel.DEVELOPING
        elif score < 0.6:
            return CompetencyLevel.PROFICIENT
        elif score < 0.8:
            return CompetencyLevel.ADVANCED
        else:
            return CompetencyLevel.EXPERT

    def calculate_change(self) -> None:
        """Calculate score change from previous"""
        if self.previous_score is not None:
            self.score_change = self.current_score - self.previous_score


class CompetencyScoreModel(BaseModel):
    """Database model for competency scores"""

    id: UUID4 = Field(default_factory=uuid.uuid4, description="Database record ID")
    user_id: UUID4 = Field(..., description="User identifier")
    score_data: CompetencyScore = Field(..., description="Score data")

    # History tracking
    version: int = Field(default=1, description="Score version")
    superseded_by: UUID4 | None = Field(None, description="ID of newer score record")
    is_current: bool = Field(default=True, description="Current score indicator")

    # Audit fields
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    created_by: UUID4 | None = Field(None, description="Created by user")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Update timestamp")
    updated_by: UUID4 | None = Field(None, description="Updated by user")

    # Data quality
    data_quality_score: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Data quality indicator"
    )
    requires_review: bool = Field(default=False, description="Needs manual review")
    review_notes: str | None = Field(None, description="Review notes")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat(), UUID4: lambda v: str(v)}
