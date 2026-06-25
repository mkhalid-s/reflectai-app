"""
Pytest configuration for classification tests

Handles import mocking to avoid circular dependencies during testing.
"""

import sys
from unittest.mock import MagicMock

# Mock database dependencies that cause import issues
sys.modules["src.infrastructure.database.db_manager"] = MagicMock()
sys.modules["src.infrastructure.database.repositories"] = MagicMock()
sys.modules["src.infrastructure.database.repositories.base_repository"] = MagicMock()
