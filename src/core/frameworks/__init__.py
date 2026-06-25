"""
Competency Framework Management for ReflectAI

Implements framework loading and validation components including:
- CompetencyFrameworkLoader for JSON-based framework loading
- FrameworkValidator for schema validation and integrity checks
- Hot-reloading capabilities without service restart
- Multi-organization framework support

Provides the infrastructure for dynamic competency framework management.
"""

from .competency_loader import CompetencyFrameworkLoader, FrameworkLoadResult, get_framework_loader
from .framework_validator import (
    FrameworkValidator,
    ValidationError,
    ValidationResult,
    get_framework_validator,
)

__all__ = [
    # Framework loading
    "CompetencyFrameworkLoader",
    "FrameworkLoadResult",
    "get_framework_loader",
    # Framework validation
    "FrameworkValidator",
    "ValidationResult",
    "ValidationError",
    "get_framework_validator",
]
