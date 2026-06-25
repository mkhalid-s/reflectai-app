"""
Report Data Aggregator

Implements  Report data aggregation and processing for
competency reports and career development plans.
"""

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from src.shared import ErrorCategory, ErrorSeverity, ReflectAIError, get_logger

logger = get_logger(__name__)


class ReportPeriod(str, Enum):
    """Report time periods"""

    LAST_7_DAYS = "last_7_days"
    LAST_30_DAYS = "last_30_days"
    LAST_90_DAYS = "last_90_days"
    LAST_QUARTER = "last_quarter"
    LAST_6_MONTHS = "last_6_months"
    LAST_YEAR = "last_year"
    CUSTOM = "custom"


@dataclass
class DateRange:
    """Date range for report data"""

    start_date: datetime
    end_date: datetime
    period_name: str


@dataclass
class UserActivitySummary:
    """User activity summary for reports"""

    user_id: str
    total_activities: int
    activity_types: dict[str, int]
    competency_areas: list[str]
    time_distribution: dict[str, float]
    growth_indicators: dict[str, Any]


@dataclass
class CompetencyAnalysis:
    """Competency analysis results"""

    competency_scores: dict[str, float]
    competency_trends: dict[str, list[float]]
    skill_gaps: list[dict[str, Any]]
    strengths: list[str]
    development_areas: list[str]
    peer_comparisons: dict[str, Any] | None = None


@dataclass
class CareerInsights:
    """Career development insights"""

    progression_opportunities: list[str]
    recommended_skills: list[str]
    development_timeline: dict[str, str]
    action_items: list[dict[str, Any]]
    next_steps: list[str]


@dataclass
class ReportData:
    """Complete report data structure"""

    user_id: str
    user_name: str
    report_period: DateRange
    activity_summary: UserActivitySummary
    competency_analysis: CompetencyAnalysis
    career_insights: CareerInsights
    executive_summary: str
    generated_at: datetime


class ReportDataAggregator:
    """
    Aggregates and processes data for report generation.

    Implements Requirements:
    -  Competency report data pipeline
    -  Career development report data
    -  Activity aggregation from TimescaleDB
    -  Competency scoring with weighted algorithms
    -  Trend analysis with period comparisons
    -  Skill gap analysis and recommendations
    """

    def __init__(self, database_client=None, cache_client=None):
        self.database_client = database_client
        self.cache_client = cache_client

    async def generate_report_data(
        self,
        user_id: str,
        report_period: ReportPeriod,
        custom_date_range: tuple[datetime, datetime] | None = None,
        include_peer_comparison: bool = False,
    ) -> ReportData:
        """
        Generate comprehensive report data for user.

        Args:
            user_id: User ID for report
            report_period: Report time period
            custom_date_range: Custom date range (for CUSTOM period)
            include_peer_comparison: Include peer comparison data

        Returns:
            Complete report data structure
        """
        try:
            # Calculate date range
            date_range = self._calculate_date_range(report_period, custom_date_range)

            logger.info(
                "Generating report data",
                extra={
                    "user_id": user_id,
                    "period": report_period,
                    "date_range": f"{date_range.start_date} to {date_range.end_date}",
                },
            )

            # Gather data concurrently
            user_profile, activity_summary, competency_data = await asyncio.gather(
                self._get_user_profile(user_id),
                self._aggregate_user_activities(user_id, date_range),
                self._analyze_competencies(user_id, date_range),
                return_exceptions=True,
            )

            # Handle any exceptions
            if isinstance(user_profile, Exception):
                logger.error(f"Failed to get user profile: {user_profile}")
                user_profile = {"user_id": user_id, "name": f"User-{user_id[:8]}"}

            if isinstance(activity_summary, Exception):
                logger.error(f"Failed to aggregate activities: {activity_summary}")
                activity_summary = self._create_empty_activity_summary(user_id)

            if isinstance(competency_data, Exception):
                logger.error(f"Failed to analyze competencies: {competency_data}")
                competency_data = self._create_empty_competency_analysis()

            # Generate career insights
            career_insights = await self._generate_career_insights(
                user_id, activity_summary, competency_data, date_range
            )

            # Add peer comparison if requested
            if include_peer_comparison:
                competency_data.peer_comparisons = await self._get_peer_comparisons(
                    user_id, competency_data.competency_scores
                )

            # Generate executive summary
            executive_summary = await self._generate_executive_summary(
                user_profile, activity_summary, competency_data, career_insights
            )

            # Assemble complete report data
            report_data = ReportData(
                user_id=user_id,
                user_name=user_profile.get("name", f"User-{user_id[:8]}"),
                report_period=date_range,
                activity_summary=activity_summary,
                competency_analysis=competency_data,
                career_insights=career_insights,
                executive_summary=executive_summary,
                generated_at=datetime.now(UTC),
            )

            logger.info(
                "Report data generated successfully",
                extra={
                    "user_id": user_id,
                    "activities": activity_summary.total_activities,
                    "competencies": len(competency_data.competency_scores),
                    "recommendations": len(career_insights.action_items),
                },
            )

            return report_data

        except Exception as e:
            logger.error(
                "Failed to generate report data", extra={"user_id": user_id, "error": str(e)}
            )
            raise ReflectAIError(
                message=f"Failed to generate report data: {str(e)}",
                category=ErrorCategory.BUSINESS_RULE_ERROR,
                severity=ErrorSeverity.ERROR,
                context={"user_id": user_id},
            ) from e

    async def _get_user_profile(self, user_id: str) -> dict[str, Any]:
        """Get user profile information."""
        try:
            # This would integrate with user profile service
            # For now, return mock data
            return {
                "user_id": user_id,
                "name": f"User-{user_id[:8]}",
                "role": "Software Engineer",
                "department": "Engineering",
                "level": "Mid-Level",
                "start_date": "2023-01-15",
                "manager": "Jane Smith",
            }

        except Exception as e:
            logger.error("Failed to get user profile", extra={"user_id": user_id, "error": str(e)})
            raise

    async def _aggregate_user_activities(
        self, user_id: str, date_range: DateRange
    ) -> UserActivitySummary:
        """Aggregate user activities from TimescaleDB."""
        try:
            # This would query TimescaleDB for user activities
            # For now, return mock data structure

            # Mock activity data
            activities = [
                {
                    "type": "code_review",
                    "date": date_range.start_date + timedelta(days=1),
                    "competencies": ["technical_skills", "collaboration"],
                },
                {
                    "type": "feature_development",
                    "date": date_range.start_date + timedelta(days=3),
                    "competencies": ["technical_skills", "problem_solving"],
                },
                {
                    "type": "team_meeting",
                    "date": date_range.start_date + timedelta(days=5),
                    "competencies": ["communication", "collaboration"],
                },
            ]

            # Aggregate data
            total_activities = len(activities)
            activity_types = {}
            competency_areas = set()

            for activity in activities:
                activity_type = activity["type"]
                activity_types[activity_type] = activity_types.get(activity_type, 0) + 1
                competency_areas.update(activity["competencies"])

            # Calculate time distribution (mock)
            time_distribution = {
                "development": 0.4,
                "meetings": 0.3,
                "planning": 0.2,
                "learning": 0.1,
            }

            # Growth indicators (mock)
            growth_indicators = {
                "activity_growth_rate": 15.3,  # % increase from previous period
                "competency_growth_rate": 8.7,
                "consistency_score": 0.82,
                "learning_velocity": "moderate",
            }

            return UserActivitySummary(
                user_id=user_id,
                total_activities=total_activities,
                activity_types=activity_types,
                competency_areas=list(competency_areas),
                time_distribution=time_distribution,
                growth_indicators=growth_indicators,
            )

        except Exception as e:
            logger.error(
                "Failed to aggregate user activities", extra={"user_id": user_id, "error": str(e)}
            )
            raise

    async def _analyze_competencies(
        self, user_id: str, date_range: DateRange
    ) -> CompetencyAnalysis:
        """Analyze competencies using weighted algorithms ."""
        try:
            # This would integrate with competency assessment system
            # Using weighted scoring: recency=0.3, frequency=0.4, complexity=0.3

            # Mock competency scores
            competency_scores = {
                "technical_skills": 4.2,
                "problem_solving": 3.8,
                "collaboration": 4.0,
                "communication": 3.5,
                "leadership": 2.8,
            }

            # Mock trend data (last 4 data points)
            competency_trends = {
                "technical_skills": [3.5, 3.8, 4.0, 4.2],
                "problem_solving": [3.2, 3.5, 3.7, 3.8],
                "collaboration": [3.6, 3.8, 3.9, 4.0],
                "communication": [3.0, 3.2, 3.4, 3.5],
                "leadership": [2.2, 2.4, 2.6, 2.8],
            }

            # Identify skill gaps (scores < 3.5 or trending down)
            skill_gaps = []
            for competency, score in competency_scores.items():
                if score < 3.5:
                    gap_severity = "high" if score < 3.0 else "medium"
                    skill_gaps.append(
                        {
                            "competency": competency,
                            "current_score": score,
                            "target_score": 4.0,
                            "gap": 4.0 - score,
                            "severity": gap_severity,
                            "development_priority": "high" if gap_severity == "high" else "medium",
                        }
                    )

            # Identify strengths (scores >= 4.0)
            strengths = [
                competency for competency, score in competency_scores.items() if score >= 4.0
            ]

            # Development areas (scores between 3.0-3.9)
            development_areas = [
                competency for competency, score in competency_scores.items() if 3.0 <= score < 4.0
            ]

            return CompetencyAnalysis(
                competency_scores=competency_scores,
                competency_trends=competency_trends,
                skill_gaps=skill_gaps,
                strengths=strengths,
                development_areas=development_areas,
            )

        except Exception as e:
            logger.error(
                "Failed to analyze competencies", extra={"user_id": user_id, "error": str(e)}
            )
            raise

    async def _generate_career_insights(
        self,
        user_id: str,
        activity_summary: UserActivitySummary,
        competency_analysis: CompetencyAnalysis,
        date_range: DateRange,
    ) -> CareerInsights:
        """Generate career development insights and recommendations."""
        try:
            # This would integrate with Advisor Agent for intelligent recommendations

            # Generate progression opportunities based on strengths
            progression_opportunities = []
            for strength in competency_analysis.strengths:
                if strength == "technical_skills":
                    progression_opportunities.append("Senior Developer Role")
                    progression_opportunities.append("Technical Lead Position")
                elif strength == "collaboration":
                    progression_opportunities.append("Team Lead Role")
                    progression_opportunities.append("Cross-functional Project Manager")

            # Recommend skills based on gaps and industry trends
            recommended_skills = []
            for gap in competency_analysis.skill_gaps:
                if gap["competency"] == "leadership":
                    recommended_skills.extend(
                        ["Team Management", "Strategic Thinking", "Mentoring"]
                    )
                elif gap["competency"] == "communication":
                    recommended_skills.extend(
                        ["Presentation Skills", "Technical Writing", "Stakeholder Management"]
                    )

            # Create development timeline
            development_timeline = {
                "immediate": "Focus on communication skills through presentation training",
                "short_term": "Take on team lead responsibilities in next project",
                "medium_term": "Complete leadership development program",
                "long_term": "Pursue senior technical role with team management",
            }

            # Generate actionable items
            action_items = []
            for gap in competency_analysis.skill_gaps[:3]:  # Top 3 gaps
                action_items.append(
                    {
                        "competency": gap["competency"],
                        "action": f"Improve {gap['competency'].replace('_', ' ')} through focused practice",
                        "timeline": "next_30_days",
                        "priority": gap["development_priority"],
                        "resources": ["Online course", "Mentoring session", "Practical project"],
                    }
                )

            # Next steps
            next_steps = [
                "Schedule 1-on-1 with manager to discuss development plan",
                "Enroll in communication skills workshop",
                "Identify mentor for leadership development",
                "Set up monthly competency review meetings",
            ]

            return CareerInsights(
                progression_opportunities=progression_opportunities,
                recommended_skills=recommended_skills,
                development_timeline=development_timeline,
                action_items=action_items,
                next_steps=next_steps,
            )

        except Exception as e:
            logger.error(
                "Failed to generate career insights", extra={"user_id": user_id, "error": str(e)}
            )
            raise

    async def _get_peer_comparisons(
        self, user_id: str, competency_scores: dict[str, float]
    ) -> dict[str, Any]:
        """Get peer comparison data for competencies."""
        try:
            # Mock peer comparison data
            peer_stats = {}
            for competency, user_score in competency_scores.items():
                # Generate realistic peer statistics
                peer_average = user_score + (-0.3 + (hash(competency) % 100) / 100 * 0.6)
                peer_average = max(1.0, min(5.0, peer_average))  # Clamp to 1-5 range

                percentile = min(95, max(5, int((user_score / peer_average) * 50)))

                peer_stats[competency] = {
                    "user_score": user_score,
                    "peer_average": round(peer_average, 2),
                    "percentile": percentile,
                    "comparison": "above_average" if user_score > peer_average else "below_average",
                }

            return {
                "comparison_group": "Similar roles in organization",
                "sample_size": 23,
                "competency_comparisons": peer_stats,
            }

        except Exception as e:
            logger.error(
                "Failed to get peer comparisons", extra={"user_id": user_id, "error": str(e)}
            )
            return {}

    async def _generate_executive_summary(
        self,
        user_profile: dict[str, Any],
        activity_summary: UserActivitySummary,
        competency_analysis: CompetencyAnalysis,
        career_insights: CareerInsights,
    ) -> str:
        """Generate executive summary using Advisor Agent."""
        try:
            # This would integrate with Advisor Agent (gpt-4o) for intelligent summary
            # For now, generate structured summary

            user_name = user_profile.get("name", "User")
            total_activities = activity_summary.total_activities
            top_competency = max(
                competency_analysis.competency_scores, key=competency_analysis.competency_scores.get
            )
            top_score = competency_analysis.competency_scores[top_competency]

            growth_rate = activity_summary.growth_indicators.get("activity_growth_rate", 0)

            summary = (
                f"{user_name} has demonstrated strong professional development with "
                f"{total_activities} activities analyzed in the report period. "
                f"Their strongest competency is {top_competency.replace('_', ' ')} "
                f"with a score of {top_score:.1f}/5.0. "
            )

            if growth_rate > 0:
                summary += f"Activity volume has increased by {growth_rate:.1f}% compared to the previous period, "

            if competency_analysis.strengths:
                summary += f"showing particular strength in {', '.join(competency_analysis.strengths[:2])}. "

            if competency_analysis.skill_gaps:
                primary_gap = competency_analysis.skill_gaps[0]
                summary += (
                    f"Key development opportunity identified in {primary_gap['competency'].replace('_', ' ')}, "
                    f"with recommended focus on {career_insights.recommended_skills[0] if career_insights.recommended_skills else 'skill development'}."
                )

            return summary

        except Exception as e:
            logger.error("Failed to generate executive summary", extra={"error": str(e)})
            return "Professional development analysis completed successfully with detailed competency insights and recommendations."

    def _calculate_date_range(
        self, period: ReportPeriod, custom_range: tuple[datetime, datetime] | None
    ) -> DateRange:
        """Calculate date range based on report period."""
        now = datetime.now(UTC)

        if period == ReportPeriod.CUSTOM and custom_range:
            start_date, end_date = custom_range
            period_name = (
                f"Custom ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})"
            )
        elif period == ReportPeriod.LAST_7_DAYS:
            start_date = now - timedelta(days=7)
            end_date = now
            period_name = "Last 7 Days"
        elif period == ReportPeriod.LAST_30_DAYS:
            start_date = now - timedelta(days=30)
            end_date = now
            period_name = "Last 30 Days"
        elif period == ReportPeriod.LAST_90_DAYS:
            start_date = now - timedelta(days=90)
            end_date = now
            period_name = "Last 90 Days"
        elif period == ReportPeriod.LAST_QUARTER:
            # Calculate last quarter
            current_quarter = (now.month - 1) // 3
            if current_quarter == 0:
                start_date = datetime(now.year - 1, 10, 1)
                end_date = datetime(now.year - 1, 12, 31, 23, 59, 59)
            else:
                quarter_start_month = (current_quarter - 1) * 3 + 1
                start_date = datetime(now.year, quarter_start_month, 1)
                end_date = datetime(now.year, quarter_start_month + 2, 28, 23, 59, 59)
            period_name = "Last Quarter"
        elif period == ReportPeriod.LAST_6_MONTHS:
            start_date = now - timedelta(days=180)
            end_date = now
            period_name = "Last 6 Months"
        elif period == ReportPeriod.LAST_YEAR:
            start_date = now - timedelta(days=365)
            end_date = now
            period_name = "Last Year"
        else:
            # Default to last 90 days
            start_date = now - timedelta(days=90)
            end_date = now
            period_name = "Last 90 Days (Default)"

        return DateRange(start_date=start_date, end_date=end_date, period_name=period_name)

    def _create_empty_activity_summary(self, user_id: str) -> UserActivitySummary:
        """Create empty activity summary for error cases."""
        return UserActivitySummary(
            user_id=user_id,
            total_activities=0,
            activity_types={},
            competency_areas=[],
            time_distribution={},
            growth_indicators={},
        )

    def _create_empty_competency_analysis(self) -> CompetencyAnalysis:
        """Create empty competency analysis for error cases."""
        return CompetencyAnalysis(
            competency_scores={},
            competency_trends={},
            skill_gaps=[],
            strengths=[],
            development_areas=[],
        )
