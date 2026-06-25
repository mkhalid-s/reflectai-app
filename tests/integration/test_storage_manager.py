"""
Integration tests for storage managers

Tests the fixed ActivityDataManager and IntegratedActivityManager
to ensure proper database initialization and operations.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.storage import ActivityData, ActivityDataManager, get_activity_data_manager
from src.core.storage.models.activity_data import ActivitySource, ActivityType


@pytest.fixture
def mock_db_manager():
    """Mock database manager with TimescaleDB support"""
    db_manager = MagicMock()
    db_manager.is_initialized = True

    # Mock TimescaleDB manager
    timescale_manager = AsyncMock()
    timescale_manager.execute_query = AsyncMock(return_value=[])
    timescale_manager.execute_batch = AsyncMock(return_value=1)

    db_manager.get_timescale_manager = MagicMock(return_value=timescale_manager)

    return db_manager


@pytest.fixture
def mock_redis_manager():
    """Mock Redis manager"""
    redis_manager = AsyncMock()
    redis_manager.get = AsyncMock(return_value=None)
    redis_manager.set = AsyncMock(return_value=True)
    return redis_manager


@pytest.fixture
def sample_activity():
    """Create a sample activity for testing"""
    return ActivityData(
        activity_id=str(uuid.uuid4()),
        user_id="test_user_123",
        title="Test Activity",
        description="This is a test activity",
        activity_type=ActivityType.CODE_REVIEW,
        source=ActivitySource.GITHUB,
        timestamp=datetime.now(UTC),
        confidence_score=0.85,
        metadata={"repo": "test-repo"},
        competencies={"code_quality": 0.9, "collaboration": 0.8},
    )


class TestActivityDataManagerInitialization:
    """Test ActivityDataManager initialization fix"""

    @pytest.mark.asyncio
    async def test_timescale_lazy_initialization(self, mock_db_manager, mock_redis_manager):
        """Test that timescale is initialized lazily when first accessed"""
        manager = ActivityDataManager(
            database_manager=mock_db_manager, redis_manager=mock_redis_manager
        )

        # Verify _timescale starts as None
        assert manager._timescale is None

        # Call _get_timescale to trigger lazy initialization
        timescale = await manager._get_timescale()

        # Verify initialization happened
        assert timescale is not None
        assert manager._timescale is not None
        mock_db_manager.get_timescale_manager.assert_called_once()

    @pytest.mark.asyncio
    async def test_timescale_initialization_caching(self, mock_db_manager, mock_redis_manager):
        """Test that timescale manager is cached after first initialization"""
        manager = ActivityDataManager(
            database_manager=mock_db_manager, redis_manager=mock_redis_manager
        )

        # Get timescale twice
        timescale1 = await manager._get_timescale()
        timescale2 = await manager._get_timescale()

        # Should be the same instance
        assert timescale1 is timescale2
        # Should only call get_timescale_manager once
        assert mock_db_manager.get_timescale_manager.call_count == 1

    @pytest.mark.asyncio
    async def test_db_initialization_if_needed(self):
        """Test that database is initialized if not already initialized"""
        db_manager = MagicMock()
        db_manager.is_initialized = False
        db_manager.initialize = AsyncMock()

        timescale_manager = AsyncMock()
        db_manager.get_timescale_manager = MagicMock(return_value=timescale_manager)

        redis_manager = AsyncMock()

        manager = ActivityDataManager(database_manager=db_manager, redis_manager=redis_manager)

        # Get timescale should trigger db initialization
        await manager._get_timescale()

        # Verify database was initialized
        db_manager.initialize.assert_called_once()


class TestActivityDataManagerOperations:
    """Test ActivityDataManager database operations"""

    @pytest.mark.asyncio
    async def test_query_activities_uses_timescale(self, mock_db_manager, mock_redis_manager):
        """Test that query_activities properly uses timescale manager"""
        # Setup mock to return sample data
        mock_timescale = mock_db_manager.get_timescale_manager()
        mock_timescale.execute_query = AsyncMock(return_value=[])

        manager = ActivityDataManager(
            database_manager=mock_db_manager, redis_manager=mock_redis_manager
        )

        # Import the query model
        from src.core.storage.managers.activity_manager import ActivityQuery

        query = ActivityQuery(user_id="test_user", limit=10, offset=0)

        # Execute query
        result = await manager.query_activities(query)

        # Verify timescale was used
        mock_timescale.execute_query.assert_called_once()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_activity_by_id_uses_timescale(self, mock_db_manager, mock_redis_manager):
        """Test that get_activity_by_id properly uses timescale manager"""
        mock_timescale = mock_db_manager.get_timescale_manager()
        mock_timescale.execute_query = AsyncMock(return_value=None)

        manager = ActivityDataManager(
            database_manager=mock_db_manager, redis_manager=mock_redis_manager
        )

        activity_id = str(uuid.uuid4())

        # Execute get
        result = await manager.get_activity_by_id(activity_id)

        # Verify timescale was used
        mock_timescale.execute_query.assert_called_once()
        assert result is None  # Since we mocked to return None


class TestActivityDataManagerErrorHandling:
    """Test error handling in ActivityDataManager"""

    @pytest.mark.asyncio
    async def test_handles_timescale_initialization_error(self):
        """Test that initialization errors are handled gracefully"""
        db_manager = MagicMock()
        db_manager.is_initialized = True
        db_manager.get_timescale_manager = MagicMock(side_effect=Exception("DB Error"))

        redis_manager = AsyncMock()

        manager = ActivityDataManager(database_manager=db_manager, redis_manager=redis_manager)

        # Should raise the exception
        with pytest.raises(Exception, match="DB Error"):
            await manager._get_timescale()

    @pytest.mark.asyncio
    async def test_handles_query_error_gracefully(self, mock_db_manager, mock_redis_manager):
        """Test that query errors are handled and logged"""
        mock_timescale = mock_db_manager.get_timescale_manager()
        mock_timescale.execute_query = AsyncMock(side_effect=Exception("Query failed"))

        manager = ActivityDataManager(
            database_manager=mock_db_manager, redis_manager=mock_redis_manager
        )

        from src.core.storage.managers.activity_manager import ActivityQuery

        query = ActivityQuery(user_id="test_user")

        # Should handle error gracefully
        with pytest.raises(Exception):
            await manager.query_activities(query)


class TestGlobalActivityManagerSingleton:
    """Test the global activity manager singleton"""

    def test_get_activity_data_manager_returns_singleton(self):
        """Test that get_activity_data_manager returns the same instance"""
        manager1 = get_activity_data_manager()
        manager2 = get_activity_data_manager()

        # Should be the same instance
        assert manager1 is manager2
        assert isinstance(manager1, ActivityDataManager)


@pytest.mark.integration
class TestActivityDataManagerRealScenarios:
    """Integration tests for real-world scenarios"""

    @pytest.mark.asyncio
    async def test_full_activity_lifecycle_mock(
        self, mock_db_manager, mock_redis_manager, sample_activity
    ):
        """Test full activity lifecycle with mocked dependencies"""
        # Setup mock to simulate successful operations
        mock_timescale = mock_db_manager.get_timescale_manager()
        mock_timescale.execute_query = AsyncMock(return_value=0)  # No duplicates

        # Mock repository
        with patch("src.core.storage.managers.activity_manager.ActivityRepository") as MockRepo:
            mock_repo_instance = MockRepo.return_value
            mock_repo_instance.create = AsyncMock(
                return_value=MagicMock(id=sample_activity.activity_id)
            )

            manager = ActivityDataManager(
                database_manager=mock_db_manager, redis_manager=mock_redis_manager
            )

            # Insert activity
            result = await manager.insert_activity(sample_activity)

            # Verify success
            assert result.success is True
            assert result.activity_id == str(sample_activity.activity_id)
            assert result.processing_time_ms > 0

    @pytest.mark.asyncio
    async def test_performance_stats_tracking(self, mock_db_manager, mock_redis_manager):
        """Test that performance statistics are tracked correctly"""
        manager = ActivityDataManager(
            database_manager=mock_db_manager, redis_manager=mock_redis_manager
        )

        # Check initial stats
        assert manager.operation_stats["inserts"]["count"] == 0
        assert manager.operation_stats["queries"]["count"] == 0

        # Stats should be structured correctly
        stats = await manager.get_performance_stats()
        assert "inserts" in stats
        assert "queries" in stats
        assert "updates" in stats
        assert "deletes" in stats
