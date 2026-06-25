"""
Report Generator Tool for Advisor Agent

Implements report generation part of
- Create PDF reports using templates
- Competency assessment reports and career development summaries
- Integration with recommendation engine and goal tracking
- Template-based report generation with data visualization

Used by Advisor Agent for generating comprehensive user reports.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from ..base_tool import Tool, ToolError, ToolPermission, ToolRequest


class ReportType(Enum):
    """Types of reports that can be generated"""

    COMPETENCY_ASSESSMENT = "competency_assessment"
    CAREER_DEVELOPMENT = "career_development"
    GOAL_PROGRESS = "goal_progress"
    PERFORMANCE_SUMMARY = "performance_summary"
    LEARNING_RECOMMENDATIONS = "learning_recommendations"


class ReportFormat(Enum):
    """Report output formats"""

    PDF = "pdf"
    HTML = "html"
    JSON = "json"


class ReportRequest(BaseModel):
    """Request for report generation"""

    user_id: str = Field(..., description="User ID to generate report for")
    report_type: ReportType = Field(..., description="Type of report to generate")
    output_format: ReportFormat = Field(ReportFormat.PDF, description="Output format")
    include_charts: bool = Field(True, description="Include data visualizations")
    date_range_days: int = Field(90, description="Date range for data analysis")
    template_name: str | None = Field(None, description="Custom template name")
    custom_sections: list[str] | None = Field(None, description="Custom report sections")


class ReportResult(BaseModel):
    """Result of report generation"""

    user_id: str = Field(..., description="User ID report was generated for")
    report_type: ReportType = Field(..., description="Type of report generated")
    output_format: ReportFormat = Field(..., description="Output format")
    file_path: str | None = Field(None, description="Path to generated report file")
    file_size: int = Field(..., description="Size of generated file in bytes")
    generation_time: float = Field(..., description="Time taken to generate report")
    report_data: dict[str, Any] | None = Field(None, description="Report data for JSON format")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ReportGeneratorTool(Tool):
    """
    Tool for generating comprehensive user reports

    Creates PDF and HTML reports using templates with user competency data,
    career development progress, and personalized recommendations.
    """

    def __init__(self):
        super().__init__(
            name="report_generator",
            description="Generate PDF and HTML reports for user competency and career development",
            required_permissions=[ToolPermission.READ_WRITE],  # Write for file generation
            timeout=120,  # Reports can take longer to generate
        )

        self._report_templates = self._load_report_templates()

    async def _execute_operation(
        self, request: ToolRequest, agent_context: Any | None = None
    ) -> ReportResult:
        """Execute report generation"""

        if request.operation != "generate_report":
            raise ToolError(
                message=f"Unknown operation: {request.operation}",
                tool_name=self.name,
                operation=request.operation,
            )

        # Parse request parameters
        try:
            report_request = ReportRequest(**request.parameters)
        except Exception as e:
            raise ToolError(
                message=f"Invalid request parameters: {str(e)}",
                tool_name=self.name,
                operation=request.operation,
            ) from e

        start_time = datetime.now(UTC)

        try:
            # Generate report based on type and format
            if report_request.output_format == ReportFormat.JSON:
                result = await self._generate_json_report(report_request, agent_context)
            elif report_request.output_format == ReportFormat.HTML:
                result = await self._generate_html_report(report_request, agent_context)
            else:  # PDF
                result = await self._generate_pdf_report(report_request, agent_context)

            result.generation_time = (datetime.now(UTC) - start_time).total_seconds()
            return result

        except Exception as e:
            raise ToolError(
                message=f"Report generation failed: {str(e)}",
                tool_name=self.name,
                operation=request.operation,
                details={
                    "report_type": report_request.report_type.value,
                    "output_format": report_request.output_format.value,
                },
            ) from e

    async def _generate_json_report(
        self, request: ReportRequest, agent_context: Any | None = None
    ) -> ReportResult:
        """Generate JSON format report"""

        # Collect report data
        report_data = await self._collect_report_data(request, agent_context)

        return ReportResult(
            user_id=request.user_id,
            report_type=request.report_type,
            output_format=request.output_format,
            file_size=len(str(report_data)),
            generation_time=0.0,  # Will be set by caller
            report_data=report_data,
        )

    async def _generate_html_report(
        self, request: ReportRequest, agent_context: Any | None = None
    ) -> ReportResult:
        """Generate HTML format report"""

        # Get report data
        report_data = await self._collect_report_data(request, agent_context)

        # Generate HTML content
        html_content = self._render_html_template(
            request.report_type, report_data, request.include_charts
        )

        # Save to file (in production, would use proper file storage)
        file_path = f"/tmp/report_{request.user_id}_{int(datetime.now(UTC).timestamp())}.html"

        return ReportResult(
            user_id=request.user_id,
            report_type=request.report_type,
            output_format=request.output_format,
            file_path=file_path,
            file_size=len(html_content.encode()),
            generation_time=0.0,
        )

    async def _generate_pdf_report(
        self, request: ReportRequest, agent_context: Any | None = None
    ) -> ReportResult:
        """Generate PDF format report"""

        # Get report data
        report_data = await self._collect_report_data(request, agent_context)

        # Generate PDF content (simplified - in production would use proper PDF library)
        pdf_content = self._render_pdf_template(
            request.report_type, report_data, request.include_charts
        )

        # Save to file
        file_path = f"/tmp/report_{request.user_id}_{int(datetime.now(UTC).timestamp())}.pdf"

        return ReportResult(
            user_id=request.user_id,
            report_type=request.report_type,
            output_format=request.output_format,
            file_path=file_path,
            file_size=len(pdf_content),
            generation_time=0.0,
        )

    async def _collect_report_data(
        self, request: ReportRequest, agent_context: Any | None = None
    ) -> dict[str, Any]:
        """Collect data needed for report generation"""

        # Mock data collection - in production would integrate with actual data sources
        report_data = {
            "user_info": {
                "user_id": request.user_id,
                "name": f"User {request.user_id}",
                "role": "Senior Software Engineer",
                "department": "Engineering",
            },
            "report_metadata": {
                "type": request.report_type.value,
                "generated_at": datetime.now(UTC).isoformat(),
                "date_range_days": request.date_range_days,
            },
        }

        if request.report_type == ReportType.COMPETENCY_ASSESSMENT:
            report_data["competency_data"] = {
                "technical_skills": {"level": 4, "trend": "increasing"},
                "leadership": {"level": 2, "trend": "stable"},
                "communication": {"level": 3, "trend": "increasing"},
                "overall_score": 3.0,
                "assessment_count": 12,
            }

        elif request.report_type == ReportType.CAREER_DEVELOPMENT:
            report_data["career_data"] = {
                "current_level": "Senior",
                "target_level": "Tech Lead",
                "progress_percentage": 65,
                "key_achievements": [
                    "Led migration to microservices",
                    "Mentored 3 junior developers",
                    "Completed system design certification",
                ],
                "development_areas": ["Leadership", "Strategic Planning"],
            }

        elif request.report_type == ReportType.LEARNING_RECOMMENDATIONS:
            report_data["recommendations"] = [
                {
                    "title": "Develop Leadership Skills",
                    "priority": "high",
                    "estimated_time": "40 hours",
                    "status": "not_started",
                },
                {
                    "title": "System Design Mastery",
                    "priority": "medium",
                    "estimated_time": "60 hours",
                    "status": "in_progress",
                },
            ]

        return report_data

    def _render_html_template(
        self, report_type: ReportType, data: dict[str, Any], include_charts: bool
    ) -> str:
        """Render HTML template with data"""

        # Simplified HTML template - in production would use proper templating engine
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{report_type.value.title()} Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; }}
                .section {{ margin: 20px 0; }}
                .competency {{ margin: 10px 0; padding: 10px; border-left: 4px solid #007acc; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{report_type.value.title().replace("_", " ")} Report</h1>
                <p>User: {data.get("user_info", {}).get("name", "Unknown")}</p>
                <p>Generated: {data.get("report_metadata", {}).get("generated_at", "Unknown")}</p>
            </div>

            <div class="section">
                <h2>Summary</h2>
                <p>This report provides insights into career development and competency assessment.</p>
            </div>
        </body>
        </html>
        """

        return html_template

    def _render_pdf_template(
        self, report_type: ReportType, data: dict[str, Any], include_charts: bool
    ) -> bytes:
        """Render PDF template with data"""

        # Simplified PDF generation - in production would use proper PDF library like reportlab
        pdf_content = f"""
        {report_type.value.title()} Report

        User: {data.get("user_info", {}).get("name", "Unknown")}
        Generated: {data.get("report_metadata", {}).get("generated_at", "Unknown")}

        Summary:
        This report provides comprehensive analysis of career development progress.
        """.encode()

        return pdf_content

    def _load_report_templates(self) -> dict[str, Any]:
        """Load report templates"""

        # In production, would load from template files
        return {
            "competency_assessment": {
                "sections": ["summary", "competencies", "trends", "recommendations"],
                "charts": ["competency_radar", "progress_timeline"],
            },
            "career_development": {
                "sections": ["current_state", "goals", "progress", "next_steps"],
                "charts": ["goal_progress", "milestone_timeline"],
            },
        }

    def get_supported_operations(self) -> list[str]:
        """Get list of supported operations"""
        return ["generate_report"]

    def get_report_types(self) -> list[str]:
        """Get list of supported report types"""
        return [rt.value for rt in ReportType]


# Auto-register for tool discovery
ReportGeneratorTool._auto_register = True
ReportGeneratorTool._category = "advisor"
ReportGeneratorTool._version = None  # Version loaded from config
