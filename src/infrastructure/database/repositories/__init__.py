"""
Repository Layer for ReflectAI Database Operations

Provides comprehensive repository pattern implementation with:
- Base repository with generic CRUD operations and async support
- Domain-specific repositories for all core entities
- SQLAlchemy 2.0 async patterns with type safety
- TimescaleDB optimizations for time-series data
- Advanced filtering, pagination, and sorting
- Bulk operations and transaction management
- Caching strategies and error handling
- Dependency injection support

All repositories extend the base repository and provide:
- Type-safe operations with generic model typing
- Async/await patterns for non-blocking operations
- Comprehensive filtering and search capabilities
- Time-series analytics for TimescaleDB hypertables
- Bulk operations for high-performance scenarios
- Proper error handling and logging
- Transaction support and connection management
"""

# Base repository
from .activity_repository import ActivityRepository
from .base_repository import (
    BaseRepository,
    FilterCriteria,
    PaginatedResult,
    PaginationParams,
    SortCriteria,
)
from .competency_repository import CompetencyRepository
from .event_repository import AuditEventRepository, EventRepository
from .report_repository import ReportRepository

# Domain-specific repositories
from .user_repository import UserRepository
from .workflow_repository import WorkflowRepository

# Export all repository classes and utilities
__all__ = [
    # Base repository and utilities
    "BaseRepository",
    "FilterCriteria",
    "SortCriteria",
    "PaginationParams",
    "PaginatedResult",
    # Domain repositories
    "UserRepository",
    "ActivityRepository",
    "CompetencyRepository",
    "WorkflowRepository",
    "ReportRepository",
    "EventRepository",
    "AuditEventRepository",
]


# Repository factory function for dependency injection
def get_user_repository() -> UserRepository:
    """Get User repository instance"""
    return UserRepository()


def get_activity_repository() -> ActivityRepository:
    """Get Activity repository instance"""
    return ActivityRepository()


def get_competency_repository() -> CompetencyRepository:
    """Get Competency repository instance"""
    return CompetencyRepository()


def get_workflow_repository() -> WorkflowRepository:
    """Get Workflow repository instance"""
    return WorkflowRepository()


def get_report_repository() -> ReportRepository:
    """Get Report repository instance"""
    return ReportRepository()


def get_event_repository() -> EventRepository:
    """Get Event repository instance"""
    return EventRepository()


def get_audit_event_repository() -> AuditEventRepository:
    """Get AuditEvent repository instance"""
    return AuditEventRepository()


# Repository registry for dynamic access
REPOSITORY_REGISTRY = {
    "user": UserRepository,
    "activity": ActivityRepository,
    "competency": CompetencyRepository,
    "workflow": WorkflowRepository,
    "report": ReportRepository,
    "event": EventRepository,
    "audit_event": AuditEventRepository,
}


def get_repository(repository_name: str):
    """Get repository instance by name"""
    repository_class = REPOSITORY_REGISTRY.get(repository_name)
    if not repository_class:
        raise ValueError(f"Unknown repository: {repository_name}")
    return repository_class()


# Add factory functions to __all__
__all__.extend(
    [
        "get_user_repository",
        "get_activity_repository",
        "get_competency_repository",
        "get_workflow_repository",
        "get_report_repository",
        "get_event_repository",
        "get_audit_event_repository",
        "get_repository",
        "REPOSITORY_REGISTRY",
    ]
)
