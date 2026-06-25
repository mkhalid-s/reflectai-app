"""
Date Range Extraction for ReflectAI

Extracts date ranges from natural language user input for report generation.
Supports various formats:
- Relative: "last 30 days", "past 2 weeks", "last 3 months"
- This/Last periods: "this month", "last quarter", "this year"
- Quarters: "Q1 2025", "Q2", "first quarter"
- Year to date: "ytd", "year to date"
- Month names: "January", "Sep 2024", "October 2025"
- Date ranges: "Jan 1 to Mar 31", "January 1 - March 31"
- Since expressions: "since January", "since last month"

This component is critical for enabling natural language date range parsing
across all report generation workflows.
"""

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from dateutil.relativedelta import relativedelta

from src.shared import get_logger


class DateRangeType(Enum):
    """Types of date ranges that can be extracted"""

    RELATIVE_DAYS = "relative_days"
    RELATIVE_WEEKS = "relative_weeks"
    RELATIVE_MONTHS = "relative_months"
    THIS_PERIOD = "this_period"
    LAST_PERIOD = "last_period"
    QUARTER = "quarter"
    YEAR_TO_DATE = "ytd"
    MONTH_NAME = "month_name"
    EXPLICIT_RANGE = "explicit_range"
    FISCAL_YEAR = "fiscal_year"
    SINCE = "since"
    DEFAULT = "default"


@dataclass
class DateRange:
    """Represents an extracted date range"""

    start_date: datetime
    end_date: datetime
    days_span: int
    range_type: DateRangeType
    confidence: float  # 0.0-1.0
    original_text: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "days_span": self.days_span,
            "range_type": self.range_type.value,
            "confidence": self.confidence,
            "original_text": self.original_text,
        }


class DateRangeExtractor:
    """
    Extract date ranges from natural language text.

    Uses pattern matching and context analysis to identify and extract
    date ranges from user messages. Provides confidence scoring for
    routing and fallback logic.

    Usage:
        extractor = get_date_range_extractor()
        result = await extractor.extract_date_range(
            "Generate report for last 30 days",
            user_context={"timezone": "UTC"}
        )
    """

    def __init__(self, reference_date: datetime | None = None):
        """
        Initialize date range extractor.

        Args:
            reference_date: Reference date for relative calculations (defaults to now)
        """
        self.logger = get_logger("classification.date_range")
        self.reference_date = reference_date or datetime.now(UTC)
        self._compile_patterns()

        # Month name to number mapping
        self.month_map = {
            "january": 1,
            "jan": 1,
            "february": 2,
            "feb": 2,
            "march": 3,
            "mar": 3,
            "april": 4,
            "apr": 4,
            "may": 5,
            "june": 6,
            "jun": 6,
            "july": 7,
            "jul": 7,
            "august": 8,
            "aug": 8,
            "september": 9,
            "sep": 9,
            "sept": 9,
            "october": 10,
            "oct": 10,
            "november": 11,
            "nov": 11,
            "december": 12,
            "dec": 12,
        }

    def _compile_patterns(self) -> None:
        """Compile regex patterns for date extraction"""

        # Relative days: "last 30 days", "past 7 days"
        self.relative_days_pattern = re.compile(
            r"\b(?:last|past|previous)\s+(\d+)\s+days?\b", re.IGNORECASE
        )

        # Relative weeks: "last 2 weeks", "past 3 weeks"
        self.relative_weeks_pattern = re.compile(
            r"\b(?:last|past|previous)\s+(\d+)\s+weeks?\b", re.IGNORECASE
        )

        # Relative months: "last 3 months", "past 6 months"
        self.relative_months_pattern = re.compile(
            r"\b(?:last|past|previous)\s+(\d+)\s+months?\b", re.IGNORECASE
        )

        # This period: "this week", "this month", "this quarter", "this year"
        self.this_period_pattern = re.compile(
            r"\bthis\s+(week|month|quarter|year)\b", re.IGNORECASE
        )

        # Last period: "last week", "last month", "last quarter", "last year"
        self.last_period_pattern = re.compile(
            r"\blast\s+(week|month|quarter|year)\b", re.IGNORECASE
        )

        # Quarter: "Q1", "Q2 2025", "first quarter"
        self.quarter_pattern = re.compile(
            r"\b(?:Q([1-4])|([1-4])(?:st|nd|rd|th)\s+quarter)(?:\s+(\d{4}))?\b", re.IGNORECASE
        )

        # Year to date: "ytd", "year to date"
        self.ytd_pattern = re.compile(r"\b(?:ytd|year\s+to\s+date)\b", re.IGNORECASE)

        # Month names: "January", "Sep 2024", "October 2025"
        self.month_name_pattern = re.compile(
            r"\b(january|jan|february|feb|march|mar|april|apr|may|june|jun|"
            r"july|jul|august|aug|september|sep|sept|october|oct|november|nov|december|dec)"
            r"(?:\s+(\d{4}))?\b",
            re.IGNORECASE,
        )

        # Explicit date range: "Jan 1 to Mar 31", "January 1 - March 31"
        self.date_range_pattern = re.compile(
            r"\b(january|jan|february|feb|march|mar|april|apr|may|june|jun|"
            r"july|jul|august|aug|september|sep|sept|october|oct|november|nov|december|dec)"
            r"\s+(\d{1,2})(?:\s+(\d{4}))?\s+(?:to|-)\s+"
            r"(january|jan|february|feb|march|mar|april|apr|may|june|jun|"
            r"july|jul|august|aug|september|sep|sept|october|oct|november|nov|december|dec)"
            r"\s+(\d{1,2})(?:\s+(\d{4}))?\b",
            re.IGNORECASE,
        )

        # Since expressions: "since January", "since last month"
        self.since_pattern = re.compile(
            r"\bsince\s+(january|jan|february|feb|march|mar|april|apr|may|june|jun|"
            r"july|jul|august|aug|september|sep|sept|october|oct|november|nov|december|dec|"
            r"last\s+(?:week|month|quarter|year))\b",
            re.IGNORECASE,
        )

        # Fiscal year: "fiscal year", "FY2025", "FY 2025"
        self.fiscal_pattern = re.compile(r"\b(?:fiscal\s+year|FY)(?:\s*(\d{4}))?\b", re.IGNORECASE)

    async def extract_date_range(
        self, text: str, user_context: dict[str, Any] | None = None
    ) -> DateRange | None:
        """
        Extract date range from text.

        Tries extractors in priority order, returning the first match
        with sufficient confidence.

        Args:
            text: User input text
            user_context: Optional user context (timezone, preferences)

        Returns:
            DateRange if found, None otherwise
        """
        if not text:
            return None

        text_lower = text.lower()

        # Try extractors in priority order (most specific first)
        extractors = [
            self._extract_date_range,  # Most specific: "Jan 1 to Mar 31"
            self._extract_quarter,  # Specific: "Q1 2025"
            self._extract_ytd,  # Specific: "ytd"
            self._extract_since,  # Specific: "since January", "since last month" (must be before last_period!)
            self._extract_relative_days,  # Common: "last 30 days"
            self._extract_relative_weeks,  # Common: "last 2 weeks"
            self._extract_relative_months,  # Common: "last 3 months"
            self._extract_this_period,  # Common: "this month"
            self._extract_last_period,  # Common: "last quarter"
            self._extract_month_name,  # Moderate: "January"
            self._extract_fiscal,  # Less common: "fiscal year"
        ]

        for extractor in extractors:
            try:
                result = extractor(text, text_lower)
                if result:
                    self.logger.info(
                        f"Extracted date range: {result.original_text}",
                        extra={
                            "range_type": result.range_type.value,
                            "start": result.start_date.isoformat(),
                            "end": result.end_date.isoformat(),
                            "days": result.days_span,
                            "confidence": result.confidence,
                        },
                    )
                    return result
            except Exception as e:
                self.logger.warning(f"Date extraction error in {extractor.__name__}: {e}")
                continue

        self.logger.debug("No date range found in text")
        return None

    def _extract_relative_days(self, text: str, text_lower: str) -> DateRange | None:
        """Extract relative days: 'last 30 days', 'past 7 days'"""
        match = self.relative_days_pattern.search(text_lower)
        if not match:
            return None

        days = int(match.group(1))
        end_date = self.reference_date
        start_date = end_date - timedelta(days=days)

        return DateRange(
            start_date=start_date,
            end_date=end_date,
            days_span=days,
            range_type=DateRangeType.RELATIVE_DAYS,
            confidence=0.95,
            original_text=match.group(0),
        )

    def _extract_relative_weeks(self, text: str, text_lower: str) -> DateRange | None:
        """Extract relative weeks: 'last 2 weeks', 'past 3 weeks'"""
        match = self.relative_weeks_pattern.search(text_lower)
        if not match:
            return None

        weeks = int(match.group(1))
        days = weeks * 7
        end_date = self.reference_date
        start_date = end_date - timedelta(days=days)

        return DateRange(
            start_date=start_date,
            end_date=end_date,
            days_span=days,
            range_type=DateRangeType.RELATIVE_WEEKS,
            confidence=0.95,
            original_text=match.group(0),
        )

    def _extract_relative_months(self, text: str, text_lower: str) -> DateRange | None:
        """Extract relative months: 'last 3 months', 'past 6 months'"""
        match = self.relative_months_pattern.search(text_lower)
        if not match:
            return None

        months = int(match.group(1))
        end_date = self.reference_date
        start_date = end_date - relativedelta(months=months)
        days_span = (end_date - start_date).days

        return DateRange(
            start_date=start_date,
            end_date=end_date,
            days_span=days_span,
            range_type=DateRangeType.RELATIVE_MONTHS,
            confidence=0.95,
            original_text=match.group(0),
        )

    def _extract_this_period(self, text: str, text_lower: str) -> DateRange | None:
        """Extract 'this' periods: 'this week', 'this month', 'this quarter', 'this year'"""
        match = self.this_period_pattern.search(text_lower)
        if not match:
            return None

        period = match.group(1).lower()
        end_date = self.reference_date

        if period == "week":
            # Start of current week (Monday)
            start_date = end_date - timedelta(days=end_date.weekday())
        elif period == "month":
            # Start of current month
            start_date = end_date.replace(day=1)
        elif period == "quarter":
            # Start of current quarter
            current_month = end_date.month
            quarter_start_month = ((current_month - 1) // 3) * 3 + 1
            start_date = end_date.replace(month=quarter_start_month, day=1)
        elif period == "year":
            # Start of current year
            start_date = end_date.replace(month=1, day=1)
        else:
            return None

        days_span = (end_date - start_date).days

        return DateRange(
            start_date=start_date,
            end_date=end_date,
            days_span=days_span,
            range_type=DateRangeType.THIS_PERIOD,
            confidence=0.90,
            original_text=match.group(0),
        )

    def _extract_last_period(self, text: str, text_lower: str) -> DateRange | None:
        """Extract 'last' periods: 'last week', 'last month', 'last quarter', 'last year'"""
        match = self.last_period_pattern.search(text_lower)
        if not match:
            return None

        period = match.group(1).lower()

        if period == "week":
            # Last week (Monday to Sunday)
            end_date = self.reference_date - timedelta(days=self.reference_date.weekday() + 1)
            start_date = end_date - timedelta(days=6)
        elif period == "month":
            # Last month (1st to last day)
            first_of_this_month = self.reference_date.replace(day=1)
            end_date = first_of_this_month - timedelta(days=1)
            start_date = end_date.replace(day=1)
        elif period == "quarter":
            # Last quarter
            current_month = self.reference_date.month
            current_quarter_start = ((current_month - 1) // 3) * 3 + 1
            last_quarter_start = current_quarter_start - 3

            if last_quarter_start <= 0:
                # Previous year
                last_quarter_start = 10
                year = self.reference_date.year - 1
            else:
                year = self.reference_date.year

            start_date = self.reference_date.replace(year=year, month=last_quarter_start, day=1)
            end_date = start_date + relativedelta(months=3) - timedelta(days=1)
        elif period == "year":
            # Last year
            start_date = self.reference_date.replace(
                year=self.reference_date.year - 1, month=1, day=1
            )
            end_date = self.reference_date.replace(
                year=self.reference_date.year - 1, month=12, day=31
            )
        else:
            return None

        days_span = (end_date - start_date).days + 1

        return DateRange(
            start_date=start_date,
            end_date=end_date,
            days_span=days_span,
            range_type=DateRangeType.LAST_PERIOD,
            confidence=0.90,
            original_text=match.group(0),
        )

    def _extract_quarter(self, text: str, text_lower: str) -> DateRange | None:
        """Extract quarter: 'Q1', 'Q2 2025', 'first quarter'"""
        match = self.quarter_pattern.search(text)
        if not match:
            return None

        # Extract quarter number (from Q1 format or "1st quarter" format)
        quarter_str = match.group(1) or match.group(2)
        quarter = int(quarter_str)

        # Extract year (or use current year)
        year_str = match.group(3)
        year = int(year_str) if year_str else self.reference_date.year

        # Calculate quarter start and end
        start_month = (quarter - 1) * 3 + 1
        start_date = datetime(year, start_month, 1)
        end_date = start_date + relativedelta(months=3) - timedelta(days=1)

        # Adjust end_date if it's in the future
        if end_date > self.reference_date:
            end_date = self.reference_date

        days_span = (end_date - start_date).days + 1

        return DateRange(
            start_date=start_date,
            end_date=end_date,
            days_span=days_span,
            range_type=DateRangeType.QUARTER,
            confidence=0.95,
            original_text=match.group(0),
        )

    def _extract_ytd(self, text: str, text_lower: str) -> DateRange | None:
        """Extract year to date: 'ytd', 'year to date'"""
        match = self.ytd_pattern.search(text_lower)
        if not match:
            return None

        end_date = self.reference_date
        start_date = end_date.replace(month=1, day=1)
        days_span = (end_date - start_date).days + 1

        return DateRange(
            start_date=start_date,
            end_date=end_date,
            days_span=days_span,
            range_type=DateRangeType.YEAR_TO_DATE,
            confidence=0.95,
            original_text=match.group(0),
        )

    def _extract_month_name(self, text: str, text_lower: str) -> DateRange | None:
        """Extract month name: 'January', 'Sep 2024', 'October 2025'"""
        match = self.month_name_pattern.search(text_lower)
        if not match:
            return None

        month_name = match.group(1).lower()
        month = self.month_map.get(month_name)
        if not month:
            return None

        # Extract year (or use current year)
        year_str = match.group(2)
        year = int(year_str) if year_str else self.reference_date.year

        # Calculate month range
        start_date = datetime(year, month, 1)
        end_date = start_date + relativedelta(months=1) - timedelta(days=1)

        # Adjust end_date if it's in the future
        if end_date > self.reference_date:
            end_date = self.reference_date

        days_span = (end_date - start_date).days + 1

        return DateRange(
            start_date=start_date,
            end_date=end_date,
            days_span=days_span,
            range_type=DateRangeType.MONTH_NAME,
            confidence=0.85,
            original_text=match.group(0),
        )

    def _extract_date_range(self, text: str, text_lower: str) -> DateRange | None:
        """Extract explicit date range: 'Jan 1 to Mar 31', 'January 1 - March 31'"""
        match = self.date_range_pattern.search(text_lower)
        if not match:
            return None

        # Parse start date
        start_month_name = match.group(1).lower()
        start_day = int(match.group(2))
        start_year_str = match.group(3)

        # Parse end date
        end_month_name = match.group(4).lower()
        end_day = int(match.group(5))
        end_year_str = match.group(6)

        # Get month numbers
        start_month = self.month_map.get(start_month_name)
        end_month = self.month_map.get(end_month_name)

        if not start_month or not end_month:
            return None

        # Determine years
        current_year = self.reference_date.year
        start_year = int(start_year_str) if start_year_str else current_year
        end_year = int(end_year_str) if end_year_str else current_year

        try:
            start_date = datetime(start_year, start_month, start_day)
            end_date = datetime(end_year, end_month, end_day)
        except ValueError:
            return None

        # Validate date range
        if start_date > end_date:
            return None

        days_span = (end_date - start_date).days + 1

        return DateRange(
            start_date=start_date,
            end_date=end_date,
            days_span=days_span,
            range_type=DateRangeType.EXPLICIT_RANGE,
            confidence=0.95,
            original_text=match.group(0),
        )

    def _extract_since(self, text: str, text_lower: str) -> DateRange | None:
        """Extract 'since' expressions: 'since January', 'since last month'"""
        match = self.since_pattern.search(text_lower)
        if not match:
            return None

        since_expr = match.group(1).lower()
        end_date = self.reference_date

        # Check if it's a month name
        if since_expr in self.month_map:
            month = self.month_map[since_expr]
            year = self.reference_date.year
            # If month is in the future, use last year
            if month > self.reference_date.month:
                year -= 1
            start_date = datetime(year, month, 1)
        # Check if it's "last week/month/quarter/year"
        elif "last week" in since_expr:
            start_date = self.reference_date - timedelta(days=self.reference_date.weekday() + 7)
        elif "last month" in since_expr:
            start_date = (self.reference_date.replace(day=1) - timedelta(days=1)).replace(day=1)
        elif "last quarter" in since_expr:
            current_quarter_start = ((self.reference_date.month - 1) // 3) * 3 + 1
            last_quarter_start = current_quarter_start - 3
            if last_quarter_start <= 0:
                last_quarter_start = 10
                year = self.reference_date.year - 1
            else:
                year = self.reference_date.year
            start_date = self.reference_date.replace(year=year, month=last_quarter_start, day=1)
        elif "last year" in since_expr:
            start_date = self.reference_date.replace(
                year=self.reference_date.year - 1, month=1, day=1
            )
        else:
            return None

        days_span = (end_date - start_date).days + 1

        return DateRange(
            start_date=start_date,
            end_date=end_date,
            days_span=days_span,
            range_type=DateRangeType.SINCE,
            confidence=0.85,
            original_text=match.group(0),
        )

    def _extract_fiscal(self, text: str, text_lower: str) -> DateRange | None:
        """Extract fiscal year: 'fiscal year', 'FY2025', 'FY 2025'"""
        match = self.fiscal_pattern.search(text)
        if not match:
            return None

        # Extract year (or use current year)
        year_str = match.group(1)
        year = int(year_str) if year_str else self.reference_date.year

        # Fiscal year typically starts in October (configurable)
        start_date = datetime(year - 1, 10, 1)
        end_date = datetime(year, 9, 30)

        # Adjust end_date if it's in the future
        if end_date > self.reference_date:
            end_date = self.reference_date

        days_span = (end_date - start_date).days + 1

        return DateRange(
            start_date=start_date,
            end_date=end_date,
            days_span=days_span,
            range_type=DateRangeType.FISCAL_YEAR,
            confidence=0.90,
            original_text=match.group(0),
        )


# Singleton instance
_date_range_extractor_instance: DateRangeExtractor | None = None


def get_date_range_extractor() -> DateRangeExtractor:
    """Get or create singleton date range extractor instance"""
    global _date_range_extractor_instance

    if _date_range_extractor_instance is None:
        _date_range_extractor_instance = DateRangeExtractor()

    return _date_range_extractor_instance


def reset_date_range_extractor() -> None:
    """Reset singleton instance (primarily for testing)"""
    global _date_range_extractor_instance
    _date_range_extractor_instance = None
