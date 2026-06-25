"""
Analysis Agent Tools for ReflectAI

Currently available:
- DatabaseQueryTool: Fetch user activities and profile data from PostgreSQL

Note: Additional analysis tools (ActivityClassifierTool, CompetencyAssessorTool)
are planned but not yet implemented.
"""

from .database_query import DatabaseQueryTool


def get_analysis_tools():
    """Get all available analysis agent tools"""
    return [
        DatabaseQueryTool(),
    ]


__all__ = ["DatabaseQueryTool", "get_analysis_tools"]
