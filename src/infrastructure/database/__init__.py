"""
Database Infrastructure for ReflectAI

PostgreSQL 15+ with TimescaleDB for production time-series optimization.

⚠️ IMPORTANT: To avoid circular import issues, this package does NOT
export anything at the package level. Always import directly from submodules:

CORRECT USAGE:
    from src.infrastructure.database.db_manager import get_database_manager
    from src.infrastructure.database.models import User, Activity
    from src.infrastructure.database.repositories import UserRepository

INCORRECT (will cause circular imports):
    from src.infrastructure.database import get_database_manager  ❌
"""

# Intentionally empty to avoid circular imports
# All imports must be done directly from submodules
