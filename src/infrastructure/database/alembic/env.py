"""
Alembic Environment Configuration for ReflectAI

Configured to work with:
- ReflectAI's ConfigManager for database URL
- All SQLAlchemy models for auto-generation
- Async/await patterns (if needed in future)
"""

import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# Import all models so Alembic can detect them
from src.infrastructure.database.models.base import Base
from src.infrastructure.database.models import (
    activity,
    competency,
    event,
    report,
    user,
    user_preferences,
    user_sessions,
    workflow,
)

# Import config manager
from src.infrastructure.config import get_config_manager

# This is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Get database URL from ConfigManager
try:
    app_config = get_config_manager().get_config()
    database_url = app_config.database.url

    # Override sqlalchemy.url in alembic.ini with actual database URL
    config.set_main_option("sqlalchemy.url", database_url)
except Exception as e:
    print(f"Warning: Could not load config from ConfigManager: {e}")
    print("Using URL from alembic.ini")

# Add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine,
    though an Engine is acceptable here as well. By skipping the Engine
    creation we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,  # Detect column type changes
        compare_server_default=True,  # Detect server default changes
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    In this scenario we need to create an Engine and associate
    a connection with the context.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,  # Detect column type changes
            compare_server_default=True,  # Detect server default changes
        )

        with context.begin_transaction():
            context.run_migrations()


# Run migrations
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
