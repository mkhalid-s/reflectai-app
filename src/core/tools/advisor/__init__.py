"""
Advisor Agent Tools for ReflectAI

Currently available:
- ReportGeneratorTool: Create PDF reports using templates
- GoalTrackerTool: Track and update user development goals
- ResourceFinderTool: Find external learning resources and opportunities

Note: RecommendationEngineTool is planned but not yet implemented.
"""

from .goal_tracker import GoalTrackerTool
from .report_generator import ReportGeneratorTool
from .resource_finder import ResourceFinderTool


def get_advisor_tools():
    """Get all available advisor agent tools"""
    return [ReportGeneratorTool(), GoalTrackerTool(), ResourceFinderTool()]


__all__ = ["ReportGeneratorTool", "GoalTrackerTool", "ResourceFinderTool", "get_advisor_tools"]
