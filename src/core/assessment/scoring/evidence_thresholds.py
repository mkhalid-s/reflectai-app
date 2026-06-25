"""
Evidence Thresholds for ReflectAI Competency Assessment

Implements  Simple Competency Assessment evidence thresholds:
- Strong evidence: >8 activities in time window
- Moderate evidence: 4-8 activities in time window
- Weak evidence: <4 activities in time window
- Configurable thresholds per competency type
- Evidence quality assessment and validation

Provides evidence-based competency level determination.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from src.shared import get_logger


class ThresholdLevel(Enum):
    """Evidence threshold levels"""

    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    INSUFFICIENT = "insufficient"


@dataclass
class ThresholdConfiguration:
    """Configuration for evidence thresholds"""

    competency_type: str
    strong_threshold: int = 8
    moderate_threshold: int = 4
    weak_threshold: int = 1
    time_window_days: int = 90
    quality_multipliers: dict[str, float] = None  # Activity quality adjustments

    def __post_init__(self) -> None:
        if self.quality_multipliers is None:
            self.quality_multipliers = {
                "high_impact": 2.0,
                "medium_impact": 1.0,
                "low_impact": 0.5,
                "demonstrated": 1.5,
                "mentioned": 0.8,
            }


class EvidenceAssessment(BaseModel):
    """Assessment result for evidence quality"""

    competency_type: str = Field(..., description="Competency being assessed")
    threshold_level: ThresholdLevel = Field(..., description="Determined evidence level")
    activity_count: int = Field(..., description="Raw activity count")
    weighted_count: float = Field(..., description="Quality-weighted activity count")
    time_weighted_count: float = Field(..., description="Time and quality weighted count")
    confidence_score: float = Field(..., description="Confidence in assessment (0.0-1.0)")
    evidence_details: dict[str, Any] = Field(
        default_factory=dict, description="Detailed evidence breakdown"
    )
    recommendations: list[str] = Field(
        default_factory=list, description="Improvement recommendations"
    )


class EvidenceThreshold:
    """Evidence threshold calculator for competency assessment"""

    def __init__(self):
        self.logger = get_logger("assessment.evidence_thresholds")

        # Default threshold configurations by competency type
        self.threshold_configs = {
            "technical_skills": ThresholdConfiguration(
                competency_type="technical_skills",
                strong_threshold=10,
                moderate_threshold=5,
                weak_threshold=2,
                time_window_days=90,
                quality_multipliers={
                    "project_completion": 3.0,
                    "code_review": 2.0,
                    "bug_fix": 1.5,
                    "documentation": 1.0,
                    "discussion": 0.5,
                },
            ),
            "leadership": ThresholdConfiguration(
                competency_type="leadership",
                strong_threshold=6,
                moderate_threshold=3,
                weak_threshold=1,
                time_window_days=120,  # Leadership evidence lasts longer
                quality_multipliers={
                    "team_leadership": 3.0,
                    "decision_making": 2.5,
                    "mentoring": 2.0,
                    "meeting_leadership": 1.5,
                    "guidance_provided": 1.0,
                },
            ),
            "communication": ThresholdConfiguration(
                competency_type="communication",
                strong_threshold=12,
                moderate_threshold=6,
                weak_threshold=2,
                time_window_days=60,  # Communication needs recent evidence
                quality_multipliers={
                    "presentation": 2.5,
                    "documentation": 2.0,
                    "client_communication": 2.0,
                    "team_communication": 1.5,
                    "written_communication": 1.0,
                },
            ),
            "project_management": ThresholdConfiguration(
                competency_type="project_management",
                strong_threshold=8,
                moderate_threshold=4,
                weak_threshold=1,
                time_window_days=90,
                quality_multipliers={
                    "project_completion": 3.0,
                    "milestone_achievement": 2.0,
                    "risk_management": 2.0,
                    "stakeholder_management": 1.5,
                    "planning": 1.0,
                },
            ),
            "problem_solving": ThresholdConfiguration(
                competency_type="problem_solving",
                strong_threshold=10,
                moderate_threshold=5,
                weak_threshold=2,
                time_window_days=90,
                quality_multipliers={
                    "complex_problem_solved": 3.0,
                    "innovative_solution": 2.5,
                    "troubleshooting": 2.0,
                    "analysis": 1.5,
                    "investigation": 1.0,
                },
            ),
        }

        # Default configuration for unspecified competency types
        self.default_config = ThresholdConfiguration(
            competency_type="general",
            strong_threshold=8,
            moderate_threshold=4,
            weak_threshold=1,
            time_window_days=90,
        )

    def assess_evidence(
        self,
        activities: list[dict[str, Any]],
        competency_type: str,
        custom_config: ThresholdConfiguration | None = None,
        include_quality_weighting: bool = True,
        include_time_weighting: bool = True,
    ) -> EvidenceAssessment:
        """Assess evidence quality for a competency"""

        config = custom_config or self.threshold_configs.get(competency_type, self.default_config)

        # Basic counts
        activity_count = len(activities)

        # Calculate quality-weighted count
        weighted_count = (
            self._calculate_quality_weighted_count(activities, config)
            if include_quality_weighting
            else float(activity_count)
        )

        # Calculate time-weighted count (if time decay results are available)
        time_weighted_count = (
            self._calculate_time_weighted_count(activities, config)
            if include_time_weighting
            else weighted_count
        )

        # Determine threshold level based on time-weighted count
        threshold_level = self._determine_threshold_level(time_weighted_count, config)

        # Calculate confidence score
        confidence_score = self._calculate_confidence_score(
            time_weighted_count, threshold_level, config
        )

        # Generate evidence details
        evidence_details = self._generate_evidence_details(activities, config)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            threshold_level, time_weighted_count, config, evidence_details
        )

        return EvidenceAssessment(
            competency_type=competency_type,
            threshold_level=threshold_level,
            activity_count=activity_count,
            weighted_count=weighted_count,
            time_weighted_count=time_weighted_count,
            confidence_score=confidence_score,
            evidence_details=evidence_details,
            recommendations=recommendations,
        )

    def batch_assess_competencies(
        self,
        competency_activities: dict[str, list[dict[str, Any]]],
        include_quality_weighting: bool = True,
        include_time_weighting: bool = True,
    ) -> dict[str, EvidenceAssessment]:
        """Assess evidence for multiple competencies"""

        assessments = {}

        for competency_type, activities in competency_activities.items():
            try:
                assessment = self.assess_evidence(
                    activities,
                    competency_type,
                    include_quality_weighting=include_quality_weighting,
                    include_time_weighting=include_time_weighting,
                )
                assessments[competency_type] = assessment

            except Exception as e:
                self.logger.error(f"Error assessing competency {competency_type}: {str(e)}")
                # Create fallback assessment
                assessments[competency_type] = EvidenceAssessment(
                    competency_type=competency_type,
                    threshold_level=ThresholdLevel.INSUFFICIENT,
                    activity_count=0,
                    weighted_count=0.0,
                    time_weighted_count=0.0,
                    confidence_score=0.0,
                    recommendations=["Unable to assess competency due to data error"],
                )

        return assessments

    def _calculate_quality_weighted_count(
        self, activities: list[dict[str, Any]], config: ThresholdConfiguration
    ) -> float:
        """Calculate quality-weighted activity count"""

        weighted_count = 0.0

        for activity in activities:
            # Get activity quality/type for weighting
            activity_type = activity.get("activity_type", "unknown")
            quality_level = activity.get("quality_level", "medium_impact")

            # Apply quality multiplier
            multiplier = config.quality_multipliers.get(activity_type, 1.0)
            if multiplier == 1.0:  # Fallback to quality level
                multiplier = config.quality_multipliers.get(quality_level, 1.0)

            # Get base activity value (default 1.0)
            base_value = activity.get("value", 1.0)

            weighted_count += base_value * multiplier

        return weighted_count

    def _calculate_time_weighted_count(
        self, activities: list[dict[str, Any]], config: ThresholdConfiguration
    ) -> float:
        """Calculate time-weighted activity count using decay weights"""

        time_weighted_count = 0.0

        for activity in activities:
            # If time decay weight is available, use it
            if "time_decay_weight" in activity:
                base_value = activity.get("value", 1.0)
                quality_multiplier = self._get_quality_multiplier(activity, config)
                decay_weight = activity["time_decay_weight"]

                time_weighted_count += base_value * quality_multiplier * decay_weight
            else:
                # Fallback to quality weighting only
                quality_multiplier = self._get_quality_multiplier(activity, config)
                base_value = activity.get("value", 1.0)
                time_weighted_count += base_value * quality_multiplier

        return time_weighted_count

    def _get_quality_multiplier(
        self, activity: dict[str, Any], config: ThresholdConfiguration
    ) -> float:
        """Get quality multiplier for an activity"""
        activity_type = activity.get("activity_type", "unknown")
        quality_level = activity.get("quality_level", "medium_impact")

        # Try activity type first, fallback to quality level
        multiplier = config.quality_multipliers.get(activity_type, 1.0)
        if multiplier == 1.0:
            multiplier = config.quality_multipliers.get(quality_level, 1.0)

        return multiplier

    def _determine_threshold_level(
        self, weighted_count: float, config: ThresholdConfiguration
    ) -> ThresholdLevel:
        """Determine threshold level based on weighted count"""

        if weighted_count >= config.strong_threshold:
            return ThresholdLevel.STRONG
        elif weighted_count >= config.moderate_threshold:
            return ThresholdLevel.MODERATE
        elif weighted_count >= config.weak_threshold:
            return ThresholdLevel.WEAK
        else:
            return ThresholdLevel.INSUFFICIENT

    def _calculate_confidence_score(
        self, weighted_count: float, threshold_level: ThresholdLevel, config: ThresholdConfiguration
    ) -> float:
        """Calculate confidence score for the assessment"""

        if threshold_level == ThresholdLevel.STRONG:
            # High confidence for strong evidence
            excess = weighted_count - config.strong_threshold
            max_excess = config.strong_threshold * 0.5  # 50% above threshold = max confidence
            confidence = min(0.9, 0.7 + (excess / max_excess) * 0.2)

        elif threshold_level == ThresholdLevel.MODERATE:
            # Medium confidence for moderate evidence
            progress = (weighted_count - config.moderate_threshold) / (
                config.strong_threshold - config.moderate_threshold
            )
            confidence = 0.5 + progress * 0.2  # 0.5 to 0.7 range

        elif threshold_level == ThresholdLevel.WEAK:
            # Low confidence for weak evidence
            progress = (weighted_count - config.weak_threshold) / (
                config.moderate_threshold - config.weak_threshold
            )
            confidence = 0.3 + progress * 0.2  # 0.3 to 0.5 range

        else:  # INSUFFICIENT
            # Very low confidence
            if weighted_count > 0:
                confidence = min(0.3, weighted_count / config.weak_threshold * 0.3)
            else:
                confidence = 0.0

        return min(1.0, max(0.0, confidence))

    def _generate_evidence_details(
        self, activities: list[dict[str, Any]], config: ThresholdConfiguration
    ) -> dict[str, Any]:
        """Generate detailed evidence breakdown"""

        # Group activities by type
        activity_types = {}
        total_impact = 0.0

        for activity in activities:
            activity_type = activity.get("activity_type", "unknown")
            if activity_type not in activity_types:
                activity_types[activity_type] = {"count": 0, "impact": 0.0}

            activity_types[activity_type]["count"] += 1

            # Calculate impact
            base_value = activity.get("value", 1.0)
            quality_multiplier = self._get_quality_multiplier(activity, config)
            impact = base_value * quality_multiplier
            activity_types[activity_type]["impact"] += impact
            total_impact += impact

        # Calculate recency distribution
        recent_count = len([a for a in activities if a.get("days_ago", 999) <= 30])
        medium_count = len([a for a in activities if 30 < a.get("days_ago", 999) <= 60])
        older_count = len([a for a in activities if a.get("days_ago", 999) > 60])

        return {
            "activity_breakdown": activity_types,
            "total_impact": total_impact,
            "recency_distribution": {
                "recent_30_days": recent_count,
                "medium_30_60_days": medium_count,
                "older_60_plus_days": older_count,
            },
            "time_window_days": config.time_window_days,
            "thresholds": {
                "strong": config.strong_threshold,
                "moderate": config.moderate_threshold,
                "weak": config.weak_threshold,
            },
        }

    def _generate_recommendations(
        self,
        threshold_level: ThresholdLevel,
        weighted_count: float,
        config: ThresholdConfiguration,
        evidence_details: dict[str, Any],
    ) -> list[str]:
        """Generate improvement recommendations"""

        recommendations = []

        if threshold_level == ThresholdLevel.INSUFFICIENT:
            recommendations.extend(
                [
                    f"Increase activity in {config.competency_type} to build evidence",
                    f"Target at least {config.weak_threshold} activities in the next {config.time_window_days} days",
                    "Focus on high-impact activities for faster competency development",
                ]
            )

        elif threshold_level == ThresholdLevel.WEAK:
            gap_to_moderate = config.moderate_threshold - weighted_count
            recommendations.extend(
                [
                    f"Strengthen evidence with {gap_to_moderate:.1f} more activity points",
                    "Focus on higher-impact activities to reach moderate evidence level",
                    "Consider taking on more challenging projects in this competency area",
                ]
            )

        elif threshold_level == ThresholdLevel.MODERATE:
            gap_to_strong = config.strong_threshold - weighted_count
            recommendations.extend(
                [
                    f"Achieve strong evidence with {gap_to_strong:.1f} more activity points",
                    "Lead more complex initiatives to demonstrate advanced competency",
                    "Consider mentoring others to show expertise depth",
                ]
            )

        else:  # STRONG
            recommendations.extend(
                [
                    "Excellent evidence level - maintain current activity patterns",
                    "Consider becoming a mentor or subject matter expert",
                    "Share knowledge through documentation or training",
                ]
            )

        # Add specific recommendations based on activity patterns
        activity_breakdown = evidence_details.get("activity_breakdown", {})
        if len(activity_breakdown) == 1:
            recommendations.append("Diversify activity types to demonstrate broader competency")

        recency = evidence_details.get("recency_distribution", {})
        if recency.get("recent_30_days", 0) == 0:
            recommendations.append("Include more recent activities to maintain competency currency")

        return recommendations

    def get_threshold_config(self, competency_type: str) -> ThresholdConfiguration:
        """Get threshold configuration for a competency type"""
        return self.threshold_configs.get(competency_type, self.default_config)

    def update_threshold_config(self, config: ThresholdConfiguration):
        """Update threshold configuration for a competency type"""
        self.threshold_configs[config.competency_type] = config
        self.logger.info(f"Updated threshold configuration for: {config.competency_type}")

    def get_threshold_summary(self) -> dict[str, dict[str, int]]:
        """Get summary of all threshold configurations"""
        summary = {}

        for comp_type, config in self.threshold_configs.items():
            summary[comp_type] = {
                "strong": config.strong_threshold,
                "moderate": config.moderate_threshold,
                "weak": config.weak_threshold,
                "time_window": config.time_window_days,
            }

        return summary


# Global threshold calculator instance
_global_threshold_calculator: EvidenceThreshold | None = None


def get_evidence_threshold() -> EvidenceThreshold:
    """Get global evidence threshold calculator instance"""
    global _global_threshold_calculator
    if _global_threshold_calculator is None:
        _global_threshold_calculator = EvidenceThreshold()
    return _global_threshold_calculator
