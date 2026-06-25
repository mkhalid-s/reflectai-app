"""
Date Range and Period Management for Reports

Implements  Flexible date range parsing, timezone handling,
assessment period configuration, and period comparison analytics.
"""

import calendar
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from src.shared import get_logger

logger = get_logger(__name__)


class PeriodType(str, Enum):
    """Standard period types"""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMI_ANNUAL = "semi_annual"
    ANNUAL = "annual"
    CUSTOM = "custom"


class FiscalYearStart(str, Enum):
    """Fiscal year start months"""

    JANUARY = "january"  # Calendar year
    APRIL = "april"  # Common fiscal year
    JULY = "july"  # Government fiscal year
    OCTOBER = "october"  # Many companies


@dataclass
class DateRange:
    """Date range with timezone and metadata"""

    start_date: datetime
    end_date: datetime
    timezone_name: str
    period_name: str
    period_type: PeriodType
    is_complete: bool = True
    data_availability: float = 1.0  # 0.0-1.0, percentage of expected data


@dataclass
class PeriodComparison:
    """Period-over-period comparison data"""

    current_period: DateRange
    comparison_period: DateRange
    comparison_type: str  # "previous", "year_over_year", "rolling"
    growth_rate: float | None = None
    trend_direction: str | None = None


@dataclass
class AssessmentPeriod:
    """Assessment period configuration"""

    name: str
    period_type: PeriodType
    start_date: datetime
    end_date: datetime
    is_active: bool
    progress_percentage: float
    days_remaining: int
    fiscal_year_aligned: bool = False


@dataclass
class UserDatePreferences:
    """User date preferences for reports"""

    user_id: str
    timezone: str
    preferred_periods: dict[str, str]  # report_type -> period
    custom_ranges: list[dict[str, Any]]
    fiscal_year_start: FiscalYearStart = FiscalYearStart.JANUARY
    date_format: str = "%Y-%m-%d"


class DateRangeManager:
    """
    Manages date ranges and periods for report generation.

    Implements Requirements:
    -  Natural language date processing
    -  Intelligent date defaults
    -  Timezone handling and user preferences
    -  Assessment period configuration
    -  Period comparison and trend analysis
    """

    def __init__(self):
        self._natural_language_patterns = self._load_nl_patterns()
        self._default_periods = self._load_default_periods()

        # Cache for user preferences
        self._user_preferences: dict[str, UserDatePreferences] = {}

    async def parse_date_expression(
        self, expression: str, user_timezone: str = "UTC", reference_date: datetime | None = None
    ) -> DateRange:
        """
        Parse natural language date expressions into date ranges.

        Args:
            expression: Natural language date expression
            user_timezone: User's timezone for calculations
            reference_date: Reference date for relative expressions

        Returns:
            Parsed date range with metadata
        """
        try:
            expression = expression.lower().strip()
            ref_date = reference_date or datetime.now(UTC)

            logger.debug(
                "Parsing date expression",
                extra={
                    "expression": expression,
                    "timezone": user_timezone,
                    "reference_date": ref_date.isoformat(),
                },
            )

            # Try specific patterns first
            for pattern_name, pattern_info in self._natural_language_patterns.items():
                for regex_pattern in pattern_info["patterns"]:
                    match = re.search(regex_pattern, expression)
                    if match:
                        date_range = await self._parse_pattern_match(
                            pattern_name, match, ref_date, user_timezone
                        )
                        if date_range:
                            return date_range

            # Try absolute date parsing
            date_range = await self._parse_absolute_dates(expression, user_timezone)
            if date_range:
                return date_range

            # Fallback to default period
            logger.warning(
                "Could not parse date expression, using default", extra={"expression": expression}
            )
            return await self._get_default_period("competency", user_timezone)

        except Exception as e:
            logger.error(
                "Failed to parse date expression", extra={"expression": expression, "error": str(e)}
            )
            # Return safe default
            return await self._get_default_period("competency", user_timezone)

    async def get_period_comparison(
        self, current_period: DateRange, comparison_type: str = "previous"
    ) -> PeriodComparison:
        """
        Generate period-over-period comparison data.

        Args:
            current_period: Current date range
            comparison_type: Type of comparison ("previous", "year_over_year", "rolling")

        Returns:
            Period comparison with calculated metrics
        """
        try:
            if comparison_type == "previous":
                comparison_period = await self._get_previous_period(current_period)
            elif comparison_type == "year_over_year":
                comparison_period = await self._get_year_over_year_period(current_period)
            elif comparison_type == "rolling":
                comparison_period = await self._get_rolling_period(current_period)
            else:
                raise ValueError(f"Unknown comparison type: {comparison_type}")

            return PeriodComparison(
                current_period=current_period,
                comparison_period=comparison_period,
                comparison_type=comparison_type,
            )

        except Exception as e:
            logger.error(
                "Failed to create period comparison",
                extra={"comparison_type": comparison_type, "error": str(e)},
            )
            raise

    async def get_assessment_periods(
        self, organization_id: str, year: int | None = None
    ) -> list[AssessmentPeriod]:
        """
        Get assessment periods for organization.

        Args:
            organization_id: Organization identifier
            year: Year for assessment periods (current year if None)

        Returns:
            List of assessment periods with progress
        """
        try:
            year = year or datetime.now().year

            # This would load from organization configuration
            # For now, return standard quarterly assessment periods
            assessment_periods = []

            for quarter in range(1, 5):
                start_month = (quarter - 1) * 3 + 1
                start_date = datetime(year, start_month, 1)

                # End of quarter
                if quarter == 4:
                    end_date = datetime(year, 12, 31, 23, 59, 59)
                else:
                    next_quarter_month = quarter * 3 + 1
                    end_date = datetime(year, next_quarter_month, 1) - timedelta(seconds=1)

                # Calculate progress
                now = datetime.now()
                if now > end_date:
                    progress = 100.0
                    days_remaining = 0
                    is_active = False
                elif now < start_date:
                    progress = 0.0
                    days_remaining = (start_date - now).days
                    is_active = False
                else:
                    total_days = (end_date - start_date).days
                    elapsed_days = (now - start_date).days
                    progress = min(100.0, (elapsed_days / total_days) * 100)
                    days_remaining = (end_date - now).days
                    is_active = True

                assessment_periods.append(
                    AssessmentPeriod(
                        name=f"Q{quarter} {year}",
                        period_type=PeriodType.QUARTERLY,
                        start_date=start_date,
                        end_date=end_date,
                        is_active=is_active,
                        progress_percentage=progress,
                        days_remaining=max(0, days_remaining),
                        fiscal_year_aligned=True,
                    )
                )

            return assessment_periods

        except Exception as e:
            logger.error(
                "Failed to get assessment periods",
                extra={"organization_id": organization_id, "year": year, "error": str(e)},
            )
            return []

    async def validate_date_range(
        self, date_range: DateRange, max_range_days: int = 365
    ) -> tuple[bool, str | None]:
        """
        Validate date range for data availability and business rules.

        Args:
            date_range: Date range to validate
            max_range_days: Maximum allowed range in days

        Returns:
            (is_valid, error_message)
        """
        try:
            # Check if range is too large
            range_days = (date_range.end_date - date_range.start_date).days
            if range_days > max_range_days:
                return (
                    False,
                    f"Date range too large ({range_days} days). Maximum allowed: {max_range_days} days.",
                )

            # Check if start date is after end date
            if date_range.start_date >= date_range.end_date:
                return False, "Start date must be before end date."

            # Check if dates are too far in the future
            now = datetime.now(UTC)
            if date_range.start_date > now:
                return False, "Start date cannot be in the future."

            # Check data availability (mock - would integrate with data service)
            if range_days < 7:
                date_range.data_availability = 0.9  # Less data for short periods
            elif range_days > 180:
                date_range.data_availability = 0.7  # Less data for very old periods
            else:
                date_range.data_availability = 1.0

            # Warn about low data availability
            if date_range.data_availability < 0.5:
                return (
                    True,
                    f"Limited data available for this period ({date_range.data_availability * 100:.0f}% coverage).",
                )

            return True, None

        except Exception as e:
            logger.error("Date range validation failed", extra={"error": str(e)})
            return False, f"Validation error: {str(e)}"

    async def get_user_preferences(self, user_id: str) -> UserDatePreferences:
        """Get user date preferences with defaults."""
        if user_id in self._user_preferences:
            return self._user_preferences[user_id]

        # Create default preferences
        preferences = UserDatePreferences(
            user_id=user_id,
            timezone="UTC",
            preferred_periods={
                "competency": "last_90_days",
                "career_development": "last_year",
                "executive_summary": "current_quarter",
                "team_analysis": "last_6_months",
            },
            custom_ranges=[],
        )

        self._user_preferences[user_id] = preferences
        return preferences

    async def update_user_preferences(self, user_id: str, preferences: dict[str, Any]):
        """Update user date preferences."""
        try:
            user_prefs = await self.get_user_preferences(user_id)

            if "timezone" in preferences:
                user_prefs.timezone = preferences["timezone"]

            if "preferred_periods" in preferences:
                user_prefs.preferred_periods.update(preferences["preferred_periods"])

            if "custom_ranges" in preferences:
                user_prefs.custom_ranges = preferences["custom_ranges"]

            if "fiscal_year_start" in preferences:
                user_prefs.fiscal_year_start = FiscalYearStart(preferences["fiscal_year_start"])

            logger.info(
                "User date preferences updated",
                extra={"user_id": user_id, "preferences": list(preferences.keys())},
            )

        except Exception as e:
            logger.error(
                "Failed to update user preferences", extra={"user_id": user_id, "error": str(e)}
            )
            raise

    def _load_nl_patterns(self) -> dict[str, dict[str, Any]]:
        """Load natural language parsing patterns."""
        return {
            "relative_days": {
                "patterns": [r"last (\d+) days?", r"past (\d+) days?", r"previous (\d+) days?"],
                "handler": "parse_relative_days",
            },
            "relative_weeks": {
                "patterns": [r"last (\d+) weeks?", r"past (\d+) weeks?", r"previous (\d+) weeks?"],
                "handler": "parse_relative_weeks",
            },
            "relative_months": {
                "patterns": [
                    r"last (\d+) months?",
                    r"past (\d+) months?",
                    r"previous (\d+) months?",
                ],
                "handler": "parse_relative_months",
            },
            "named_periods": {
                "patterns": [
                    r"this (week|month|quarter|year)",
                    r"last (week|month|quarter|year)",
                    r"current (week|month|quarter|year)",
                    r"previous (week|month|quarter|year)",
                ],
                "handler": "parse_named_periods",
            },
            "specific_months": {
                "patterns": [
                    r"(january|february|march|april|may|june|july|august|september|october|november|december) (\d{4})",
                    r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec) (\d{4})",
                ],
                "handler": "parse_specific_months",
            },
            "quarters": {
                "patterns": [r"q([1-4]) (\d{4})", r"quarter ([1-4]) (\d{4})", r"(\d{4}) q([1-4])"],
                "handler": "parse_quarters",
            },
            "year_to_date": {
                "patterns": [r"year.to.date", r"ytd", r"since january"],
                "handler": "parse_year_to_date",
            },
        }

    def _load_default_periods(self) -> dict[str, str]:
        """Load default periods for different report types."""
        return {
            "competency": "last_90_days",
            "career_development": "last_year",
            "executive_summary": "current_quarter",
            "team_analysis": "last_6_months",
        }

    async def _parse_pattern_match(
        self, pattern_name: str, match: re.Match, ref_date: datetime, timezone_name: str
    ) -> DateRange | None:
        """Parse matched pattern into date range."""
        try:
            if pattern_name == "relative_days":
                days = int(match.group(1))
                start_date = ref_date - timedelta(days=days)
                return DateRange(
                    start_date=start_date,
                    end_date=ref_date,
                    timezone_name=timezone_name,
                    period_name=f"Last {days} days",
                    period_type=PeriodType.DAILY,
                )

            elif pattern_name == "relative_weeks":
                weeks = int(match.group(1))
                start_date = ref_date - timedelta(weeks=weeks)
                return DateRange(
                    start_date=start_date,
                    end_date=ref_date,
                    timezone_name=timezone_name,
                    period_name=f"Last {weeks} weeks",
                    period_type=PeriodType.WEEKLY,
                )

            elif pattern_name == "relative_months":
                months = int(match.group(1))
                # Approximate months as 30 days each
                start_date = ref_date - timedelta(days=months * 30)
                return DateRange(
                    start_date=start_date,
                    end_date=ref_date,
                    timezone_name=timezone_name,
                    period_name=f"Last {months} months",
                    period_type=PeriodType.MONTHLY,
                )

            elif pattern_name == "named_periods":
                modifier = match.group(0).split()[0]  # "this", "last", etc.
                period = match.group(1)  # "week", "month", etc.

                return await self._parse_named_period(modifier, period, ref_date, timezone_name)

            elif pattern_name == "year_to_date":
                start_date = datetime(ref_date.year, 1, 1)
                return DateRange(
                    start_date=start_date,
                    end_date=ref_date,
                    timezone_name=timezone_name,
                    period_name=f"Year to Date {ref_date.year}",
                    period_type=PeriodType.ANNUAL,
                )

            return None

        except Exception as e:
            logger.error(
                "Failed to parse pattern match", extra={"pattern": pattern_name, "error": str(e)}
            )
            return None

    async def _parse_named_period(
        self, modifier: str, period: str, ref_date: datetime, timezone_name: str
    ) -> DateRange:
        """Parse named periods like 'this month', 'last quarter'."""

        if period == "week":
            # Start of week (Monday)
            days_since_monday = ref_date.weekday()
            week_start = ref_date - timedelta(days=days_since_monday)
            week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)

            if modifier in ["last", "previous"]:
                week_start -= timedelta(weeks=1)
                week_end -= timedelta(weeks=1)

            return DateRange(
                start_date=week_start,
                end_date=week_end,
                timezone_name=timezone_name,
                period_name=f"{modifier.title()} week",
                period_type=PeriodType.WEEKLY,
            )

        elif period == "month":
            if modifier in ["last", "previous"]:
                # Last month
                last_month = ref_date.replace(day=1) - timedelta(days=1)
                start_date = last_month.replace(day=1)
                end_date = datetime(
                    last_month.year,
                    last_month.month,
                    calendar.monthrange(last_month.year, last_month.month)[1],
                    23,
                    59,
                    59,
                )
            else:
                # This/current month
                start_date = ref_date.replace(day=1)
                end_date = datetime(
                    ref_date.year,
                    ref_date.month,
                    calendar.monthrange(ref_date.year, ref_date.month)[1],
                    23,
                    59,
                    59,
                )

            return DateRange(
                start_date=start_date,
                end_date=end_date,
                timezone_name=timezone_name,
                period_name=f"{modifier.title()} month",
                period_type=PeriodType.MONTHLY,
            )

        elif period == "quarter":
            current_quarter = (ref_date.month - 1) // 3 + 1

            if modifier in ["last", "previous"]:
                if current_quarter == 1:
                    quarter = 4
                    year = ref_date.year - 1
                else:
                    quarter = current_quarter - 1
                    year = ref_date.year
            else:
                quarter = current_quarter
                year = ref_date.year

            quarter_start_month = (quarter - 1) * 3 + 1
            start_date = datetime(year, quarter_start_month, 1)

            # End of quarter
            if quarter == 4:
                end_date = datetime(year, 12, 31, 23, 59, 59)
            else:
                next_quarter_month = quarter * 3 + 1
                end_date = datetime(year, next_quarter_month, 1) - timedelta(seconds=1)

            return DateRange(
                start_date=start_date,
                end_date=end_date,
                timezone_name=timezone_name,
                period_name=f"{modifier.title()} quarter (Q{quarter} {year})",
                period_type=PeriodType.QUARTERLY,
            )

        elif period == "year":
            if modifier in ["last", "previous"]:
                year = ref_date.year - 1
            else:
                year = ref_date.year

            start_date = datetime(year, 1, 1)
            end_date = datetime(year, 12, 31, 23, 59, 59)

            return DateRange(
                start_date=start_date,
                end_date=end_date,
                timezone_name=timezone_name,
                period_name=f"{modifier.title()} year ({year})",
                period_type=PeriodType.ANNUAL,
            )

        raise ValueError(f"Unknown period: {period}")

    async def _parse_absolute_dates(self, expression: str, timezone_name: str) -> DateRange | None:
        """Try to parse absolute date expressions."""
        # Look for patterns like "2024-01-01 to 2024-03-31"
        date_range_pattern = r"(\d{4}-\d{2}-\d{2})\s*to\s*(\d{4}-\d{2}-\d{2})"
        match = re.search(date_range_pattern, expression)

        if match:
            try:
                start_str, end_str = match.groups()
                start_date = datetime.strptime(start_str, "%Y-%m-%d")
                end_date = datetime.strptime(end_str, "%Y-%m-%d")
                end_date = end_date.replace(hour=23, minute=59, second=59)

                return DateRange(
                    start_date=start_date,
                    end_date=end_date,
                    timezone_name=timezone_name,
                    period_name=f"{start_str} to {end_str}",
                    period_type=PeriodType.CUSTOM,
                )
            except ValueError:
                pass

        return None

    async def _get_default_period(self, report_type: str, timezone_name: str) -> DateRange:
        """Get default period for report type."""
        period_name = self._default_periods.get(report_type, "last_90_days")

        # Parse the default period name
        now = datetime.now(UTC)

        if period_name == "last_90_days":
            start_date = now - timedelta(days=90)
            return DateRange(
                start_date=start_date,
                end_date=now,
                timezone_name=timezone_name,
                period_name="Last 90 days (default)",
                period_type=PeriodType.DAILY,
            )

        # Add other default periods as needed
        return DateRange(
            start_date=now - timedelta(days=30),
            end_date=now,
            timezone_name=timezone_name,
            period_name="Last 30 days (fallback)",
            period_type=PeriodType.DAILY,
        )

    async def _get_previous_period(self, current: DateRange) -> DateRange:
        """Get previous period of same duration."""
        duration = current.end_date - current.start_date

        return DateRange(
            start_date=current.start_date - duration,
            end_date=current.start_date,
            timezone_name=current.timezone_name,
            period_name=f"Previous {current.period_name.lower()}",
            period_type=current.period_type,
        )

    async def _get_year_over_year_period(self, current: DateRange) -> DateRange:
        """Get same period from previous year."""
        start_prev_year = current.start_date.replace(year=current.start_date.year - 1)
        end_prev_year = current.end_date.replace(year=current.end_date.year - 1)

        return DateRange(
            start_date=start_prev_year,
            end_date=end_prev_year,
            timezone_name=current.timezone_name,
            period_name=f"{current.period_name} (previous year)",
            period_type=current.period_type,
        )

    async def _get_rolling_period(self, current: DateRange) -> DateRange:
        """Get rolling period ending before current period starts."""
        duration = current.end_date - current.start_date

        return DateRange(
            start_date=current.start_date - duration,
            end_date=current.start_date,
            timezone_name=current.timezone_name,
            period_name=f"Rolling {current.period_name.lower()}",
            period_type=current.period_type,
        )
