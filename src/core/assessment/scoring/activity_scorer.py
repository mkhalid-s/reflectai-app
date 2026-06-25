"""
Activity Scoring System for ReflectAI Competency Assessment

Implements  Simple Competency Assessment activity scoring:
- Count relevant activities for each competency in the last 90 days
- Calculate competency level: Level = min(activity_count * time_weighted_average, 5.0)
- Integration with time decay and evidence threshold systems
- Activity quality assessment and normalization

Provides the core scoring algorithm for competency assessment.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from src.shared import get_logger

from .evidence_thresholds import get_evidence_threshold
from .time_decay import get_time_decay_calculator


class ScoringMethod(Enum):
    """Competency scoring methods"""

    SIMPLE_COUNT = "simple_count"
    TIME_WEIGHTED = "time_weighted"
    QUALITY_WEIGHTED = "quality_weighted"
    COMPREHENSIVE = "comprehensive"  # Time + quality + evidence


class CompetencyScoreLevel(Enum):
    """Competency score levels (1-5 scale)"""

    NOVICE = 1
    DEVELOPING = 2
    PROFICIENT = 3
    ADVANCED = 4
    EXPERT = 5


class ScoringResult(BaseModel):
    """Result of activity scoring for a competency"""

    competency_type: str = Field(..., description="Competency being scored")
    scoring_method: str = Field(..., description="Scoring method used")
    raw_activity_count: int = Field(..., description="Raw number of activities")
    weighted_activity_count: float = Field(..., description="Time/quality weighted count")
    competency_score: float = Field(..., description="Final competency score (0.0-5.0)")
    competency_level: CompetencyScoreLevel = Field(..., description="Discrete competency level")
    evidence_level: str = Field(..., description="Evidence threshold level")
    confidence_score: float = Field(..., description="Confidence in score (0.0-1.0)")

    # Detailed breakdowns
    time_decay_impact: float = Field(default=0.0, description="Impact of time decay on score")
    quality_impact: float = Field(default=0.0, description="Impact of quality weighting")
    activities_analyzed: list[dict[str, Any]] = Field(
        default_factory=list, description="Activities used in scoring"
    )
    scoring_factors: dict[str, float] = Field(
        default_factory=dict, description="Factors affecting final score"
    )
    recommendations: list[str] = Field(
        default_factory=list, description="Scoring-based recommendations"
    )


class ActivityScorer:
    """Activity-based competency scorer"""

    def __init__(self):
        self.logger = get_logger("assessment.activity_scorer")
        self.time_decay = get_time_decay_calculator()
        self.evidence_threshold = get_evidence_threshold()

        # Scoring parameters per competency type
        self.scoring_parameters = {
            "technical_skills": {
                "max_score": 5.0,
                "count_to_score_ratio": 0.3,  # activities needed per score point
                "quality_boost": 1.2,
                "recency_bonus": 1.1,
                "minimum_activities_for_level": {1: 1, 2: 3, 3: 6, 4: 10, 5: 15},
            },
            "leadership": {
                "max_score": 5.0,
                "count_to_score_ratio": 0.5,  # Leadership needs fewer but higher quality
                "quality_boost": 1.5,
                "recency_bonus": 1.0,
                "minimum_activities_for_level": {1: 1, 2: 2, 3: 4, 4: 7, 5: 12},
            },
            "communication": {
                "max_score": 5.0,
                "count_to_score_ratio": 0.25,  # Communication is frequent
                "quality_boost": 1.3,
                "recency_bonus": 1.2,  # Communication skills need recent practice
                "minimum_activities_for_level": {1: 2, 2: 5, 3: 8, 4: 12, 5: 18},
            },
            "project_management": {
                "max_score": 5.0,
                "count_to_score_ratio": 0.4,
                "quality_boost": 1.4,
                "recency_bonus": 1.1,
                "minimum_activities_for_level": {1: 1, 2: 2, 3: 4, 4: 8, 5: 12},
            },
            "general": {
                "max_score": 5.0,
                "count_to_score_ratio": 0.35,
                "quality_boost": 1.25,
                "recency_bonus": 1.1,
                "minimum_activities_for_level": {1: 1, 2: 3, 3: 5, 4: 8, 5: 12},
            },
        }

    def score_competency(
        self,
        activities: list[dict[str, Any]],
        competency_type: str,
        scoring_method: ScoringMethod = ScoringMethod.COMPREHENSIVE,
        reference_date: datetime | None = None,
        user_context: dict[str, Any] | None = None,
    ) -> ScoringResult:
        """Score a competency based on activities"""

        if reference_date is None:
            reference_date = datetime.now(UTC)

        # Get scoring parameters
        params = self.scoring_parameters.get(competency_type, self.scoring_parameters["general"])

        # Filter activities within time window
        time_filtered_activities = self.time_decay.get_time_window_activities(
            activities, competency_type, reference_date=reference_date
        )

        # Calculate scores based on method
        if scoring_method == ScoringMethod.SIMPLE_COUNT:
            result = self._simple_count_scoring(time_filtered_activities, competency_type, params)
        elif scoring_method == ScoringMethod.TIME_WEIGHTED:
            result = self._time_weighted_scoring(
                time_filtered_activities, competency_type, params, reference_date
            )
        elif scoring_method == ScoringMethod.QUALITY_WEIGHTED:
            result = self._quality_weighted_scoring(
                time_filtered_activities, competency_type, params
            )
        else:  # COMPREHENSIVE
            result = self._comprehensive_scoring(
                time_filtered_activities, competency_type, params, reference_date, user_context
            )

        # Apply final adjustments
        result = self._apply_final_adjustments(result, params, user_context)

        return result

    def score_multiple_competencies(
        self,
        competency_activities: dict[str, list[dict[str, Any]]],
        scoring_method: ScoringMethod = ScoringMethod.COMPREHENSIVE,
        reference_date: datetime | None = None,
        user_context: dict[str, Any] | None = None,
    ) -> dict[str, ScoringResult]:
        """Score multiple competencies"""

        results = {}

        for competency_type, activities in competency_activities.items():
            try:
                result = self.score_competency(
                    activities, competency_type, scoring_method, reference_date, user_context
                )
                results[competency_type] = result

            except Exception as e:
                self.logger.error(f"Error scoring competency {competency_type}: {str(e)}")
                # Create fallback result
                results[competency_type] = ScoringResult(
                    competency_type=competency_type,
                    scoring_method=scoring_method.value,
                    raw_activity_count=0,
                    weighted_activity_count=0.0,
                    competency_score=0.0,
                    competency_level=CompetencyScoreLevel.NOVICE,
                    evidence_level="insufficient",
                    confidence_score=0.0,
                    recommendations=["Unable to score competency due to data error"],
                )

        return results

    def _simple_count_scoring(
        self, activities: list[dict[str, Any]], competency_type: str, params: dict[str, Any]
    ) -> ScoringResult:
        """Simple activity count-based scoring"""

        raw_count = len(activities)
        weighted_count = float(raw_count)

        # Calculate score: Level = min(activity_count * ratio, max_score)
        score = min(raw_count * params["count_to_score_ratio"], params["max_score"])
        level = self._score_to_level(score)

        return ScoringResult(
            competency_type=competency_type,
            scoring_method=ScoringMethod.SIMPLE_COUNT.value,
            raw_activity_count=raw_count,
            weighted_activity_count=weighted_count,
            competency_score=score,
            competency_level=level,
            evidence_level="basic",
            confidence_score=0.6 if raw_count > 0 else 0.0,
            activities_analyzed=[{"count": raw_count}],
            scoring_factors={"raw_count_impact": 1.0},
            recommendations=self._generate_basic_recommendations(score, level),
        )

    def _time_weighted_scoring(
        self,
        activities: list[dict[str, Any]],
        competency_type: str,
        params: dict[str, Any],
        reference_date: datetime,
    ) -> ScoringResult:
        """Time decay weighted scoring"""

        raw_count = len(activities)

        # Calculate time-weighted counts
        time_decay_results = self.time_decay.calculate_bulk_weighted_values(
            activities, competency_field="competency_type"
        )

        weighted_count = sum(result.weighted_value for result in time_decay_results)
        time_decay_impact = (weighted_count / max(raw_count, 1)) if raw_count > 0 else 0.0

        # Calculate score with time weighting
        score = min(weighted_count * params["count_to_score_ratio"], params["max_score"])
        level = self._score_to_level(score)

        # Enhanced confidence based on recency
        recency_factor = self._calculate_recency_factor(activities, reference_date)
        confidence = min(0.8, 0.4 + recency_factor * 0.4) if weighted_count > 0 else 0.0

        return ScoringResult(
            competency_type=competency_type,
            scoring_method=ScoringMethod.TIME_WEIGHTED.value,
            raw_activity_count=raw_count,
            weighted_activity_count=weighted_count,
            competency_score=score,
            competency_level=level,
            evidence_level="time_adjusted",
            confidence_score=confidence,
            time_decay_impact=time_decay_impact,
            activities_analyzed=[
                result.dict() for result in time_decay_results[:10]
            ],  # Limit for brevity
            scoring_factors={
                "time_decay_impact": time_decay_impact,
                "recency_factor": recency_factor,
            },
            recommendations=self._generate_time_based_recommendations(score, level, recency_factor),
        )

    def _quality_weighted_scoring(
        self, activities: list[dict[str, Any]], competency_type: str, params: dict[str, Any]
    ) -> ScoringResult:
        """Quality-weighted scoring"""

        raw_count = len(activities)

        # Get evidence assessment for quality weighting
        evidence_assessment = self.evidence_threshold.assess_evidence(
            activities, competency_type, include_time_weighting=False
        )

        weighted_count = evidence_assessment.weighted_count
        quality_impact = (weighted_count / max(raw_count, 1)) if raw_count > 0 else 0.0

        # Calculate score with quality boost
        base_score = weighted_count * params["count_to_score_ratio"]
        quality_boosted_score = base_score * params["quality_boost"]
        score = min(quality_boosted_score, params["max_score"])
        level = self._score_to_level(score)

        return ScoringResult(
            competency_type=competency_type,
            scoring_method=ScoringMethod.QUALITY_WEIGHTED.value,
            raw_activity_count=raw_count,
            weighted_activity_count=weighted_count,
            competency_score=score,
            competency_level=level,
            evidence_level=evidence_assessment.threshold_level.value,
            confidence_score=evidence_assessment.confidence_score,
            quality_impact=quality_impact,
            activities_analyzed=activities[:10],  # Limit for brevity
            scoring_factors={
                "quality_impact": quality_impact,
                "quality_boost": params["quality_boost"],
            },
            recommendations=evidence_assessment.recommendations,
        )

    def _comprehensive_scoring(
        self,
        activities: list[dict[str, Any]],
        competency_type: str,
        params: dict[str, Any],
        reference_date: datetime,
        user_context: dict[str, Any] | None,
    ) -> ScoringResult:
        """Comprehensive scoring with time, quality, and evidence factors"""

        raw_count = len(activities)

        if raw_count == 0:
            return self._create_empty_result(competency_type)

        # Get time decay results
        time_decay_results = self.time_decay.calculate_bulk_weighted_values(
            activities, competency_field="competency_type"
        )

        # Add time decay weights back to activities for evidence assessment
        activities_with_decay = []
        for i, activity in enumerate(activities):
            if i < len(time_decay_results):
                activity_copy = activity.copy()
                activity_copy["time_decay_weight"] = time_decay_results[i].decay_weight
                activities_with_decay.append(activity_copy)
            else:
                activities_with_decay.append(activity)

        # Get evidence assessment with both time and quality weighting
        evidence_assessment = self.evidence_threshold.assess_evidence(
            activities_with_decay, competency_type, include_time_weighting=True
        )

        # Calculate comprehensive score
        time_weighted_count = evidence_assessment.time_weighted_count
        base_score = time_weighted_count * params["count_to_score_ratio"]

        # Apply quality boost
        quality_boosted_score = base_score * params["quality_boost"]

        # Apply recency bonus
        recency_factor = self._calculate_recency_factor(activities, reference_date)
        recency_bonus = 1.0 + (recency_factor * (params["recency_bonus"] - 1.0))
        final_score = quality_boosted_score * recency_bonus

        # Cap at maximum score
        score = min(final_score, params["max_score"])
        level = self._score_to_level(score)

        # Enhanced confidence calculation
        confidence = self._calculate_comprehensive_confidence(
            evidence_assessment, recency_factor, raw_count, params
        )

        # Calculate impact factors
        time_decay_impact = sum(r.decay_weight for r in time_decay_results) / len(
            time_decay_results
        )
        quality_impact = evidence_assessment.weighted_count / max(raw_count, 1)

        return ScoringResult(
            competency_type=competency_type,
            scoring_method=ScoringMethod.COMPREHENSIVE.value,
            raw_activity_count=raw_count,
            weighted_activity_count=time_weighted_count,
            competency_score=score,
            competency_level=level,
            evidence_level=evidence_assessment.threshold_level.value,
            confidence_score=confidence,
            time_decay_impact=time_decay_impact,
            quality_impact=quality_impact,
            activities_analyzed=activities[:10],  # Limit for brevity
            scoring_factors={
                "base_score": base_score,
                "quality_boost": params["quality_boost"],
                "recency_bonus": recency_bonus,
                "time_decay_impact": time_decay_impact,
                "quality_impact": quality_impact,
                "recency_factor": recency_factor,
            },
            recommendations=self._generate_comprehensive_recommendations(
                score, level, evidence_assessment, recency_factor, params
            ),
        )

    def _apply_final_adjustments(
        self, result: ScoringResult, params: dict[str, Any], user_context: dict[str, Any] | None
    ) -> ScoringResult:
        """Apply final adjustments based on user context and validation rules"""

        adjusted_score = result.competency_score
        adjustments = []

        # Check minimum activity requirements for level
        min_activities = params["minimum_activities_for_level"]
        current_level_value = result.competency_level.value

        if result.raw_activity_count < min_activities.get(current_level_value, 0):
            # Downgrade level if insufficient activities
            max_achievable_level = 1
            for level_val, min_count in min_activities.items():
                if result.raw_activity_count >= min_count:
                    max_achievable_level = max(max_achievable_level, level_val)

            adjusted_score = min(adjusted_score, float(max_achievable_level))
            adjustments.append(f"Level capped at {max_achievable_level} due to activity count")

        # User context adjustments (if available)
        if user_context:
            # Experience level adjustment
            experience_years = user_context.get("experience_years", 0)
            if experience_years > 0:
                # Experienced users get small boost for same activity levels
                experience_boost = min(0.2, experience_years * 0.02)
                adjusted_score *= 1.0 + experience_boost
                adjustments.append(f"Experience boost: {experience_boost:.2f}")

            # Role level adjustment
            role_level = user_context.get("role_level", "junior")
            if role_level in ["senior", "lead", "principal"]:
                # Higher role expectations - need more evidence for same score
                role_adjustment = 0.9 if role_level == "senior" else 0.85
                adjusted_score *= role_adjustment
                adjustments.append(f"Role level adjustment: {role_adjustment}")

        # Final bounds checking
        adjusted_score = min(params["max_score"], max(0.0, adjusted_score))
        adjusted_level = self._score_to_level(adjusted_score)

        # Update result if adjustments were made
        if adjustments:
            result.competency_score = adjusted_score
            result.competency_level = adjusted_level
            result.scoring_factors["final_adjustments"] = adjustments
            result.recommendations.extend([f"Note: {adj}" for adj in adjustments])

        return result

    def _score_to_level(self, score: float) -> CompetencyScoreLevel:
        """Convert numeric score to competency level"""
        if score < 1.0:
            return CompetencyScoreLevel.NOVICE
        elif score < 2.0:
            return CompetencyScoreLevel.DEVELOPING
        elif score < 3.0:
            return CompetencyScoreLevel.PROFICIENT
        elif score < 4.0:
            return CompetencyScoreLevel.ADVANCED
        else:
            return CompetencyScoreLevel.EXPERT

    def _calculate_recency_factor(
        self, activities: list[dict[str, Any]], reference_date: datetime
    ) -> float:
        """Calculate recency factor based on activity distribution"""
        if not activities:
            return 0.0

        recent_count = 0
        for activity in activities:
            activity_date = activity.get("date")
            if activity_date:
                if isinstance(activity_date, str):
                    activity_date = datetime.fromisoformat(activity_date.replace("Z", "+00:00"))
                days_ago = (reference_date - activity_date).days
                if days_ago <= 30:  # Recent = last 30 days
                    recent_count += 1

        return recent_count / len(activities)

    def _calculate_comprehensive_confidence(
        self, evidence_assessment, recency_factor: float, raw_count: int, params: dict[str, Any]
    ) -> float:
        """Calculate comprehensive confidence score"""

        base_confidence = evidence_assessment.confidence_score

        # Recency bonus to confidence
        recency_bonus = recency_factor * 0.1

        # Activity count bonus
        count_bonus = min(0.1, raw_count * 0.01)

        # Evidence level bonus
        evidence_bonus = {"strong": 0.1, "moderate": 0.05, "weak": 0.0, "insufficient": -0.1}.get(
            evidence_assessment.threshold_level.value, 0.0
        )

        final_confidence = base_confidence + recency_bonus + count_bonus + evidence_bonus

        return min(1.0, max(0.0, final_confidence))

    def _create_empty_result(self, competency_type: str) -> ScoringResult:
        """Create empty result for competency with no activities"""
        return ScoringResult(
            competency_type=competency_type,
            scoring_method=ScoringMethod.COMPREHENSIVE.value,
            raw_activity_count=0,
            weighted_activity_count=0.0,
            competency_score=0.0,
            competency_level=CompetencyScoreLevel.NOVICE,
            evidence_level="insufficient",
            confidence_score=0.0,
            recommendations=["No activities found for this competency in the assessment period"],
        )

    def _generate_basic_recommendations(
        self, score: float, level: CompetencyScoreLevel
    ) -> list[str]:
        """Generate basic recommendations"""
        if score < 1.0:
            return ["Begin building experience in this competency area"]
        elif score < 3.0:
            return ["Continue practicing to build proficiency"]
        else:
            return ["Maintain current activity levels"]

    def _generate_time_based_recommendations(
        self, score: float, level: CompetencyScoreLevel, recency_factor: float
    ) -> list[str]:
        """Generate time-based recommendations"""
        recommendations = self._generate_basic_recommendations(score, level)

        if recency_factor < 0.3:
            recommendations.append("Focus on more recent activities to maintain skill currency")

        return recommendations

    def _generate_comprehensive_recommendations(
        self,
        score: float,
        level: CompetencyScoreLevel,
        evidence_assessment,
        recency_factor: float,
        params: dict[str, Any],
    ) -> list[str]:
        """Generate comprehensive recommendations"""
        recommendations = evidence_assessment.recommendations.copy()

        # Add score-specific recommendations
        if score >= 4.0:
            recommendations.append("Consider mentoring others or leading initiatives in this area")
        elif score >= 3.0:
            recommendations.append("Look for opportunities to take on more challenging work")

        # Add recency recommendations
        if recency_factor < 0.4:
            recommendations.append("Prioritize recent activities to demonstrate current competency")

        return recommendations


# Global scorer instance
_global_scorer: ActivityScorer | None = None


def get_activity_scorer() -> ActivityScorer:
    """Get global activity scorer instance"""
    global _global_scorer
    if _global_scorer is None:
        _global_scorer = ActivityScorer()
    return _global_scorer
