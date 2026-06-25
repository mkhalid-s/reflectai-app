"""
Growth Engine for ReflectAI
Handles career growth planning, progression tracking, and development recommendations.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

import numpy as np

from src.shared.error_handlers import handle_errors
from src.shared.exceptions import ErrorCategory
from src.shared.logging import get_logger

logger = get_logger(__name__)


class GrowthStage(Enum):
    """Career growth stages."""

    EXPLORATION = "exploration"
    FOUNDATION = "foundation"
    ADVANCEMENT = "advancement"
    EXPERTISE = "expertise"
    LEADERSHIP = "leadership"
    MASTERY = "mastery"


@dataclass
class GrowthMetrics:
    """Metrics for tracking growth."""

    user_id: str
    current_stage: GrowthStage
    growth_velocity: float  # Rate of progression
    momentum_score: float  # Current momentum
    trajectory: str  # "accelerating", "steady", "plateauing", "declining"
    time_in_stage: timedelta
    achievements: list[dict[str, Any]]
    milestones_completed: int
    next_milestone: str | None
    estimated_next_stage: timedelta | None


@dataclass
class CareerPath:
    """Represents a career path."""

    path_id: str
    title: str
    description: str
    stages: list[str]
    required_competencies: dict[str, int]  # competency: required_level
    typical_duration: timedelta
    next_roles: list[str]
    success_metrics: dict[str, float]


@dataclass
class DevelopmentRecommendation:
    """Development recommendation."""

    recommendation_id: str
    type: str  # "skill", "experience", "certification", "project", "mentorship"
    title: str
    description: str
    priority: int  # 1-5
    effort_hours: int
    expected_impact: float  # 0-1
    resources: list[str]
    deadline: datetime | None = None


class GrowthEngine:
    """
    Engine for managing career growth and development.

    Features:
    - Growth stage assessment
    - Career path optimization
    - Milestone tracking
    - Personalized recommendations
    - Growth velocity calculation
    """

    def __init__(self):
        self.growth_stages = self._initialize_growth_stages()
        self.career_paths = self._load_career_paths()
        self.milestone_templates = self._load_milestone_templates()

        logger.info("Growth Engine initialized")

    def _initialize_growth_stages(self) -> dict[GrowthStage, dict]:
        """Initialize growth stage definitions."""
        return {
            GrowthStage.EXPLORATION: {
                "duration_months": 6,
                "focus": "discovering strengths and interests",
                "key_activities": ["learning", "experimenting", "networking"],
            },
            GrowthStage.FOUNDATION: {
                "duration_months": 12,
                "focus": "building core competencies",
                "key_activities": ["skill development", "project work", "mentorship"],
            },
            GrowthStage.ADVANCEMENT: {
                "duration_months": 18,
                "focus": "deepening expertise",
                "key_activities": ["specialization", "leadership", "innovation"],
            },
            GrowthStage.EXPERTISE: {
                "duration_months": 24,
                "focus": "becoming domain expert",
                "key_activities": ["thought leadership", "mentoring", "strategy"],
            },
            GrowthStage.LEADERSHIP: {
                "duration_months": 36,
                "focus": "leading teams and initiatives",
                "key_activities": ["team building", "vision setting", "execution"],
            },
            GrowthStage.MASTERY: {
                "duration_months": None,
                "focus": "industry leadership",
                "key_activities": ["innovation", "transformation", "legacy building"],
            },
        }

    def _load_career_paths(self) -> list[CareerPath]:
        """Load career path definitions."""
        return [
            CareerPath(
                path_id="tech_ic",
                title="Technical Individual Contributor",
                description="Deep technical expertise path",
                stages=["Junior", "Mid", "Senior", "Staff", "Principal", "Distinguished"],
                required_competencies={
                    "technical.programming": 5,
                    "technical.architecture": 4,
                    "technical.data": 3,
                },
                typical_duration=timedelta(days=365 * 8),
                next_roles=["Staff Engineer", "Principal Engineer", "Architect"],
                success_metrics={"technical_depth": 0.9, "innovation": 0.7},
            ),
            CareerPath(
                path_id="tech_lead",
                title="Technical Leadership",
                description="Technical leadership and people management",
                stages=["Senior", "Lead", "Manager", "Director", "VP"],
                required_competencies={
                    "technical.programming": 4,
                    "leadership.team_management": 5,
                    "leadership.communication": 4,
                },
                typical_duration=timedelta(days=365 * 10),
                next_roles=["Engineering Manager", "Director", "VP Engineering"],
                success_metrics={"team_success": 0.8, "technical_vision": 0.7},
            ),
            CareerPath(
                path_id="product",
                title="Product Management",
                description="Product strategy and execution",
                stages=["Associate", "PM", "Senior PM", "Principal PM", "Director"],
                required_competencies={
                    "business.product": 5,
                    "business.domain_knowledge": 4,
                    "leadership.strategic_thinking": 4,
                },
                typical_duration=timedelta(days=365 * 8),
                next_roles=["Senior PM", "Director of Product", "VP Product"],
                success_metrics={"product_success": 0.8, "user_satisfaction": 0.8},
            ),
        ]

    def _load_milestone_templates(self) -> dict[str, list[dict]]:
        """Load milestone templates for different paths."""
        return {
            "tech_ic": [
                {"name": "First Production Deploy", "stage": "Junior", "impact": 0.3},
                {"name": "Lead Feature Development", "stage": "Mid", "impact": 0.5},
                {"name": "System Architecture Design", "stage": "Senior", "impact": 0.7},
                {"name": "Technical Innovation", "stage": "Staff", "impact": 0.9},
            ],
            "tech_lead": [
                {"name": "First Team Lead Role", "stage": "Lead", "impact": 0.6},
                {"name": "Successful Team Delivery", "stage": "Manager", "impact": 0.7},
                {"name": "Cross-team Initiative", "stage": "Director", "impact": 0.8},
                {"name": "Organizational Impact", "stage": "VP", "impact": 0.9},
            ],
        }

    @handle_errors(category=ErrorCategory.BUSINESS_RULE_ERROR)
    async def assess_growth_stage(
        self,
        user_id: str,
        competencies: dict[str, float],
        experience_months: int,
        achievements: list[dict[str, Any]],
    ) -> GrowthMetrics:
        """
        Assess current growth stage and metrics.

        Args:
            user_id: User identifier
            competencies: Current competency scores
            experience_months: Months of experience
            achievements: List of achievements

        Returns:
            Growth metrics
        """
        try:
            # Determine current stage
            current_stage = self._determine_growth_stage(
                competencies, experience_months, achievements
            )

            # Calculate growth velocity
            growth_velocity = await self._calculate_growth_velocity(
                user_id, competencies, achievements
            )

            # Calculate momentum
            momentum_score = self._calculate_momentum(growth_velocity, achievements, competencies)

            # Determine trajectory
            trajectory = self._determine_trajectory(growth_velocity, momentum_score)

            # Calculate time in stage
            time_in_stage = self._calculate_time_in_stage(user_id, current_stage)

            # Identify next milestone
            next_milestone = self._identify_next_milestone(
                current_stage, achievements, competencies
            )

            # Estimate time to next stage
            estimated_next = self._estimate_next_stage_timeline(
                current_stage, growth_velocity, competencies
            )

            # Count completed milestones
            milestones_completed = len([a for a in achievements if a.get("is_milestone")])

            return GrowthMetrics(
                user_id=user_id,
                current_stage=current_stage,
                growth_velocity=growth_velocity,
                momentum_score=momentum_score,
                trajectory=trajectory,
                time_in_stage=time_in_stage,
                achievements=achievements[:5],  # Recent 5
                milestones_completed=milestones_completed,
                next_milestone=next_milestone,
                estimated_next_stage=estimated_next,
            )

        except Exception as e:
            logger.error(f"Failed to assess growth stage: {e}")
            raise

    def _determine_growth_stage(
        self, competencies: dict[str, float], experience_months: int, achievements: list[dict]
    ) -> GrowthStage:
        """Determine current growth stage."""
        avg_competency = np.mean(list(competencies.values())) if competencies else 0
        achievement_count = len(achievements)

        # Simple heuristic (would be ML model in production)
        if experience_months < 6:
            return GrowthStage.EXPLORATION
        elif experience_months < 24 and avg_competency < 40:
            return GrowthStage.FOUNDATION
        elif experience_months < 48 and avg_competency < 60:
            return GrowthStage.ADVANCEMENT
        elif experience_months < 72 and avg_competency < 80:
            return GrowthStage.EXPERTISE
        elif achievement_count > 20 and avg_competency >= 80:
            return GrowthStage.LEADERSHIP
        elif avg_competency >= 90:
            return GrowthStage.MASTERY
        else:
            return GrowthStage.ADVANCEMENT

    async def _calculate_growth_velocity(
        self, user_id: str, competencies: dict[str, float], achievements: list[dict]
    ) -> float:
        """Calculate growth velocity (rate of progression)."""
        # Simplified calculation
        # In production, would compare with historical data

        base_velocity = 1.0

        # Adjust based on competency improvement
        avg_competency = np.mean(list(competencies.values())) if competencies else 0
        if avg_competency > 70:
            base_velocity *= 1.3
        elif avg_competency > 50:
            base_velocity *= 1.1

        # Adjust based on recent achievements
        recent_achievements = len(
            [
                a
                for a in achievements
                if (datetime.now(UTC) - a.get("date", datetime.now(UTC))).days < 90
            ]
        )
        if recent_achievements > 5:
            base_velocity *= 1.2
        elif recent_achievements > 2:
            base_velocity *= 1.1

        return min(base_velocity, 2.0)  # Cap at 2x

    def _calculate_momentum(
        self, growth_velocity: float, achievements: list[dict], competencies: dict[str, float]
    ) -> float:
        """Calculate current momentum score."""
        # Momentum = velocity * mass (where mass is competency depth)
        mass = np.mean(list(competencies.values())) / 100 if competencies else 0.5
        base_momentum = growth_velocity * mass

        # Boost for recent achievements
        recent_boost = min(len(achievements) / 10, 0.3)

        return min(base_momentum + recent_boost, 1.0)

    def _determine_trajectory(self, velocity: float, momentum: float) -> str:
        """Determine growth trajectory."""
        if velocity > 1.5 and momentum > 0.7:
            return "accelerating"
        elif velocity > 1.0 and momentum > 0.5:
            return "steady"
        elif velocity < 0.8 or momentum < 0.3:
            return "declining"
        else:
            return "plateauing"

    def _calculate_time_in_stage(self, user_id: str, stage: GrowthStage) -> timedelta:
        """Calculate time spent in current stage."""
        # Simplified - would query historical data in production
        return timedelta(days=180)  # 6 months default

    def _identify_next_milestone(
        self, stage: GrowthStage, achievements: list[dict], competencies: dict[str, float]
    ) -> str | None:
        """Identify next milestone to achieve."""
        stage_milestones = {
            GrowthStage.FOUNDATION: "Complete core skill certification",
            GrowthStage.ADVANCEMENT: "Lead a major project",
            GrowthStage.EXPERTISE: "Become recognized expert in domain",
            GrowthStage.LEADERSHIP: "Build and lead high-performing team",
            GrowthStage.MASTERY: "Drive organizational transformation",
        }

        return stage_milestones.get(stage, "Continue skill development")

    def _estimate_next_stage_timeline(
        self, current_stage: GrowthStage, velocity: float, competencies: dict[str, float]
    ) -> timedelta | None:
        """Estimate time to reach next stage."""
        stage_duration = self.growth_stages[current_stage].get("duration_months")

        if not stage_duration:
            return None

        # Adjust based on velocity
        adjusted_months = stage_duration / velocity

        return timedelta(days=int(adjusted_months * 30))

    async def recommend_career_path(
        self, user_id: str, competencies: dict[str, float], interests: list[str], goals: list[str]
    ) -> list[CareerPath]:
        """
        Recommend suitable career paths.

        Args:
            user_id: User identifier
            competencies: Current competencies
            interests: User interests
            goals: Career goals

        Returns:
            Ranked list of career paths
        """
        scored_paths = []

        for path in self.career_paths:
            score = await self._score_career_path(path, competencies, interests, goals)
            scored_paths.append((path, score))

        # Sort by score
        scored_paths.sort(key=lambda x: x[1], reverse=True)

        return [path for path, _ in scored_paths[:3]]  # Top 3

    async def _score_career_path(
        self,
        path: CareerPath,
        competencies: dict[str, float],
        interests: list[str],
        goals: list[str],
    ) -> float:
        """Score a career path based on fit."""
        score = 0.0

        # Competency alignment
        for req_comp, req_level in path.required_competencies.items():
            if req_comp in competencies:
                alignment = 1.0 - abs(competencies[req_comp] - req_level * 20) / 100
                score += alignment * 0.4

        # Interest alignment
        path_keywords = path.title.lower().split() + path.description.lower().split()
        interest_match = sum(
            1
            for interest in interests
            if any(keyword in interest.lower() for keyword in path_keywords)
        )
        score += min(interest_match / 3, 1.0) * 0.3

        # Goal alignment
        goal_match = sum(1 for goal in goals if any(role in goal for role in path.next_roles))
        score += min(goal_match / 2, 1.0) * 0.3

        return score

    async def generate_development_recommendations(
        self,
        user_id: str,
        growth_metrics: GrowthMetrics,
        competency_gaps: list[dict],
        career_path: CareerPath | None = None,
    ) -> list[DevelopmentRecommendation]:
        """
        Generate personalized development recommendations.

        Args:
            user_id: User identifier
            growth_metrics: Current growth metrics
            competency_gaps: Identified competency gaps
            career_path: Selected career path

        Returns:
            List of development recommendations
        """
        recommendations = []

        # Stage-specific recommendations
        stage_recs = self._get_stage_recommendations(growth_metrics.current_stage)
        recommendations.extend(stage_recs)

        # Gap-based recommendations
        for gap in competency_gaps[:3]:  # Top 3 gaps
            gap_recs = self._get_gap_recommendations(gap)
            recommendations.extend(gap_recs)

        # Path-specific recommendations
        if career_path:
            path_recs = self._get_path_recommendations(career_path, growth_metrics)
            recommendations.extend(path_recs)

        # Trajectory-based recommendations
        if growth_metrics.trajectory == "plateauing":
            recommendations.append(
                DevelopmentRecommendation(
                    recommendation_id="stretch_assignment",
                    type="experience",
                    title="Take on stretch assignment",
                    description="Challenge yourself with project outside comfort zone",
                    priority=5,
                    effort_hours=80,
                    expected_impact=0.8,
                    resources=["Manager discussion", "Project proposals"],
                )
            )

        # Sort by priority and impact
        recommendations.sort(key=lambda r: (r.priority, r.expected_impact), reverse=True)

        return recommendations[:5]  # Top 5

    def _get_stage_recommendations(self, stage: GrowthStage) -> list[DevelopmentRecommendation]:
        """Get stage-specific recommendations."""
        stage_recs = {
            GrowthStage.FOUNDATION: [
                DevelopmentRecommendation(
                    recommendation_id="core_skills",
                    type="skill",
                    title="Master core technical skills",
                    description="Build strong foundation in programming and tools",
                    priority=5,
                    effort_hours=200,
                    expected_impact=0.9,
                    resources=["Online courses", "Practice projects", "Mentorship"],
                )
            ],
            GrowthStage.ADVANCEMENT: [
                DevelopmentRecommendation(
                    recommendation_id="specialization",
                    type="skill",
                    title="Develop specialization",
                    description="Deep dive into specific technical domain",
                    priority=4,
                    effort_hours=150,
                    expected_impact=0.8,
                    resources=["Advanced courses", "Conferences", "Research papers"],
                )
            ],
            GrowthStage.EXPERTISE: [
                DevelopmentRecommendation(
                    recommendation_id="thought_leadership",
                    type="experience",
                    title="Establish thought leadership",
                    description="Share expertise through writing and speaking",
                    priority=4,
                    effort_hours=100,
                    expected_impact=0.7,
                    resources=["Blog platform", "Conference CFPs", "Social media"],
                )
            ],
        }

        return stage_recs.get(stage, [])

    def _get_gap_recommendations(self, gap: dict) -> list[DevelopmentRecommendation]:
        """Get recommendations for closing competency gap."""
        return [
            DevelopmentRecommendation(
                recommendation_id=f"close_gap_{gap.get('competency', 'unknown')}",
                type="skill",
                title=f"Improve {gap.get('competency', 'skill')}",
                description=f"Focus on closing gap in {gap.get('competency', 'area')}",
                priority=4,
                effort_hours=80,
                expected_impact=0.7,
                resources=gap.get("recommended_actions", []),
            )
        ]

    def _get_path_recommendations(
        self, path: CareerPath, metrics: GrowthMetrics
    ) -> list[DevelopmentRecommendation]:
        """Get career path specific recommendations."""
        return [
            DevelopmentRecommendation(
                recommendation_id=f"path_{path.path_id}",
                type="experience",
                title=f"Gain experience for {path.next_roles[0]}",
                description=f"Build experience required for {path.title} progression",
                priority=3,
                effort_hours=120,
                expected_impact=0.6,
                resources=["Role shadowing", "Stretch projects", "Cross-training"],
            )
        ]

    def calculate_growth_score(self, metrics: GrowthMetrics) -> float:
        """Calculate overall growth score."""
        score = 0.0

        # Velocity component (30%)
        score += min(metrics.growth_velocity / 2.0, 0.3) * 100

        # Momentum component (30%)
        score += metrics.momentum_score * 30

        # Achievement component (20%)
        achievement_score = min(metrics.milestones_completed / 10, 1.0)
        score += achievement_score * 20

        # Trajectory component (20%)
        trajectory_scores = {"accelerating": 20, "steady": 15, "plateauing": 10, "declining": 5}
        score += trajectory_scores.get(metrics.trajectory, 10)

        return min(score, 100)
