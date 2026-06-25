"""
Tool Registry System for ReflectAI

Implements tool discovery and management part of
- Tool registry as dictionary mapping tool names to classes
- Dynamic tool discovery and registration
- Tool metadata and categorization
- Health monitoring and metrics aggregation
- Integration with production agent system

Provides centralized management of all agent tools.
"""

import importlib
import inspect
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import Field

from src.infrastructure.config.config_manager import get_config_manager
from src.shared import ErrorCategory, ErrorSeverity, ReflectAIError, get_logger

from .base_tool import Tool, ToolPermission


class ToolCategory(Enum):
    """Tool categories for organization and discovery"""

    ANALYSIS = "analysis"
    ADVISOR = "advisor"
    DATABASE = "database"
    CACHE = "cache"
    CLASSIFICATION = "classification"
    ASSESSMENT = "assessment"
    STORAGE = "storage"
    REPORTING = "reporting"
    UTILITY = "utility"


@dataclass
class ToolInfo:
    """Tool metadata and registration information"""

    name: str
    description: str
    category: ToolCategory
    tool_class: type[Tool]
    required_permissions: list[ToolPermission]
    version: str = Field(default_factory=lambda: get_config_manager().app.version)
    author: str = "ReflectAI"
    registered_at: datetime = None
    instance: Tool | None = None

    def __post_init__(self):
        if self.registered_at is None:
            self.registered_at = datetime.now(UTC)


class ToolRegistryError(ReflectAIError):
    """Specialized error for tool registry operations"""

    def __init__(self, message: str, operation: str, tool_name: str | None = None):
        super().__init__(
            message=message,
            category=ErrorCategory.CONFIGURATION_ERROR,
            severity=ErrorSeverity.WARNING,
            context={"operation": operation, "tool_name": tool_name or "unknown"},
        )


class ToolRegistry:
    """
    Central registry for managing agent tools

    Provides:
    - Tool registration and discovery
    - Category-based organization
    - Health monitoring and metrics
    - Dynamic tool loading and instantiation
    """

    def __init__(self):
        self.logger = get_logger("tool.registry")
        self._tools: dict[str, ToolInfo] = {}
        self._categories: dict[ToolCategory, set[str]] = {cat: set() for cat in ToolCategory}
        self._health_cache: dict[str, dict[str, Any]] = {}
        self._last_health_check = datetime.now(UTC)

    def register_tool(
        self,
        tool_class: type[Tool],
        category: ToolCategory,
        name: str | None = None,
        version: str | None = None,
        auto_instantiate: bool = True,
    ) -> str:
        """
        Register a tool class in the registry

        Args:
            tool_class: Tool class to register
            category: Tool category for organization
            name: Optional custom name (defaults to class name)
            version: Tool version
            auto_instantiate: Whether to create tool instance automatically

        Returns:
            Registered tool name

        Raises:
            ToolRegistryError: If registration fails
        """
        if not issubclass(tool_class, Tool):
            raise ToolRegistryError(
                message=f"Class {tool_class.__name__} must inherit from Tool",
                operation="register",
                tool_name=name or tool_class.__name__,
            )

        tool_name = name or tool_class.__name__.replace("Tool", "").lower()

        # Check for name conflicts
        if tool_name in self._tools:
            raise ToolRegistryError(
                message=f"Tool '{tool_name}' is already registered",
                operation="register",
                tool_name=tool_name,
            )

        try:
            # Create tool info
            tool_info = ToolInfo(
                name=tool_name,
                description=getattr(tool_class, "__doc__", "") or f"{tool_name} tool",
                category=category,
                tool_class=tool_class,
                required_permissions=getattr(
                    tool_class, "required_permissions", [ToolPermission.READ_ONLY]
                ),
                version=version or get_config_manager().app.version,
            )

            # Auto-instantiate if requested
            if auto_instantiate:
                tool_info.instance = self._instantiate_tool(tool_class, tool_name)

            # Register tool
            self._tools[tool_name] = tool_info
            self._categories[category].add(tool_name)

            self.logger.info(f"Registered tool: {tool_name} (category: {category.value})")
            return tool_name

        except Exception as e:
            raise ToolRegistryError(
                message=f"Failed to register tool '{tool_name}': {str(e)}",
                operation="register",
                tool_name=tool_name,
            ) from e

    def unregister_tool(self, name: str) -> bool:
        """
        Unregister a tool from the registry

        Args:
            name: Tool name to unregister

        Returns:
            True if tool was unregistered, False if not found
        """
        if name not in self._tools:
            return False

        tool_info = self._tools[name]

        # Remove from category
        self._categories[tool_info.category].discard(name)

        # Remove from registry
        del self._tools[name]

        # Clear health cache
        self._health_cache.pop(name, None)

        self.logger.info(f"Unregistered tool: {name}")
        return True

    def get_tool_info(self, name: str) -> ToolInfo | None:
        """Get tool information by name"""
        return self._tools.get(name)

    def get_tool_instance(self, name: str) -> Tool | None:
        """
        Get or create tool instance by name

        Args:
            name: Tool name

        Returns:
            Tool instance or None if not found
        """
        tool_info = self._tools.get(name)
        if not tool_info:
            return None

        # Return existing instance if available
        if tool_info.instance:
            return tool_info.instance

        # Create new instance
        try:
            tool_info.instance = self._instantiate_tool(tool_info.tool_class, name)
            return tool_info.instance
        except Exception as e:
            self.logger.error(f"Failed to instantiate tool '{name}': {str(e)}")
            return None

    def list_tools(self, category: ToolCategory | None = None) -> list[ToolInfo]:
        """
        List registered tools, optionally filtered by category

        Args:
            category: Optional category filter

        Returns:
            List of tool information
        """
        if category:
            tool_names = self._categories.get(category, set())
            return [self._tools[name] for name in tool_names]

        return list(self._tools.values())

    def list_tool_names(self, category: ToolCategory | None = None) -> list[str]:
        """
        List tool names, optionally filtered by category

        Args:
            category: Optional category filter

        Returns:
            List of tool names
        """
        if category:
            return list(self._categories.get(category, set()))

        return list(self._tools.keys())

    def get_tool_health(self, name: str) -> dict[str, Any] | None:
        """
        Get health status for a specific tool

        Args:
            name: Tool name

        Returns:
            Health status dict or None if tool not found
        """
        tool_instance = self.get_tool_instance(name)
        if not tool_instance:
            return None

        return tool_instance.get_health_status()

    def get_registry_health(self, refresh: bool = False) -> dict[str, Any]:
        """
        Get overall registry health status

        Args:
            refresh: Whether to refresh cached health data

        Returns:
            Registry health summary
        """
        now = datetime.now(UTC)

        # Use cache if recent and not forcing refresh
        if not refresh and (now - self._last_health_check).seconds < 60:
            return self._health_cache.copy()

        healthy_tools = 0
        degraded_tools = 0
        unhealthy_tools = 0
        total_executions = 0
        total_failures = 0

        tool_health = {}

        for name, tool_info in self._tools.items():
            if tool_info.instance:
                health = tool_info.instance.get_health_status()
                tool_health[name] = health

                # Aggregate metrics
                metrics = tool_info.instance.get_metrics_summary()
                total_executions += metrics["overall"]["execution_count"]
                failure_count = tool_info.instance.metrics.failure_count
                total_failures += failure_count

                # Categorize health
                status = health["status"]
                if status == "healthy":
                    healthy_tools += 1
                elif status == "degraded":
                    degraded_tools += 1
                else:
                    unhealthy_tools += 1
            else:
                tool_health[name] = {"status": "not_instantiated"}

        # Calculate overall health
        total_tools = len(self._tools)
        overall_success_rate = 1.0 - (total_failures / max(total_executions, 1))

        if unhealthy_tools > total_tools * 0.2:
            overall_status = "unhealthy"
        elif degraded_tools > total_tools * 0.3:
            overall_status = "degraded"
        else:
            overall_status = "healthy"

        health_summary = {
            "overall_status": overall_status,
            "total_tools": total_tools,
            "healthy_tools": healthy_tools,
            "degraded_tools": degraded_tools,
            "unhealthy_tools": unhealthy_tools,
            "success_rate": overall_success_rate,
            "total_executions": total_executions,
            "tool_health": tool_health,
            "last_updated": now.isoformat(),
        }

        # Update cache
        self._health_cache = health_summary
        self._last_health_check = now

        return health_summary

    def discover_tools(self, module_paths: list[str]) -> int:
        """
        Dynamically discover and register tools from modules

        Args:
            module_paths: List of module paths to search

        Returns:
            Number of tools discovered and registered
        """
        discovered_count = 0

        for module_path in module_paths:
            try:
                module = importlib.import_module(module_path)

                # Find Tool classes in module
                for _name, obj in inspect.getmembers(module):
                    if (
                        inspect.isclass(obj)
                        and issubclass(obj, Tool)
                        and obj != Tool
                        and hasattr(obj, "_auto_register")
                    ):
                        # Get registration info from class
                        category = getattr(obj, "_category", ToolCategory.UTILITY)
                        version = getattr(obj, "_version", get_config_manager().app.version)

                        try:
                            self.register_tool(obj, category, version=version)
                            discovered_count += 1
                        except ToolRegistryError:
                            # Tool already registered, skip
                            pass

            except Exception as e:
                self.logger.warning(f"Failed to discover tools in {module_path}: {str(e)}")

        self.logger.info(f"Discovered and registered {discovered_count} tools")
        return discovered_count

    def _instantiate_tool(self, tool_class: type[Tool], name: str) -> Tool:
        """
        Instantiate a tool class with proper error handling

        Args:
            tool_class: Tool class to instantiate
            name: Tool name for error reporting

        Returns:
            Tool instance

        Raises:
            ToolRegistryError: If instantiation fails
        """
        try:
            # Get constructor signature to provide appropriate args
            sig = inspect.signature(tool_class.__init__)
            params = list(sig.parameters.keys())[1:]  # Skip 'self'

            # Provide basic args that most tools expect
            kwargs = {}
            if "name" in params:
                kwargs["name"] = name
            if "description" in params:
                kwargs["description"] = getattr(tool_class, "__doc__", "") or f"{name} tool"

            return tool_class(**kwargs)

        except Exception as e:
            raise ToolRegistryError(
                message=f"Failed to instantiate tool class {tool_class.__name__}: {str(e)}",
                operation="instantiate",
                tool_name=name,
            ) from e


# Global registry instance
_global_registry: ToolRegistry | None = None


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry instance"""
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry


def register_tool(
    tool_class: type[Tool],
    category: ToolCategory,
    name: str | None = None,
    version: str | None = None,
    auto_instantiate: bool = True,
) -> str:
    """Register a tool in the global registry"""
    registry = get_tool_registry()
    return registry.register_tool(
        tool_class, category, name, version or get_config_manager().app.version, auto_instantiate
    )


def unregister_tool(name: str) -> bool:
    """Unregister a tool from the global registry"""
    registry = get_tool_registry()
    return registry.unregister_tool(name)


def get_tool_by_name(name: str) -> Tool | None:
    """Get a tool instance by name from the global registry"""
    registry = get_tool_registry()
    return registry.get_tool_instance(name)
