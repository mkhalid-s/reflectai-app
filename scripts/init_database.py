#!/usr/bin/env python3
"""
Initialize ReflectAI Database Schema

This script creates all necessary database tables using the existing schema.sql file.
For fresh installations only - uses the built-in DBManager initialization.

Usage:
    pdm run python scripts/init_database.py
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def init_database():
    """Initialize database schema using DBManager"""
    from src.infrastructure.database.db_manager import DatabaseManager
    from src.shared.logging import get_logger

    logger = get_logger("scripts.init_database")

    print("=" * 80)
    print("ReflectAI Database Initialization")
    print("=" * 80)
    print()

    try:
        # Create database manager
        print("📦 Creating database manager...")
        db_manager = DatabaseManager()

        # Check if schema.sql exists
        if not db_manager.schema_path.exists():
            print(f"❌ Schema file not found: {db_manager.schema_path}")
            return False

        print(f"✅ Schema file found: {db_manager.schema_path}")
        print()

        # Initialize database (this will run schema.sql)
        print("🔄 Initializing database schema...")
        print(f"   Host: {db_manager.config.host}")
        print(f"   Port: {db_manager.config.port}")
        print(f"   Database: {db_manager.config.database}")
        print(f"   User: {db_manager.config.user}")
        print()

        success = await db_manager.initialize()

        if success:
            print()
            print("=" * 80)
            print("✅ Database schema initialized successfully!")
            print("=" * 80)
            print()
            print("Next steps:")
            print("  1. Seed test data: pdm run python scripts/seed_test_data.py")
            print("  2. Start the application: ./rai run app")
            print("  3. Test Slack integration")
            print()
            return True
        else:
            print()
            print("=" * 80)
            print("❌ Database initialization failed")
            print("=" * 80)
            print()
            print("Troubleshooting:")
            print("  1. Check if PostgreSQL is running: docker ps | grep postgres")
            print("  2. Check database credentials in .env file")
            print("  3. Check logs for detailed error messages")
            print()
            return False

    except Exception as e:
        print()
        print(f"❌ Error during initialization: {e}")
        print()
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(init_database())
    sys.exit(0 if success else 1)
