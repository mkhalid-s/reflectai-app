"""
Competency Gap Analyzer for ReflectAI

Implements  Competency Gap Analysis including:
- Compare current competency levels against target role requirements
- Calculate skill gap scores and prioritize development areas
- Generate competency development roadmaps with actionable next steps
- Implement skill transferability analysis for career path recommendations
- Provide personalized learning and development guidance

Enables strategic competency development planning and career guidance.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from src.shared import get_logger

from .level_calculator import get_level_calculator


class GapSeverity(Enum):
    """Severity of competency gap"""

    CRITICAL = "critical"  # >2.0 points gap
    MAJOR = "major"  # 1.0-2.0 points gap
    MODERATE = "moderate"  # 0.5-1.0 points gap
    MINOR = "minor"  # <0.5 points gap
    NONE = "none"  # No gap or exceeds requirement


class DevelopmentPriority(Enum):
    """Priority level for competency development"""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    OPTIONAL = "optional"


@dataclass
class SkillTransferability:
    """Skill transferability analysis"""

    source_competency: str
    target_competency: str
    transferability_score: float  # 0.0-1.0
    transfer_rationale: str
    development_multiplier: float  # How much source helps develop target


class SkillGap(BaseModel):
    """Individual competency gap analysis"""

    competency_id: str = Field(..., description="Competency identifier")
    competency_name: str = Field(..., description="Human-readable competency name")
    current_score: float = Field(..., description="Current competency score")
    target_score: float = Field(..., description="Required/target score")
    gap_size: float = Field(..., description="Gap size (target - current)")
    gap_severity: GapSeverity = Field(..., description="Gap severity classification")
    development_priority: DevelopmentPriority = Field(..., description="Development priority")

    # Context and analysis
    is_blocking: bool = Field(default=False, description="Blocks advancement/role change")
    is_foundational: bool = Field(default=False, description="Foundational for other competencies")
    transferable_skills: list[SkillTransferability] = Field(
        default_factory=list, description="Skills that can help develop this competency"
    )

    # Development planning
    estimated_development_time: str = Field(..., description="Estimated time to close gap")
    development_difficulty: str = Field(..., description="Development difficulty level")
    recommended_activities: list[str] = Field(
        default_factory=list, description="Specific development activities"
    )
    learning_resources: list[str] = Field(
        default_factory=list, description="Recommended learning resources"
    )

    # Progress tracking
    milestone_targets: list[dict[str, Any]] = Field(
        default_factory=list, description="Intermediate milestone targets"
    )
    success_metrics: list[str] = Field(
        default_factory=list, description="Success measurement criteria"
    )


class DevelopmentRoadmap(BaseModel):
    """Comprehensive development roadmap"""

    user_id: str = Field(..., description="User identifier")
    target_role: str | None = Field(None, description="Target role (if applicable)")
    analysis_date: datetime = Field(default_factory=datetime.utcnow)

    # Gap analysis summary
    total_gaps: int = Field(..., description="Total number of competency gaps")
    critical_gaps: int = Field(..., description="Number of critical gaps")
    average_gap_size: float = Field(..., description="Average gap size across all competencies")
    development_complexity_score: float = Field(
        ..., description="Overall development complexity (0.0-1.0)"
    )

    # Individual gaps
    skill_gaps: list[SkillGap] = Field(
        default_factory=list, description="Individual competency gaps"
    )
    priority_gaps: list[SkillGap] = Field(default_factory=list, description="High-priority gaps")

    # Strategic recommendations
    development_strategy: str = Field(..., description="Overall development strategy")
    focus_areas: list[str] = Field(
        default_factory=list, description="Key focus areas for development"
    )
    timeline_estimate: str = Field(..., description="Overall development timeline")

    # Phased development plan
    immediate_actions: list[str] = Field(
        default_factory=list, description="Actions for next 30 days"
    )
    short_term_goals: list[str] = Field(default_factory=list, description="Goals for next 90 days")
    long_term_objectives: list[str] = Field(
        default_factory=list, description="Objectives for 6-12 months"
    )

    # Career guidance
    career_path_options: list[str] = Field(
        default_factory=list, description="Potential career paths"
    )
    role_readiness_score: float = Field(
        default=0.0, description="Readiness for target role (0.0-1.0)"
    )
    alternative_roles: list[dict[str, Any]] = Field(
        default_factory=list, description="Alternative role suggestions with fit scores"
    )


class GapAnalysisResult(BaseModel):
    """Complete gap analysis result"""

    user_id: str = Field(..., description="User identifier")
    analysis_type: str = Field(..., description="Type of analysis performed")
    reference_date: datetime = Field(default_factory=datetime.utcnow)

    # Analysis results
    roadmap: DevelopmentRoadmap = Field(..., description="Development roadmap")
    skill_transferability_map: dict[str, list[SkillTransferability]] = Field(
        default_factory=dict, description="Skill transferability analysis"
    )

    # Confidence and validation
    analysis_confidence: float = Field(..., description="Confidence in analysis (0.0-1.0)")
    data_quality_score: float = Field(..., description="Quality of input data (0.0-1.0)")
    recommendations_generated: int = Field(..., description="Number of recommendations generated")

    # Metadata
    analysis_parameters: dict[str, Any] = Field(
        default_factory=dict, description="Parameters used in analysis"
    )


class GapAnalyzer:
    """Competency gap analysis engine"""

    def __init__(self):
        self.logger = get_logger("assessment.gap_analyzer")
        self.level_calculator = get_level_calculator()

        # Skill transferability knowledge base
        self.skill_transfer_matrix = {
            "technical_skills": {
                "problem_solving": 0.8,
                "analytical_thinking": 0.7,
                "communication": 0.4,
                "project_management": 0.5,
            },
            "leadership": {
                "communication": 0.9,
                "project_management": 0.8,
                "decision_making": 0.8,
                "problem_solving": 0.6,
                "technical_skills": 0.3,
            },
            "communication": {
                "leadership": 0.7,
                "project_management": 0.6,
                "client_management": 0.8,
                "technical_skills": 0.4,
            },
            "project_management": {
                "leadership": 0.7,
                "communication": 0.6,
                "problem_solving": 0.6,
                "technical_skills": 0.5,
            },
        }

        # Development activity templates
        self.development_activities = {
            "technical_skills": [
                "Complete advanced technical training courses",
                "Lead complex technical projects",
                "Participate in code reviews and architecture discussions",
                "Contribute to open source projects",
                "Obtain relevant technical certifications",
            ],
            "leadership": [
                "Lead cross-functional project teams",
                "Mentor junior team members",
                "Complete leadership development programs",
                "Take on people management responsibilities",
                "Facilitate team meetings and decision-making sessions",
            ],
            "communication": [
                "Present to stakeholders and executives",
                "Write technical documentation and proposals",
                "Facilitate workshops and training sessions",
                "Lead client meetings and negotiations",
                "Participate in public speaking opportunities",
            ],
            "project_management": [
                "Manage end-to-end project delivery",
                "Implement project management methodologies",
                "Lead risk assessment and mitigation",
                "Coordinate with multiple stakeholders",
                "Obtain project management certifications (PMP, Agile)",
            ],
        }

    def analyze_competency_gaps(
        self,
        user_id: str,
        current_scores: dict[str, float],
        target_requirements: dict[str, float],
        user_context: dict[str, Any] | None = None,
        target_role: str | None = None,
    ) -> GapAnalysisResult:
        """Perform comprehensive competency gap analysis"""

        self.logger.info(f"Starting gap analysis for user {user_id}")

        # Calculate individual gaps
        skill_gaps = []
        for competency_id, target_score in target_requirements.items():
            current_score = current_scores.get(competency_id, 0.0)

            gap = self._analyze_single_gap(
                competency_id, current_score, target_score, user_context, target_role
            )
            skill_gaps.append(gap)

        # Sort gaps by priority and severity
        priority_gaps = [
            gap
            for gap in skill_gaps
            if gap.development_priority in [DevelopmentPriority.HIGH, DevelopmentPriority.MEDIUM]
        ]
        priority_gaps.sort(key=lambda x: (x.development_priority.value, -x.gap_size))

        # Create development roadmap
        roadmap = self._create_development_roadmap(
            user_id, skill_gaps, priority_gaps, user_context, target_role
        )

        # Analyze skill transferability
        transferability_map = self._analyze_skill_transferability(current_scores, skill_gaps)

        # Calculate overall metrics
        analysis_confidence = self._calculate_analysis_confidence(skill_gaps, user_context)
        data_quality_score = self._calculate_data_quality_score(current_scores, user_context)

        return GapAnalysisResult(
            user_id=user_id,
            analysis_type="comprehensive_gap_analysis",
            roadmap=roadmap,
            skill_transferability_map=transferability_map,
            analysis_confidence=analysis_confidence,
            data_quality_score=data_quality_score,
            recommendations_generated=len(
                [rec for gap in skill_gaps for rec in gap.recommended_activities]
            ),
            analysis_parameters={
                "target_role": target_role,
                "competencies_analyzed": len(target_requirements),
                "analysis_method": "gap_severity_prioritization",
            },
        )

    def analyze_role_readiness(
        self,
        user_id: str,
        current_scores: dict[str, float],
        target_role: str,
        role_requirements: dict[str, float],
        user_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Analyze readiness for a specific target role"""

        gap_analysis = self.analyze_competency_gaps(
            user_id, current_scores, role_requirements, user_context, target_role
        )

        # Calculate role readiness score
        total_gaps = len(gap_analysis.roadmap.skill_gaps)
        critical_gaps = gap_analysis.roadmap.critical_gaps

        if total_gaps == 0:
            readiness_score = 1.0
        else:
            # Base readiness on gap severity distribution
            minor_gaps = len(
                [g for g in gap_analysis.roadmap.skill_gaps if g.gap_severity == GapSeverity.MINOR]
            )
            moderate_gaps = len(
                [
                    g
                    for g in gap_analysis.roadmap.skill_gaps
                    if g.gap_severity == GapSeverity.MODERATE
                ]
            )
            major_gaps = len(
                [g for g in gap_analysis.roadmap.skill_gaps if g.gap_severity == GapSeverity.MAJOR]
            )

            readiness_score = max(
                0.0,
                1.0
                - (
                    critical_gaps * 0.4 + major_gaps * 0.2 + moderate_gaps * 0.1 + minor_gaps * 0.05
                ),
            )

        # Determine readiness category
        if readiness_score >= 0.9:
            readiness_category = "Ready"
        elif readiness_score >= 0.7:
            readiness_category = "Nearly Ready"
        elif readiness_score >= 0.5:
            readiness_category = "Developing"
        else:
            readiness_category = "Significant Development Needed"

        return {
            "user_id": user_id,
            "target_role": target_role,
            "readiness_score": readiness_score,
            "readiness_category": readiness_category,
            "critical_gaps": critical_gaps,
            "total_gaps": total_gaps,
            "estimated_development_time": gap_analysis.roadmap.timeline_estimate,
            "top_development_priorities": [
                gap.competency_name for gap in gap_analysis.roadmap.priority_gaps[:3]
            ],
            "gap_analysis": gap_analysis,
        }

    def generate_career_path_recommendations(
        self,
        user_id: str,
        current_scores: dict[str, float],
        available_roles: dict[str, dict[str, float]],  # role_name -> competency_requirements
        user_context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Generate career path recommendations based on competency fit"""

        role_recommendations = []

        for role_name, role_requirements in available_roles.items():
            # Analyze fit for this role
            readiness_analysis = self.analyze_role_readiness(
                user_id, current_scores, role_name, role_requirements, user_context
            )

            # Calculate additional metrics
            competency_overlap = self._calculate_competency_overlap(
                current_scores, role_requirements
            )
            development_effort = self._estimate_development_effort(
                readiness_analysis["gap_analysis"].roadmap.skill_gaps
            )

            role_recommendation = {
                "role_name": role_name,
                "readiness_score": readiness_analysis["readiness_score"],
                "readiness_category": readiness_analysis["readiness_category"],
                "competency_overlap": competency_overlap,
                "development_effort": development_effort,
                "critical_gaps": readiness_analysis["critical_gaps"],
                "estimated_timeline": readiness_analysis["estimated_development_time"],
                "fit_rationale": self._generate_fit_rationale(
                    current_scores, role_requirements, readiness_analysis
                ),
            }

            role_recommendations.append(role_recommendation)

        # Sort by readiness score and competency overlap
        role_recommendations.sort(
            key=lambda x: (x["readiness_score"] + x["competency_overlap"]) / 2, reverse=True
        )

        return role_recommendations

    def _analyze_single_gap(
        self,
        competency_id: str,
        current_score: float,
        target_score: float,
        user_context: dict[str, Any] | None,
        target_role: str | None,
    ) -> SkillGap:
        """Analyze a single competency gap"""

        gap_size = target_score - current_score

        # Determine gap severity
        if gap_size <= 0:
            gap_severity = GapSeverity.NONE
        elif gap_size < 0.5:
            gap_severity = GapSeverity.MINOR
        elif gap_size < 1.0:
            gap_severity = GapSeverity.MODERATE
        elif gap_size < 2.0:
            gap_severity = GapSeverity.MAJOR
        else:
            gap_severity = GapSeverity.CRITICAL

        # Determine development priority
        development_priority = self._determine_development_priority(
            gap_severity, competency_id, target_role
        )

        # Check if gap is blocking
        is_blocking = gap_severity in [GapSeverity.CRITICAL, GapSeverity.MAJOR]

        # Check if competency is foundational
        is_foundational = competency_id in ["technical_skills", "communication", "problem_solving"]

        # Get transferable skills
        transferable_skills = self._get_transferable_skills(competency_id)

        # Estimate development time and difficulty
        development_time = self._estimate_development_time(gap_size, gap_severity, competency_id)
        development_difficulty = self._assess_development_difficulty(competency_id, gap_size)

        # Generate recommendations and resources
        recommended_activities = self._generate_development_activities(competency_id, gap_severity)
        learning_resources = self._suggest_learning_resources(competency_id, gap_severity)

        # Create milestone targets
        milestone_targets = self._create_milestone_targets(
            current_score, target_score, development_time
        )

        # Define success metrics
        success_metrics = self._define_success_metrics(competency_id, target_score)

        return SkillGap(
            competency_id=competency_id,
            competency_name=competency_id.replace("_", " ").title(),
            current_score=current_score,
            target_score=target_score,
            gap_size=gap_size,
            gap_severity=gap_severity,
            development_priority=development_priority,
            is_blocking=is_blocking,
            is_foundational=is_foundational,
            transferable_skills=transferable_skills,
            estimated_development_time=development_time,
            development_difficulty=development_difficulty,
            recommended_activities=recommended_activities,
            learning_resources=learning_resources,
            milestone_targets=milestone_targets,
            success_metrics=success_metrics,
        )

    def _create_development_roadmap(
        self,
        user_id: str,
        skill_gaps: list[SkillGap],
        priority_gaps: list[SkillGap],
        user_context: dict[str, Any] | None,
        target_role: str | None,
    ) -> DevelopmentRoadmap:
        """Create comprehensive development roadmap"""

        # Calculate summary metrics
        total_gaps = len(skill_gaps)
        critical_gaps = len([g for g in skill_gaps if g.gap_severity == GapSeverity.CRITICAL])
        average_gap_size = sum(g.gap_size for g in skill_gaps) / max(total_gaps, 1)

        # Calculate development complexity
        complexity_factors = [
            len([g for g in skill_gaps if g.development_difficulty == "high"]) / max(total_gaps, 1),
            len([g for g in skill_gaps if g.is_blocking]) / max(total_gaps, 1),
            critical_gaps / max(total_gaps, 1),
        ]
        development_complexity_score = sum(complexity_factors) / len(complexity_factors)

        # Determine development strategy
        if critical_gaps > 0:
            development_strategy = "Critical Gap Closure"
        elif development_complexity_score > 0.6:
            development_strategy = "Structured Skill Building"
        else:
            development_strategy = "Continuous Improvement"

        # Identify focus areas
        focus_areas = [gap.competency_name for gap in priority_gaps[:3]]

        # Estimate overall timeline
        max_timeline_months = max(
            [self._parse_timeline_months(g.estimated_development_time) for g in skill_gaps],
            default=0,
        )
        timeline_estimate = self._format_timeline_estimate(max_timeline_months)

        # Generate phased action plan
        immediate_actions = self._generate_immediate_actions(priority_gaps[:2])
        short_term_goals = self._generate_short_term_goals(priority_gaps)
        long_term_objectives = self._generate_long_term_objectives(skill_gaps, target_role)

        # Career path analysis
        career_path_options = self._suggest_career_paths(skill_gaps, user_context)
        role_readiness_score = self._calculate_role_readiness_score(skill_gaps)
        alternative_roles = self._suggest_alternative_roles(skill_gaps, user_context)

        return DevelopmentRoadmap(
            user_id=user_id,
            target_role=target_role,
            total_gaps=total_gaps,
            critical_gaps=critical_gaps,
            average_gap_size=average_gap_size,
            development_complexity_score=development_complexity_score,
            skill_gaps=skill_gaps,
            priority_gaps=priority_gaps,
            development_strategy=development_strategy,
            focus_areas=focus_areas,
            timeline_estimate=timeline_estimate,
            immediate_actions=immediate_actions,
            short_term_goals=short_term_goals,
            long_term_objectives=long_term_objectives,
            career_path_options=career_path_options,
            role_readiness_score=role_readiness_score,
            alternative_roles=alternative_roles,
        )

    def _analyze_skill_transferability(
        self, current_scores: dict[str, float], skill_gaps: list[SkillGap]
    ) -> dict[str, list[SkillTransferability]]:
        """Analyze which current skills can help develop gap areas"""

        transferability_map = {}

        for gap in skill_gaps:
            transferable_skills = []

            for current_competency, current_score in current_scores.items():
                if current_score > 0 and current_competency != gap.competency_id:
                    transfer_score = self.skill_transfer_matrix.get(current_competency, {}).get(
                        gap.competency_id, 0.0
                    )

                    if transfer_score > 0.3:  # Meaningful transferability
                        transferable_skill = SkillTransferability(
                            source_competency=current_competency,
                            target_competency=gap.competency_id,
                            transferability_score=transfer_score,
                            transfer_rationale=f"{current_competency.replace('_', ' ').title()} skills enhance {gap.competency_name} development",
                            development_multiplier=1.0
                            + (transfer_score * 0.3),  # Up to 30% faster development
                        )
                        transferable_skills.append(transferable_skill)

            # Sort by transferability score
            transferable_skills.sort(key=lambda x: x.transferability_score, reverse=True)
            transferability_map[gap.competency_id] = transferable_skills[:3]  # Top 3

        return transferability_map

    def _determine_development_priority(
        self, gap_severity: GapSeverity, competency_id: str, target_role: str | None
    ) -> DevelopmentPriority:
        """Determine development priority for a competency gap"""

        if gap_severity == GapSeverity.CRITICAL:
            return DevelopmentPriority.HIGH
        elif gap_severity == GapSeverity.MAJOR:
            return DevelopmentPriority.HIGH
        elif gap_severity == GapSeverity.MODERATE:
            # Check if it's a foundational skill
            if competency_id in ["technical_skills", "communication"]:
                return DevelopmentPriority.HIGH
            else:
                return DevelopmentPriority.MEDIUM
        elif gap_severity == GapSeverity.MINOR:
            return DevelopmentPriority.LOW
        else:
            return DevelopmentPriority.OPTIONAL

    def _get_transferable_skills(self, competency_id: str) -> list[SkillTransferability]:
        """Get skills that can transfer to help develop this competency"""
        transferable = []

        for source_comp, targets in self.skill_transfer_matrix.items():
            if competency_id in targets:
                transfer_score = targets[competency_id]
                transferable.append(
                    SkillTransferability(
                        source_competency=source_comp,
                        target_competency=competency_id,
                        transferability_score=transfer_score,
                        transfer_rationale=f"{source_comp.replace('_', ' ').title()} experience accelerates {competency_id.replace('_', ' ').title()} development",
                        development_multiplier=1.0 + (transfer_score * 0.2),
                    )
                )

        return sorted(transferable, key=lambda x: x.transferability_score, reverse=True)

    def _estimate_development_time(
        self, gap_size: float, gap_severity: GapSeverity, competency_id: str
    ) -> str:
        """Estimate time needed to close competency gap"""

        base_months = gap_size * 3  # Base: 3 months per point

        # Adjust for competency type
        difficulty_multipliers = {
            "technical_skills": 1.2,
            "leadership": 1.5,
            "communication": 1.0,
            "project_management": 1.3,
        }

        multiplier = difficulty_multipliers.get(competency_id, 1.1)
        estimated_months = base_months * multiplier

        if estimated_months < 1:
            return "< 1 month"
        elif estimated_months < 3:
            return "1-3 months"
        elif estimated_months < 6:
            return "3-6 months"
        elif estimated_months < 12:
            return "6-12 months"
        else:
            return "12+ months"

    def _assess_development_difficulty(self, competency_id: str, gap_size: float) -> str:
        """Assess difficulty of developing this competency"""

        base_difficulty = {
            "technical_skills": "medium",
            "leadership": "high",
            "communication": "medium",
            "project_management": "medium",
            "problem_solving": "high",
        }.get(competency_id, "medium")

        # Adjust for gap size
        if gap_size > 2.0:
            if base_difficulty == "medium":
                return "high"
            elif base_difficulty == "low":
                return "medium"

        return base_difficulty

    def _generate_development_activities(
        self, competency_id: str, gap_severity: GapSeverity
    ) -> list[str]:
        """Generate specific development activities"""

        base_activities = self.development_activities.get(
            competency_id,
            [
                f"Seek opportunities to practice {competency_id.replace('_', ' ')}",
                f"Find a mentor with strong {competency_id.replace('_', ' ')} skills",
                f"Take courses or training in {competency_id.replace('_', ' ')}",
            ],
        )

        # Adjust recommendations based on gap severity
        if gap_severity in [GapSeverity.CRITICAL, GapSeverity.MAJOR]:
            return base_activities[:4]  # More comprehensive recommendations
        else:
            return base_activities[:2]  # Focus on key activities

    def _suggest_learning_resources(
        self, competency_id: str, gap_severity: GapSeverity
    ) -> list[str]:
        """Suggest learning resources for competency development"""

        resource_templates = {
            "technical_skills": [
                "Advanced technical training programs",
                "Industry certifications and credentials",
                "Technical conferences and workshops",
                "Online coding platforms and challenges",
            ],
            "leadership": [
                "Leadership development programs",
                "Executive coaching sessions",
                "Management training courses",
                "Leadership books and case studies",
            ],
            "communication": [
                "Public speaking courses (Toastmasters)",
                "Business writing workshops",
                "Presentation skills training",
                "Communication coaching",
            ],
        }

        return resource_templates.get(
            competency_id,
            [
                f"Professional development courses in {competency_id.replace('_', ' ')}",
                f"Industry resources and best practices for {competency_id.replace('_', ' ')}",
            ],
        )

    def _create_milestone_targets(
        self, current_score: float, target_score: float, timeline: str
    ) -> list[dict[str, Any]]:
        """Create intermediate milestone targets"""

        gap = target_score - current_score
        if gap <= 0:
            return []

        milestones = []

        # Create 2-3 intermediate milestones
        if gap > 1.0:
            milestone1 = current_score + (gap * 0.33)
            milestone2 = current_score + (gap * 0.67)

            milestones = [
                {
                    "target_score": round(milestone1, 1),
                    "timeline": "30% progress",
                    "description": f"Reach {milestone1:.1f} points",
                },
                {
                    "target_score": round(milestone2, 1),
                    "timeline": "67% progress",
                    "description": f"Reach {milestone2:.1f} points",
                },
                {
                    "target_score": target_score,
                    "timeline": "100% complete",
                    "description": f"Reach target of {target_score} points",
                },
            ]
        else:
            milestones = [
                {
                    "target_score": target_score,
                    "timeline": "Complete",
                    "description": f"Reach target of {target_score} points",
                }
            ]

        return milestones

    def _define_success_metrics(self, competency_id: str, target_score: float) -> list[str]:
        """Define success measurement criteria"""

        return [
            f"Achieve competency score of {target_score}",
            f"Demonstrate {competency_id.replace('_', ' ')} in real work situations",
            f"Receive positive feedback on {competency_id.replace('_', ' ')} performance",
            f"Successfully complete {competency_id.replace('_', ' ')}-related projects",
        ]

    def _parse_timeline_months(self, timeline_str: str) -> int:
        """Parse timeline string to months"""
        if "month" in timeline_str:
            if "< 1" in timeline_str:
                return 1
            elif "1-3" in timeline_str:
                return 3
            elif "3-6" in timeline_str:
                return 6
            elif "6-12" in timeline_str:
                return 12
            elif "12+" in timeline_str:
                return 18
        return 6  # Default

    def _format_timeline_estimate(self, months: int) -> str:
        """Format timeline estimate"""
        if months < 1:
            return "< 1 month"
        elif months <= 3:
            return "1-3 months"
        elif months <= 6:
            return "3-6 months"
        elif months <= 12:
            return "6-12 months"
        else:
            return "12+ months"

    def _generate_immediate_actions(self, priority_gaps: list[SkillGap]) -> list[str]:
        """Generate immediate actions for next 30 days"""
        actions = []
        for gap in priority_gaps[:2]:  # Focus on top 2 priorities
            if gap.recommended_activities:
                actions.append(f"Start: {gap.recommended_activities[0]}")
        return actions

    def _generate_short_term_goals(self, priority_gaps: list[SkillGap]) -> list[str]:
        """Generate short-term goals for next 90 days"""
        goals = []
        for gap in priority_gaps[:3]:
            if gap.milestone_targets:
                goals.append(f"{gap.competency_name}: {gap.milestone_targets[0]['description']}")
        return goals

    def _generate_long_term_objectives(
        self, skill_gaps: list[SkillGap], target_role: str | None
    ) -> list[str]:
        """Generate long-term objectives for 6-12 months"""
        objectives = []

        # Major competency objectives
        major_gaps = [
            g for g in skill_gaps if g.gap_severity in [GapSeverity.CRITICAL, GapSeverity.MAJOR]
        ]
        for gap in major_gaps[:3]:
            objectives.append(f"Close {gap.competency_name} gap to reach target level")

        # Role-specific objective
        if target_role:
            objectives.append(f"Achieve readiness for {target_role} position")

        return objectives

    def _suggest_career_paths(
        self, skill_gaps: list[SkillGap], user_context: dict[str, Any] | None
    ) -> list[str]:
        """Suggest potential career paths based on gap analysis"""

        # Analyze competency strengths and gaps to suggest paths
        strong_areas = [g.competency_name for g in skill_gaps if g.gap_size <= 0]

        path_suggestions = []
        if "Leadership" in strong_areas:
            path_suggestions.append("Management/Leadership track")
        if "Technical Skills" in strong_areas:
            path_suggestions.append("Senior technical contributor track")
        if len(strong_areas) > 2:
            path_suggestions.append("Cross-functional specialist role")

        return path_suggestions or ["Individual contributor advancement"]

    def _calculate_role_readiness_score(self, skill_gaps: list[SkillGap]) -> float:
        """Calculate overall role readiness score"""
        if not skill_gaps:
            return 1.0

        # Weight gaps by severity
        severity_weights = {
            GapSeverity.CRITICAL: 0.4,
            GapSeverity.MAJOR: 0.2,
            GapSeverity.MODERATE: 0.1,
            GapSeverity.MINOR: 0.05,
            GapSeverity.NONE: 0.0,
        }

        total_penalty = sum(severity_weights.get(gap.gap_severity, 0) for gap in skill_gaps)
        return max(0.0, 1.0 - total_penalty)

    def _suggest_alternative_roles(
        self, skill_gaps: list[SkillGap], user_context: dict[str, Any] | None
    ) -> list[dict[str, Any]]:
        """Suggest alternative roles that might be better fits"""

        # This is a simplified implementation
        # In practice, would analyze role databases and competency requirements

        alternatives = []

        # Suggest roles based on lowest gap areas
        low_gap_competencies = [
            g.competency_id
            for g in skill_gaps
            if g.gap_severity in [GapSeverity.MINOR, GapSeverity.NONE]
        ]

        if "technical_skills" in low_gap_competencies:
            alternatives.append(
                {
                    "role": "Senior Technical Specialist",
                    "fit_score": 0.8,
                    "rationale": "Strong technical skills with minimal development needed",
                }
            )

        if "communication" in low_gap_competencies:
            alternatives.append(
                {
                    "role": "Technical Consultant",
                    "fit_score": 0.7,
                    "rationale": "Communication strengths enable client-facing technical role",
                }
            )

        return alternatives

    def _calculate_analysis_confidence(
        self, skill_gaps: list[SkillGap], user_context: dict[str, Any] | None
    ) -> float:
        """Calculate confidence in the gap analysis"""

        confidence_factors = []

        # Data completeness
        if user_context:
            context_completeness = (
                len([k for k in ["role", "experience_years", "team_size"] if k in user_context]) / 3
            )
            confidence_factors.append(context_completeness)
        else:
            confidence_factors.append(0.5)  # Default moderate confidence

        # Number of competencies analyzed
        competency_coverage = min(1.0, len(skill_gaps) / 5)  # Ideal: 5+ competencies
        confidence_factors.append(competency_coverage)

        # Gap distribution (more balanced distribution = higher confidence)
        if skill_gaps:
            severity_distribution = len({g.gap_severity for g in skill_gaps}) / len(GapSeverity)
            confidence_factors.append(severity_distribution)
        else:
            confidence_factors.append(0.5)

        return sum(confidence_factors) / len(confidence_factors)

    def _calculate_data_quality_score(
        self, current_scores: dict[str, float], user_context: dict[str, Any] | None
    ) -> float:
        """Calculate quality score for input data"""

        quality_factors = []

        # Score completeness (all scores > 0 indicates good data)
        if current_scores:
            score_completeness = len([s for s in current_scores.values() if s > 0]) / len(
                current_scores
            )
            quality_factors.append(score_completeness)
        else:
            quality_factors.append(0.0)

        # Context richness
        if user_context:
            context_richness = min(1.0, len(user_context) / 5)  # More context = better quality
            quality_factors.append(context_richness)
        else:
            quality_factors.append(0.3)

        # Score distribution (avoid all zeros or all identical scores)
        if current_scores:
            unique_scores = len(set(current_scores.values()))
            score_variance = min(1.0, unique_scores / max(len(current_scores), 1))
            quality_factors.append(score_variance)
        else:
            quality_factors.append(0.0)

        return sum(quality_factors) / len(quality_factors)

    def _calculate_competency_overlap(
        self, current_scores: dict[str, float], requirements: dict[str, float]
    ) -> float:
        """Calculate overlap between current competencies and role requirements"""

        common_competencies = set(current_scores.keys()) & set(requirements.keys())
        if not common_competencies:
            return 0.0

        overlap_score = len(common_competencies) / len(requirements)
        return overlap_score

    def _estimate_development_effort(self, skill_gaps: list[SkillGap]) -> str:
        """Estimate overall development effort"""

        if not skill_gaps:
            return "minimal"

        effort_scores = {"low": 1, "medium": 2, "high": 3}

        total_effort = sum(
            effort_scores.get(gap.development_difficulty, 2) * gap.gap_size for gap in skill_gaps
        )
        average_effort = total_effort / len(skill_gaps)

        if average_effort < 2:
            return "low"
        elif average_effort < 4:
            return "medium"
        else:
            return "high"

    def _generate_fit_rationale(
        self,
        current_scores: dict[str, float],
        role_requirements: dict[str, float],
        readiness_analysis: dict[str, Any],
    ) -> str:
        """Generate rationale for role fit assessment"""

        readiness_score = readiness_analysis["readiness_score"]

        if readiness_score >= 0.9:
            return "Excellent fit - meets or exceeds most role requirements"
        elif readiness_score >= 0.7:
            return "Good fit - minor development needed in a few areas"
        elif readiness_score >= 0.5:
            return "Moderate fit - focused development required"
        else:
            return "Significant development needed - consider alternative paths"


# Global analyzer instance
_global_analyzer: GapAnalyzer | None = None


def get_gap_analyzer() -> GapAnalyzer:
    """Get global gap analyzer instance"""
    global _global_analyzer
    if _global_analyzer is None:
        _global_analyzer = GapAnalyzer()
    return _global_analyzer
