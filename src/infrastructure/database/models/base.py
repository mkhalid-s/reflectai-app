"""
Base SQLAlchemy configuration for ReflectAI models

Provides declarative base and common model utilities for all database models.
Optimized for PostgreSQL with TimescaleDB extensions.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import UUID, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models using SQLAlchemy 2.0 style"""

    # Type annotation for mypy
    __abstract__ = True


class TimestampMixin:
    """Mixin for models that need created_at/updated_at timestamps"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Record creation timestamp",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Record last update timestamp",
    )


class UUIDMixin:
    """Mixin for models that use UUID primary keys"""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
        nullable=False,
        comment="Primary key UUID",
    )


class BaseModel(Base, UUIDMixin, TimestampMixin):
    """Base model with UUID primary key and timestamps"""

    __abstract__ = True

    def to_dict(self) -> dict[str, Any]:
        """Convert model instance to dictionary"""
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}

    def update_from_dict(self, data: dict[str, Any]) -> None:
        """Update model instance from dictionary"""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def __repr__(self) -> str:
        """Default string representation"""
        class_name = self.__class__.__name__
        if hasattr(self, "id"):
            return f"<{class_name}(id={self.id})>"
        return f"<{class_name}()>"


class TimescaleModel(Base, UUIDMixin):
    """Base model for TimescaleDB hypertables (no updated_at as they're append-only)"""

    __abstract__ = True

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
        comment="Timestamp for TimescaleDB partitioning",
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert model instance to dictionary"""
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}

    def __repr__(self) -> str:
        """Default string representation"""
        class_name = self.__class__.__name__
        if hasattr(self, "id"):
            return f"<{class_name}(id={self.id}, timestamp={self.timestamp})>"
        return f"<{class_name}()>"


# Export the declarative base for use in models
__all__ = ["Base", "BaseModel", "TimescaleModel", "TimestampMixin", "UUIDMixin"]
