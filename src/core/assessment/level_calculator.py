"""
Level Advancement Calculator for ReflectAI

Implements  Level advancement logic and validation:
- Time-in-role requirements for level advancement
- Competency threshold calculations based on framework definitions
- Peer comparison and historical benchmarks
- Custom advancement rules per organization and role type
- Level validation with evidence requirements

Provides structured advancement pathways for competency development.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from src.shared import get_logger


class CompetencyLevel(Enum):
    """Standard competency levels (1-5 scale)"""

    NOVICE = 1
    DEVELOPING = 2
    PROFICIENT = 3
    ADVANCED = 4
    EXPERT = 5


class AdvancementStatus(Enum):
    """Level advancement status"""

    ELIGIBLE = "eligible"
    PENDING_EVIDENCE = "pending_evidence"
    PENDING_TIME = "pending_time"
    BLOCKED = "blocked"
    NOT_APPLICABLE = "not_applicable"


@dataclass
class LevelRequirement:
    """Requirements for a specific competency level"""

    level: CompetencyLevel
    minimum_score: float
    minimum_evidence_activities: int
    minimum_time_in_role_days: int
    required_peer_percentile: int | None = None  # e.g., top 25% of peers
    required_competencies: list[str] = None
    blocking_competencies: list[str] = None  # Competencies that must not be below threshold

    def __post_init__(self):
        if self.required_competencies is None:
            self.required_competencies = []
        if self.blocking_competencies is None:
            self.blocking_competencies = []


class LevelAdvancementResult(BaseModel):
    """Result of level advancement calculation"""

    competency_id: str = Field(..., description="Competency being evaluated")
    current_level: CompetencyLevel = Field(..., description="Current competency level")
    target_level: CompetencyLevel = Field(..., description="Target advancement level")
    advancement_status: AdvancementStatus = Field(..., description="Advancement eligibility")

    # Requirement validation
    score_requirement_met: bool = Field(..., description="Score threshold met")
    evidence_requirement_met: bool = Field(..., description="Evidence threshold met")
    time_requirement_met: bool = Field(..., description="Time-in-role requirement met")
    peer_comparison_met: bool = Field(default=True, description="Peer comparison requirement met")

    # Detailed metrics
    current_score: float = Field(..., description="Current competency score")
    required_score: float = Field(..., description="Required score for advancement")
    current_evidence_count: int = Field(..., description="Current evidence activities")
    required_evidence_count: int = Field(..., description="Required evidence activities")
    current_time_in_role_days: int = Field(..., description="Current time in role (days)")
    required_time_in_role_days: int = Field(..., description="Required time in role (days)")

    # Gaps and recommendations
    score_gap: float = Field(default=0.0, description="Score gap to meet requirement")
    evidence_gap: int = Field(default=0, description="Evidence gap to meet requirement")
    time_gap_days: int = Field(default=0, description="Time gap to meet requirement")

    advancement_recommendations: list[str] = Field(
        default_factory=list, description="Specific advancement recommendations"
    )
    estimated_timeline: str | None = Field(None, description="Estimated time to advancement")

    # Validation details
    validation_details: dict[str, Any] = Field(
        default_factory=dict, description="Detailed validation information"
    )


class LevelCalculator:
    """Level advancement calculator and validator"""

    def __init__(self, organization_id: str = "default"):
        self.logger = get_logger("assessment.level_calculator")
        self.organization_id = organization_id

        # Default level requirements by role type
        self.role_requirements = {
            "junior_engineer": {
                CompetencyLevel.DEVELOPING: LevelRequirement(
                    level=CompetencyLevel.DEVELOPING,
                    minimum_score=1.5,
                    minimum_evidence_activities=5,
                    minimum_time_in_role_days=30,
                ),
                CompetencyLevel.PROFICIENT: LevelRequirement(
                    level=CompetencyLevel.PROFICIENT,
                    minimum_score=2.5,
                    minimum_evidence_activities=10,
                    minimum_time_in_role_days=180,  # 6 months
                    required_peer_percentile=50,
                ),
            },
            "mid_engineer": {
                CompetencyLevel.PROFICIENT: LevelRequirement(
                    level=CompetencyLevel.PROFICIENT,
                    minimum_score=2.0,
                    minimum_evidence_activities=8,
                    minimum_time_in_role_days=30,
                ),
                CompetencyLevel.ADVANCED: LevelRequirement(
                    level=CompetencyLevel.ADVANCED,
                    minimum_score=3.5,
                    minimum_evidence_activities=15,
                    minimum_time_in_role_days=365,  # 1 year
                    required_peer_percentile=25,
                ),
            },
            "senior_engineer": {
                CompetencyLevel.ADVANCED: LevelRequirement(
                    level=CompetencyLevel.ADVANCED,
                    minimum_score=3.0,
                    minimum_evidence_activities=12,
                    minimum_time_in_role_days=30,
                ),
                CompetencyLevel.EXPERT: LevelRequirement(
                    level=CompetencyLevel.EXPERT,
                    minimum_score=4.5,
                    minimum_evidence_activities=25,
                    minimum_time_in_role_days=730,  # 2 years
                    required_peer_percentile=10,
                ),
            },
            "lead_engineer": {
                CompetencyLevel.ADVANCED: LevelRequirement(
                    level=CompetencyLevel.ADVANCED,
                    minimum_score=3.5,
                    minimum_evidence_activities=15,
                    minimum_time_in_role_days=30,
                    required_competencies=["leadership", "communication"],
                ),
                CompetencyLevel.EXPERT: LevelRequirement(
                    level=CompetencyLevel.EXPERT,
                    minimum_score=4.5,
                    minimum_evidence_activities=30,
                    minimum_time_in_role_days=1095,  # 3 years
                    required_peer_percentile=5,
                    required_competencies=["leadership", "communication", "technical_skills"],
                ),
            },
        }

        # Default requirements for unknown roles
        self.default_requirements = {
            CompetencyLevel.DEVELOPING: LevelRequirement(
                level=CompetencyLevel.DEVELOPING,
                minimum_score=1.5,
                minimum_evidence_activities=5,
                minimum_time_in_role_days=60,
            ),
            CompetencyLevel.PROFICIENT: LevelRequirement(
                level=CompetencyLevel.PROFICIENT,
                minimum_score=2.5,
                minimum_evidence_activities=10,
                minimum_time_in_role_days=180,
            ),
            CompetencyLevel.ADVANCED: LevelRequirement(
                level=CompetencyLevel.ADVANCED,
                minimum_score=3.5,
                minimum_evidence_activities=15,
                minimum_time_in_role_days=365,
            ),
            CompetencyLevel.EXPERT: LevelRequirement(
                level=CompetencyLevel.EXPERT,
                minimum_score=4.5,
                minimum_evidence_activities=25,
                minimum_time_in_role_days=730,
            ),
        }

    def calculate_advancement_eligibility(
        self,
        competency_id: str,
        current_score: float,
        current_evidence_count: int,
        user_context: dict[str, Any],
        peer_benchmarks: dict[str, float] | None = None,
        target_level: CompetencyLevel | None = None,
    ) -> LevelAdvancementResult:
        """Calculate level advancement eligibility"""

        # Determine current level from score
        current_level = self._score_to_level(current_score)

        # Determine target level (next level if not specified)
        if target_level is None:
            if current_level.value < 5:
                target_level = CompetencyLevel(current_level.value + 1)
            else:
                target_level = current_level  # Already at max level

        # Get requirements for target level
        requirements = self._get_level_requirements(
            target_level, user_context.get("role", "unknown")
        )

        # Calculate time in role
        time_in_role_days = self._calculate_time_in_role(user_context)

        # Validate each requirement
        score_met = current_score >= requirements.minimum_score
        evidence_met = current_evidence_count >= requirements.minimum_evidence_activities
        time_met = time_in_role_days >= requirements.minimum_time_in_role_days

        # Peer comparison (if required)
        peer_met = True
        if requirements.required_peer_percentile is not None and peer_benchmarks:
            peer_met = self._validate_peer_comparison(
                current_score, peer_benchmarks, requirements.required_peer_percentile
            )

        # Determine advancement status
        advancement_status = self._determine_advancement_status(
            score_met, evidence_met, time_met, peer_met, current_level, target_level
        )

        # Calculate gaps
        score_gap = max(0.0, requirements.minimum_score - current_score)
        evidence_gap = max(0, requirements.minimum_evidence_activities - current_evidence_count)
        time_gap = max(0, requirements.minimum_time_in_role_days - time_in_role_days)

        # Generate recommendations
        recommendations = self._generate_advancement_recommendations(
            advancement_status, score_gap, evidence_gap, time_gap, requirements
        )

        # Estimate timeline
        estimated_timeline = self._estimate_advancement_timeline(
            score_gap, evidence_gap, time_gap, user_context
        )

        return LevelAdvancementResult(
            competency_id=competency_id,
            current_level=current_level,
            target_level=target_level,
            advancement_status=advancement_status,
            score_requirement_met=score_met,
            evidence_requirement_met=evidence_met,
            time_requirement_met=time_met,
            peer_comparison_met=peer_met,
            current_score=current_score,
            required_score=requirements.minimum_score,
            current_evidence_count=current_evidence_count,
            required_evidence_count=requirements.minimum_evidence_activities,
            current_time_in_role_days=time_in_role_days,
            required_time_in_role_days=requirements.minimum_time_in_role_days,
            score_gap=score_gap,
            evidence_gap=evidence_gap,
            time_gap_days=time_gap,
            advancement_recommendations=recommendations,
            estimated_timeline=estimated_timeline,
            validation_details={
                "requirements_used": requirements.__dict__,
                "peer_percentile_required": requirements.required_peer_percentile,
                "role": user_context.get("role", "unknown"),
            },
        )

    def calculate_multiple_advancements(
        self,
        competency_scores: dict[str, float],
        evidence_counts: dict[str, int],
        user_context: dict[str, Any],
        peer_benchmarks: dict[str, dict[str, float]] | None = None,
    ) -> dict[str, LevelAdvancementResult]:
        """Calculate advancement eligibility for multiple competencies"""

        results = {}

        for competency_id, score in competency_scores.items():
            try:
                evidence_count = evidence_counts.get(competency_id, 0)
                comp_peer_benchmarks = (
                    peer_benchmarks.get(competency_id) if peer_benchmarks else None
                )

                result = self.calculate_advancement_eligibility(
                    competency_id, score, evidence_count, user_context, comp_peer_benchmarks
                )

                results[competency_id] = result

            except Exception as e:
                self.logger.error(f"Error calculating advancement for {competency_id}: {str(e)}")
                # Create error result
                current_level = self._score_to_level(score)
                results[competency_id] = LevelAdvancementResult(
                    competency_id=competency_id,
                    current_level=current_level,
                    target_level=current_level,
                    advancement_status=AdvancementStatus.BLOCKED,
                    score_requirement_met=False,
                    evidence_requirement_met=False,
                    time_requirement_met=False,
                    current_score=score,
                    required_score=0.0,
                    current_evidence_count=0,
                    required_evidence_count=0,
                    current_time_in_role_days=0,
                    required_time_in_role_days=0,
                    advancement_recommendations=["Unable to calculate advancement requirements"],
                )

        return results

    def get_advancement_path(
        self,
        competency_id: str,
        current_score: float,
        user_context: dict[str, Any],
        target_level: CompetencyLevel = CompetencyLevel.EXPERT,
    ) -> list[LevelAdvancementResult]:
        """Get complete advancement path from current level to target"""

        current_level = self._score_to_level(current_score)
        advancement_path = []

        # Generate advancement results for each level from current+1 to target
        for level_value in range(current_level.value + 1, target_level.value + 1):
            level = CompetencyLevel(level_value)

            result = self.calculate_advancement_eligibility(
                competency_id, current_score, 0, user_context, target_level=level
            )

            advancement_path.append(result)

        return advancement_path

    def _score_to_level(self, score: float) -> CompetencyLevel:
        """Convert numeric score to competency level"""
        if score < 1.0:
            return CompetencyLevel.NOVICE
        elif score < 2.0:
            return CompetencyLevel.DEVELOPING
        elif score < 3.0:
            return CompetencyLevel.PROFICIENT
        elif score < 4.0:
            return CompetencyLevel.ADVANCED
        else:
            return CompetencyLevel.EXPERT

    def _get_level_requirements(self, level: CompetencyLevel, role: str) -> LevelRequirement:
        """Get requirements for a specific level and role"""

        # Check role-specific requirements first
        if role in self.role_requirements:
            if level in self.role_requirements[role]:
                return self.role_requirements[role][level]

        # Fallback to default requirements
        if level in self.default_requirements:
            return self.default_requirements[level]

        # Ultimate fallback
        return LevelRequirement(
            level=level,
            minimum_score=float(level.value),
            minimum_evidence_activities=level.value * 5,
            minimum_time_in_role_days=level.value * 90,
        )

    def _calculate_time_in_role(self, user_context: dict[str, Any]) -> int:
        """Calculate time in current role"""

        role_start_date = user_context.get("role_start_date")
        if role_start_date:
            if isinstance(role_start_date, str):
                try:
                    role_start_date = datetime.fromisoformat(role_start_date.replace("Z", "+00:00"))
                except Exception:
                    role_start_date = None

            if role_start_date:
                return (datetime.now(UTC) - role_start_date).days

        # Fallback: use overall experience
        experience_years = user_context.get("experience_years", 0)
        return int(experience_years * 365)

    def _validate_peer_comparison(
        self, current_score: float, peer_benchmarks: dict[str, float], required_percentile: int
    ) -> bool:
        """Validate if score meets peer comparison requirement"""

        percentile_key = f"p{required_percentile}"
        if percentile_key in peer_benchmarks:
            return current_score >= peer_benchmarks[percentile_key]

        # Fallback: use median if specific percentile not available
        median = peer_benchmarks.get("p50", peer_benchmarks.get("median", 0.0))
        # Adjust median based on required percentile
        adjustment_factor = (
            50 - required_percentile
        ) / 50.0  # Higher percentile = higher requirement
        adjusted_benchmark = median * (1.0 + adjustment_factor)

        return current_score >= adjusted_benchmark

    def _determine_advancement_status(
        self,
        score_met: bool,
        evidence_met: bool,
        time_met: bool,
        peer_met: bool,
        current_level: CompetencyLevel,
        target_level: CompetencyLevel,
    ) -> AdvancementStatus:
        """Determine overall advancement status"""

        if current_level.value >= target_level.value:
            return AdvancementStatus.NOT_APPLICABLE

        if score_met and evidence_met and time_met and peer_met:
            return AdvancementStatus.ELIGIBLE
        elif not time_met:
            return AdvancementStatus.PENDING_TIME
        elif not (score_met and evidence_met):
            return AdvancementStatus.PENDING_EVIDENCE
        else:
            return AdvancementStatus.BLOCKED

    def _generate_advancement_recommendations(
        self,
        status: AdvancementStatus,
        score_gap: float,
        evidence_gap: int,
        time_gap: int,
        requirements: LevelRequirement,
    ) -> list[str]:
        """Generate specific advancement recommendations"""

        recommendations = []

        if status == AdvancementStatus.ELIGIBLE:
            recommendations.append("All requirements met - ready for level advancement")
            recommendations.append("Consider discussing promotion with manager")

        elif status == AdvancementStatus.PENDING_EVIDENCE:
            if score_gap > 0:
                recommendations.append(f"Increase competency score by {score_gap:.1f} points")
                recommendations.append("Focus on high-impact activities and skill development")

            if evidence_gap > 0:
                recommendations.append(f"Document {evidence_gap} more relevant activities")
                recommendations.append("Seek opportunities to demonstrate this competency")

        elif status == AdvancementStatus.PENDING_TIME:
            recommendations.append(f"Continue building experience for {time_gap} more days")
            recommendations.append("Use this time to strengthen competency evidence")

        elif status == AdvancementStatus.BLOCKED:
            recommendations.append("Review advancement requirements with manager")
            recommendations.append("Consider alternative development paths")

        else:  # NOT_APPLICABLE
            recommendations.append("Already at or above target level")
            recommendations.append("Focus on maintaining excellence and mentoring others")

        # Add level-specific recommendations
        if requirements.required_competencies:
            recommendations.append(
                f"Ensure strong performance in: {', '.join(requirements.required_competencies)}"
            )

        return recommendations

    def _estimate_advancement_timeline(
        self, score_gap: float, evidence_gap: int, time_gap: int, user_context: dict[str, Any]
    ) -> str:
        """Estimate timeline for advancement"""

        if score_gap == 0 and evidence_gap == 0 and time_gap == 0:
            return "Ready now"

        # Estimate time needed for score improvement (assuming 0.1 points per month of focused effort)
        score_months = score_gap * 10 if score_gap > 0 else 0

        # Estimate time needed for evidence building (assuming 2 activities per month)
        evidence_months = evidence_gap / 2 if evidence_gap > 0 else 0

        # Time gap in months
        time_months = time_gap / 30

        # Take the maximum of all requirements
        total_months = max(score_months, evidence_months, time_months)

        if total_months < 1:
            return "Within 1 month"
        elif total_months < 3:
            return "1-3 months"
        elif total_months < 6:
            return "3-6 months"
        elif total_months < 12:
            return "6-12 months"
        else:
            return "12+ months"

    def update_role_requirements(
        self, role: str, level: CompetencyLevel, requirements: LevelRequirement
    ):
        """Update requirements for a specific role and level"""
        if role not in self.role_requirements:
            self.role_requirements[role] = {}

        self.role_requirements[role][level] = requirements
        self.logger.info(f"Updated requirements for {role} level {level.name}")

    def get_role_requirements_summary(self, role: str) -> dict[str, dict[str, Any]]:
        """Get summary of requirements for a role"""
        requirements = self.role_requirements.get(role, self.default_requirements)

        summary = {}
        for level, req in requirements.items():
            summary[level.name] = {
                "minimum_score": req.minimum_score,
                "minimum_evidence": req.minimum_evidence_activities,
                "minimum_time_days": req.minimum_time_in_role_days,
                "peer_percentile": req.required_peer_percentile,
                "required_competencies": req.required_competencies,
            }

        return summary


# Global calculator instance
_global_calculator: LevelCalculator | None = None


def get_level_calculator(organization_id: str = "default") -> LevelCalculator:
    """Get global level calculator instance"""
    global _global_calculator
    if _global_calculator is None:
        _global_calculator = LevelCalculator(organization_id)
    return _global_calculator
