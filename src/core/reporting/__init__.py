"""
Core Reporting Components

Contains data aggregation and date management utilities for reporting.
Note: PDF generation is handled by src.services.reporting.pdf_report_engine
"""

from .data_aggregator import ReportDataAggregator
from .date_manager import DateRangeManager

__all__ = ["ReportDataAggregator", "DateRangeManager"]
