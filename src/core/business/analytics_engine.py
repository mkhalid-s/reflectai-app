"""
Analytics Engine for ReflectAI
Handles data analysis, insights generation, and trend detection.
"""

from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

import numpy as np

from src.shared.error_handlers import handle_errors
from src.shared.exceptions import ErrorCategory
from src.shared.logging import get_logger

logger = get_logger(__name__)


class AnalyticsType(Enum):
    """Types of analytics."""

    DESCRIPTIVE = "descriptive"  # What happened
    DIAGNOSTIC = "diagnostic"  # Why it happened
    PREDICTIVE = "predictive"  # What will happen
    PRESCRIPTIVE = "prescriptive"  # What should be done


class MetricType(Enum):
    """Types of metrics."""

    GROWTH = "growth"
    ENGAGEMENT = "engagement"
    PERFORMANCE = "performance"
    EFFICIENCY = "efficiency"
    QUALITY = "quality"


@dataclass
class Metric:
    """Represents a metric."""

    name: str
    value: float
    unit: str
    type: MetricType
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)
    trend: str | None = None  # "up", "down", "stable"
    change_rate: float | None = None


@dataclass
class Insight:
    """Represents an analytical insight."""

    insight_id: str
    type: str
    title: str
    description: str
    impact: str  # "high", "medium", "low"
    confidence: float
    supporting_data: dict[str, Any]
    recommendations: list[str]
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AnalyticsReport:
    """Analytics report."""

    report_id: str
    user_id: str
    period_start: datetime
    period_end: datetime
    metrics: dict[str, Metric]
    insights: list[Insight]
    trends: dict[str, Any]
    predictions: dict[str, Any]
    recommendations: list[str]
    generated_at: datetime = field(default_factory=datetime.utcnow)


class AnalyticsEngine:
    """
    Core engine for analytics and insights.

    Features:
    - Multi-dimensional analysis
    - Trend detection
    - Anomaly detection
    - Predictive analytics
    - Insight generation
    - Performance benchmarking
    """

    def __init__(self):
        self.metric_definitions = self._load_metric_definitions()
        self.benchmarks = self._load_benchmarks()
        self.analysis_functions = self._initialize_analysis_functions()

        logger.info("Analytics Engine initialized")

    def _load_metric_definitions(self) -> dict[str, dict]:
        """Load metric definitions."""
        return {
            "activity_rate": {
                "type": MetricType.ENGAGEMENT,
                "unit": "activities/week",
                "calculation": "count",
                "benchmark": 10,
            },
            "competency_growth": {
                "type": MetricType.GROWTH,
                "unit": "percentage",
                "calculation": "change_rate",
                "benchmark": 5,
            },
            "goal_completion": {
                "type": MetricType.PERFORMANCE,
                "unit": "percentage",
                "calculation": "ratio",
                "benchmark": 80,
            },
            "learning_velocity": {
                "type": MetricType.EFFICIENCY,
                "unit": "skills/month",
                "calculation": "rate",
                "benchmark": 2,
            },
            "engagement_score": {
                "type": MetricType.ENGAGEMENT,
                "unit": "score",
                "calculation": "composite",
                "benchmark": 70,
            },
        }

    def _load_benchmarks(self) -> dict[str, dict]:
        """Load performance benchmarks."""
        return {
            "junior": {"activity_rate": 5, "competency_growth": 10, "goal_completion": 60},
            "mid": {"activity_rate": 10, "competency_growth": 7, "goal_completion": 75},
            "senior": {"activity_rate": 15, "competency_growth": 5, "goal_completion": 85},
            "lead": {"activity_rate": 12, "competency_growth": 3, "goal_completion": 90},
        }

    def _initialize_analysis_functions(self) -> dict[str, Any]:
        """Initialize analysis functions."""
        return {
            AnalyticsType.DESCRIPTIVE: self._descriptive_analysis,
            AnalyticsType.DIAGNOSTIC: self._diagnostic_analysis,
            AnalyticsType.PREDICTIVE: self._predictive_analysis,
            AnalyticsType.PRESCRIPTIVE: self._prescriptive_analysis,
        }

    @handle_errors(category=ErrorCategory.BUSINESS_RULE_ERROR)
    async def generate_analytics_report(
        self,
        user_id: str,
        data: dict[str, Any],
        period_days: int = 30,
        analytics_types: list[AnalyticsType] | None = None,
    ) -> AnalyticsReport:
        """
        Generate comprehensive analytics report.

        Args:
            user_id: User identifier
            data: User data for analysis
            period_days: Analysis period in days
            analytics_types: Types of analytics to include

        Returns:
            Analytics report
        """
        try:
            period_end = datetime.now(UTC)
            period_start = period_end - timedelta(days=period_days)

            # Default to all analytics types
            if not analytics_types:
                analytics_types = list(AnalyticsType)

            # Calculate metrics
            metrics = await self._calculate_metrics(data, period_start, period_end)

            # Detect trends
            trends = await self._detect_trends(data, metrics, period_days)

            # Generate insights
            insights = []
            predictions = {}

            for analytics_type in analytics_types:
                analysis_func = self.analysis_functions.get(analytics_type)
                if analysis_func:
                    result = await analysis_func(data, metrics, trends)

                    if analytics_type == AnalyticsType.PREDICTIVE:
                        predictions = result
                    else:
                        insights.extend(result)

            # Generate recommendations
            recommendations = await self._generate_recommendations(insights, metrics, trends)

            # Create report
            report = AnalyticsReport(
                report_id=f"report_{user_id}_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
                user_id=user_id,
                period_start=period_start,
                period_end=period_end,
                metrics=metrics,
                insights=insights,
                trends=trends,
                predictions=predictions,
                recommendations=recommendations,
            )

            logger.info(
                "Analytics report generated",
                extra={
                    "user_id": user_id,
                    "period_days": period_days,
                    "metrics_count": len(metrics),
                    "insights_count": len(insights),
                },
            )

            return report

        except Exception as e:
            logger.error(f"Failed to generate analytics report: {e}")
            raise

    async def _calculate_metrics(
        self, data: dict[str, Any], period_start: datetime, period_end: datetime
    ) -> dict[str, Metric]:
        """Calculate metrics from data."""
        metrics = {}

        # Activity rate
        activities = data.get("activities", [])
        period_activities = [
            a
            for a in activities
            if period_start <= a.get("timestamp", datetime.now(UTC)) <= period_end
        ]

        weeks = max((period_end - period_start).days / 7, 1)
        activity_rate = len(period_activities) / weeks

        metrics["activity_rate"] = Metric(
            name="Activity Rate",
            value=activity_rate,
            unit="activities/week",
            type=MetricType.ENGAGEMENT,
            timestamp=datetime.now(UTC),
            trend=self._calculate_trend(activity_rate, 10),
        )

        # Competency growth
        competencies = data.get("competencies", {})
        prev_competencies = data.get("previous_competencies", {})

        growth_rates = []
        for comp, score in competencies.items():
            prev_score = prev_competencies.get(comp, 0)
            if prev_score > 0:
                growth = ((score - prev_score) / prev_score) * 100
                growth_rates.append(growth)

        avg_growth = np.mean(growth_rates) if growth_rates else 0

        metrics["competency_growth"] = Metric(
            name="Competency Growth",
            value=avg_growth,
            unit="percentage",
            type=MetricType.GROWTH,
            timestamp=datetime.now(UTC),
            trend=self._calculate_trend(avg_growth, 5),
        )

        # Goal completion
        goals = data.get("goals", [])
        completed_goals = [g for g in goals if g.get("status") == "completed"]

        completion_rate = (len(completed_goals) / len(goals) * 100) if goals else 0

        metrics["goal_completion"] = Metric(
            name="Goal Completion",
            value=completion_rate,
            unit="percentage",
            type=MetricType.PERFORMANCE,
            timestamp=datetime.now(UTC),
            trend=self._calculate_trend(completion_rate, 80),
        )

        # Learning velocity
        new_skills = data.get("new_skills", [])
        period_skills = [
            s
            for s in new_skills
            if period_start <= s.get("acquired_date", datetime.now(UTC)) <= period_end
        ]

        months = max((period_end - period_start).days / 30, 1)
        learning_velocity = len(period_skills) / months

        metrics["learning_velocity"] = Metric(
            name="Learning Velocity",
            value=learning_velocity,
            unit="skills/month",
            type=MetricType.EFFICIENCY,
            timestamp=datetime.now(UTC),
            trend=self._calculate_trend(learning_velocity, 2),
        )

        # Engagement score (composite)
        engagement_score = self._calculate_engagement_score(
            activity_rate, completion_rate, learning_velocity
        )

        metrics["engagement_score"] = Metric(
            name="Engagement Score",
            value=engagement_score,
            unit="score",
            type=MetricType.ENGAGEMENT,
            timestamp=datetime.now(UTC),
            trend=self._calculate_trend(engagement_score, 70),
        )

        return metrics

    def _calculate_trend(self, current: float, benchmark: float) -> str:
        """Calculate trend based on benchmark."""
        if current > benchmark * 1.1:
            return "up"
        elif current < benchmark * 0.9:
            return "down"
        else:
            return "stable"

    def _calculate_engagement_score(
        self, activity_rate: float, completion_rate: float, learning_velocity: float
    ) -> float:
        """Calculate composite engagement score."""
        # Normalize to 0-100 scale
        activity_score = min(activity_rate / 20 * 100, 100)
        completion_score = completion_rate
        learning_score = min(learning_velocity / 5 * 100, 100)

        # Weighted average
        engagement = activity_score * 0.3 + completion_score * 0.4 + learning_score * 0.3

        return engagement

    async def _detect_trends(
        self, data: dict[str, Any], metrics: dict[str, Metric], period_days: int
    ) -> dict[str, Any]:
        """Detect trends in data."""
        trends = {
            "overall_direction": "stable",
            "momentum": 0.0,
            "patterns": [],
            "anomalies": [],
            "seasonality": {},
        }

        # Overall direction based on metrics
        up_trends = sum(1 for m in metrics.values() if m.trend == "up")
        down_trends = sum(1 for m in metrics.values() if m.trend == "down")

        if up_trends > down_trends:
            trends["overall_direction"] = "improving"
            trends["momentum"] = (up_trends - down_trends) / len(metrics)
        elif down_trends > up_trends:
            trends["overall_direction"] = "declining"
            trends["momentum"] = -(down_trends - up_trends) / len(metrics)

        # Detect patterns
        activities = data.get("activities", [])
        if activities:
            # Day of week pattern
            weekday_counts = Counter()
            for activity in activities:
                timestamp = activity.get("timestamp", datetime.now(UTC))
                weekday_counts[timestamp.strftime("%A")] += 1

            most_active_day = weekday_counts.most_common(1)[0] if weekday_counts else None
            if most_active_day:
                trends["patterns"].append(
                    {
                        "type": "weekly",
                        "pattern": f"Most active on {most_active_day[0]}",
                        "strength": most_active_day[1] / sum(weekday_counts.values()),
                    }
                )

            # Time of day pattern
            hour_counts = Counter()
            for activity in activities:
                timestamp = activity.get("timestamp", datetime.now(UTC))
                hour_counts[timestamp.hour] += 1

            peak_hour = hour_counts.most_common(1)[0] if hour_counts else None
            if peak_hour:
                trends["patterns"].append(
                    {
                        "type": "daily",
                        "pattern": f"Peak activity at {peak_hour[0]}:00",
                        "strength": peak_hour[1] / sum(hour_counts.values()),
                    }
                )

        # Detect anomalies
        for metric_name, metric in metrics.items():
            benchmark = self.metric_definitions.get(metric_name, {}).get("benchmark", 0)
            if benchmark:
                deviation = abs(metric.value - benchmark) / benchmark
                if deviation > 0.5:  # 50% deviation
                    trends["anomalies"].append(
                        {
                            "metric": metric_name,
                            "value": metric.value,
                            "expected": benchmark,
                            "deviation": deviation,
                        }
                    )

        return trends

    async def _descriptive_analysis(
        self, data: dict[str, Any], metrics: dict[str, Metric], trends: dict[str, Any]
    ) -> list[Insight]:
        """Perform descriptive analysis - what happened."""
        insights = []

        # Activity summary
        activity_metric = metrics.get("activity_rate")
        if activity_metric:
            insights.append(
                Insight(
                    insight_id="desc_activity",
                    type="descriptive",
                    title="Activity Level Analysis",
                    description=f"You completed {activity_metric.value:.1f} activities per week",
                    impact="medium" if activity_metric.trend == "stable" else "high",
                    confidence=0.9,
                    supporting_data={
                        "metric_value": activity_metric.value,
                        "trend": activity_metric.trend,
                    },
                    recommendations=[],
                )
            )

        # Performance summary
        completion_metric = metrics.get("goal_completion")
        if completion_metric:
            insights.append(
                Insight(
                    insight_id="desc_performance",
                    type="descriptive",
                    title="Goal Achievement",
                    description=f"You achieved {completion_metric.value:.1f}% of your goals",
                    impact="high" if completion_metric.value > 80 else "medium",
                    confidence=0.95,
                    supporting_data={
                        "completion_rate": completion_metric.value,
                        "trend": completion_metric.trend,
                    },
                    recommendations=[],
                )
            )

        return insights

    async def _diagnostic_analysis(
        self, data: dict[str, Any], metrics: dict[str, Metric], trends: dict[str, Any]
    ) -> list[Insight]:
        """Perform diagnostic analysis - why it happened."""
        insights = []

        # Analyze low performance
        for metric_name, metric in metrics.items():
            if metric.trend == "down":
                # Identify potential causes
                causes = []

                if metric_name == "activity_rate":
                    causes = [
                        "Decreased time availability",
                        "Lower engagement",
                        "Competing priorities",
                    ]
                elif metric_name == "competency_growth":
                    causes = [
                        "Plateau in learning curve",
                        "Need for new challenges",
                        "Lack of structured learning",
                    ]

                if causes:
                    insights.append(
                        Insight(
                            insight_id=f"diag_{metric_name}",
                            type="diagnostic",
                            title=f"Analysis: Declining {metric.name}",
                            description=f"Your {metric.name} is declining. Potential causes identified.",
                            impact="high",
                            confidence=0.7,
                            supporting_data={
                                "metric": metric_name,
                                "value": metric.value,
                                "causes": causes,
                            },
                            recommendations=[
                                f"Address {causes[0]}",
                                "Review your goals and priorities",
                            ],
                        )
                    )

        # Analyze anomalies
        for anomaly in trends.get("anomalies", []):
            insights.append(
                Insight(
                    insight_id=f"diag_anomaly_{anomaly['metric']}",
                    type="diagnostic",
                    title=f"Unusual Pattern: {anomaly['metric']}",
                    description=f"Detected {anomaly['deviation']:.0%} deviation from expected",
                    impact="medium",
                    confidence=0.8,
                    supporting_data=anomaly,
                    recommendations=["Review recent changes", "Adjust expectations or approach"],
                )
            )

        return insights

    async def _predictive_analysis(
        self, data: dict[str, Any], metrics: dict[str, Metric], trends: dict[str, Any]
    ) -> dict[str, Any]:
        """Perform predictive analysis - what will happen."""
        predictions = {
            "next_30_days": {},
            "next_90_days": {},
            "risk_factors": [],
            "opportunities": [],
        }

        # Project metrics forward
        for metric_name, metric in metrics.items():
            # Simple linear projection (would use ML in production)
            if metric.trend == "up":
                growth_rate = 0.1  # 10% growth
            elif metric.trend == "down":
                growth_rate = -0.1  # 10% decline
            else:
                growth_rate = 0  # stable

            predictions["next_30_days"][metric_name] = metric.value * (1 + growth_rate)
            predictions["next_90_days"][metric_name] = metric.value * (1 + growth_rate * 3)

        # Identify risk factors
        if trends["overall_direction"] == "declining":
            predictions["risk_factors"].append(
                {
                    "risk": "Continued decline in engagement",
                    "probability": 0.6,
                    "impact": "high",
                    "mitigation": "Implement engagement recovery plan",
                }
            )

        if (
            metrics.get(
                "learning_velocity", Metric("", 0, "", MetricType.EFFICIENCY, datetime.now(UTC))
            ).value
            < 1
        ):
            predictions["risk_factors"].append(
                {
                    "risk": "Skills stagnation",
                    "probability": 0.7,
                    "impact": "medium",
                    "mitigation": "Enroll in structured learning program",
                }
            )

        # Identify opportunities
        if (
            metrics.get(
                "competency_growth", Metric("", 0, "", MetricType.GROWTH, datetime.now(UTC))
            ).value
            > 10
        ):
            predictions["opportunities"].append(
                {
                    "opportunity": "Ready for advanced roles",
                    "probability": 0.8,
                    "impact": "high",
                    "action": "Apply for senior positions",
                }
            )

        return predictions

    async def _prescriptive_analysis(
        self, data: dict[str, Any], metrics: dict[str, Metric], trends: dict[str, Any]
    ) -> list[Insight]:
        """Perform prescriptive analysis - what should be done."""
        insights = []

        # Generate actionable recommendations
        for metric_name, metric in metrics.items():
            if metric.trend == "down" or metric.value < self.metric_definitions.get(
                metric_name, {}
            ).get("benchmark", 0):
                actions = self._get_improvement_actions(metric_name, metric)

                if actions:
                    insights.append(
                        Insight(
                            insight_id=f"presc_{metric_name}",
                            type="prescriptive",
                            title=f"Action Plan: Improve {metric.name}",
                            description=f"Specific actions to improve your {metric.name}",
                            impact="high",
                            confidence=0.85,
                            supporting_data={
                                "current_value": metric.value,
                                "target_value": self.metric_definitions.get(metric_name, {}).get(
                                    "benchmark", 0
                                ),
                            },
                            recommendations=actions,
                        )
                    )

        # Overall optimization plan
        if trends["overall_direction"] != "improving":
            insights.append(
                Insight(
                    insight_id="presc_overall",
                    type="prescriptive",
                    title="Performance Optimization Plan",
                    description="Comprehensive plan to improve overall performance",
                    impact="high",
                    confidence=0.8,
                    supporting_data={
                        "current_direction": trends["overall_direction"],
                        "momentum": trends["momentum"],
                    },
                    recommendations=[
                        "Set specific, measurable weekly goals",
                        "Establish daily learning routine",
                        "Track progress with weekly reviews",
                        "Seek feedback and mentorship",
                        "Focus on high-impact activities",
                    ],
                )
            )

        return insights

    def _get_improvement_actions(self, metric_name: str, metric: Metric) -> list[str]:
        """Get specific improvement actions for a metric."""
        actions_map = {
            "activity_rate": [
                "Schedule dedicated time blocks for activities",
                "Set daily activity targets",
                "Use reminders and automation",
            ],
            "competency_growth": [
                "Take on stretch projects",
                "Pursue certifications",
                "Join communities of practice",
            ],
            "goal_completion": [
                "Break down large goals into smaller tasks",
                "Use SMART goal framework",
                "Review and adjust goals weekly",
            ],
            "learning_velocity": [
                "Follow structured learning paths",
                "Practice deliberate learning",
                "Apply new skills immediately",
            ],
            "engagement_score": [
                "Reconnect with your 'why'",
                "Celebrate small wins",
                "Find accountability partner",
            ],
        }

        return actions_map.get(metric_name, ["Review and adjust approach"])

    async def _generate_recommendations(
        self, insights: list[Insight], metrics: dict[str, Metric], trends: dict[str, Any]
    ) -> list[str]:
        """Generate overall recommendations."""
        recommendations = []

        # Priority 1: Address declining metrics
        declining_metrics = [m for m in metrics.values() if m.trend == "down"]
        if declining_metrics:
            recommendations.append(
                f"Focus on improving {declining_metrics[0].name} - currently trending down"
            )

        # Priority 2: Leverage strengths
        strong_metrics = [m for m in metrics.values() if m.trend == "up"]
        if strong_metrics:
            recommendations.append(
                f"Build on your strength in {strong_metrics[0].name} to accelerate growth"
            )

        # Priority 3: Address anomalies
        if trends.get("anomalies"):
            recommendations.append("Investigate and address unusual patterns in your metrics")

        # Priority 4: Optimize patterns
        if trends.get("patterns"):
            pattern = trends["patterns"][0]
            recommendations.append(f"Optimize your schedule around {pattern['pattern']}")

        # Priority 5: General improvement
        if trends["overall_direction"] != "improving":
            recommendations.append("Implement systematic improvement plan to reverse current trend")

        return recommendations[:5]  # Top 5 recommendations

    async def benchmark_performance(
        self, user_metrics: dict[str, Metric], user_level: str = "mid"
    ) -> dict[str, Any]:
        """Benchmark user performance against peers."""
        benchmarks = self.benchmarks.get(user_level, self.benchmarks["mid"])
        comparison = {}

        for metric_name, metric in user_metrics.items():
            benchmark_value = benchmarks.get(
                metric_name, self.metric_definitions.get(metric_name, {}).get("benchmark", 0)
            )

            if benchmark_value:
                percentile = self._calculate_percentile(metric.value, benchmark_value)
                comparison[metric_name] = {
                    "user_value": metric.value,
                    "benchmark": benchmark_value,
                    "percentile": percentile,
                    "rating": self._get_performance_rating(percentile),
                }

        return comparison

    def _calculate_percentile(self, value: float, benchmark: float) -> float:
        """Calculate percentile based on benchmark."""
        # Simplified - would use actual distribution in production
        if value >= benchmark * 1.5:
            return 90
        elif value >= benchmark * 1.2:
            return 75
        elif value >= benchmark:
            return 60
        elif value >= benchmark * 0.8:
            return 40
        else:
            return 25

    def _get_performance_rating(self, percentile: float) -> str:
        """Get performance rating based on percentile."""
        if percentile >= 90:
            return "exceptional"
        elif percentile >= 75:
            return "excellent"
        elif percentile >= 60:
            return "good"
        elif percentile >= 40:
            return "average"
        else:
            return "needs improvement"
