"""
Tool Framework for ReflectAI production

Implements  Simple agent tools and task processing including:
- Base Tool class with execute() method and error handling
- Tool registry for dynamic tool discovery and management
- Redis-based task processing with priority queues
- Tool access control and security validation
- Performance metrics and audit logging

Provides the foundation for agent-specific tools and business logic integration.
"""

# Advisor Agent Tools
from .advisor import GoalTrackerTool, ReportGeneratorTool, ResourceFinderTool, get_advisor_tools

# Analysis Agent Tools
from .analysis import DatabaseQueryTool, get_analysis_tools
from .base_tool import (
    Tool,
    ToolError,
    ToolMetrics,
    ToolPermission,
    ToolRequest,
    ToolResponse,
    ToolStatus,
    get_tool_base_class,
)
from .task_processor import (
    ProcessingResult,
    TaskPriority,
    TaskProcessor,
    TaskRequest,
    TaskStatus,
    get_task_processor,
)
from .tool_registry import (
    ToolCategory,
    ToolInfo,
    ToolRegistry,
    get_tool_registry,
    register_tool,
    unregister_tool,
)

__all__ = [
    # Base framework
    "Tool",
    "ToolRequest",
    "ToolResponse",
    "ToolError",
    "ToolPermission",
    "ToolMetrics",
    "ToolStatus",
    "get_tool_base_class",
    # Tool registry
    "ToolRegistry",
    "ToolInfo",
    "ToolCategory",
    "get_tool_registry",
    "register_tool",
    "unregister_tool",
    # Task processing
    "TaskProcessor",
    "TaskRequest",
    "TaskStatus",
    "TaskPriority",
    "ProcessingResult",
    "get_task_processor",
    # Analysis Agent Tools
    "DatabaseQueryTool",
    "get_analysis_tools",
    # Advisor Agent Tools
    "ReportGeneratorTool",
    "GoalTrackerTool",
    "ResourceFinderTool",
    "get_advisor_tools",
]
