"""
SQLAlchemy ORM Models for ReflectAI Database

Provides database models for all core entities:
- User management and profiles
- Activity tracking and analysis
- Competency scoring and history
- Workflow orchestration
- Report generation
- Event tracking and audit logs
- User preferences and sessions

All models are optimized for PostgreSQL with TimescaleDB extensions.
Uses SQLAlchemy 2.0 style with proper type annotations and relationships.
"""

# Import base classes
from .activity import Activity
from .base import Base, BaseModel, TimescaleModel
from .competency import Competency, CompetencyHistory
from .event import AuditEvent, Event
from .report import Report

# Import core models
from .user import User

# Import support models
from .user_preferences import UserPreference
from .user_sessions import UserSession
from .workflow import Workflow

__all__ = [
    # Base classes
    "Base",
    "BaseModel",
    "TimescaleModel",
    # Core models
    "User",
    "Activity",
    "Competency",
    "CompetencyHistory",
    "Workflow",
    "Report",
    "Event",
    "AuditEvent",
    # Support models
    "UserPreference",
    "UserSession",
]
