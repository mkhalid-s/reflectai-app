"""
Competency Manager for ReflectAI

Implements competency assessment data management operations:
- Competency score storage and retrieval with time-series optimization
- Competency trend analysis and progression tracking
- Batch operations for performance competency updates
- Competency snapshot and milestone management
- Data validation and integrity checks
- Performance monitoring and optimization

Provides high-level interface for all competency data operations.
"""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field

from src.infrastructure.cache.redis_manager import RedisManager, get_redis_manager
from src.infrastructure.database.db_manager import get_database_manager
from src.infrastructure.database.models.competency import Competency
from src.infrastructure.database.repositories import CompetencyRepository
from src.shared import get_logger

from ..models.competency_data import (
    CompetencyScore,
    CompetencyScoreModel,
    CompetencySnapshot,
)


class CompetencyInsertResult(BaseModel):
    """Result of competency score insertion operation"""

    success: bool = Field(..., description="Whether insertion succeeded")
    score_id: str | None = Field(None, description="Inserted score ID")
    errors: list[str] = Field(default_factory=list, description="Any errors encountered")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    cache_updated: bool = Field(default=False, description="Whether cache was updated")


class CompetencyBatchResult(BaseModel):
    """Result of batch competency operations"""

    total_scores: int = Field(..., description="Total scores in batch")
    successful_inserts: int = Field(..., description="Number of successful insertions")
    failed_inserts: int = Field(default=0, description="Number of failed insertions")
    errors: list[str] = Field(default_factory=list, description="Batch processing errors")
    processing_time_ms: float = Field(..., description="Total processing time")
    batch_id: str | None = Field(None, description="Batch identifier")


class CompetencyTrendAnalysis(BaseModel):
    """Competency trend analysis results"""

    user_id: str = Field(..., description="User identifier")
    competency_name: str = Field(..., description="Competency name")
    time_period: str = Field(..., description="Time period of analysis")
    current_score: float = Field(..., description="Current competency score")
    previous_score: float = Field(..., description="Previous period score")
    score_change: float = Field(..., description="Change in score")
    trend_direction: str = Field(..., description="Trend direction")
    confidence_level: float = Field(..., description="Confidence in trend analysis")
    milestones_achieved: list[str] = Field(
        default_factory=list, description="Milestones achieved in period"
    )


class CompetencyManager:
    """High-level competency data management"""

    def __init__(self, database_manager=None, redis_manager: RedisManager | None = None):
        self.logger = get_logger("storage.competency_manager")
        self.db = database_manager or get_database_manager()
        self.redis = redis_manager or get_redis_manager()
        self.repository = CompetencyRepository()

        # Performance tracking
        self.operation_stats = {
            "inserts": {"count": 0, "total_time": 0.0},
            "queries": {"count": 0, "total_time": 0.0},
            "updates": {"count": 0, "total_time": 0.0},
            "deletes": {"count": 0, "total_time": 0.0},
        }

    def _convert_to_db_model(self, score: CompetencyScore) -> Competency:
        """Convert CompetencyScore to Competency database model"""
        return Competency(
            id=score.score_id,
            user_id=score.user_id,
            competency_id=score.competency_name,  # Using competency_name as competency_id
            competency_name=score.competency_name,
            current_level=score.score_value,
            evidence_count=len(score.evidence_sources) if score.evidence_sources else 0,
            confidence_interval=score.confidence_level,
            last_calculated_at=score.assessed_at,
            assessment_method=score.assessment_method,
            metadata_=score.metadata or {},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            version=1,
        )

    async def insert_competency_score(
        self, score: CompetencyScore, update_cache: bool = True, validate_duplicates: bool = True
    ) -> CompetencyInsertResult:
        """Insert a single competency score with validation and caching"""

        start_time = datetime.now(UTC)

        try:
            # Validate for duplicates if requested
            if validate_duplicates:
                duplicate = await self._check_duplicate_score(score)
                if duplicate:
                    return CompetencyInsertResult(
                        success=False,
                        errors=["Duplicate competency score detected"],
                        processing_time_ms=0.0,
                    )

            # Convert to database model and use repository
            db_competency = self._convert_to_db_model(score)
            created_competency = await self.repository.create(db_competency)

            # Update cache if requested
            cache_updated = False
            if update_cache:
                cache_updated = await self._update_competency_cache(score)

            # Update competency trends and snapshots
            await self._update_competency_trends(score)

            # Track performance
            processing_time = (datetime.now(UTC) - start_time).total_seconds() * 1000
            self.operation_stats["inserts"]["count"] += 1
            self.operation_stats["inserts"]["total_time"] += processing_time

            self.logger.info(f"Successfully inserted competency score {score.score_id}")

            return CompetencyInsertResult(
                success=True,
                score_id=str(created_competency.id),
                processing_time_ms=processing_time,
                cache_updated=cache_updated,
            )

        except Exception as e:
            error_msg = f"Failed to insert competency score: {str(e)}"
            self.logger.error(error_msg)

            processing_time = (datetime.now(UTC) - start_time).total_seconds() * 1000

            return CompetencyInsertResult(
                success=False, errors=[error_msg], processing_time_ms=processing_time
            )

    async def insert_competency_batch(
        self, scores: list[CompetencyScore], batch_size: int = 100, update_cache: bool = True
    ) -> CompetencyBatchResult:
        """Insert competency scores in batches for performance"""

        start_time = datetime.now(UTC)
        total_scores = len(scores)
        successful_inserts = 0
        errors = []
        batch_id = str(uuid.uuid4())

        try:
            # Process in batches
            for i in range(0, total_scores, batch_size):
                batch = scores[i : i + batch_size]

                try:
                    # Convert to database models
                    db_models = [
                        CompetencyScoreModel.from_competency_score(score) for score in batch
                    ]

                    # Prepare batch insert query
                    insert_query = """
                        INSERT INTO competency_scores (
                            score_id, user_id, competency_name, competency_category,
                            score_value, confidence_level, assessment_method,
                            evidence_sources, metadata, assessed_at, created_at, updated_at, version
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                    """

                    # Prepare parameters for batch
                    batch_params = []
                    for model in db_models:
                        batch_params.append(
                            [
                                model.score_id,
                                model.user_id,
                                model.competency_name,
                                model.competency_category.value
                                if model.competency_category
                                else None,
                                model.score_value,
                                model.confidence_level,
                                model.assessment_method,
                                model.evidence_sources,
                                model.metadata,
                                model.assessed_at,
                                model.created_at,
                                model.updated_at,
                                model.version,
                            ]
                        )

                    # Execute batch insert
                    timescale_manager = self.db.get_timescale_manager()
                    result_count = await timescale_manager.execute_batch(
                        insert_query, batch_params, query_type="competency_batch_insert"
                    )

                    successful_inserts += result_count

                    # Update cache for recent scores if requested
                    if update_cache:
                        recent_scores = [
                            s
                            for s in batch
                            if s.assessed_at > datetime.now(UTC) - timedelta(hours=24)
                        ]
                        for score in recent_scores[:10]:  # Limit cache updates
                            await self._update_competency_cache(score)

                    self.logger.info(
                        f"Successfully inserted batch of {result_count} competency scores"
                    )

                except Exception as e:
                    error_msg = f"Batch insert failed for scores {i}-{i + len(batch)}: {str(e)}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)

            # Update competency trends in background
            asyncio.create_task(self._update_batch_trends(scores))

            processing_time = (datetime.now(UTC) - start_time).total_seconds() * 1000

            return CompetencyBatchResult(
                total_scores=total_scores,
                successful_inserts=successful_inserts,
                failed_inserts=total_scores - successful_inserts,
                errors=errors,
                processing_time_ms=processing_time,
                batch_id=batch_id,
            )

        except Exception as e:
            error_msg = f"Batch insert operation failed: {str(e)}"
            self.logger.error(error_msg)

            processing_time = (datetime.now(UTC) - start_time).total_seconds() * 1000

            return CompetencyBatchResult(
                total_scores=total_scores,
                successful_inserts=successful_inserts,
                failed_inserts=total_scores - successful_inserts,
                errors=[error_msg],
                processing_time_ms=processing_time,
                batch_id=batch_id,
            )

    async def get_competency_score_by_id(self, score_id: str | uuid.UUID) -> CompetencyScore | None:
        """Get a specific competency score by ID"""

        try:
            # Try cache first
            cache_key = f"score:{str(score_id)}"
            cached_score = await self.redis.get("competency", cache_key)

            if cached_score:
                return CompetencyScore(**cached_score)

            # Query database
            query = """
                SELECT score_id, user_id, competency_name, competency_category,
                       score_value, confidence_level, assessment_method, evidence_sources,
                       metadata, assessed_at, created_at, updated_at, version
                FROM competency_scores
                WHERE score_id = $1
            """

            timescale_manager = self.db.get_timescale_manager()
            row = await timescale_manager.execute_query(
                query, [str(score_id)], fetch="one", query_type="competency_get_by_id"
            )

            if row:
                db_model = CompetencyScoreModel(**dict(row))
                score = db_model.to_competency_score()

                # Cache the result
                await self.redis.set("competency", cache_key, score.dict(), ttl_seconds=3600)

                return score

            return None

        except Exception as e:
            self.logger.error(f"Failed to get competency score {score_id}: {str(e)}")
            return None

    async def get_user_competency_scores(
        self,
        user_id: str | uuid.UUID,
        competency_name: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
    ) -> list[CompetencyScore]:
        """Get competency scores for a user"""

        try:
            # Build query conditions
            where_conditions = ["user_id = $1"]
            params = [str(user_id)]
            param_count = 2

            if competency_name:
                where_conditions.append(f"competency_name = ${param_count}")
                params.append(competency_name)
                param_count += 1

            if start_date:
                where_conditions.append(f"assessed_at >= ${param_count}")
                params.append(start_date)
                param_count += 1

            if end_date:
                where_conditions.append(f"assessed_at <= ${param_count}")
                params.append(end_date)
                param_count += 1

            # nosec B608: SQL injection false positive - all user input is parameterized
            # where_conditions contains only hardcoded SQL fragments with $ placeholders
            query = f"""
                SELECT score_id, user_id, competency_name, competency_category,
                       score_value, confidence_level, assessment_method, evidence_sources,
                       metadata, assessed_at, created_at, updated_at, version
                FROM competency_scores
                WHERE {" AND ".join(where_conditions)}
                ORDER BY assessed_at DESC
                LIMIT ${param_count}
            """
            params.append(limit)

            timescale_manager = self.db.get_timescale_manager()
            rows = await timescale_manager.execute_query(
                query, params, fetch="all", query_type="user_competency_scores"
            )

            scores = []
            for row in rows:
                db_model = CompetencyScoreModel(**dict(row))
                score = db_model.to_competency_score()
                scores.append(score)

            return scores

        except Exception as e:
            self.logger.error(f"Failed to get competency scores for user {user_id}: {str(e)}")
            return []

    async def get_competency_trends(
        self, user_id: str | uuid.UUID, time_period: str = "30_days"
    ) -> list[CompetencyTrendAnalysis]:
        """Get competency trend analysis for user"""

        try:
            # Calculate time range
            if time_period == "7_days":
                days_back = 7
            elif time_period == "30_days":
                days_back = 30
            elif time_period == "90_days":
                days_back = 90
            else:
                days_back = 30  # Default

            current_date = datetime.now(UTC)
            period_start = current_date - timedelta(days=days_back)
            previous_period_start = period_start - timedelta(days=days_back)

            # Get current period scores
            current_query = """
                SELECT competency_name,
                       AVG(score_value) as avg_score,
                       COUNT(*) as assessment_count
                FROM competency_scores
                WHERE user_id = $1 AND assessed_at BETWEEN $2 AND $3
                GROUP BY competency_name
            """

            # Get previous period scores
            previous_query = """
                SELECT competency_name,
                       AVG(score_value) as avg_score
                FROM competency_scores
                WHERE user_id = $1 AND assessed_at BETWEEN $2 AND $3
                GROUP BY competency_name
            """

            timescale_manager = self.db.get_timescale_manager()

            current_rows = await timescale_manager.execute_query(
                current_query,
                [str(user_id), period_start, current_date],
                fetch="all",
                query_type="current_competency_trends",
            )

            previous_rows = await timescale_manager.execute_query(
                previous_query,
                [str(user_id), previous_period_start, period_start],
                fetch="all",
                query_type="previous_competency_trends",
            )

            # Build trend analysis
            previous_scores = {row["competency_name"]: row["avg_score"] for row in previous_rows}
            trends = []

            for row in current_rows:
                competency_name = row["competency_name"]
                current_score = float(row["avg_score"])
                previous_score = previous_scores.get(competency_name, current_score)

                score_change = current_score - previous_score

                # Determine trend direction
                if abs(score_change) < 0.1:
                    trend_direction = "stable"
                elif score_change > 0:
                    trend_direction = "improving"
                else:
                    trend_direction = "declining"

                # Confidence based on assessment count
                assessment_count = int(row["assessment_count"])
                confidence_level = min(0.95, 0.5 + (assessment_count * 0.1))

                # Detect milestones achieved
                milestones = []

                # Score threshold milestones
                score_thresholds = [(70, "Proficient"), (80, "Advanced"), (90, "Expert")]

                for threshold, level in score_thresholds:
                    if previous_score < threshold <= current_score:
                        milestones.append(f"Reached {level} level ({threshold}+ score)")

                # Significant improvement milestone
                if score_change >= 10:
                    milestones.append(f"Significant improvement (+{score_change:.1f} points)")

                # Consistency milestone (if score is high and stable)
                if current_score >= 85 and abs(score_change) < 2:
                    milestones.append("Maintaining excellence")

                trends.append(
                    CompetencyTrendAnalysis(
                        user_id=str(user_id),
                        competency_name=competency_name,
                        time_period=time_period,
                        current_score=current_score,
                        previous_score=previous_score,
                        score_change=score_change,
                        trend_direction=trend_direction,
                        confidence_level=confidence_level,
                        milestones_achieved=milestones,
                    )
                )

            return trends

        except Exception as e:
            self.logger.error(f"Failed to get competency trends for user {user_id}: {str(e)}")
            return []

    async def get_competency_snapshot(
        self, user_id: str | uuid.UUID, snapshot_date: datetime | None = None
    ) -> CompetencySnapshot | None:
        """Get competency snapshot for a specific date"""

        try:
            if not snapshot_date:
                snapshot_date = datetime.now(UTC)

            query = """
                SELECT snapshot_id, user_id, snapshot_date, competency_scores,
                       overall_score, competency_categories, trends, metadata,
                       created_at, updated_at, version
                FROM competency_snapshots
                WHERE user_id = $1 AND snapshot_date::date = $2::date
                ORDER BY created_at DESC
                LIMIT 1
            """

            timescale_manager = self.db.get_timescale_manager()
            row = await timescale_manager.execute_query(
                query,
                [str(user_id), snapshot_date.date()],
                fetch="one",
                query_type="competency_snapshot",
            )

            if row:
                return CompetencySnapshot(**dict(row))

            return None

        except Exception as e:
            self.logger.error(f"Failed to get competency snapshot: {str(e)}")
            return None

    async def _check_duplicate_score(self, score: CompetencyScore) -> bool:
        """Check if competency score is a duplicate"""

        try:
            # Check for scores with same user, competency, and timestamp (±1 hour)
            time_buffer = timedelta(hours=1)
            start_time = score.assessed_at - time_buffer
            end_time = score.assessed_at + time_buffer

            query = """
                SELECT COUNT(*) as count
                FROM competency_scores
                WHERE user_id = $1
                AND competency_name = $2
                AND assessed_at BETWEEN $3 AND $4
                LIMIT 1
            """

            timescale_manager = self.db.get_timescale_manager()
            result = await timescale_manager.execute_query(
                query,
                [str(score.user_id), score.competency_name, start_time, end_time],
                fetch="val",
                query_type="duplicate_check",
            )

            return result > 0

        except Exception as e:
            self.logger.error(f"Duplicate check failed: {str(e)}")
            return False

    async def _update_competency_cache(self, score: CompetencyScore) -> bool:
        """Update competency cache"""

        try:
            cache_key = str(score.score_id)
            user_cache_key = f"user:{str(score.user_id)}:{score.competency_name}"

            # Cache by both score ID and user+competency
            await self.redis.set("competency", cache_key, score.dict(), ttl_seconds=3600)
            await self.redis.set("competency", user_cache_key, score.dict(), ttl_seconds=1800)

            return True
        except Exception as e:
            self.logger.error(f"Cache update failed: {str(e)}")
            return False

    async def _update_competency_trends(self, score: CompetencyScore):
        """Update competency trends for the score"""

        try:
            # This would implement trend calculation and update logic
            # For now, just log that we're updating trends
            self.logger.debug(f"Updating trends for competency {score.competency_name}")
            pass

        except Exception as e:
            self.logger.error(f"Trend update failed: {str(e)}")

    async def _update_batch_trends(self, scores: list[CompetencyScore]):
        """Update competency trends for batch of scores (background task)"""

        try:
            # Group scores by user and competency
            user_competency_scores = {}
            for score in scores:
                key = (str(score.user_id), score.competency_name)
                if key not in user_competency_scores:
                    user_competency_scores[key] = []
                user_competency_scores[key].append(score)

            # Update trends for each user-competency combination
            for (_user_id, _competency), competency_scores in user_competency_scores.items():
                await self._update_competency_trends(
                    competency_scores[0]
                )  # Use first score for trend update

        except Exception as e:
            self.logger.error(f"Batch trend update failed: {str(e)}")

    async def get_performance_stats(self) -> dict[str, Any]:
        """Get performance statistics"""

        stats = self.operation_stats.copy()

        # Calculate averages
        for _operation, data in stats.items():
            if data["count"] > 0:
                data["avg_time_ms"] = data["total_time"] / data["count"]
            else:
                data["avg_time_ms"] = 0.0

        return stats


# Global manager instance
_global_competency_manager: CompetencyManager | None = None


def get_competency_manager() -> CompetencyManager:
    """Get global competency manager instance"""
    global _global_competency_manager
    if _global_competency_manager is None:
        _global_competency_manager = CompetencyManager()
    return _global_competency_manager
