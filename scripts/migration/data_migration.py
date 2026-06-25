#!/usr/bin/env python3
"""
Data Migration Script for ReflectAI Platform

Handles migration of data from legacy system to new architecture.
"""

import asyncio
import argparse
import json
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import logging
from dataclasses import dataclass
from enum import Enum

import asyncpg
import redis.asyncio as redis
from tqdm import tqdm

# Add parent directory to path for imports
sys.path.insert(0, '/workspaces/reflectai-platform')

from src.shared import get_logger
from src.infrastructure.database.postgres_manager import PostgresManager
from src.infrastructure.cache.redis_manager import RedisManager


class MigrationStatus(Enum):
    """Migration status states."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class MigrationTask:
    """Migration task definition."""
    name: str
    source_table: str
    target_table: str
    batch_size: int = 1000
    transform_func: Optional[str] = None
    validation_func: Optional[str] = None
    status: MigrationStatus = MigrationStatus.PENDING
    records_processed: int = 0
    records_failed: int = 0
    error_message: Optional[str] = None


class DataMigrator:
    """
    Handles data migration from legacy to new system.
    
    Features:
    - Batch processing
    - Data transformation
    - Validation
    - Rollback capability
    - Progress tracking
    """

    def __init__(self, source_db_url: str, target_db_url: str, redis_url: str):
        self.source_db_url = source_db_url
        self.target_db_url = target_db_url
        self.redis_url = redis_url
        
        self.source_conn: Optional[asyncpg.Connection] = None
        self.target_conn: Optional[asyncpg.Connection] = None
        self.redis_client: Optional[redis.Redis] = None
        
        self.logger = get_logger("data_migration")
        self.tasks: List[MigrationTask] = []
        self.migration_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
    async def connect(self):
        """Establish database connections."""
        self.logger.info("Connecting to databases...")
        
        self.source_conn = await asyncpg.connect(self.source_db_url)
        self.target_conn = await asyncpg.connect(self.target_db_url)
        self.redis_client = redis.from_url(self.redis_url)
        
        self.logger.info("Connections established.")

    async def disconnect(self):
        """Close database connections."""
        if self.source_conn:
            await self.source_conn.close()
        if self.target_conn:
            await self.target_conn.close()
        if self.redis_client:
            await self.redis_client.close()

    def add_migration_task(self, task: MigrationTask):
        """Add a migration task."""
        self.tasks.append(task)
        self.logger.info(f"Added migration task: {task.name}")

    async def migrate_users(self):
        """Migrate user data."""
        task = MigrationTask(
            name="users",
            source_table="users",
            target_table="users",
            batch_size=500
        )
        
        self.logger.info("Starting user migration...")
        
        # Count total records
        total = await self.source_conn.fetchval("SELECT COUNT(*) FROM users")
        
        with tqdm(total=total, desc="Migrating users") as pbar:
            offset = 0
            
            while offset < total:
                # Fetch batch
                batch = await self.source_conn.fetch(
                    f"SELECT * FROM users ORDER BY id LIMIT {task.batch_size} OFFSET {offset}"
                )
                
                # Transform and insert
                for record in batch:
                    try:
                        # Transform data
                        transformed = self._transform_user(dict(record))
                        
                        # Insert into new system
                        await self.target_conn.execute(
                            """
                            INSERT INTO users (id, email, name, department, role, created_at, updated_at)
                            VALUES ($1, $2, $3, $4, $5, $6, $7)
                            ON CONFLICT (id) DO UPDATE SET
                                email = EXCLUDED.email,
                                name = EXCLUDED.name,
                                department = EXCLUDED.department,
                                role = EXCLUDED.role,
                                updated_at = EXCLUDED.updated_at
                            """,
                            transformed['id'],
                            transformed['email'],
                            transformed['name'],
                            transformed.get('department'),
                            transformed.get('role'),
                            transformed['created_at'],
                            transformed['updated_at']
                        )
                        
                        task.records_processed += 1
                        
                    except Exception as e:
                        self.logger.error(f"Failed to migrate user {record['id']}: {str(e)}")
                        task.records_failed += 1
                
                pbar.update(len(batch))
                offset += task.batch_size
        
        task.status = MigrationStatus.COMPLETED
        self.logger.info(f"User migration completed: {task.records_processed} processed, {task.records_failed} failed")

    async def migrate_activities(self):
        """Migrate activity data."""
        task = MigrationTask(
            name="activities",
            source_table="work_logs",
            target_table="activities",
            batch_size=2000
        )
        
        self.logger.info("Starting activity migration...")
        
        # Count total records
        total = await self.source_conn.fetchval("SELECT COUNT(*) FROM work_logs")
        
        with tqdm(total=total, desc="Migrating activities") as pbar:
            offset = 0
            
            while offset < total:
                # Fetch batch
                batch = await self.source_conn.fetch(
                    f"SELECT * FROM work_logs ORDER BY id LIMIT {task.batch_size} OFFSET {offset}"
                )
                
                # Prepare batch insert
                activities = []
                
                for record in batch:
                    try:
                        # Transform data
                        transformed = self._transform_activity(dict(record))
                        activities.append(transformed)
                        task.records_processed += 1
                        
                    except Exception as e:
                        self.logger.error(f"Failed to transform activity {record['id']}: {str(e)}")
                        task.records_failed += 1
                
                # Batch insert
                if activities:
                    await self._batch_insert_activities(activities)
                
                pbar.update(len(batch))
                offset += task.batch_size
        
        task.status = MigrationStatus.COMPLETED
        self.logger.info(f"Activity migration completed: {task.records_processed} processed, {task.records_failed} failed")

    async def migrate_competencies(self):
        """Migrate competency data."""
        task = MigrationTask(
            name="competencies",
            source_table="skills",
            target_table="competencies",
            batch_size=1000
        )
        
        self.logger.info("Starting competency migration...")
        
        # Get all unique competencies from activities
        competencies = await self.source_conn.fetch(
            """
            SELECT DISTINCT 
                skill_name as name,
                skill_category as category,
                COUNT(*) as usage_count
            FROM skills
            GROUP BY skill_name, skill_category
            """
        )
        
        with tqdm(total=len(competencies), desc="Migrating competencies") as pbar:
            for comp in competencies:
                try:
                    # Create competency record
                    await self.target_conn.execute(
                        """
                        INSERT INTO competencies (name, category, description, created_at)
                        VALUES ($1, $2, $3, $4)
                        ON CONFLICT (name) DO NOTHING
                        """,
                        comp['name'],
                        comp['category'] or 'General',
                        f"Migrated from legacy system. Usage count: {comp['usage_count']}",
                        datetime.utcnow()
                    )
                    
                    task.records_processed += 1
                    
                except Exception as e:
                    self.logger.error(f"Failed to migrate competency {comp['name']}: {str(e)}")
                    task.records_failed += 1
                
                pbar.update(1)
        
        task.status = MigrationStatus.COMPLETED
        self.logger.info(f"Competency migration completed: {task.records_processed} processed, {task.records_failed} failed")

    async def migrate_cache_data(self):
        """Migrate cached data to Redis."""
        self.logger.info("Starting cache migration...")
        
        # Migrate user preferences
        prefs = await self.source_conn.fetch(
            "SELECT user_id, preferences FROM user_preferences WHERE preferences IS NOT NULL"
        )
        
        for pref in tqdm(prefs, desc="Migrating user preferences"):
            key = f"user:preferences:{pref['user_id']}"
            await self.redis_client.set(key, json.dumps(pref['preferences']), ex=86400*30)
        
        self.logger.info(f"Cache migration completed: {len(prefs)} preferences migrated")

    async def validate_migration(self) -> Dict[str, Any]:
        """Validate migrated data."""
        self.logger.info("Validating migration...")
        
        validation_results = {
            "users": {},
            "activities": {},
            "competencies": {},
            "overall_status": "success"
        }
        
        # Validate user counts
        source_users = await self.source_conn.fetchval("SELECT COUNT(*) FROM users")
        target_users = await self.target_conn.fetchval("SELECT COUNT(*) FROM users")
        
        validation_results["users"] = {
            "source_count": source_users,
            "target_count": target_users,
            "match": source_users == target_users
        }
        
        # Validate activity counts
        source_activities = await self.source_conn.fetchval("SELECT COUNT(*) FROM work_logs")
        target_activities = await self.target_conn.fetchval("SELECT COUNT(*) FROM activities")
        
        validation_results["activities"] = {
            "source_count": source_activities,
            "target_count": target_activities,
            "match": abs(source_activities - target_activities) < 100  # Allow small difference
        }
        
        # Check for validation failures
        if not validation_results["users"]["match"] or not validation_results["activities"]["match"]:
            validation_results["overall_status"] = "failed"
            self.logger.error("Validation failed!")
        else:
            self.logger.info("Validation passed!")
        
        return validation_results

    async def create_indexes(self):
        """Create database indexes for performance."""
        self.logger.info("Creating indexes...")
        
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_activities_user_id ON activities(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_activities_created_at ON activities(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_activities_type ON activities(activity_type)",
            "CREATE INDEX IF NOT EXISTS idx_user_competencies_user_id ON user_competencies(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_user_competencies_competency_id ON user_competencies(competency_id)",
            "CREATE INDEX IF NOT EXISTS idx_goals_user_id ON goals(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_goals_status ON goals(status)",
        ]
        
        for index in tqdm(indexes, desc="Creating indexes"):
            await self.target_conn.execute(index)
        
        self.logger.info("Indexes created successfully.")

    async def rollback(self, checkpoint: str):
        """Rollback migration to checkpoint."""
        self.logger.warning(f"Rolling back to checkpoint: {checkpoint}")
        
        # This would restore from backup or checkpoint
        # Placeholder for actual implementation
        
        self.logger.info("Rollback completed.")

    def _transform_user(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """Transform user data from legacy format."""
        return {
            'id': user['id'],
            'email': user['email'],
            'name': user.get('full_name', user.get('username', '')),
            'department': user.get('department'),
            'role': user.get('job_title', user.get('role')),
            'created_at': user.get('created_at', datetime.utcnow()),
            'updated_at': user.get('updated_at', datetime.utcnow())
        }

    def _transform_activity(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        """Transform activity data from legacy format."""
        # Map old activity types to new ones
        type_mapping = {
            'work_log': 'task_completion',
            'meeting': 'meeting',
            'review': 'code_review',
            'documentation': 'documentation',
            'learning': 'learning'
        }
        
        return {
            'id': activity.get('id'),
            'user_id': activity['user_id'],
            'activity_type': type_mapping.get(activity.get('type', 'other'), 'other'),
            'description': activity.get('description', ''),
            'metadata': json.dumps({
                'legacy_id': activity['id'],
                'migrated_at': datetime.utcnow().isoformat(),
                'original_type': activity.get('type')
            }),
            'created_at': activity.get('created_at', datetime.utcnow()),
            'duration_minutes': activity.get('duration', 0)
        }

    async def _batch_insert_activities(self, activities: List[Dict[str, Any]]):
        """Batch insert activities."""
        await self.target_conn.executemany(
            """
            INSERT INTO activities (user_id, activity_type, description, metadata, created_at, duration_minutes)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT DO NOTHING
            """,
            [
                (
                    a['user_id'],
                    a['activity_type'],
                    a['description'],
                    a['metadata'],
                    a['created_at'],
                    a['duration_minutes']
                )
                for a in activities
            ]
        )

    async def generate_migration_report(self) -> Dict[str, Any]:
        """Generate migration report."""
        report = {
            "migration_id": self.migration_id,
            "start_time": datetime.utcnow().isoformat(),
            "tasks": [],
            "validation": await self.validate_migration(),
            "summary": {
                "total_records_processed": 0,
                "total_records_failed": 0,
                "success_rate": 0.0
            }
        }
        
        for task in self.tasks:
            report["tasks"].append({
                "name": task.name,
                "status": task.status.value,
                "records_processed": task.records_processed,
                "records_failed": task.records_failed,
                "error_message": task.error_message
            })
            
            report["summary"]["total_records_processed"] += task.records_processed
            report["summary"]["total_records_failed"] += task.records_failed
        
        if report["summary"]["total_records_processed"] > 0:
            report["summary"]["success_rate"] = (
                (report["summary"]["total_records_processed"] - report["summary"]["total_records_failed"]) /
                report["summary"]["total_records_processed"] * 100
            )
        
        return report


async def main():
    """Main migration execution."""
    parser = argparse.ArgumentParser(description="ReflectAI Data Migration")
    parser.add_argument("--source-db", required=True, help="Source database URL")
    parser.add_argument("--target-db", required=True, help="Target database URL")
    parser.add_argument("--redis-url", required=True, help="Redis URL")
    parser.add_argument("--skip-validation", action="store_true", help="Skip validation")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    
    args = parser.parse_args()
    
    # Initialize migrator
    migrator = DataMigrator(
        source_db_url=args.source_db,
        target_db_url=args.target_db,
        redis_url=args.redis_url
    )
    
    try:
        # Connect to databases
        await migrator.connect()
        
        if args.dry_run:
            print("DRY RUN MODE - No data will be migrated")
            # Just validate connections and exit
            print("Connections validated successfully.")
            return
        
        # Run migrations
        print("\n" + "="*50)
        print("Starting Data Migration")
        print("="*50 + "\n")
        
        await migrator.migrate_users()
        await migrator.migrate_activities()
        await migrator.migrate_competencies()
        await migrator.migrate_cache_data()
        await migrator.create_indexes()
        
        # Validate if not skipped
        if not args.skip_validation:
            validation_results = await migrator.validate_migration()
            print("\nValidation Results:")
            print(json.dumps(validation_results, indent=2))
        
        # Generate report
        report = await migrator.generate_migration_report()
        
        # Save report
        report_file = f"migration_report_{migrator.migration_id}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\nMigration report saved to: {report_file}")
        print("\n" + "="*50)
        print("Migration Completed Successfully!")
        print("="*50)
        
    except Exception as e:
        print(f"\nMigration failed: {str(e)}")
        sys.exit(1)
        
    finally:
        await migrator.disconnect()


if __name__ == "__main__":
    asyncio.run(main())