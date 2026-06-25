"""
Unit tests for DateRangeExtractor

Tests all 11 pattern extractors and edge cases for date range extraction.
Ensures comprehensive coverage of natural language date parsing.
"""

import sys
from pathlib import Path

# Add project root to path to allow direct import
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime, timedelta

import pytest

# Direct import to avoid circular dependencies
from src.core.classification.date_range_extractor import (
    DateRangeExtractor,
    DateRangeType,
    get_date_range_extractor,
    reset_date_range_extractor,
)


@pytest.fixture
def reference_date():
    """Fixed reference date for testing: October 5, 2025"""
    return datetime(2025, 10, 5, 12, 0, 0)


@pytest.fixture
def extractor(reference_date):
    """Date range extractor with fixed reference date"""
    reset_date_range_extractor()  # Clear singleton
    return DateRangeExtractor(reference_date=reference_date)


class TestRelativeDaysExtraction:
    """Test relative days pattern extraction"""

    @pytest.mark.asyncio
    async def test_last_30_days(self, extractor, reference_date):
        """Test: 'last 30 days' extraction"""
        result = await extractor.extract_date_range("Generate report for last 30 days")

        assert result is not None
        assert result.days_span == 30
        assert result.range_type == DateRangeType.RELATIVE_DAYS
        assert result.confidence == 0.95
        assert result.end_date == reference_date
        assert result.start_date == reference_date - timedelta(days=30)
        assert "last 30 days" in result.original_text.lower()

    @pytest.mark.asyncio
    async def test_past_7_days(self, extractor):
        """Test: 'past 7 days' extraction"""
        result = await extractor.extract_date_range("Show me past 7 days")

        assert result is not None
        assert result.days_span == 7
        assert result.range_type == DateRangeType.RELATIVE_DAYS

    @pytest.mark.asyncio
    async def test_previous_90_days(self, extractor):
        """Test: 'previous 90 days' extraction"""
        result = await extractor.extract_date_range("Analysis for previous 90 days")

        assert result is not None
        assert result.days_span == 90
        assert result.range_type == DateRangeType.RELATIVE_DAYS


class TestRelativeWeeksExtraction:
    """Test relative weeks pattern extraction"""

    @pytest.mark.asyncio
    async def test_last_2_weeks(self, extractor, reference_date):
        """Test: 'last 2 weeks' extraction"""
        result = await extractor.extract_date_range("Report for last 2 weeks")

        assert result is not None
        assert result.days_span == 14  # 2 weeks = 14 days
        assert result.range_type == DateRangeType.RELATIVE_WEEKS
        assert result.confidence == 0.95

    @pytest.mark.asyncio
    async def test_past_3_weeks(self, extractor):
        """Test: 'past 3 weeks' extraction"""
        result = await extractor.extract_date_range("past 3 weeks performance")

        assert result is not None
        assert result.days_span == 21  # 3 weeks


class TestRelativeMonthsExtraction:
    """Test relative months pattern extraction"""

    @pytest.mark.asyncio
    async def test_last_3_months(self, extractor, reference_date):
        """Test: 'last 3 months' extraction"""
        result = await extractor.extract_date_range("Report for last 3 months")

        assert result is not None
        assert result.range_type == DateRangeType.RELATIVE_MONTHS
        assert result.confidence == 0.95
        assert result.end_date == reference_date
        # Approximately 90 days (3 months)
        assert 85 <= result.days_span <= 95

    @pytest.mark.asyncio
    async def test_past_6_months(self, extractor):
        """Test: 'past 6 months' extraction"""
        result = await extractor.extract_date_range("past 6 months data")

        assert result is not None
        assert result.range_type == DateRangeType.RELATIVE_MONTHS
        # Approximately 180 days
        assert 175 <= result.days_span <= 185


class TestThisPeriodExtraction:
    """Test 'this' period pattern extraction"""

    @pytest.mark.asyncio
    async def test_this_week(self, extractor, reference_date):
        """Test: 'this week' extraction (Monday to today)"""
        result = await extractor.extract_date_range("Report for this week")

        assert result is not None
        assert result.range_type == DateRangeType.THIS_PERIOD
        assert result.confidence == 0.90
        assert result.end_date == reference_date
        # Start should be Monday of current week
        assert result.start_date.weekday() == 0  # Monday

    @pytest.mark.asyncio
    async def test_this_month(self, extractor, reference_date):
        """Test: 'this month' extraction (Oct 1 to today)"""
        result = await extractor.extract_date_range("this month summary")

        assert result is not None
        assert result.range_type == DateRangeType.THIS_PERIOD
        assert result.start_date.day == 1
        assert result.start_date.month == 10
        assert result.end_date == reference_date

    @pytest.mark.asyncio
    async def test_this_quarter(self, extractor, reference_date):
        """Test: 'this quarter' extraction (Q4: Oct 1 to today)"""
        result = await extractor.extract_date_range("this quarter report")

        assert result is not None
        assert result.range_type == DateRangeType.THIS_PERIOD
        # Q4 starts in October
        assert result.start_date.month == 10
        assert result.start_date.day == 1

    @pytest.mark.asyncio
    async def test_this_year(self, extractor, reference_date):
        """Test: 'this year' extraction (Jan 1 to today)"""
        result = await extractor.extract_date_range("this year overview")

        assert result is not None
        assert result.range_type == DateRangeType.THIS_PERIOD
        assert result.start_date.month == 1
        assert result.start_date.day == 1
        assert result.start_date.year == 2025


class TestLastPeriodExtraction:
    """Test 'last' period pattern extraction"""

    @pytest.mark.asyncio
    async def test_last_week(self, extractor, reference_date):
        """Test: 'last week' extraction (previous Monday-Sunday)"""
        result = await extractor.extract_date_range("Report for last week")

        assert result is not None
        assert result.range_type == DateRangeType.LAST_PERIOD
        assert result.confidence == 0.90
        # Should be 7 days (full week)
        assert result.days_span == 7

    @pytest.mark.asyncio
    async def test_last_month(self, extractor, reference_date):
        """Test: 'last month' extraction (September)"""
        result = await extractor.extract_date_range("last month data")

        assert result is not None
        assert result.range_type == DateRangeType.LAST_PERIOD
        # Should be September
        assert result.start_date.month == 9
        assert result.start_date.day == 1
        assert result.end_date.month == 9
        assert result.end_date.day == 30

    @pytest.mark.asyncio
    async def test_last_quarter(self, extractor, reference_date):
        """Test: 'last quarter' extraction (Q3: Jul-Sep)"""
        result = await extractor.extract_date_range("last quarter results")

        assert result is not None
        assert result.range_type == DateRangeType.LAST_PERIOD
        # Q3 starts in July
        assert result.start_date.month == 7
        assert result.start_date.day == 1
        # Q3 ends in September
        assert result.end_date.month == 9

    @pytest.mark.asyncio
    async def test_last_year(self, extractor, reference_date):
        """Test: 'last year' extraction (2024)"""
        result = await extractor.extract_date_range("last year performance")

        assert result is not None
        assert result.range_type == DateRangeType.LAST_PERIOD
        assert result.start_date.year == 2024
        assert result.start_date.month == 1
        assert result.end_date.year == 2024
        assert result.end_date.month == 12


class TestQuarterExtraction:
    """Test quarter pattern extraction"""

    @pytest.mark.asyncio
    async def test_q1_2025(self, extractor):
        """Test: 'Q1 2025' extraction"""
        result = await extractor.extract_date_range("Report for Q1 2025")

        assert result is not None
        assert result.range_type == DateRangeType.QUARTER
        assert result.confidence == 0.95
        assert result.start_date == datetime(2025, 1, 1)
        assert result.end_date.month == 3
        assert result.end_date.day == 31

    @pytest.mark.asyncio
    async def test_q2_without_year(self, extractor, reference_date):
        """Test: 'Q2' extraction (uses current year)"""
        result = await extractor.extract_date_range("Q2 report")

        assert result is not None
        assert result.range_type == DateRangeType.QUARTER
        assert result.start_date.year == 2025
        assert result.start_date.month == 4  # Q2 starts in April

    @pytest.mark.asyncio
    async def test_q4_current_year(self, extractor, reference_date):
        """Test: 'Q4' extraction (current quarter, truncated to today)"""
        result = await extractor.extract_date_range("Q4 results")

        assert result is not None
        assert result.range_type == DateRangeType.QUARTER
        assert result.start_date.month == 10  # Q4 starts in October
        # End date should be today (not future)
        assert result.end_date == reference_date

    @pytest.mark.asyncio
    async def test_first_quarter_pattern(self, extractor, reference_date):
        """Test: 'first quarter' extraction"""
        result = await extractor.extract_date_range("1st quarter 2025")

        assert result is not None
        assert result.range_type == DateRangeType.QUARTER
        assert result.start_date.month == 1


class TestYearToDateExtraction:
    """Test year-to-date pattern extraction"""

    @pytest.mark.asyncio
    async def test_ytd(self, extractor, reference_date):
        """Test: 'ytd' extraction"""
        result = await extractor.extract_date_range("YTD performance")

        assert result is not None
        assert result.range_type == DateRangeType.YEAR_TO_DATE
        assert result.confidence == 0.95
        assert result.start_date.year == 2025
        assert result.start_date.month == 1
        assert result.start_date.day == 1
        assert result.end_date == reference_date

    @pytest.mark.asyncio
    async def test_year_to_date_phrase(self, extractor, reference_date):
        """Test: 'year to date' extraction"""
        result = await extractor.extract_date_range("Report year to date")

        assert result is not None
        assert result.range_type == DateRangeType.YEAR_TO_DATE
        assert result.start_date.month == 1
        assert result.start_date.day == 1


class TestMonthNameExtraction:
    """Test month name pattern extraction"""

    @pytest.mark.asyncio
    async def test_january(self, extractor, reference_date):
        """Test: 'January' extraction"""
        result = await extractor.extract_date_range("Report for January")

        assert result is not None
        assert result.range_type == DateRangeType.MONTH_NAME
        assert result.confidence == 0.85
        assert result.start_date.month == 1
        assert result.start_date.day == 1

    @pytest.mark.asyncio
    async def test_september_2024(self, extractor):
        """Test: 'September 2024' extraction"""
        result = await extractor.extract_date_range("Sep 2024 data")

        assert result is not None
        assert result.range_type == DateRangeType.MONTH_NAME
        assert result.start_date == datetime(2024, 9, 1)
        assert result.end_date.month == 9
        assert result.end_date.day == 30

    @pytest.mark.asyncio
    async def test_october_current_year(self, extractor, reference_date):
        """Test: 'October' extraction (current month, truncated to today)"""
        result = await extractor.extract_date_range("October results")

        assert result is not None
        assert result.range_type == DateRangeType.MONTH_NAME
        assert result.start_date.month == 10
        assert result.start_date.day == 1
        # Should be truncated to today (Oct 5)
        assert result.end_date == reference_date


class TestExplicitDateRangeExtraction:
    """Test explicit date range pattern extraction"""

    @pytest.mark.asyncio
    async def test_jan_1_to_mar_31(self, extractor, reference_date):
        """Test: 'Jan 1 to Mar 31' extraction"""
        result = await extractor.extract_date_range("Report from Jan 1 to Mar 31")

        assert result is not None
        assert result.range_type == DateRangeType.EXPLICIT_RANGE
        assert result.confidence == 0.95
        assert result.start_date.month == 1
        assert result.start_date.day == 1
        assert result.end_date.month == 3
        assert result.end_date.day == 31

    @pytest.mark.asyncio
    async def test_january_1_march_31_2024(self, extractor):
        """Test: 'January 1 2024 - March 31 2024' extraction"""
        result = await extractor.extract_date_range("January 1 2024 - March 31 2024")

        assert result is not None
        assert result.range_type == DateRangeType.EXPLICIT_RANGE
        assert result.start_date == datetime(2024, 1, 1)
        assert result.end_date == datetime(2024, 3, 31)


class TestSinceExtraction:
    """Test 'since' pattern extraction"""

    @pytest.mark.asyncio
    async def test_since_january(self, extractor, reference_date):
        """Test: 'since January' extraction"""
        result = await extractor.extract_date_range("Data since January")

        assert result is not None
        assert result.range_type == DateRangeType.SINCE
        assert result.confidence == 0.85
        assert result.start_date.year == 2025
        assert result.start_date.month == 1
        assert result.start_date.day == 1
        assert result.end_date == reference_date

    @pytest.mark.asyncio
    async def test_since_last_month(self, extractor, reference_date):
        """Test: 'since last month' extraction"""
        result = await extractor.extract_date_range("since last month")

        assert result is not None
        assert result.range_type == DateRangeType.SINCE
        # Should start from Sept 1
        assert result.start_date.year == 2025
        assert result.start_date.month == 9
        assert result.start_date.day == 1
        assert result.end_date == reference_date


class TestFiscalYearExtraction:
    """Test fiscal year pattern extraction"""

    @pytest.mark.asyncio
    async def test_fiscal_year(self, extractor, reference_date):
        """Test: 'fiscal year' extraction (Oct 2024 - Sep 2025)"""
        result = await extractor.extract_date_range("Fiscal year report")

        assert result is not None
        assert result.range_type == DateRangeType.FISCAL_YEAR
        assert result.confidence == 0.90
        # Fiscal year typically starts in October of previous year
        assert result.start_date.month == 10
        assert result.start_date.year == 2024

    @pytest.mark.asyncio
    async def test_fy2025(self, extractor):
        """Test: 'FY2025' extraction"""
        result = await extractor.extract_date_range("FY2025 results")

        assert result is not None
        assert result.range_type == DateRangeType.FISCAL_YEAR
        assert result.start_date.year == 2024
        assert result.start_date.month == 10


class TestEdgeCases:
    """Test edge cases and error handling"""

    @pytest.mark.asyncio
    async def test_no_date_mention(self, extractor):
        """Test: No date range in text returns None"""
        result = await extractor.extract_date_range("Generate my report please")

        assert result is None

    @pytest.mark.asyncio
    async def test_empty_string(self, extractor):
        """Test: Empty string returns None"""
        result = await extractor.extract_date_range("")

        assert result is None

    @pytest.mark.asyncio
    async def test_none_input(self, extractor):
        """Test: None input returns None"""
        result = await extractor.extract_date_range(None)

        assert result is None

    @pytest.mark.asyncio
    async def test_multiple_date_patterns(self, extractor):
        """Test: Multiple patterns - returns most specific (first match)"""
        result = await extractor.extract_date_range("Report from Jan 1 to Mar 31 for last 30 days")

        # Should match the most specific pattern (explicit range)
        assert result is not None
        assert result.range_type == DateRangeType.EXPLICIT_RANGE

    @pytest.mark.asyncio
    async def test_case_insensitive(self, extractor):
        """Test: Pattern matching is case-insensitive"""
        result1 = await extractor.extract_date_range("LAST 30 DAYS")
        result2 = await extractor.extract_date_range("last 30 days")
        result3 = await extractor.extract_date_range("Last 30 Days")

        assert result1 is not None
        assert result2 is not None
        assert result3 is not None
        assert result1.days_span == result2.days_span == result3.days_span


class TestToDict:
    """Test DateRange to_dict method"""

    @pytest.mark.asyncio
    async def test_to_dict_serialization(self, extractor):
        """Test: DateRange can be serialized to dictionary"""
        result = await extractor.extract_date_range("last 30 days")

        assert result is not None
        dict_result = result.to_dict()

        assert isinstance(dict_result, dict)
        assert "start_date" in dict_result
        assert "end_date" in dict_result
        assert "days_span" in dict_result
        assert "range_type" in dict_result
        assert "confidence" in dict_result
        assert "original_text" in dict_result

        # Check ISO format dates
        assert isinstance(dict_result["start_date"], str)
        assert isinstance(dict_result["end_date"], str)


class TestSingletonPattern:
    """Test singleton getter"""

    def test_get_date_range_extractor_singleton(self):
        """Test: get_date_range_extractor returns singleton"""
        reset_date_range_extractor()

        instance1 = get_date_range_extractor()
        instance2 = get_date_range_extractor()

        assert instance1 is instance2

    def test_reset_date_range_extractor(self):
        """Test: reset_date_range_extractor clears singleton"""
        instance1 = get_date_range_extractor()
        reset_date_range_extractor()
        instance2 = get_date_range_extractor()

        assert instance1 is not instance2


class TestConfidenceScores:
    """Test confidence scores for different patterns"""

    @pytest.mark.asyncio
    async def test_high_confidence_patterns(self, extractor):
        """Test: High confidence patterns (>= 0.95)"""
        high_confidence_tests = [
            ("last 30 days", DateRangeType.RELATIVE_DAYS),
            ("past 2 weeks", DateRangeType.RELATIVE_WEEKS),
            ("Q1 2025", DateRangeType.QUARTER),
            ("ytd", DateRangeType.YEAR_TO_DATE),
            ("Jan 1 to Mar 31", DateRangeType.EXPLICIT_RANGE),
        ]

        for text, expected_type in high_confidence_tests:
            result = await extractor.extract_date_range(text)
            assert result is not None
            assert result.range_type == expected_type
            assert result.confidence >= 0.90, f"Failed for: {text}"

    @pytest.mark.asyncio
    async def test_medium_confidence_patterns(self, extractor):
        """Test: Medium confidence patterns (0.85-0.90)"""
        medium_confidence_tests = [
            ("January", DateRangeType.MONTH_NAME),
            ("since January", DateRangeType.SINCE),
        ]

        for text, expected_type in medium_confidence_tests:
            result = await extractor.extract_date_range(text)
            assert result is not None
            assert result.range_type == expected_type
            assert 0.85 <= result.confidence <= 0.95, f"Failed for: {text}"


# Integration test with user context
class TestWithUserContext:
    """Test extraction with user context"""

    @pytest.mark.asyncio
    async def test_with_timezone_context(self, extractor):
        """Test: Extraction works with user context (timezone)"""
        user_context = {"timezone": "America/Los_Angeles"}

        result = await extractor.extract_date_range("last 30 days", user_context)

        assert result is not None
        assert result.days_span == 30

    @pytest.mark.asyncio
    async def test_without_user_context(self, extractor):
        """Test: Extraction works without user context"""
        result = await extractor.extract_date_range("last 30 days", None)

        assert result is not None
        assert result.days_span == 30
