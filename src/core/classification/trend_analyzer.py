"""
Trend Analysis and Progression Tracking for ReflectAI

Implements  Trend Analysis and Progression Tracking including:
- Competency Progression Analysis with moving averages and growth rates
- Performance Benchmarking against peer groups
- Predictive competency trajectories using statistical analysis
- Competency momentum indicators and milestone detection

Provides comprehensive analysis of competency development over time.
"""

import statistics
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from src.shared import get_logger


class TrendDirection(Enum):
    """Trend direction indicators"""

    ACCELERATING = "accelerating"
    INCREASING = "increasing"
    STABLE = "stable"
    DECLINING = "declining"
    STAGNANT = "stagnant"


class MomentumIndicator(Enum):
    """Competency momentum indicators"""

    HIGH_MOMENTUM = "high_momentum"  # Accelerating growth
    POSITIVE_MOMENTUM = "positive_momentum"  # Steady growth
    NEUTRAL = "neutral"  # Stable
    NEGATIVE_MOMENTUM = "negative_momentum"  # Declining
    STALLED = "stalled"  # No progress


class BenchmarkCategory(Enum):
    """Peer benchmark categories"""

    PEER_GROUP = "peer_group"  # Same role/level
    DEPARTMENT = "department"  # Same department
    ORGANIZATION = "organization"  # Same organization
    INDUSTRY = "industry"  # Industry-wide
    ALL_USERS = "all_users"  # Platform-wide


@dataclass
class CompetencyDataPoint:
    """Single competency measurement point"""

    timestamp: datetime
    score: float
    evidence_count: int
    confidence: float
    assessment_method: str
    user_id: str
    competency_id: str


@dataclass
class MovingAverage:
    """Moving average calculation result"""

    window_days: int
    current_average: float
    previous_average: float
    change_percentage: float
    trend_direction: TrendDirection
    data_points: int


class CompetencyTrend(BaseModel):
    """Competency trend analysis result"""

    user_id: str = Field(..., description="User ID")
    competency_id: str = Field(..., description="Competency being analyzed")
    analysis_period_days: int = Field(..., description="Days analyzed")

    # Current state
    current_score: float = Field(..., description="Most recent competency score")
    current_confidence: float = Field(..., description="Confidence in current score")

    # Trend analysis
    overall_trend: TrendDirection = Field(..., description="Overall trend direction")
    momentum_indicator: MomentumIndicator = Field(..., description="Current momentum")

    # Moving averages
    short_term_average: MovingAverage = Field(..., description="30-day moving average")
    medium_term_average: MovingAverage = Field(..., description="90-day moving average")
    long_term_average: MovingAverage = Field(..., description="180-day moving average")

    # Growth analysis
    growth_rate_percentage: float = Field(..., description="Overall growth rate")
    velocity: float = Field(..., description="Current velocity (score change per month)")
    acceleration: float = Field(..., description="Change in velocity")

    # Milestones and achievements
    milestones_achieved: list[dict[str, Any]] = Field(
        default_factory=list, description="Recent milestones"
    )
    next_milestone: dict[str, Any] | None = Field(None, description="Predicted next milestone")

    # Seasonal patterns
    seasonal_adjustment: float = Field(0.0, description="Seasonal adjustment factor")
    seasonal_pattern: str | None = Field(None, description="Detected seasonal pattern")

    # Data quality
    data_points_count: int = Field(..., description="Number of data points analyzed")
    analysis_confidence: float = Field(..., description="Confidence in trend analysis")

    created_at: datetime = Field(default_factory=datetime.utcnow)


class ProgressionMetrics(BaseModel):
    """Comprehensive progression metrics for a user"""

    user_id: str = Field(..., description="User ID")
    analysis_date: datetime = Field(default_factory=datetime.utcnow)

    # Overall progression
    overall_progress_score: float = Field(..., description="Weighted overall progress (0-100)")
    competency_count: int = Field(..., description="Number of competencies analyzed")

    # Individual competency trends
    competency_trends: list[CompetencyTrend] = Field(
        ..., description="Individual competency trends"
    )

    # Progression categories
    improving_competencies: list[str] = Field(
        default_factory=list, description="Competencies showing improvement"
    )
    stable_competencies: list[str] = Field(default_factory=list, description="Stable competencies")
    declining_competencies: list[str] = Field(
        default_factory=list, description="Declining competencies"
    )

    # Benchmarking results
    peer_comparison: dict[str, float] = Field(
        default_factory=dict, description="Comparison to peer groups"
    )
    percentile_ranking: dict[str, float] = Field(
        default_factory=dict, description="Percentile rankings"
    )

    # Predictive insights
    predicted_trajectories: dict[str, list[float]] = Field(
        default_factory=dict, description="6-month predictions"
    )
    development_recommendations: list[str] = Field(
        default_factory=list, description="Development recommendations"
    )

    # Quality metrics
    analysis_confidence: float = Field(..., description="Overall analysis confidence")
    data_coverage: float = Field(..., description="Data coverage percentage")


class TrendAnalyzer:
    """
    Competency trend analysis and progression tracking

    Provides sophisticated analysis of competency development over time with
    statistical modeling, peer benchmarking, and predictive capabilities.
    """

    def __init__(self):
        self.logger = get_logger("classification.trend_analyzer")

        # Analysis configuration
        self.moving_average_windows = {
            "short_term": 30,  # 30 days
            "medium_term": 90,  # 90 days
            "long_term": 180,  # 180 days
        }

        # Milestone definitions
        self.milestone_thresholds = {
            1.5: "Basic Proficiency Achieved",
            2.5: "Intermediate Level Reached",
            3.5: "Advanced Skills Demonstrated",
            4.5: "Expert Level Attained",
            5.0: "Mastery Achieved",
        }

        # Performance tracking
        self._stats = {
            "total_analyses": 0,
            "trends_calculated": 0,
            "predictions_generated": 0,
            "average_data_points": 0.0,
            "analysis_success_rate": 0.0,
        }

    async def analyze_competency_trend(
        self,
        user_id: str,
        competency_id: str,
        data_points: list[CompetencyDataPoint],
        analysis_period_days: int = 180,
    ) -> CompetencyTrend:
        """
        Analyze trend for a specific competency

        Args:
            user_id: User identifier
            competency_id: Competency to analyze
            data_points: Historical competency data points
            analysis_period_days: Days to analyze

        Returns:
            CompetencyTrend with comprehensive analysis
        """
        try:
            if not data_points:
                return self._create_empty_trend_analysis(
                    user_id, competency_id, analysis_period_days
                )

            # Sort data points by timestamp
            sorted_data = sorted(data_points, key=lambda x: x.timestamp)

            # Filter to analysis period
            cutoff_date = datetime.now(UTC) - timedelta(days=analysis_period_days)
            recent_data = [dp for dp in sorted_data if dp.timestamp >= cutoff_date]

            if not recent_data:
                return self._create_empty_trend_analysis(
                    user_id, competency_id, analysis_period_days
                )

            # Calculate moving averages
            short_term_avg = self._calculate_moving_average(
                recent_data, self.moving_average_windows["short_term"]
            )
            medium_term_avg = self._calculate_moving_average(
                recent_data, self.moving_average_windows["medium_term"]
            )
            long_term_avg = self._calculate_moving_average(
                recent_data, self.moving_average_windows["long_term"]
            )

            # Determine overall trend
            overall_trend = self._determine_trend_direction(
                short_term_avg, medium_term_avg, long_term_avg
            )
            momentum = self._calculate_momentum_indicator(recent_data, overall_trend)

            # Calculate growth metrics
            growth_rate = self._calculate_growth_rate(recent_data)
            velocity = self._calculate_velocity(recent_data)
            acceleration = self._calculate_acceleration(recent_data)

            # Identify milestones
            milestones = self._identify_milestones(recent_data)
            next_milestone = self._predict_next_milestone(recent_data, velocity)

            # Seasonal analysis
            seasonal_adj, seasonal_pattern = self._analyze_seasonal_patterns(recent_data)

            # Calculate analysis confidence
            analysis_confidence = self._calculate_analysis_confidence(recent_data)

            trend = CompetencyTrend(
                user_id=user_id,
                competency_id=competency_id,
                analysis_period_days=analysis_period_days,
                current_score=recent_data[-1].score,
                current_confidence=recent_data[-1].confidence,
                overall_trend=overall_trend,
                momentum_indicator=momentum,
                short_term_average=short_term_avg,
                medium_term_average=medium_term_avg,
                long_term_average=long_term_avg,
                growth_rate_percentage=growth_rate,
                velocity=velocity,
                acceleration=acceleration,
                milestones_achieved=milestones,
                next_milestone=next_milestone,
                seasonal_adjustment=seasonal_adj,
                seasonal_pattern=seasonal_pattern,
                data_points_count=len(recent_data),
                analysis_confidence=analysis_confidence,
            )

            self._update_stats(len(recent_data), True)
            return trend

        except Exception as e:
            self.logger.error(f"Trend analysis failed for {user_id}/{competency_id}: {str(e)}")
            self._update_stats(len(data_points), False)
            return self._create_empty_trend_analysis(user_id, competency_id, analysis_period_days)

    async def analyze_user_progression(
        self,
        user_id: str,
        competency_data: dict[str, list[CompetencyDataPoint]],
        peer_data: dict[str, Any] | None = None,
    ) -> ProgressionMetrics:
        """
        Analyze overall progression for a user across all competencies

        Args:
            user_id: User identifier
            competency_data: Dict of competency_id -> data points
            peer_data: Optional peer comparison data

        Returns:
            ProgressionMetrics with comprehensive progression analysis
        """
        try:
            competency_trends = []
            improving = []
            stable = []
            declining = []

            # Analyze each competency
            for competency_id, data_points in competency_data.items():
                trend = await self.analyze_competency_trend(user_id, competency_id, data_points)
                competency_trends.append(trend)

                # Categorize trends
                if trend.overall_trend in [TrendDirection.ACCELERATING, TrendDirection.INCREASING]:
                    improving.append(competency_id)
                elif trend.overall_trend == TrendDirection.STABLE:
                    stable.append(competency_id)
                else:
                    declining.append(competency_id)

            # Calculate overall progress score
            overall_score = self._calculate_overall_progress_score(competency_trends)

            # Perform peer comparison
            peer_comparison = {}
            percentile_ranking = {}
            if peer_data:
                peer_comparison, percentile_ranking = self._perform_peer_comparison(
                    competency_trends, peer_data
                )

            # Generate predictions
            predicted_trajectories = self._generate_trajectory_predictions(competency_trends)

            # Development recommendations
            recommendations = self._generate_development_recommendations(
                competency_trends, improving, stable, declining
            )

            # Quality metrics
            sum(len(data_points) for data_points in competency_data.values())
            data_coverage = self._calculate_data_coverage(competency_data)
            analysis_confidence = (
                sum(t.analysis_confidence for t in competency_trends) / len(competency_trends)
                if competency_trends
                else 0.0
            )

            return ProgressionMetrics(
                user_id=user_id,
                overall_progress_score=overall_score,
                competency_count=len(competency_trends),
                competency_trends=competency_trends,
                improving_competencies=improving,
                stable_competencies=stable,
                declining_competencies=declining,
                peer_comparison=peer_comparison,
                percentile_ranking=percentile_ranking,
                predicted_trajectories=predicted_trajectories,
                development_recommendations=recommendations,
                analysis_confidence=analysis_confidence,
                data_coverage=data_coverage,
            )

        except Exception as e:
            self.logger.error(f"Progression analysis failed for {user_id}: {str(e)}")

            # Return minimal progression metrics
            return ProgressionMetrics(
                user_id=user_id,
                overall_progress_score=50.0,
                competency_count=0,
                competency_trends=[],
                analysis_confidence=0.2,
                data_coverage=0.0,
            )

    def _calculate_moving_average(
        self, data_points: list[CompetencyDataPoint], window_days: int
    ) -> MovingAverage:
        """Calculate moving average for a time window"""

        if not data_points:
            return MovingAverage(
                window_days=window_days,
                current_average=0.0,
                previous_average=0.0,
                change_percentage=0.0,
                trend_direction=TrendDirection.STABLE,
                data_points=0,
            )

        now = datetime.now(UTC)
        current_window_start = now - timedelta(days=window_days)
        previous_window_start = current_window_start - timedelta(days=window_days)

        # Current window data
        current_data = [dp for dp in data_points if current_window_start <= dp.timestamp <= now]

        # Previous window data
        previous_data = [
            dp for dp in data_points if previous_window_start <= dp.timestamp < current_window_start
        ]

        current_avg = statistics.mean([dp.score for dp in current_data]) if current_data else 0.0
        previous_avg = statistics.mean([dp.score for dp in previous_data]) if previous_data else 0.0

        # Calculate change percentage
        change_pct = 0.0
        if previous_avg > 0:
            change_pct = ((current_avg - previous_avg) / previous_avg) * 100

        # Determine trend direction
        if change_pct > 5:
            direction = TrendDirection.INCREASING
        elif change_pct < -5:
            direction = TrendDirection.DECLINING
        else:
            direction = TrendDirection.STABLE

        return MovingAverage(
            window_days=window_days,
            current_average=current_avg,
            previous_average=previous_avg,
            change_percentage=change_pct,
            trend_direction=direction,
            data_points=len(current_data),
        )

    def _determine_trend_direction(
        self, short_term: MovingAverage, medium_term: MovingAverage, long_term: MovingAverage
    ) -> TrendDirection:
        """Determine overall trend direction from moving averages"""

        # Weight short-term trends more heavily
        short_weight = 0.5
        medium_weight = 0.3
        long_weight = 0.2

        weighted_change = (
            short_term.change_percentage * short_weight
            + medium_term.change_percentage * medium_weight
            + long_term.change_percentage * long_weight
        )

        # Check for acceleration (short-term > medium-term > long-term)
        if (
            short_term.change_percentage > medium_term.change_percentage > 0
            and medium_term.change_percentage > long_term.change_percentage
        ):
            return TrendDirection.ACCELERATING
        elif weighted_change > 3:
            return TrendDirection.INCREASING
        elif weighted_change < -3:
            return TrendDirection.DECLINING
        elif abs(weighted_change) <= 1:
            return TrendDirection.STABLE
        else:
            return TrendDirection.STAGNANT

    def _calculate_momentum_indicator(
        self, data_points: list[CompetencyDataPoint], trend_direction: TrendDirection
    ) -> MomentumIndicator:
        """Calculate momentum indicator"""

        if len(data_points) < 3:
            return MomentumIndicator.NEUTRAL

        # Calculate recent velocity (last 30 days)
        recent_velocity = self._calculate_velocity(data_points, days=30)

        # Map trend and velocity to momentum
        if trend_direction == TrendDirection.ACCELERATING:
            return MomentumIndicator.HIGH_MOMENTUM
        elif trend_direction == TrendDirection.INCREASING and recent_velocity > 0.1:
            return MomentumIndicator.POSITIVE_MOMENTUM
        elif trend_direction == TrendDirection.DECLINING:
            return MomentumIndicator.NEGATIVE_MOMENTUM
        elif trend_direction == TrendDirection.STAGNANT:
            return MomentumIndicator.STALLED
        else:
            return MomentumIndicator.NEUTRAL

    def _calculate_growth_rate(self, data_points: list[CompetencyDataPoint]) -> float:
        """Calculate overall growth rate percentage"""

        if len(data_points) < 2:
            return 0.0

        first_score = data_points[0].score
        last_score = data_points[-1].score

        if first_score == 0:
            return 0.0

        growth_rate = ((last_score - first_score) / first_score) * 100
        return round(growth_rate, 2)

    def _calculate_velocity(self, data_points: list[CompetencyDataPoint], days: int = 30) -> float:
        """Calculate velocity (score change per month)"""

        if len(data_points) < 2:
            return 0.0

        # Use recent data points
        cutoff_date = datetime.now(UTC) - timedelta(days=days)
        recent_data = [dp for dp in data_points if dp.timestamp >= cutoff_date]

        if len(recent_data) < 2:
            recent_data = data_points[-2:]  # Use last 2 points

        # Calculate linear regression slope
        try:
            timestamps = [dp.timestamp.timestamp() for dp in recent_data]
            scores = [dp.score for dp in recent_data]

            if len(set(timestamps)) < 2:  # Avoid division by zero
                return 0.0

            # Simple linear regression
            n = len(recent_data)
            sum_x = sum(timestamps)
            sum_y = sum(scores)
            sum_xy = sum(t * s for t, s in zip(timestamps, scores, strict=False))
            sum_x2 = sum(t * t for t in timestamps)

            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)

            # Convert to score change per month (30 days = 2592000 seconds)
            velocity = slope * 2592000

            return round(velocity, 4)

        except (ZeroDivisionError, ValueError):
            return 0.0

    def _calculate_acceleration(self, data_points: list[CompetencyDataPoint]) -> float:
        """Calculate acceleration (change in velocity)"""

        if len(data_points) < 6:  # Need enough points for acceleration
            return 0.0

        # Calculate velocity for first and second half of data
        mid_point = len(data_points) // 2
        first_half = data_points[: mid_point + 1]
        second_half = data_points[mid_point:]

        first_velocity = self._calculate_velocity(first_half)
        second_velocity = self._calculate_velocity(second_half)

        acceleration = second_velocity - first_velocity
        return round(acceleration, 4)

    def _identify_milestones(self, data_points: list[CompetencyDataPoint]) -> list[dict[str, Any]]:
        """Identify achieved milestones"""

        milestones = []
        current_max = 0.0

        for dp in data_points:
            # Check if a new milestone threshold was crossed
            for threshold, description in self.milestone_thresholds.items():
                if dp.score >= threshold > current_max:
                    milestones.append(
                        {
                            "threshold": threshold,
                            "description": description,
                            "achieved_at": dp.timestamp.isoformat(),
                            "score": dp.score,
                        }
                    )

            current_max = max(current_max, dp.score)

        # Sort by timestamp
        milestones.sort(key=lambda x: x["achieved_at"])

        # Return only recent milestones (last 90 days)
        recent_cutoff = datetime.now(UTC) - timedelta(days=90)
        recent_milestones = [
            m for m in milestones if datetime.fromisoformat(m["achieved_at"]) >= recent_cutoff
        ]

        return recent_milestones

    def _predict_next_milestone(
        self, data_points: list[CompetencyDataPoint], velocity: float
    ) -> dict[str, Any] | None:
        """Predict next milestone achievement"""

        if not data_points or velocity <= 0:
            return None

        current_score = data_points[-1].score

        # Find next milestone threshold
        next_threshold = None
        for threshold in sorted(self.milestone_thresholds.keys()):
            if threshold > current_score:
                next_threshold = threshold
                break

        if not next_threshold:
            return None  # Already at maximum

        # Calculate time to reach next milestone
        score_gap = next_threshold - current_score
        months_to_milestone = score_gap / velocity if velocity > 0 else None

        if months_to_milestone and months_to_milestone <= 12:  # Within reasonable timeframe
            predicted_date = datetime.now(UTC) + timedelta(days=months_to_milestone * 30)

            return {
                "threshold": next_threshold,
                "description": self.milestone_thresholds[next_threshold],
                "predicted_date": predicted_date.isoformat(),
                "estimated_months": round(months_to_milestone, 1),
                "current_gap": round(score_gap, 2),
            }

        return None

    def _analyze_seasonal_patterns(
        self, data_points: list[CompetencyDataPoint]
    ) -> tuple[float, str | None]:
        """Analyze seasonal patterns in competency development"""

        if len(data_points) < 12:  # Need at least a year of data
            return 0.0, None

        # Group data by month
        monthly_scores = {}
        for dp in data_points:
            month = dp.timestamp.month
            if month not in monthly_scores:
                monthly_scores[month] = []
            monthly_scores[month].append(dp.score)

        # Calculate monthly averages
        monthly_averages = {
            month: statistics.mean(scores) for month, scores in monthly_scores.items()
        }

        if len(monthly_averages) < 6:  # Need sufficient months
            return 0.0, None

        # Look for patterns
        summer_months = [6, 7, 8]  # June, July, August
        winter_months = [12, 1, 2]  # December, January, February

        summer_avg = (
            statistics.mean([monthly_averages[m] for m in summer_months if m in monthly_averages])
            if any(m in monthly_averages for m in summer_months)
            else 0
        )

        winter_avg = (
            statistics.mean([monthly_averages[m] for m in winter_months if m in monthly_averages])
            if any(m in monthly_averages for m in winter_months)
            else 0
        )

        overall_avg = statistics.mean(monthly_averages.values())

        # Detect seasonal patterns
        seasonal_adjustment = 0.0
        seasonal_pattern = None

        if summer_avg > 0 and winter_avg > 0:
            if summer_avg > overall_avg * 1.1 and winter_avg < overall_avg * 0.9:
                seasonal_pattern = "summer_peak"
                seasonal_adjustment = (summer_avg - winter_avg) / overall_avg
            elif winter_avg > overall_avg * 1.1 and summer_avg < overall_avg * 0.9:
                seasonal_pattern = "winter_peak"
                seasonal_adjustment = (winter_avg - summer_avg) / overall_avg

        return round(seasonal_adjustment, 3), seasonal_pattern

    def _calculate_analysis_confidence(self, data_points: list[CompetencyDataPoint]) -> float:
        """Calculate confidence in trend analysis"""

        confidence = 0.0

        # Data quantity factor
        data_count = len(data_points)
        if data_count >= 20:
            confidence += 0.4
        elif data_count >= 10:
            confidence += 0.3
        elif data_count >= 5:
            confidence += 0.2

        # Data quality factor (average confidence of data points)
        if data_points:
            avg_data_confidence = statistics.mean([dp.confidence for dp in data_points])
            confidence += avg_data_confidence * 0.3

        # Time span factor
        if len(data_points) >= 2:
            time_span_days = (data_points[-1].timestamp - data_points[0].timestamp).days
            if time_span_days >= 90:
                confidence += 0.2
            elif time_span_days >= 30:
                confidence += 0.1

        # Consistency factor
        if data_count >= 3:
            scores = [dp.score for dp in data_points]
            score_std = statistics.stdev(scores) if len(scores) > 1 else 0
            if score_std < 0.5:  # Low variability indicates consistent data
                confidence += 0.1

        return min(confidence, 1.0)

    def _calculate_overall_progress_score(self, competency_trends: list[CompetencyTrend]) -> float:
        """Calculate weighted overall progress score"""

        if not competency_trends:
            return 0.0

        total_weighted_score = 0.0
        total_weight = 0.0

        for trend in competency_trends:
            # Weight by analysis confidence and data quality
            weight = trend.analysis_confidence * (trend.data_points_count / 10)
            weight = min(weight, 1.0)  # Cap weight at 1.0

            # Convert trend to progress score (0-100)
            trend_score = 50.0  # Neutral baseline

            if trend.overall_trend == TrendDirection.ACCELERATING:
                trend_score += 30
            elif trend.overall_trend == TrendDirection.INCREASING:
                trend_score += 20
            elif trend.overall_trend == TrendDirection.DECLINING:
                trend_score -= 20
            elif trend.overall_trend == TrendDirection.STAGNANT:
                trend_score -= 10

            # Add momentum bonus/penalty
            if trend.momentum_indicator == MomentumIndicator.HIGH_MOMENTUM:
                trend_score += 15
            elif trend.momentum_indicator == MomentumIndicator.POSITIVE_MOMENTUM:
                trend_score += 10
            elif trend.momentum_indicator == MomentumIndicator.NEGATIVE_MOMENTUM:
                trend_score -= 10
            elif trend.momentum_indicator == MomentumIndicator.STALLED:
                trend_score -= 15

            # Add current score factor
            trend_score += (trend.current_score / 5.0) * 20  # Scale to 0-20

            total_weighted_score += trend_score * weight
            total_weight += weight

        if total_weight == 0:
            return 50.0

        overall_score = total_weighted_score / total_weight
        return max(0.0, min(100.0, overall_score))

    def _perform_peer_comparison(
        self, competency_trends: list[CompetencyTrend], peer_data: dict[str, Any]
    ) -> tuple[dict[str, float], dict[str, float]]:
        """Perform peer comparison analysis"""

        # Simplified peer comparison - in production would use actual peer data
        peer_comparison = {}
        percentile_ranking = {}

        for trend in competency_trends:
            # Mock peer comparison values
            peer_avg = peer_data.get(trend.competency_id, {}).get("average", 3.0)
            peer_std = peer_data.get(trend.competency_id, {}).get("std_dev", 0.5)

            # Calculate relative performance
            if peer_std > 0:
                z_score = (trend.current_score - peer_avg) / peer_std
                percentile = max(0, min(100, 50 + (z_score * 15)))  # Rough percentile conversion
            else:
                percentile = 50  # Average if no variance

            peer_comparison[trend.competency_id] = round(trend.current_score - peer_avg, 2)
            percentile_ranking[trend.competency_id] = round(percentile, 1)

        return peer_comparison, percentile_ranking

    def _generate_trajectory_predictions(
        self, competency_trends: list[CompetencyTrend]
    ) -> dict[str, list[float]]:
        """Generate 6-month trajectory predictions"""

        predictions = {}

        for trend in competency_trends:
            if trend.data_points_count >= 3:
                # Simple linear projection
                monthly_predictions = []
                current_score = trend.current_score
                monthly_velocity = trend.velocity

                for month in range(1, 7):  # Next 6 months
                    predicted_score = current_score + (monthly_velocity * month)

                    # Apply seasonal adjustment if available
                    if trend.seasonal_adjustment != 0.0:
                        seasonal_factor = 1 + (trend.seasonal_adjustment * 0.5)  # Dampen effect
                        predicted_score *= seasonal_factor

                    # Cap predictions at reasonable bounds
                    predicted_score = max(0.0, min(5.0, predicted_score))
                    monthly_predictions.append(round(predicted_score, 2))

                predictions[trend.competency_id] = monthly_predictions

        return predictions

    def _generate_development_recommendations(
        self,
        competency_trends: list[CompetencyTrend],
        improving: list[str],
        stable: list[str],
        declining: list[str],
    ) -> list[str]:
        """Generate development recommendations based on trends"""

        recommendations = []

        # Recommendations for declining competencies
        if declining:
            recommendations.append(
                f"Focus immediate attention on declining competencies: {', '.join(declining[:3])}"
            )
            recommendations.append(
                "Consider additional training or mentoring for areas showing decline"
            )

        # Recommendations for stable competencies
        if len(stable) > len(improving):
            recommendations.append(
                "Many competencies are stable - consider setting stretch goals to drive growth"
            )

        # Recommendations for improving competencies
        if improving:
            recommendations.append(
                f"Continue momentum in improving areas: {', '.join(improving[:3])}"
            )

        # Specific recommendations based on momentum
        high_momentum_count = sum(
            1 for t in competency_trends if t.momentum_indicator == MomentumIndicator.HIGH_MOMENTUM
        )

        if high_momentum_count == 0:
            recommendations.append(
                "Consider increasing learning activities to build competency momentum"
            )

        # Data quality recommendations
        low_data_trends = [t for t in competency_trends if t.data_points_count < 5]
        if len(low_data_trends) > len(competency_trends) / 2:
            recommendations.append(
                "Increase activity logging to improve competency assessment accuracy"
            )

        return recommendations[:5]  # Limit to top 5 recommendations

    def _calculate_data_coverage(
        self, competency_data: dict[str, list[CompetencyDataPoint]]
    ) -> float:
        """Calculate data coverage percentage"""

        if not competency_data:
            return 0.0

        total_possible_days = 180  # Analysis period
        covered_days = set()

        for data_points in competency_data.values():
            for dp in data_points:
                days_ago = (datetime.now(UTC) - dp.timestamp).days
                if 0 <= days_ago <= total_possible_days:
                    covered_days.add(days_ago)

        coverage = len(covered_days) / total_possible_days
        return round(coverage * 100, 1)

    def _create_empty_trend_analysis(
        self, user_id: str, competency_id: str, analysis_period_days: int
    ) -> CompetencyTrend:
        """Create empty trend analysis for insufficient data"""

        empty_ma = MovingAverage(
            window_days=30,
            current_average=0.0,
            previous_average=0.0,
            change_percentage=0.0,
            trend_direction=TrendDirection.STABLE,
            data_points=0,
        )

        return CompetencyTrend(
            user_id=user_id,
            competency_id=competency_id,
            analysis_period_days=analysis_period_days,
            current_score=0.0,
            current_confidence=0.0,
            overall_trend=TrendDirection.STABLE,
            momentum_indicator=MomentumIndicator.NEUTRAL,
            short_term_average=empty_ma,
            medium_term_average=empty_ma,
            long_term_average=empty_ma,
            growth_rate_percentage=0.0,
            velocity=0.0,
            acceleration=0.0,
            milestones_achieved=[],
            data_points_count=0,
            analysis_confidence=0.0,
        )

    def _update_stats(self, data_points_count: int, success: bool):
        """Update analyzer statistics"""

        self._stats["total_analyses"] += 1

        if success:
            self._stats["trends_calculated"] += 1
            self._stats["predictions_generated"] += 1

        # Update average data points
        total_analyses = self._stats["total_analyses"]
        current_avg = self._stats["average_data_points"]
        self._stats["average_data_points"] = (
            (current_avg * (total_analyses - 1)) + data_points_count
        ) / total_analyses

        # Update success rate
        self._stats["analysis_success_rate"] = self._stats["trends_calculated"] / total_analyses

    def get_analyzer_stats(self) -> dict[str, Any]:
        """Get trend analyzer statistics"""
        return self._stats.copy()


# Global analyzer instance
_global_analyzer: TrendAnalyzer | None = None


def get_trend_analyzer() -> TrendAnalyzer:
    """Get global trend analyzer instance"""
    global _global_analyzer
    if _global_analyzer is None:
        _global_analyzer = TrendAnalyzer()
    return _global_analyzer
