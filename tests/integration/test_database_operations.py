"""
Integration tests for database operations

IMPORTANT: These tests are currently OUTDATED and need to be rewritten.
They were written for the old PostgresManager (SQLAlchemy-based) which has been
archived. The new DatabaseManager uses asyncpg and the Repository pattern.

TODO: Rewrite these tests to use:
- DatabaseManager from src/infrastructure/database/db_manager.py
- Repository classes from src/infrastructure/database/repositories/
- asyncpg connection patterns instead of SQLAlchemy

Tests should cover:
- Connection pooling
- Transaction management
- Data persistence and retrieval (via Repositories)
- Query performance
- Concurrent operations
"""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest

# SKIP ALL TESTS - Need rewrite for new DatabaseManager architecture
pytestmark = pytest.mark.skip(
    reason="Tests need rewrite for new DatabaseManager + Repository pattern"
)

# Outdated imports - modules no longer exist (archived)
# from src.infrastructure.database.postgres_manager import PostgresManager
# from src.infrastructure.database.timescale_manager import TimescaleManager
from src.shared.exceptions import DatabaseError


class TestPostgresIntegration:
    """Integration tests for PostgreSQL operations"""

    @pytest.fixture
    async def db_manager(self):
        """Create database manager with test configuration"""
        manager = PostgresManager(
            connection_string="postgresql://test_user:test_pass@localhost:5432/test_db",
            pool_size=5,
            max_overflow=10,
        )
        await manager.initialize()
        yield manager
        await manager.cleanup()

    @pytest.fixture
    async def test_user_data(self):
        """Sample user data for testing"""
        return {
            "user_id": f"test_user_{uuid.uuid4().hex[:8]}",
            "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
            "name": "Test User",
            "team_id": "test_team",
            "slack_id": f"U{uuid.uuid4().hex[:10].upper()}",
            "metadata": {"department": "Engineering", "role": "Senior Developer"},
        }

    @pytest.mark.asyncio
    async def test_user_crud_operations(self, db_manager, test_user_data):
        """Test complete CRUD cycle for users"""

        # Create user
        user_id = await db_manager.create_user(test_user_data)
        assert user_id is not None

        # Read user
        user = await db_manager.get_user(user_id)
        assert user is not None
        assert user["email"] == test_user_data["email"]
        assert user["name"] == test_user_data["name"]

        # Update user
        update_data = {
            "name": "Updated User",
            "metadata": {"department": "Product", "role": "Product Manager"},
        }
        success = await db_manager.update_user(user_id, update_data)
        assert success is True

        # Verify update
        updated_user = await db_manager.get_user(user_id)
        assert updated_user["name"] == "Updated User"
        assert updated_user["metadata"]["department"] == "Product"

        # Delete user (soft delete)
        success = await db_manager.delete_user(user_id)
        assert success is True

        # Verify soft delete
        deleted_user = await db_manager.get_user(user_id, include_deleted=True)
        assert deleted_user is not None
        assert deleted_user["deleted_at"] is not None

    @pytest.mark.asyncio
    async def test_activity_creation_and_retrieval(self, db_manager, test_user_data):
        """Test activity creation and retrieval workflows"""

        # Create user first
        user_id = await db_manager.create_user(test_user_data)

        # Create multiple activities
        activities = []
        for i in range(10):
            activity_data = {
                "user_id": user_id,
                "activity_type": "reflection" if i % 2 == 0 else "feedback",
                "content": f"Test activity {i}",
                "metadata": {"index": i, "source": "integration_test"},
                "timestamp": datetime.now(UTC) - timedelta(days=i),
            }
            activity_id = await db_manager.create_activity(activity_data)
            activities.append(activity_id)

        # Retrieve user activities
        user_activities = await db_manager.get_user_activities(user_id=user_id, limit=5)
        assert len(user_activities) == 5

        # Filter by activity type
        reflections = await db_manager.get_user_activities(
            user_id=user_id, activity_type="reflection"
        )
        assert all(a["activity_type"] == "reflection" for a in reflections)

        # Time range query
        start_date = datetime.now(UTC) - timedelta(days=5)
        end_date = datetime.now(UTC) - timedelta(days=2)

        time_filtered = await db_manager.get_user_activities(
            user_id=user_id, start_date=start_date, end_date=end_date
        )

        for activity in time_filtered:
            activity_time = activity["timestamp"]
            assert start_date <= activity_time <= end_date

    @pytest.mark.asyncio
    async def test_transaction_rollback(self, db_manager, test_user_data):
        """Test transaction rollback on error"""

        async with db_manager.transaction() as txn:
            try:
                # Create user
                user_id = await txn.create_user(test_user_data)

                # Create activity
                activity_data = {
                    "user_id": user_id,
                    "activity_type": "test",
                    "content": "Transaction test",
                }
                await txn.create_activity(activity_data)

                # Simulate error
                raise DatabaseError("Simulated error for rollback test")

            except DatabaseError:
                # Transaction should be rolled back
                pass

        # Verify user was not created
        user = await db_manager.get_user(test_user_data["user_id"])
        assert user is None

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, db_manager):
        """Test concurrent database operations"""

        async def create_user_task(index: int):
            """Task to create a user"""
            user_data = {
                "user_id": f"concurrent_user_{index}",
                "email": f"concurrent_{index}@example.com",
                "name": f"Concurrent User {index}",
                "team_id": "test_team",
            }
            return await db_manager.create_user(user_data)

        # Create 20 users concurrently
        tasks = [create_user_task(i) for i in range(20)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Check all succeeded
        successful = [r for r in results if not isinstance(r, Exception)]
        assert len(successful) == 20

        # Verify all users exist
        for i in range(20):
            user = await db_manager.get_user(f"concurrent_user_{i}")
            assert user is not None

    @pytest.mark.asyncio
    async def test_bulk_insert_performance(self, db_manager, test_user_data):
        """Test bulk insert operations for performance"""

        # Create user
        user_id = await db_manager.create_user(test_user_data)

        # Prepare bulk data
        activities = []
        for i in range(1000):
            activities.append(
                {
                    "user_id": user_id,
                    "activity_type": "bulk_test",
                    "content": f"Bulk activity {i}",
                    "metadata": {"index": i},
                    "timestamp": datetime.now(UTC),
                }
            )

        # Measure bulk insert time
        import time

        start_time = time.time()

        results = await db_manager.bulk_create_activities(activities)

        elapsed = time.time() - start_time

        # Should complete within reasonable time (< 5 seconds for 1000 records)
        assert elapsed < 5.0
        assert len(results) == 1000

        # Verify count
        count = await db_manager.count_user_activities(user_id)
        assert count == 1000

    @pytest.mark.asyncio
    async def test_connection_pool_exhaustion(self, db_manager):
        """Test behavior when connection pool is exhausted"""

        async def long_running_query():
            """Simulate a long-running query"""
            async with db_manager.get_connection() as conn:
                await asyncio.sleep(2)
                return await conn.fetch("SELECT 1")

        # Create more concurrent connections than pool size
        tasks = [long_running_query() for _ in range(20)]

        # Should handle pool exhaustion gracefully
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Some may timeout but shouldn't crash
        successful = [r for r in results if not isinstance(r, Exception)]
        assert len(successful) > 0


class TestTimescaleIntegration:
    """Integration tests for TimescaleDB operations"""

    @pytest.fixture
    async def ts_manager(self):
        """Create TimescaleDB manager"""
        manager = TimescaleManager(
            connection_string="postgresql://test_user:test_pass@localhost:5432/test_db"
        )
        await manager.initialize()
        yield manager
        await manager.cleanup()

    @pytest.mark.asyncio
    async def test_time_series_data_ingestion(self, ts_manager):
        """Test time-series data ingestion and retrieval"""

        user_id = f"ts_user_{uuid.uuid4().hex[:8]}"

        # Insert time-series data points
        data_points = []
        base_time = datetime.now(UTC)

        for i in range(100):
            timestamp = base_time - timedelta(minutes=i)
            data_point = {
                "user_id": user_id,
                "metric_type": "engagement",
                "value": 50 + (i % 20),
                "timestamp": timestamp,
                "metadata": {"source": "test", "index": i},
            }
            data_points.append(data_point)

        # Bulk insert
        await ts_manager.insert_metrics(data_points)

        # Query time range
        start = base_time - timedelta(hours=1)
        end = base_time

        metrics = await ts_manager.query_metrics(
            user_id=user_id, metric_type="engagement", start_time=start, end_time=end
        )

        assert len(metrics) > 0
        assert all(m["user_id"] == user_id for m in metrics)

    @pytest.mark.asyncio
    async def test_time_bucket_aggregation(self, ts_manager):
        """Test time-bucket aggregations for analytics"""

        user_id = f"agg_user_{uuid.uuid4().hex[:8]}"

        # Insert hourly data for 7 days
        data_points = []
        base_time = datetime.now(UTC)

        for day in range(7):
            for hour in range(24):
                timestamp = base_time - timedelta(days=day, hours=hour)
                value = 100 + (hour * 5) + (day * 10)

                data_points.append(
                    {
                        "user_id": user_id,
                        "metric_type": "performance",
                        "value": value,
                        "timestamp": timestamp,
                    }
                )

        await ts_manager.insert_metrics(data_points)

        # Get daily aggregates
        aggregates = await ts_manager.get_aggregated_metrics(
            user_id=user_id,
            metric_type="performance",
            interval="1 day",
            aggregation="avg",
            start_time=base_time - timedelta(days=7),
            end_time=base_time,
        )

        assert len(aggregates) == 7

        # Verify aggregation
        for agg in aggregates:
            assert "bucket" in agg
            assert "value" in agg
            assert agg["value"] > 0

    @pytest.mark.asyncio
    async def test_continuous_aggregate_refresh(self, ts_manager):
        """Test continuous aggregate materialization and refresh"""

        # Create continuous aggregate
        await ts_manager.create_continuous_aggregate(
            name="hourly_user_metrics",
            query="""
                SELECT
                    time_bucket('1 hour', timestamp) AS bucket,
                    user_id,
                    metric_type,
                    AVG(value) as avg_value,
                    COUNT(*) as data_points
                FROM metrics
                GROUP BY bucket, user_id, metric_type
            """,
            refresh_interval="1 hour",
        )

        # Insert new data
        user_id = f"ca_user_{uuid.uuid4().hex[:8]}"
        data_points = []

        for i in range(24):
            timestamp = datetime.now(UTC) - timedelta(hours=i)
            data_points.append(
                {
                    "user_id": user_id,
                    "metric_type": "activity",
                    "value": 50 + i,
                    "timestamp": timestamp,
                }
            )

        await ts_manager.insert_metrics(data_points)

        # Refresh aggregate
        await ts_manager.refresh_continuous_aggregate("hourly_user_metrics")

        # Query from aggregate
        results = await ts_manager.query_continuous_aggregate(
            "hourly_user_metrics", filters={"user_id": user_id}
        )

        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_retention_policy(self, ts_manager):
        """Test data retention policy enforcement"""

        # Set retention policy (keep 30 days)
        await ts_manager.set_retention_policy(table="metrics", interval="30 days")

        user_id = f"retention_user_{uuid.uuid4().hex[:8]}"

        # Insert old data (should be dropped)
        old_data = []
        for i in range(10):
            timestamp = datetime.now(UTC) - timedelta(days=40 + i)
            old_data.append(
                {
                    "user_id": user_id,
                    "metric_type": "old_metric",
                    "value": i,
                    "timestamp": timestamp,
                }
            )

        # Insert recent data (should be kept)
        recent_data = []
        for i in range(10):
            timestamp = datetime.now(UTC) - timedelta(days=i)
            recent_data.append(
                {
                    "user_id": user_id,
                    "metric_type": "recent_metric",
                    "value": i,
                    "timestamp": timestamp,
                }
            )

        await ts_manager.insert_metrics(old_data + recent_data)

        # Run retention policy job
        await ts_manager.run_retention_job()

        # Check only recent data remains
        all_metrics = await ts_manager.query_metrics(
            user_id=user_id,
            start_time=datetime.now(UTC) - timedelta(days=50),
            end_time=datetime.now(UTC),
        )

        # Should only have recent metrics
        assert all(m["metric_type"] == "recent_metric" for m in all_metrics)


class TestDatabaseResilience:
    """Test database resilience and error handling"""

    @pytest.fixture
    async def db_manager(self):
        """Create database manager"""
        manager = PostgresManager(
            connection_string="postgresql://test_user:test_pass@localhost:5432/test_db",
            pool_size=5,
            max_overflow=10,
        )
        await manager.initialize()
        yield manager
        await manager.cleanup()

    @pytest.mark.asyncio
    async def test_connection_recovery(self, db_manager):
        """Test automatic recovery from connection loss"""

        # Simulate connection loss
        await db_manager._pool.close()

        # Should automatically reconnect
        result = await db_manager.execute_query("SELECT 1")
        assert result is not None

    @pytest.mark.asyncio
    async def test_deadlock_handling(self, db_manager):
        """Test deadlock detection and retry"""

        async def transaction1():
            async with db_manager.transaction() as txn:
                await txn.execute("LOCK TABLE users IN EXCLUSIVE MODE")
                await asyncio.sleep(0.1)
                await txn.execute("LOCK TABLE activities IN EXCLUSIVE MODE")

        async def transaction2():
            async with db_manager.transaction() as txn:
                await txn.execute("LOCK TABLE activities IN EXCLUSIVE MODE")
                await asyncio.sleep(0.1)
                await txn.execute("LOCK TABLE users IN EXCLUSIVE MODE")

        # Run potentially deadlocking transactions
        results = await asyncio.gather(transaction1(), transaction2(), return_exceptions=True)

        # At least one should succeed (deadlock victim rolled back)
        successful = [r for r in results if not isinstance(r, Exception)]
        assert len(successful) >= 1

    @pytest.mark.asyncio
    async def test_query_timeout(self, db_manager):
        """Test query timeout handling"""

        # Set short timeout
        db_manager.query_timeout = 1  # 1 second

        # Long running query
        with pytest.raises(DatabaseError) as exc_info:
            await db_manager.execute_query(
                "SELECT pg_sleep(5)"  # 5 second sleep
            )

        assert "timeout" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_connection_pool_monitoring(self, db_manager):
        """Test connection pool health monitoring"""

        # Get pool stats
        stats = db_manager.get_pool_stats()

        assert "size" in stats
        assert "checked_in" in stats
        assert "checked_out" in stats
        assert "overflow" in stats

        # Use some connections
        async def use_connection():
            async with db_manager.get_connection() as conn:
                await conn.fetch("SELECT 1")
                await asyncio.sleep(0.1)

        tasks = [use_connection() for _ in range(3)]
        await asyncio.gather(*tasks)

        # Stats should reflect usage
        stats_after = db_manager.get_pool_stats()
        assert stats_after["total_connections"] >= 3
