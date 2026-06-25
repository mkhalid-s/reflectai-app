"""
Advanced Analytics Engine

Provides sophisticated analytics capabilities for competency and career insights.
"""

import statistics
from dataclasses import dataclass
from enum import Enum
from typing import Any

from src.infrastructure.cache.redis_manager import RedisManager
from src.infrastructure.database.db_manager import DatabaseManager
from src.shared import get_logger

logger = get_logger(__name__)


class AnalyticsTimeframe(Enum):
    """Analytics timeframe options."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class TrendDirection(Enum):
    """Trend direction indicators."""

    STRONG_UP = "strong_up"
    UP = "up"
    STABLE = "stable"
    DOWN = "down"
    STRONG_DOWN = "strong_down"


@dataclass
class CompetencyTrend:
    """Competency trend analysis result."""

    competency_name: str
    current_score: float
    previous_score: float
    change_percentage: float
    trend_direction: TrendDirection
    projection_30_days: float
    confidence_score: float


@dataclass
class ActivityPattern:
    """Activity pattern analysis result."""

    pattern_type: str
    frequency: int
    peak_times: list[str]
    associated_competencies: list[str]
    impact_score: float


@dataclass
class PeerComparison:
    """Peer comparison analysis result."""

    competency_name: str
    user_score: float
    peer_average: float
    percentile: int
    top_performers: list[dict[str, Any]]


@dataclass
class CareerPathAnalysis:
    """Career path analysis result."""

    current_level: str
    next_level: str
    gap_analysis: dict[str, float]
    recommended_focus_areas: list[str]
    estimated_time_to_next_level: int  # days
    milestone_progress: dict[str, float]


class AdvancedAnalyticsEngine:
    """
    Provides advanced analytics for competency and career insights.

    Features:
    - Trend analysis with projections
    - Activity pattern recognition
    - Peer comparison and benchmarking
    - Career path optimization
    - Predictive analytics
    """

    def __init__(self, postgres_manager: DatabaseManager, redis_manager: RedisManager):
        self.postgres = postgres_manager
        self.redis = redis_manager
        self.logger = get_logger(__name__)

        # Configuration
        self.cache_ttl = 3600  # 1 hour
        self.min_data_points = 5
        self.confidence_threshold = 0.7

    async def analyze_competency_trends(
        self,
        user_id: str,
        timeframe: AnalyticsTimeframe = AnalyticsTimeframe.MONTHLY,
        competencies: list[str] | None = None,
    ) -> list[CompetencyTrend]:
        """
        Analyze competency trends over time.

        Args:
            user_id: User ID
            timeframe: Analysis timeframe
            competencies: Specific competencies to analyze (all if None)

        Returns:
            List of competency trends
        """
        cache_key = f"analytics:trends:{user_id}:{timeframe.value}"
        cached = await self.redis.get(cache_key)
        if cached:
            return [self._deserialize_trend(t) for t in cached]

        # Get historical competency scores
        history = await self._get_competency_history(user_id, timeframe)

        trends = []
        for comp_name, scores in history.items():
            if competencies and comp_name not in competencies:
                continue

            if len(scores) < self.min_data_points:
                continue

            # Calculate trend
            current = scores[-1]
            previous = scores[-2] if len(scores) > 1 else current
            change = ((current - previous) / max(previous, 0.01)) * 100

            # Determine trend direction
            direction = self._calculate_trend_direction(scores)

            # Project future score
            projection = self._project_score(scores, 30)

            # Calculate confidence
            confidence = self._calculate_confidence(scores)

            trends.append(
                CompetencyTrend(
                    competency_name=comp_name,
                    current_score=current,
                    previous_score=previous,
                    change_percentage=change,
                    trend_direction=direction,
                    projection_30_days=projection,
                    confidence_score=confidence,
                )
            )

        # Cache results
        await self.redis.set(
            cache_key, [self._serialize_trend(t) for t in trends], ttl=self.cache_ttl
        )

        return trends

    async def identify_activity_patterns(
        self, user_id: str, days: int = 30
    ) -> list[ActivityPattern]:
        """
        Identify patterns in user activities.

        Args:
            user_id: User ID
            days: Number of days to analyze

        Returns:
            List of identified patterns
        """
        # Get activity data
        activities = await self._get_user_activities(user_id, days)

        patterns = []

        # Analyze time-based patterns
        time_patterns = self._analyze_time_patterns(activities)
        patterns.extend(time_patterns)

        # Analyze activity type patterns
        type_patterns = self._analyze_type_patterns(activities)
        patterns.extend(type_patterns)

        # Analyze competency impact patterns
        impact_patterns = self._analyze_impact_patterns(activities)
        patterns.extend(impact_patterns)

        return patterns

    async def compare_with_peers(
        self, user_id: str, role: str, department: str | None = None
    ) -> list[PeerComparison]:
        """
        Compare user's competencies with peers.

        Args:
            user_id: User ID
            role: User's role for comparison
            department: Optional department filter

        Returns:
            List of peer comparisons
        """
        # Get user's competencies
        user_competencies = await self._get_user_competencies(user_id)

        # Get peer competencies
        peer_data = await self._get_peer_competencies(role, department, exclude_user=user_id)

        comparisons = []

        for comp_name, user_score in user_competencies.items():
            peer_scores = [p[comp_name] for p in peer_data if comp_name in p]

            if not peer_scores:
                continue

            # Calculate statistics
            peer_average = statistics.mean(peer_scores)
            percentile = self._calculate_percentile(user_score, peer_scores)

            # Get top performers
            top_performers = self._get_top_performers(comp_name, peer_data, limit=3)

            comparisons.append(
                PeerComparison(
                    competency_name=comp_name,
                    user_score=user_score,
                    peer_average=peer_average,
                    percentile=percentile,
                    top_performers=top_performers,
                )
            )

        return comparisons

    async def analyze_career_path(
        self, user_id: str, target_role: str | None = None
    ) -> CareerPathAnalysis:
        """
        Analyze career path progression.

        Args:
            user_id: User ID
            target_role: Target role (auto-detect if None)

        Returns:
            Career path analysis
        """
        # Get user's current competencies and role
        user_data = await self._get_user_profile(user_id)
        current_role = user_data["role"]
        current_competencies = user_data["competencies"]

        # Determine target role
        if not target_role:
            target_role = await self._suggest_next_role(current_role, current_competencies)

        # Get target role requirements
        target_requirements = await self._get_role_requirements(target_role)

        # Calculate gaps
        gap_analysis = {}
        for comp, required_score in target_requirements.items():
            current_score = current_competencies.get(comp, 0)
            gap_analysis[comp] = max(0, required_score - current_score)

        # Identify focus areas
        focus_areas = sorted(gap_analysis.keys(), key=gap_analysis.get, reverse=True)[:3]

        # Estimate time to next level
        avg_growth_rate = await self._calculate_growth_rate(user_id)
        total_gap = sum(gap_analysis.values())
        estimated_days = int(total_gap / max(avg_growth_rate, 0.1))

        # Calculate milestone progress
        milestones = await self._get_career_milestones(current_role, target_role)
        milestone_progress = {}
        for milestone, requirements in milestones.items():
            progress = self._calculate_milestone_progress(current_competencies, requirements)
            milestone_progress[milestone] = progress

        return CareerPathAnalysis(
            current_level=current_role,
            next_level=target_role,
            gap_analysis=gap_analysis,
            recommended_focus_areas=focus_areas,
            estimated_time_to_next_level=estimated_days,
            milestone_progress=milestone_progress,
        )

    async def generate_predictive_insights(
        self, user_id: str, horizon_days: int = 90
    ) -> dict[str, Any]:
        """
        Generate predictive insights for user.

        Args:
            user_id: User ID
            horizon_days: Prediction horizon in days

        Returns:
            Predictive insights
        """
        insights = {
            "predicted_competencies": {},
            "risk_areas": [],
            "opportunity_areas": [],
            "recommended_actions": [],
        }

        # Get historical data
        history = await self._get_competency_history(user_id, AnalyticsTimeframe.WEEKLY)

        for comp_name, scores in history.items():
            if len(scores) < self.min_data_points:
                continue

            # Predict future score
            predicted_score = self._project_score(scores, horizon_days)
            insights["predicted_competencies"][comp_name] = {
                "current": scores[-1],
                "predicted": predicted_score,
                "confidence": self._calculate_confidence(scores),
            }

            # Identify risks
            if predicted_score < scores[-1] * 0.9:  # 10% decline
                insights["risk_areas"].append(
                    {
                        "competency": comp_name,
                        "risk_level": "high" if predicted_score < scores[-1] * 0.8 else "medium",
                        "predicted_decline": scores[-1] - predicted_score,
                    }
                )

            # Identify opportunities
            elif predicted_score > scores[-1] * 1.1:  # 10% growth
                insights["opportunity_areas"].append(
                    {
                        "competency": comp_name,
                        "growth_potential": predicted_score - scores[-1],
                        "confidence": self._calculate_confidence(scores),
                    }
                )

        # Generate recommended actions
        insights["recommended_actions"] = await self._generate_recommendations(
            insights["risk_areas"], insights["opportunity_areas"]
        )

        return insights

    def _calculate_trend_direction(self, scores: list[float]) -> TrendDirection:
        """Calculate trend direction from scores."""
        if len(scores) < 2:
            return TrendDirection.STABLE

        # Calculate moving averages
        recent_avg = statistics.mean(scores[-3:]) if len(scores) >= 3 else scores[-1]
        older_avg = statistics.mean(scores[-6:-3]) if len(scores) >= 6 else scores[0]

        change_rate = (recent_avg - older_avg) / max(older_avg, 0.01)

        if change_rate > 0.2:
            return TrendDirection.STRONG_UP
        elif change_rate > 0.05:
            return TrendDirection.UP
        elif change_rate < -0.2:
            return TrendDirection.STRONG_DOWN
        elif change_rate < -0.05:
            return TrendDirection.DOWN
        else:
            return TrendDirection.STABLE

    def _project_score(self, scores: list[float], days: int) -> float:
        """Project future score using linear regression."""
        if len(scores) < 2:
            return scores[-1]

        # Simple linear regression
        x = list(range(len(scores)))
        n = len(scores)

        # Calculate slope and intercept
        x_mean = sum(x) / n
        y_mean = sum(scores) / n

        numerator = sum((x[i] - x_mean) * (scores[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return scores[-1]

        slope = numerator / denominator
        intercept = y_mean - slope * x_mean

        # Project forward
        future_x = len(scores) + (days / 7)  # Assuming weekly data points
        projected = slope * future_x + intercept

        # Bound between 0 and 100
        return max(0, min(100, projected))

    def _calculate_confidence(self, scores: list[float]) -> float:
        """Calculate confidence score based on data consistency."""
        if len(scores) < self.min_data_points:
            return 0.5

        # Calculate coefficient of variation
        if statistics.mean(scores) == 0:
            return 0.5

        cv = statistics.stdev(scores) / statistics.mean(scores)

        # Lower CV means higher confidence
        confidence = max(0.3, min(1.0, 1.0 - cv))

        # Adjust for data recency
        if len(scores) > 10:
            confidence *= 1.1

        return min(1.0, confidence)

    def _calculate_percentile(self, value: float, population: list[float]) -> int:
        """Calculate percentile rank."""
        if not population:
            return 50

        sorted_pop = sorted(population)
        position = 0

        for val in sorted_pop:
            if val < value:
                position += 1
            else:
                break

        percentile = int((position / len(sorted_pop)) * 100)
        return percentile

    async def _get_competency_history(
        self, user_id: str, timeframe: AnalyticsTimeframe
    ) -> dict[str, list[float]]:
        """Get historical competency scores."""
        # This would query the database for historical data
        # Placeholder implementation
        return {
            "Technical Expertise": [65, 68, 70, 72, 75, 78],
            "System Design": [60, 62, 63, 65, 68, 70],
            "Leadership": [55, 56, 58, 60, 62, 65],
        }

    async def _get_user_activities(self, user_id: str, days: int) -> list[dict[str, Any]]:
        """Get user activities for analysis."""
        # Placeholder - would query database
        return []

    async def _get_user_competencies(self, user_id: str) -> dict[str, float]:
        """Get current user competencies."""
        # Placeholder - would query database
        return {"Technical Expertise": 78, "System Design": 70, "Leadership": 65}

    async def _get_peer_competencies(
        self, role: str, department: str | None, exclude_user: str
    ) -> list[dict[str, float]]:
        """Get peer competency data."""
        # Placeholder - would query database
        return []

    def _analyze_time_patterns(self, activities: list[dict[str, Any]]) -> list[ActivityPattern]:
        """Analyze time-based activity patterns."""
        # Placeholder implementation
        return []

    def _analyze_type_patterns(self, activities: list[dict[str, Any]]) -> list[ActivityPattern]:
        """Analyze activity type patterns."""
        # Placeholder implementation
        return []

    def _analyze_impact_patterns(self, activities: list[dict[str, Any]]) -> list[ActivityPattern]:
        """Analyze competency impact patterns."""
        # Placeholder implementation
        return []

    def _get_top_performers(
        self, competency: str, peer_data: list[dict[str, float]], limit: int
    ) -> list[dict[str, Any]]:
        """Get top performers for a competency."""
        # Placeholder implementation
        return []

    async def _get_user_profile(self, user_id: str) -> dict[str, Any]:
        """Get user profile data."""
        # Placeholder - would query database
        return {
            "role": "Senior Engineer",
            "competencies": {"Technical Expertise": 78, "System Design": 70, "Leadership": 65},
        }

    async def _suggest_next_role(self, current_role: str, competencies: dict[str, float]) -> str:
        """Suggest next career role."""
        # Simplified logic
        if "Senior" in current_role:
            return "Staff Engineer"
        elif "Staff" in current_role:
            return "Principal Engineer"
        else:
            return "Senior " + current_role

    async def _get_role_requirements(self, role: str) -> dict[str, float]:
        """Get competency requirements for role."""
        # Placeholder - would have role requirement data
        return {"Technical Expertise": 85, "System Design": 80, "Leadership": 75}

    async def _calculate_growth_rate(self, user_id: str) -> float:
        """Calculate average competency growth rate."""
        # Placeholder - would calculate from historical data
        return 0.5  # 0.5 points per day

    async def _get_career_milestones(
        self, current_role: str, target_role: str
    ) -> dict[str, dict[str, float]]:
        """Get career milestones between roles."""
        # Placeholder - would have milestone definitions
        return {
            "Technical Mastery": {"Technical Expertise": 80},
            "Architecture Leadership": {"System Design": 75},
            "Team Leadership": {"Leadership": 70},
        }

    def _calculate_milestone_progress(
        self, competencies: dict[str, float], requirements: dict[str, float]
    ) -> float:
        """Calculate milestone progress percentage."""
        if not requirements:
            return 100.0

        progress_sum = 0
        for comp, required in requirements.items():
            current = competencies.get(comp, 0)
            progress_sum += min(100, (current / required) * 100)

        return progress_sum / len(requirements)

    async def _generate_recommendations(
        self, risk_areas: list[dict[str, Any]], opportunity_areas: list[dict[str, Any]]
    ) -> list[dict[str, str]]:
        """Generate action recommendations."""
        recommendations = []

        # Address risks
        for risk in risk_areas[:2]:  # Top 2 risks
            recommendations.append(
                {
                    "type": "risk_mitigation",
                    "competency": risk["competency"],
                    "action": f"Focus on maintaining {risk['competency']} through regular practice",
                    "priority": "high",
                }
            )

        # Leverage opportunities
        for opportunity in opportunity_areas[:2]:  # Top 2 opportunities
            recommendations.append(
                {
                    "type": "growth_opportunity",
                    "competency": opportunity["competency"],
                    "action": f"Accelerate growth in {opportunity['competency']} with advanced projects",
                    "priority": "medium",
                }
            )

        return recommendations

    def _serialize_trend(self, trend: CompetencyTrend) -> dict[str, Any]:
        """Serialize trend for caching."""
        return {
            "competency_name": trend.competency_name,
            "current_score": trend.current_score,
            "previous_score": trend.previous_score,
            "change_percentage": trend.change_percentage,
            "trend_direction": trend.trend_direction.value,
            "projection_30_days": trend.projection_30_days,
            "confidence_score": trend.confidence_score,
        }

    def _deserialize_trend(self, data: dict[str, Any]) -> CompetencyTrend:
        """Deserialize trend from cache."""
        return CompetencyTrend(
            competency_name=data["competency_name"],
            current_score=data["current_score"],
            previous_score=data["previous_score"],
            change_percentage=data["change_percentage"],
            trend_direction=TrendDirection(data["trend_direction"]),
            projection_30_days=data["projection_30_days"],
            confidence_score=data["confidence_score"],
        )


# Export
__all__ = [
    "AdvancedAnalyticsEngine",
    "AnalyticsTimeframe",
    "TrendDirection",
    "CompetencyTrend",
    "ActivityPattern",
    "PeerComparison",
    "CareerPathAnalysis",
]
