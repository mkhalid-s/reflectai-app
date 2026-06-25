"""
Competency Assessor for ReflectAI

Implements  Simple Competency Assessment core logic:
- Integrates activity classification, time decay, and evidence thresholds
- Provides comprehensive competency scoring for individual users
- Tracks competency progression over time with timestamps
- Generates actionable insights and development recommendations
- Supports multiple competency frameworks and assessment methods

Main entry point for all competency assessment operations.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from src.core.classification.competency_mapper import CompetencyMapper
from src.core.frameworks.competency_loader import get_framework_loader
from src.shared import get_logger

from .scoring import (
    ScoringMethod,
    ScoringResult,
    get_activity_scorer,
    get_evidence_threshold,
    get_time_decay_calculator,
)


class AssessmentScope(Enum):
    """Scope of competency assessment"""

    INDIVIDUAL = "individual"
    TEAM = "team"
    ORGANIZATION = "organization"
    PEER_GROUP = "peer_group"


class CompetencyScore(BaseModel):
    """Individual competency score"""

    competency_id: str = Field(..., description="Competency identifier")
    competency_name: str = Field(..., description="Human-readable competency name")
    current_score: float = Field(..., description="Current competency score (0.0-5.0)")
    current_level: str = Field(..., description="Current competency level name")
    evidence_level: str = Field(..., description="Evidence quality level")
    confidence_score: float = Field(..., description="Confidence in assessment (0.0-1.0)")

    # Activity details
    activity_count: int = Field(..., description="Number of activities analyzed")
    recent_activity_count: int = Field(..., description="Activities in last 30 days")
    time_weighted_score: float = Field(..., description="Time-decay weighted score")

    # Progression tracking
    last_calculated: datetime = Field(default_factory=datetime.utcnow)
    previous_score: float | None = Field(None, description="Previous assessment score")
    score_change: float | None = Field(None, description="Change since last assessment")
    trend_direction: str = Field(default="stable", description="Score trend direction")

    # Insights and recommendations
    strengths: list[str] = Field(default_factory=list, description="Identified strengths")
    development_areas: list[str] = Field(default_factory=list, description="Areas for improvement")
    recommendations: list[str] = Field(
        default_factory=list, description="Actionable recommendations"
    )
    next_milestone: dict[str, Any] | None = Field(None, description="Next achievement target")


class AssessmentResult(BaseModel):
    """Complete assessment result for a user"""

    user_id: str = Field(..., description="User identifier")
    framework_id: str = Field(..., description="Competency framework used")
    assessment_date: datetime = Field(default_factory=datetime.utcnow)
    assessment_scope: str = Field(default="individual", description="Assessment scope")

    # Overall metrics
    overall_competency_score: float = Field(..., description="Weighted average of all competencies")
    competencies_assessed: int = Field(..., description="Number of competencies evaluated")
    total_activities_analyzed: int = Field(..., description="Total activities analyzed")
    assessment_confidence: float = Field(..., description="Overall assessment confidence")

    # Individual competency scores
    competency_scores: dict[str, CompetencyScore] = Field(
        default_factory=dict, description="Detailed competency scores"
    )

    # Analysis insights
    top_strengths: list[str] = Field(default_factory=list, description="Top 3 strengths")
    priority_development_areas: list[str] = Field(
        default_factory=list, description="Top 3 development priorities"
    )
    overall_recommendations: list[str] = Field(
        default_factory=list, description="High-level recommendations"
    )

    # Progression metrics
    improvement_velocity: float = Field(default=0.0, description="Rate of competency improvement")
    competency_breadth: float = Field(default=0.0, description="Breadth of competencies (0.0-1.0)")
    competency_depth: float = Field(default=0.0, description="Average competency depth")

    # Metadata
    assessment_parameters: dict[str, Any] = Field(
        default_factory=dict, description="Parameters used in assessment"
    )
    data_quality_metrics: dict[str, float] = Field(
        default_factory=dict, description="Quality metrics for source data"
    )


class CompetencyAssessor:
    """Main competency assessment engine"""

    def __init__(self, framework_id: str = "default"):
        self.logger = get_logger("assessment.competency_assessor")
        self.framework_id = framework_id

        # Get component instances
        self.activity_scorer = get_activity_scorer()
        self.time_decay = get_time_decay_calculator()
        self.evidence_threshold = get_evidence_threshold()
        self.competency_mapper = CompetencyMapper()
        self.framework_loader = get_framework_loader()

        # Assessment cache for performance
        self._assessment_cache: dict[str, AssessmentResult] = {}
        self._cache_ttl_minutes = 60  # Cache assessments for 1 hour

        # Load competency framework
        self.competency_framework = None
        self._load_framework()

    def _load_framework(self):
        """Load competency framework"""
        try:
            self.competency_framework = self.framework_loader.get_framework(self.framework_id)
            if not self.competency_framework:
                self.logger.warning(f"Framework {self.framework_id} not found, using default")
                # Note: create_sample_framework is async and can't be called from __init__
                # This will be handled lazily when needed in async methods
                self.competency_framework = None
        except Exception as e:
            self.logger.error(f"Error loading framework: {str(e)}")

    async def assess_user_competencies(
        self,
        user_id: str,
        activities: list[dict[str, Any]],
        user_context: dict[str, Any] | None = None,
        scope: AssessmentScope = AssessmentScope.INDIVIDUAL,
        scoring_method: ScoringMethod = ScoringMethod.COMPREHENSIVE,
        reference_date: datetime | None = None,
    ) -> AssessmentResult:
        """Assess all competencies for a user"""

        if reference_date is None:
            reference_date = datetime.now(UTC)

        # Check cache first
        cache_key = f"{user_id}_{self.framework_id}_{reference_date.date()}_{scoring_method.value}"
        if cache_key in self._assessment_cache:
            cached_result = self._assessment_cache[cache_key]
            cache_age = (reference_date - cached_result.assessment_date).total_seconds() / 60
            if cache_age < self._cache_ttl_minutes:
                self.logger.info(f"Using cached assessment for user {user_id}")
                return cached_result

        self.logger.info(f"Starting competency assessment for user {user_id}")

        # Group activities by competency
        competency_activities = await self._group_activities_by_competency(activities)

        # Score each competency
        competency_scores = {}
        total_activities = len(activities)

        for competency_id, comp_activities in competency_activities.items():
            try:
                # Get competency metadata
                competency_info = self._get_competency_info(competency_id)

                # Score the competency
                scoring_result = self.activity_scorer.score_competency(
                    comp_activities, competency_id, scoring_method, reference_date, user_context
                )

                # Convert to CompetencyScore
                competency_score = self._create_competency_score(
                    competency_id, competency_info, scoring_result, reference_date
                )

                competency_scores[competency_id] = competency_score

            except Exception as e:
                self.logger.error(f"Error assessing competency {competency_id}: {str(e)}")
                # Create minimal competency score for error case
                competency_scores[competency_id] = CompetencyScore(
                    competency_id=competency_id,
                    competency_name=competency_id.replace("_", " ").title(),
                    current_score=0.0,
                    current_level="Novice",
                    evidence_level="insufficient",
                    confidence_score=0.0,
                    activity_count=0,
                    recent_activity_count=0,
                    time_weighted_score=0.0,
                    recommendations=["Unable to assess this competency"],
                )

        # Calculate overall metrics
        overall_score, assessment_confidence = self._calculate_overall_metrics(competency_scores)

        # Generate insights
        top_strengths, development_areas, recommendations = self._generate_insights(
            competency_scores, user_context
        )

        # Calculate progression metrics
        progression_metrics = self._calculate_progression_metrics(competency_scores, activities)

        # Create assessment result
        result = AssessmentResult(
            user_id=user_id,
            framework_id=self.framework_id,
            assessment_date=reference_date,
            assessment_scope=scope.value,
            overall_competency_score=overall_score,
            competencies_assessed=len(competency_scores),
            total_activities_analyzed=total_activities,
            assessment_confidence=assessment_confidence,
            competency_scores=competency_scores,
            top_strengths=top_strengths,
            priority_development_areas=development_areas,
            overall_recommendations=recommendations,
            improvement_velocity=progression_metrics["improvement_velocity"],
            competency_breadth=progression_metrics["breadth"],
            competency_depth=progression_metrics["depth"],
            assessment_parameters={
                "scoring_method": scoring_method.value,
                "framework_id": self.framework_id,
                "assessment_scope": scope.value,
                "reference_date": reference_date.isoformat(),
            },
            data_quality_metrics=self._calculate_data_quality_metrics(activities),
        )

        # Cache the result
        self._assessment_cache[cache_key] = result

        self.logger.info(
            f"Completed assessment for user {user_id}: {len(competency_scores)} competencies"
        )
        return result

    async def assess_single_competency(
        self,
        user_id: str,
        competency_id: str,
        activities: list[dict[str, Any]],
        user_context: dict[str, Any] | None = None,
        scoring_method: ScoringMethod = ScoringMethod.COMPREHENSIVE,
        reference_date: datetime | None = None,
    ) -> CompetencyScore:
        """Assess a single competency for a user"""

        if reference_date is None:
            reference_date = datetime.now(UTC)

        # Filter activities for this competency
        relevant_activities = [
            activity
            for activity in activities
            if activity.get("competency_type") == competency_id
            or competency_id in activity.get("competencies", [])
        ]

        # Get competency metadata
        competency_info = self._get_competency_info(competency_id)

        # Score the competency
        scoring_result = self.activity_scorer.score_competency(
            relevant_activities, competency_id, scoring_method, reference_date, user_context
        )

        # Convert to CompetencyScore
        return self._create_competency_score(
            competency_id, competency_info, scoring_result, reference_date
        )

    async def track_competency_progression(
        self,
        user_id: str,
        competency_id: str,
        assessment_history: list[dict[str, Any]],
        time_period_days: int = 90,
    ) -> dict[str, Any]:
        """Track competency progression over time"""

        if not assessment_history:
            return {"error": "No assessment history provided"}

        # Sort assessments by date
        sorted_assessments = sorted(
            assessment_history, key=lambda x: datetime.fromisoformat(x.get("date", "1900-01-01"))
        )

        # Extract scores and dates
        scores = []
        dates = []
        for assessment in sorted_assessments:
            if competency_id in assessment.get("competency_scores", {}):
                scores.append(assessment["competency_scores"][competency_id]["current_score"])
                dates.append(datetime.fromisoformat(assessment["date"]))

        if len(scores) < 2:
            return {"error": "Insufficient assessment history for progression tracking"}

        # Calculate progression metrics
        score_change = scores[-1] - scores[0]
        time_span = (dates[-1] - dates[0]).days
        velocity = score_change / max(time_span, 1) * 30  # Score change per 30 days

        # Calculate trend
        if len(scores) >= 3:
            recent_trend = (scores[-1] - scores[-2]) / max((dates[-1] - dates[-2]).days, 1) * 30
        else:
            recent_trend = velocity

        # Determine trend direction
        if recent_trend > 0.1:
            trend_direction = "improving"
        elif recent_trend < -0.1:
            trend_direction = "declining"
        else:
            trend_direction = "stable"

        return {
            "competency_id": competency_id,
            "total_score_change": score_change,
            "velocity_per_30_days": velocity,
            "recent_trend": recent_trend,
            "trend_direction": trend_direction,
            "assessment_count": len(scores),
            "time_span_days": time_span,
            "current_score": scores[-1],
            "starting_score": scores[0],
        }

    async def _group_activities_by_competency(
        self, activities: list[dict[str, Any]]
    ) -> dict[str, list[dict[str, Any]]]:
        """Group activities by competency using classification"""

        competency_activities = {}

        # Initialize with framework competencies
        if self.competency_framework:
            for comp_id in self.competency_framework.competencies.keys():
                competency_activities[comp_id] = []

        for activity in activities:
            # Check if activity already has competency mapping
            if "competency_type" in activity:
                comp_id = activity["competency_type"]
                if comp_id not in competency_activities:
                    competency_activities[comp_id] = []
                competency_activities[comp_id].append(activity)

            # Check if activity has multiple competencies
            elif "competencies" in activity:
                for comp_id in activity["competencies"]:
                    if comp_id not in competency_activities:
                        competency_activities[comp_id] = []
                    competency_activities[comp_id].append(activity)

            else:
                # Use competency mapper for classification
                try:
                    mapping_result = await self.competency_mapper.map_activity_to_competencies(
                        activity_description=activity.description,
                        activity_type=activity.activity_type,
                        framework_id=self.framework_id,
                    )

                    # Add to primary competency
                    if mapping_result.primary_competency:
                        comp_id = mapping_result.primary_competency
                        if comp_id not in competency_activities:
                            competency_activities[comp_id] = []
                        competency_activities[comp_id].append(activity)

                    # Add to secondary competencies with lower weight
                    for secondary in mapping_result.secondary_competencies:
                        comp_id = secondary.get("competency_id")
                        if comp_id and comp_id not in competency_activities:
                            competency_activities[comp_id] = []
                            competency_activities[comp_id].append(activity)

                except Exception as e:
                    self.logger.warning(f"Error classifying activity: {str(e)}")
                    # Fallback to general competency
                    if "general" not in competency_activities:
                        competency_activities["general"] = []
                    competency_activities["general"].append(activity)

        # Remove empty competencies
        return {k: v for k, v in competency_activities.items() if v}

    def _get_competency_info(self, competency_id: str) -> dict[str, str]:
        """Get competency metadata from framework"""
        if self.competency_framework and competency_id in self.competency_framework.competencies:
            comp_data = self.competency_framework.competencies[competency_id]
            return {
                "name": comp_data.get("name", competency_id.replace("_", " ").title()),
                "description": comp_data.get("description", ""),
            }
        else:
            return {
                "name": competency_id.replace("_", " ").title(),
                "description": f"Competency: {competency_id}",
            }

    def _create_competency_score(
        self,
        competency_id: str,
        competency_info: dict[str, str],
        scoring_result: ScoringResult,
        reference_date: datetime,
    ) -> CompetencyScore:
        """Convert ScoringResult to CompetencyScore"""

        # Calculate recent activity count (last 30 days)
        recent_count = 0
        for activity in scoring_result.activities_analyzed:
            if isinstance(activity, dict) and "days_ago" in activity:
                if activity["days_ago"] <= 30:
                    recent_count += 1

        # Extract strengths and development areas from recommendations
        strengths = []
        development_areas = []
        filtered_recommendations = []

        for rec in scoring_result.recommendations:
            if "excellent" in rec.lower() or "strong" in rec.lower() or "maintain" in rec.lower():
                strengths.append(rec)
            elif "increase" in rec.lower() or "improve" in rec.lower() or "focus on" in rec.lower():
                development_areas.append(rec)
            else:
                filtered_recommendations.append(rec)

        # Determine next milestone
        next_milestone = None
        if scoring_result.competency_level.value < 5:  # Not at expert level
            next_level = scoring_result.competency_level.value + 1
            next_milestone = {
                "target_level": next_level,
                "target_score": float(next_level),
                "gap": float(next_level) - scoring_result.competency_score,
                "estimated_activities_needed": max(
                    1, int((float(next_level) - scoring_result.competency_score) * 3)
                ),
            }

        return CompetencyScore(
            competency_id=competency_id,
            competency_name=competency_info["name"],
            current_score=scoring_result.competency_score,
            current_level=scoring_result.competency_level.name.title(),
            evidence_level=scoring_result.evidence_level,
            confidence_score=scoring_result.confidence_score,
            activity_count=scoring_result.raw_activity_count,
            recent_activity_count=recent_count,
            time_weighted_score=scoring_result.weighted_activity_count,
            last_calculated=reference_date,
            strengths=strengths[:3],  # Top 3 strengths
            development_areas=development_areas[:3],  # Top 3 development areas
            recommendations=filtered_recommendations,
            next_milestone=next_milestone,
        )

    def _calculate_overall_metrics(
        self, competency_scores: dict[str, CompetencyScore]
    ) -> tuple[float, float]:
        """Calculate overall competency score and confidence"""

        if not competency_scores:
            return 0.0, 0.0

        # Calculate weighted average score
        total_weighted_score = 0.0
        total_confidence_weight = 0.0

        for score in competency_scores.values():
            weight = score.confidence_score  # Use confidence as weight
            total_weighted_score += score.current_score * weight
            total_confidence_weight += weight

        if total_confidence_weight > 0:
            overall_score = total_weighted_score / total_confidence_weight
            average_confidence = total_confidence_weight / len(competency_scores)
        else:
            overall_score = 0.0
            average_confidence = 0.0

        return overall_score, average_confidence

    def _generate_insights(
        self, competency_scores: dict[str, CompetencyScore], user_context: dict[str, Any] | None
    ) -> tuple[list[str], list[str], list[str]]:
        """Generate top-level insights and recommendations"""

        # Sort competencies by score
        sorted_competencies = sorted(
            competency_scores.items(), key=lambda x: x[1].current_score, reverse=True
        )

        # Top strengths (highest scores with good confidence)
        top_strengths = []
        for _comp_id, score in sorted_competencies:
            if score.current_score >= 3.0 and score.confidence_score >= 0.6:
                top_strengths.append(f"{score.competency_name} (Level: {score.current_level})")
            if len(top_strengths) >= 3:
                break

        # Priority development areas (lowest scores or declining trends)
        development_areas = []
        for _comp_id, score in reversed(sorted_competencies):
            if score.current_score < 2.5 or score.evidence_level in ["weak", "insufficient"]:
                development_areas.append(
                    f"{score.competency_name} (Current: {score.current_level})"
                )
            if len(development_areas) >= 3:
                break

        # Overall recommendations
        recommendations = []

        # Based on overall competency distribution
        high_scores = sum(1 for s in competency_scores.values() if s.current_score >= 4.0)
        low_scores = sum(1 for s in competency_scores.values() if s.current_score < 2.0)

        if high_scores > 0:
            recommendations.append(
                "Leverage your strong competencies to mentor others and take on leadership roles"
            )

        if low_scores > len(competency_scores) * 0.3:  # More than 30% are low
            recommendations.append(
                "Focus on building foundational skills through targeted learning and practice"
            )

        # Based on activity patterns
        total_recent_activities = sum(s.recent_activity_count for s in competency_scores.values())
        if total_recent_activities < 5:
            recommendations.append(
                "Increase overall activity levels to build stronger competency evidence"
            )

        return top_strengths, development_areas, recommendations

    def _calculate_progression_metrics(
        self, competency_scores: dict[str, CompetencyScore], activities: list[dict[str, Any]]
    ) -> dict[str, float]:
        """Calculate progression metrics"""

        if not competency_scores:
            return {"improvement_velocity": 0.0, "breadth": 0.0, "depth": 0.0}

        # Competency breadth: percentage of competencies with meaningful scores
        meaningful_scores = sum(1 for s in competency_scores.values() if s.current_score >= 1.0)
        breadth = meaningful_scores / len(competency_scores) if competency_scores else 0.0

        # Competency depth: average competency level
        depth = sum(s.current_score for s in competency_scores.values()) / len(competency_scores)

        # Improvement velocity: estimate based on recent activity patterns
        # This is simplified - in practice, would use historical assessments
        recent_activity_ratio = sum(
            s.recent_activity_count for s in competency_scores.values()
        ) / max(len(activities), 1)
        velocity = recent_activity_ratio * depth * 0.1  # Rough estimate

        return {"improvement_velocity": velocity, "breadth": breadth, "depth": depth}

    def _calculate_data_quality_metrics(self, activities: list[dict[str, Any]]) -> dict[str, float]:
        """Calculate data quality metrics for the assessment"""

        if not activities:
            return {"completeness": 0.0, "recency": 0.0, "diversity": 0.0}

        # Completeness: percentage of activities with required fields
        required_fields = ["date", "description"]
        complete_activities = 0
        for activity in activities:
            if all(field in activity for field in required_fields):
                complete_activities += 1
        completeness = complete_activities / len(activities)

        # Recency: percentage of activities from last 30 days
        recent_activities = 0
        current_date = datetime.now(UTC)
        for activity in activities:
            activity_date = activity.get("date")
            if activity_date:
                try:
                    if isinstance(activity_date, str):
                        activity_date = datetime.fromisoformat(activity_date.replace("Z", "+00:00"))
                    days_ago = (current_date - activity_date).days
                    if days_ago <= 30:
                        recent_activities += 1
                except Exception:
                    pass
        recency = recent_activities / len(activities)

        # Diversity: number of unique activity types
        activity_types = set()
        for activity in activities:
            activity_type = activity.get("activity_type", "unknown")
            activity_types.add(activity_type)
        diversity = len(activity_types) / max(
            len(activities), 10
        )  # Normalize to max expected types

        return {
            "completeness": completeness,
            "recency": recency,
            "diversity": min(1.0, diversity),  # Cap at 1.0
        }

    def get_assessment_summary(self, assessment: AssessmentResult) -> dict[str, Any]:
        """Get a summary view of the assessment"""
        return {
            "user_id": assessment.user_id,
            "overall_score": round(assessment.overall_competency_score, 2),
            "confidence": round(assessment.assessment_confidence, 2),
            "competencies_count": assessment.competencies_assessed,
            "top_strength": assessment.top_strengths[0]
            if assessment.top_strengths
            else "None identified",
            "priority_development": assessment.priority_development_areas[0]
            if assessment.priority_development_areas
            else "None identified",
            "assessment_date": assessment.assessment_date.isoformat(),
            "data_quality": round(
                sum(assessment.data_quality_metrics.values())
                / len(assessment.data_quality_metrics),
                2,
            ),
        }


# Global assessor instances
_global_assessors: dict[str, CompetencyAssessor] = {}


def get_competency_assessor(framework_id: str = "default") -> CompetencyAssessor:
    """Get competency assessor instance for a framework"""
    if framework_id not in _global_assessors:
        _global_assessors[framework_id] = CompetencyAssessor(framework_id)
    return _global_assessors[framework_id]
