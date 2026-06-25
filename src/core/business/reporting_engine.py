"""
Reporting Engine for ReflectAI
Handles report generation, formatting, and distribution.
"""

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from io import StringIO
from typing import Any

from src.shared.error_handlers import handle_errors
from src.shared.exceptions import ErrorCategory
from src.shared.logging import get_logger

logger = get_logger(__name__)


class ReportType(Enum):
    """Types of reports."""

    SUMMARY = "summary"
    DETAILED = "detailed"
    PROGRESS = "progress"
    COMPETENCY = "competency"
    ACHIEVEMENT = "achievement"
    ANALYTICS = "analytics"
    CUSTOM = "custom"


class ReportFormat(Enum):
    """Report output formats."""

    JSON = "json"
    HTML = "html"
    MARKDOWN = "markdown"
    PDF = "pdf"
    CSV = "csv"


class ReportFrequency(Enum):
    """Report generation frequency."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    ON_DEMAND = "on_demand"


@dataclass
class ReportSection:
    """Represents a report section."""

    title: str
    content: Any
    section_type: str  # "text", "table", "chart", "list"
    metadata: dict[str, Any] = field(default_factory=dict)
    order: int = 0


@dataclass
class Report:
    """Represents a generated report."""

    report_id: str
    user_id: str
    report_type: ReportType
    title: str
    sections: list[ReportSection]
    summary: str
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    format: ReportFormat = ReportFormat.JSON
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReportTemplate:
    """Template for report generation."""

    template_id: str
    name: str
    report_type: ReportType
    sections_config: list[dict[str, Any]]
    default_format: ReportFormat
    custom_styles: dict[str, Any] | None = None


class ReportingEngine:
    """
    Engine for report generation and management.

    Features:
    - Multiple report types
    - Customizable templates
    - Multi-format output
    - Scheduled generation
    - Distribution management
    """

    def __init__(self):
        self.templates = self._load_report_templates()
        self.formatters = self._initialize_formatters()

        logger.info("Reporting Engine initialized")

    def _load_report_templates(self) -> dict[str, ReportTemplate]:
        """Load report templates."""
        return {
            "weekly_summary": ReportTemplate(
                template_id="weekly_summary",
                name="Weekly Summary Report",
                report_type=ReportType.SUMMARY,
                sections_config=[
                    {"type": "overview", "title": "Week at a Glance"},
                    {"type": "activities", "title": "Key Activities"},
                    {"type": "achievements", "title": "Achievements"},
                    {"type": "metrics", "title": "Performance Metrics"},
                    {"type": "recommendations", "title": "Next Steps"},
                ],
                default_format=ReportFormat.HTML,
            ),
            "competency_assessment": ReportTemplate(
                template_id="competency_assessment",
                name="Competency Assessment Report",
                report_type=ReportType.COMPETENCY,
                sections_config=[
                    {"type": "summary", "title": "Executive Summary"},
                    {"type": "scores", "title": "Competency Scores"},
                    {"type": "growth", "title": "Growth Analysis"},
                    {"type": "gaps", "title": "Gap Analysis"},
                    {"type": "development", "title": "Development Plan"},
                ],
                default_format=ReportFormat.PDF,
            ),
            "progress_tracker": ReportTemplate(
                template_id="progress_tracker",
                name="Progress Tracking Report",
                report_type=ReportType.PROGRESS,
                sections_config=[
                    {"type": "goals", "title": "Goal Progress"},
                    {"type": "milestones", "title": "Milestones"},
                    {"type": "timeline", "title": "Timeline View"},
                    {"type": "blockers", "title": "Challenges"},
                    {"type": "next_actions", "title": "Action Items"},
                ],
                default_format=ReportFormat.MARKDOWN,
            ),
        }

    def _initialize_formatters(self) -> dict[ReportFormat, Any]:
        """Initialize report formatters."""
        return {
            ReportFormat.JSON: self._format_json,
            ReportFormat.HTML: self._format_html,
            ReportFormat.MARKDOWN: self._format_markdown,
            ReportFormat.PDF: self._format_pdf,
            ReportFormat.CSV: self._format_csv,
        }

    @handle_errors(category=ErrorCategory.BUSINESS_RULE_ERROR)
    async def generate_report(
        self,
        user_id: str,
        report_type: ReportType,
        data: dict[str, Any],
        period_days: int = 7,
        template_id: str | None = None,
        format: ReportFormat = ReportFormat.JSON,
    ) -> Report:
        """
        Generate a report based on user data.

        Args:
            user_id: User identifier
            report_type: Type of report
            data: Data for report generation
            period_days: Report period in days
            template_id: Optional template ID
            format: Output format

        Returns:
            Generated report
        """
        try:
            period_end = datetime.now(UTC)
            period_start = period_end - timedelta(days=period_days)

            # Get or create template
            if template_id:
                template = self.templates.get(template_id)
            else:
                template = self._get_default_template(report_type)

            # Generate report sections
            sections = await self._generate_sections(
                report_type, data, template, period_start, period_end
            )

            # Generate summary
            summary = await self._generate_summary(sections, data)

            # Create report
            report = Report(
                report_id=f"report_{user_id}_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
                user_id=user_id,
                report_type=report_type,
                title=self._generate_title(report_type, period_start, period_end),
                sections=sections,
                summary=summary,
                generated_at=datetime.now(UTC),
                period_start=period_start,
                period_end=period_end,
                format=format,
                metadata={
                    "template_id": template_id,
                    "data_points": len(data),
                    "period_days": period_days,
                },
            )

            logger.info(
                "Report generated",
                extra={
                    "user_id": user_id,
                    "report_type": report_type.value,
                    "format": format.value,
                    "sections": len(sections),
                },
            )

            return report

        except Exception as e:
            logger.error(f"Failed to generate report: {e}")
            raise

    def _get_default_template(self, report_type: ReportType) -> ReportTemplate:
        """Get default template for report type."""
        type_to_template = {
            ReportType.SUMMARY: "weekly_summary",
            ReportType.COMPETENCY: "competency_assessment",
            ReportType.PROGRESS: "progress_tracker",
        }

        template_id = type_to_template.get(report_type, "weekly_summary")
        return self.templates.get(template_id)

    async def _generate_sections(
        self,
        report_type: ReportType,
        data: dict[str, Any],
        template: ReportTemplate,
        period_start: datetime,
        period_end: datetime,
    ) -> list[ReportSection]:
        """Generate report sections based on template."""
        sections = []

        if not template:
            # Generate default sections
            sections = await self._generate_default_sections(
                report_type, data, period_start, period_end
            )
        else:
            # Generate template-based sections
            for idx, section_config in enumerate(template.sections_config):
                section = await self._generate_section(
                    section_config, data, period_start, period_end, idx
                )
                if section:
                    sections.append(section)

        return sections

    async def _generate_default_sections(
        self,
        report_type: ReportType,
        data: dict[str, Any],
        period_start: datetime,
        period_end: datetime,
    ) -> list[ReportSection]:
        """Generate default sections for report type."""
        sections = []

        # Overview section
        overview = self._create_overview_section(data, period_start, period_end)
        sections.append(overview)

        # Type-specific sections
        if report_type == ReportType.SUMMARY:
            sections.extend(self._create_summary_sections(data))
        elif report_type == ReportType.COMPETENCY:
            sections.extend(self._create_competency_sections(data))
        elif report_type == ReportType.PROGRESS:
            sections.extend(self._create_progress_sections(data))
        elif report_type == ReportType.ANALYTICS:
            sections.extend(self._create_analytics_sections(data))

        return sections

    def _create_overview_section(
        self, data: dict[str, Any], period_start: datetime, period_end: datetime
    ) -> ReportSection:
        """Create overview section."""
        overview_data = {
            "period": f"{period_start.date()} to {period_end.date()}",
            "total_activities": len(data.get("activities", [])),
            "goals_completed": len(
                [g for g in data.get("goals", []) if g.get("status") == "completed"]
            ),
            "key_metrics": self._extract_key_metrics(data),
        }

        return ReportSection(title="Overview", content=overview_data, section_type="text", order=0)

    def _create_summary_sections(self, data: dict[str, Any]) -> list[ReportSection]:
        """Create summary report sections."""
        sections = []

        # Activities section
        activities = data.get("activities", [])[:10]  # Top 10
        if activities:
            sections.append(
                ReportSection(
                    title="Recent Activities", content=activities, section_type="list", order=1
                )
            )

        # Achievements section
        achievements = data.get("achievements", [])
        if achievements:
            sections.append(
                ReportSection(
                    title="Key Achievements", content=achievements, section_type="list", order=2
                )
            )

        # Metrics section
        metrics = data.get("metrics", {})
        if metrics:
            sections.append(
                ReportSection(
                    title="Performance Metrics",
                    content=self._format_metrics_table(metrics),
                    section_type="table",
                    order=3,
                )
            )

        return sections

    def _create_competency_sections(self, data: dict[str, Any]) -> list[ReportSection]:
        """Create competency report sections."""
        sections = []

        # Competency scores
        competencies = data.get("competencies", {})
        if competencies:
            sections.append(
                ReportSection(
                    title="Competency Scores",
                    content=self._format_competency_scores(competencies),
                    section_type="table",
                    order=1,
                )
            )

        # Growth analysis
        growth = data.get("competency_growth", {})
        if growth:
            sections.append(
                ReportSection(
                    title="Growth Analysis",
                    content=growth,
                    section_type="chart",
                    metadata={"chart_type": "line"},
                    order=2,
                )
            )

        # Gap analysis
        gaps = data.get("competency_gaps", [])
        if gaps:
            sections.append(
                ReportSection(title="Gap Analysis", content=gaps, section_type="table", order=3)
            )

        return sections

    def _create_progress_sections(self, data: dict[str, Any]) -> list[ReportSection]:
        """Create progress report sections."""
        sections = []

        # Goals progress
        goals = data.get("goals", [])
        if goals:
            sections.append(
                ReportSection(
                    title="Goal Progress",
                    content=self._format_goals_progress(goals),
                    section_type="table",
                    order=1,
                )
            )

        # Milestones
        milestones = data.get("milestones", [])
        if milestones:
            sections.append(
                ReportSection(
                    title="Milestones", content=milestones, section_type="timeline", order=2
                )
            )

        # Blockers
        blockers = data.get("blockers", [])
        if blockers:
            sections.append(
                ReportSection(
                    title="Challenges & Blockers",
                    content=blockers,
                    section_type="list",
                    metadata={"style": "warning"},
                    order=3,
                )
            )

        return sections

    def _create_analytics_sections(self, data: dict[str, Any]) -> list[ReportSection]:
        """Create analytics report sections."""
        sections = []

        # Insights
        insights = data.get("insights", [])
        if insights:
            sections.append(
                ReportSection(
                    title="Key Insights",
                    content=insights,
                    section_type="list",
                    metadata={"style": "highlight"},
                    order=1,
                )
            )

        # Trends
        trends = data.get("trends", {})
        if trends:
            sections.append(
                ReportSection(
                    title="Trend Analysis",
                    content=trends,
                    section_type="chart",
                    metadata={"chart_type": "trend"},
                    order=2,
                )
            )

        # Predictions
        predictions = data.get("predictions", {})
        if predictions:
            sections.append(
                ReportSection(
                    title="Predictions",
                    content=predictions,
                    section_type="text",
                    metadata={"style": "forecast"},
                    order=3,
                )
            )

        return sections

    async def _generate_section(
        self,
        section_config: dict[str, Any],
        data: dict[str, Any],
        period_start: datetime,
        period_end: datetime,
        order: int,
    ) -> ReportSection | None:
        """Generate a single section based on configuration."""
        section_type = section_config.get("type")
        title = section_config.get("title", "Section")

        content = None

        if section_type == "overview":
            content = self._create_overview_content(data, period_start, period_end)
        elif section_type == "activities":
            content = data.get("activities", [])
        elif section_type == "achievements":
            content = data.get("achievements", [])
        elif section_type == "metrics":
            content = self._format_metrics_table(data.get("metrics", {}))
        elif section_type == "recommendations":
            content = data.get("recommendations", [])

        if content:
            return ReportSection(
                title=title,
                content=content,
                section_type=section_config.get("display_type", "text"),
                metadata=section_config.get("metadata", {}),
                order=order,
            )

        return None

    def _create_overview_content(
        self, data: dict[str, Any], period_start: datetime, period_end: datetime
    ) -> dict[str, Any]:
        """Create overview content."""
        return {
            "period": f"{period_start.date()} to {period_end.date()}",
            "highlights": self._extract_highlights(data),
            "summary_stats": self._calculate_summary_stats(data),
        }

    def _extract_highlights(self, data: dict[str, Any]) -> list[str]:
        """Extract highlights from data."""
        highlights = []

        # Activity highlights
        activities = data.get("activities", [])
        if activities:
            highlights.append(f"Completed {len(activities)} activities")

        # Achievement highlights
        achievements = data.get("achievements", [])
        if achievements:
            highlights.append(f"Unlocked {len(achievements)} achievements")

        # Growth highlights
        growth = data.get("competency_growth", {})
        if growth:
            avg_growth = sum(growth.values()) / len(growth) if growth else 0
            if avg_growth > 0:
                highlights.append(f"Average growth of {avg_growth:.1f}%")

        return highlights

    def _calculate_summary_stats(self, data: dict[str, Any]) -> dict[str, Any]:
        """Calculate summary statistics."""
        return {
            "total_activities": len(data.get("activities", [])),
            "goals_completed": len(
                [g for g in data.get("goals", []) if g.get("status") == "completed"]
            ),
            "total_goals": len(data.get("goals", [])),
            "achievements": len(data.get("achievements", [])),
            "active_days": self._count_active_days(data.get("activities", [])),
        }

    def _count_active_days(self, activities: list[dict]) -> int:
        """Count unique active days."""
        active_dates = set()
        for activity in activities:
            timestamp = activity.get("timestamp", datetime.now(UTC))
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            active_dates.add(timestamp.date())
        return len(active_dates)

    def _extract_key_metrics(self, data: dict[str, Any]) -> dict[str, Any]:
        """Extract key metrics from data."""
        metrics = data.get("metrics", {})
        key_metrics = {}

        # Select top metrics
        priority_metrics = ["engagement_score", "goal_completion", "competency_growth"]

        for metric_name in priority_metrics:
            if metric_name in metrics:
                key_metrics[metric_name] = metrics[metric_name]

        return key_metrics

    def _format_metrics_table(self, metrics: dict[str, Any]) -> list[dict]:
        """Format metrics as table data."""
        table_data = []

        for metric_name, metric_value in metrics.items():
            if isinstance(metric_value, dict):
                table_data.append(
                    {
                        "metric": metric_name,
                        "value": metric_value.get("value", 0),
                        "unit": metric_value.get("unit", ""),
                        "trend": metric_value.get("trend", "stable"),
                    }
                )
            else:
                table_data.append(
                    {"metric": metric_name, "value": metric_value, "unit": "", "trend": "stable"}
                )

        return table_data

    def _format_competency_scores(self, competencies: dict[str, Any]) -> list[dict]:
        """Format competency scores as table."""
        table_data = []

        for comp_name, comp_data in competencies.items():
            if isinstance(comp_data, dict):
                table_data.append(
                    {
                        "competency": comp_name,
                        "score": comp_data.get("score", 0),
                        "level": comp_data.get("level", "Novice"),
                        "growth": comp_data.get("growth_rate", 0),
                    }
                )
            else:
                table_data.append(
                    {
                        "competency": comp_name,
                        "score": comp_data,
                        "level": self._score_to_level(comp_data),
                        "growth": 0,
                    }
                )

        return sorted(table_data, key=lambda x: x["score"], reverse=True)

    def _score_to_level(self, score: float) -> str:
        """Convert score to level."""
        if score >= 90:
            return "Master"
        elif score >= 80:
            return "Expert"
        elif score >= 60:
            return "Proficient"
        elif score >= 40:
            return "Competent"
        elif score >= 20:
            return "Beginner"
        else:
            return "Novice"

    def _format_goals_progress(self, goals: list[dict]) -> list[dict]:
        """Format goals progress as table."""
        table_data = []

        for goal in goals:
            table_data.append(
                {
                    "goal": goal.get("title", "Unnamed Goal"),
                    "progress": goal.get("progress", 0),
                    "status": goal.get("status", "in_progress"),
                    "deadline": goal.get("deadline", "No deadline"),
                }
            )

        return table_data

    async def _generate_summary(self, sections: list[ReportSection], data: dict[str, Any]) -> str:
        """Generate report summary."""
        summary_parts = []

        # Extract key information from sections
        for section in sections[:3]:  # Top 3 sections
            if section.section_type == "text":
                summary_parts.append(f"{section.title}: Key insights captured")
            elif section.section_type == "table":
                summary_parts.append(f"{section.title}: {len(section.content)} items")
            elif section.section_type == "list":
                summary_parts.append(f"{section.title}: {len(section.content)} entries")

        # Add overall assessment
        metrics = data.get("metrics", {})
        if metrics:
            avg_score = (
                sum(m.get("value", 0) for m in metrics.values() if isinstance(m, dict))
                / len(metrics)
                if metrics
                else 0
            )

            if avg_score > 80:
                summary_parts.append("Overall performance: Excellent")
            elif avg_score > 60:
                summary_parts.append("Overall performance: Good")
            else:
                summary_parts.append("Overall performance: Needs improvement")

        return " | ".join(summary_parts)

    def _generate_title(
        self, report_type: ReportType, period_start: datetime, period_end: datetime
    ) -> str:
        """Generate report title."""
        type_titles = {
            ReportType.SUMMARY: "Summary Report",
            ReportType.DETAILED: "Detailed Report",
            ReportType.PROGRESS: "Progress Report",
            ReportType.COMPETENCY: "Competency Assessment",
            ReportType.ACHIEVEMENT: "Achievement Report",
            ReportType.ANALYTICS: "Analytics Report",
            ReportType.CUSTOM: "Custom Report",
        }

        base_title = type_titles.get(report_type, "Report")
        period = f"{period_start.strftime('%b %d')} - {period_end.strftime('%b %d, %Y')}"

        return f"{base_title}: {period}"

    async def format_report(self, report: Report, format: ReportFormat) -> str | dict | bytes:
        """
        Format report in specified format.

        Args:
            report: Report to format
            format: Output format

        Returns:
            Formatted report
        """
        formatter = self.formatters.get(format, self._format_json)
        return await formatter(report)

    async def _format_json(self, report: Report) -> dict:
        """Format report as JSON."""
        return {
            "report_id": report.report_id,
            "user_id": report.user_id,
            "type": report.report_type.value,
            "title": report.title,
            "summary": report.summary,
            "period": {
                "start": report.period_start.isoformat(),
                "end": report.period_end.isoformat(),
            },
            "sections": [
                {
                    "title": section.title,
                    "type": section.section_type,
                    "content": section.content,
                    "metadata": section.metadata,
                }
                for section in report.sections
            ],
            "generated_at": report.generated_at.isoformat(),
            "metadata": report.metadata,
        }

    async def _format_html(self, report: Report) -> str:
        """Format report as HTML."""
        html = StringIO()

        # HTML header
        html.write(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{report.title}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #333; }}
                h2 {{ color: #666; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .summary {{ background-color: #f9f9f9; padding: 10px; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <h1>{report.title}</h1>
            <div class="summary">{report.summary}</div>
        """)

        # Sections
        for section in report.sections:
            html.write(f"<h2>{section.title}</h2>")

            if section.section_type == "table":
                html.write(self._format_html_table(section.content))
            elif section.section_type == "list":
                html.write(self._format_html_list(section.content))
            else:
                html.write(f"<p>{section.content}</p>")

        # Footer
        html.write(f"""
            <hr>
            <p><small>Generated: {report.generated_at.strftime("%Y-%m-%d %H:%M:%S")}</small></p>
        </body>
        </html>
        """)

        return html.getvalue()

    def _format_html_table(self, data: list[dict]) -> str:
        """Format data as HTML table."""
        if not data:
            return "<p>No data available</p>"

        html = "<table>"

        # Header
        html += "<tr>"
        for key in data[0].keys():
            html += f"<th>{key.replace('_', ' ').title()}</th>"
        html += "</tr>"

        # Rows
        for row in data:
            html += "<tr>"
            for value in row.values():
                html += f"<td>{value}</td>"
            html += "</tr>"

        html += "</table>"
        return html

    def _format_html_list(self, data: list) -> str:
        """Format data as HTML list."""
        if not data:
            return "<p>No items</p>"

        html = "<ul>"
        for item in data:
            if isinstance(item, dict):
                html += f"<li>{item.get('title', item.get('name', str(item)))}</li>"
            else:
                html += f"<li>{item}</li>"
        html += "</ul>"

        return html

    async def _format_markdown(self, report: Report) -> str:
        """Format report as Markdown."""
        md = StringIO()

        # Title and summary
        md.write(f"# {report.title}\n\n")
        md.write(f"**Summary:** {report.summary}\n\n")
        md.write(f"**Period:** {report.period_start.date()} to {report.period_end.date()}\n\n")
        md.write("---\n\n")

        # Sections
        for section in report.sections:
            md.write(f"## {section.title}\n\n")

            if section.section_type == "table":
                md.write(self._format_markdown_table(section.content))
            elif section.section_type == "list":
                md.write(self._format_markdown_list(section.content))
            else:
                md.write(f"{section.content}\n\n")

        # Footer
        md.write(f"\n---\n*Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}*\n")

        return md.getvalue()

    def _format_markdown_table(self, data: list[dict]) -> str:
        """Format data as Markdown table."""
        if not data:
            return "No data available\n\n"

        md = ""

        # Header
        headers = list(data[0].keys())
        md += "| " + " | ".join(headers) + " |\n"
        md += "| " + " | ".join(["---"] * len(headers)) + " |\n"

        # Rows
        for row in data:
            values = [str(v) for v in row.values()]
            md += "| " + " | ".join(values) + " |\n"

        md += "\n"
        return md

    def _format_markdown_list(self, data: list) -> str:
        """Format data as Markdown list."""
        if not data:
            return "No items\n\n"

        md = ""
        for item in data:
            if isinstance(item, dict):
                md += f"- {item.get('title', item.get('name', str(item)))}\n"
            else:
                md += f"- {item}\n"

        md += "\n"
        return md

    async def _format_pdf(self, report: Report) -> bytes:
        """Format report as PDF."""
        # Simplified - would use reportlab or similar in production
        # For now, convert to HTML and return as bytes
        html_content = await self._format_html(report)
        return html_content.encode("utf-8")

    async def _format_csv(self, report: Report) -> str:
        """Format report as CSV."""
        csv = StringIO()

        # Simple CSV with section data
        csv.write("Section,Data\n")

        for section in report.sections:
            if section.section_type == "table" and isinstance(section.content, list):
                for row in section.content:
                    csv.write(f"{section.title},{json.dumps(row)}\n")
            else:
                csv.write(f"{section.title},{json.dumps(section.content)}\n")

        return csv.getvalue()
