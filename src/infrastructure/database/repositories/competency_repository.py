"""
⚠️ **ARCHITECTURAL NOTE**: This repository uses SQLAlchemy ORM patterns via BaseRepository,
but db_manager.py uses asyncpg. Current status: Implementation exists but may have compatibility issues.
Recommendation: Test thoroughly or rewrite to use asyncpg directly.

Competency Repository Implementation for ReflectAI

Provides comprehensive competency management with history tracking and trend analysis:
- Current competency level management and scoring
- Historical competency tracking with TimescaleDB optimization
- Trend analysis and change detection
- Evidence-based competency assessment
- Target setting and progress tracking
- Analytics and reporting for competency development
- Bulk operations for competency recalculation
"""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from src.shared import ErrorSeverity, ReflectAIError, get_logger

from ..models.competency import Competency, CompetencyHistory
from .base_repository import (
    BaseRepository,
    FilterCriteria,
    PaginationParams,
    SortCriteria,
)


class CompetencyRepository(BaseRepository[Competency]):
    """
    Competency-specific repository with advanced history tracking and trend analysis

    Features:
    - Current competency level management
    - Historical tracking with TimescaleDB optimization
    - Trend analysis and change detection
    - Evidence-based scoring and confidence intervals
    - Target setting and progress monitoring
    - Analytics and reporting capabilities
    - Bulk recalculation operations
    """

    def __init__(self):
        super().__init__(Competency)
        self.logger = get_logger("repository.competency")

        # Competency-specific caching
        self.cache_ttl_seconds = 900  # 15 minutes for competencies
        self.enable_query_cache = True

    # =====================
    # Competency Management
    # =====================

    async def get_user_competencies(
        self,
        user_id: uuid.UUID,
        competency_ids: list[str] | None = None,
        include_history: bool = False,
    ) -> list[Competency]:
        """Get all competencies for a user"""
        try:
            filters = [FilterCriteria("user_id", "eq", user_id)]

            if competency_ids:
                filters.append(FilterCriteria("competency_id", "in", competency_ids))

            with_relations = ["history"] if include_history else None
            sorts = [SortCriteria("competency_name", "asc")]

            return await self.find_all(filters, sorts, with_relations)

        except Exception as e:
            self.logger.error(f"Error getting user competencies for {user_id}: {str(e)}")
            raise ReflectAIError(
                f"Failed to get user competencies: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    async def get_user_competency(
        self, user_id: uuid.UUID, competency_id: str, include_history: bool = False
    ) -> Competency | None:
        """Get specific competency for a user"""
        try:
            filters = [
                FilterCriteria("user_id", "eq", user_id),
                FilterCriteria("competency_id", "eq", competency_id),
            ]

            with_relations = ["history"] if include_history else None

            return await self.find_one(filters, with_relations)

        except Exception as e:
            self.logger.error(
                f"Error getting user competency {competency_id} for {user_id}: {str(e)}"
            )
            raise ReflectAIError(
                f"Failed to get user competency: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    async def create_or_update_competency(
        self,
        user_id: uuid.UUID,
        competency_id: str,
        competency_name: str,
        current_level: float,
        evidence_count: int = 1,
        confidence_interval: list[float] | None = None,
        target_level: float | None = None,
        activity_id: uuid.UUID | None = None,
        change_reason: str | None = None,
    ) -> Competency:
        """Create or update a competency with history tracking"""
        try:
            # Check if competency exists
            existing = await self.get_user_competency(user_id, competency_id)

            competency_data = {
                "user_id": user_id,
                "competency_id": competency_id,
                "competency_name": competency_name,
                "current_level": Decimal(str(current_level)),
                "evidence_count": evidence_count,
                "last_evidence_date": datetime.now(UTC),
                "last_calculated_at": datetime.now(UTC),
            }

            if target_level is not None:
                competency_data["target_level"] = Decimal(str(target_level))

            if confidence_interval:
                competency_data["confidence_interval"] = [
                    Decimal(str(c)) for c in confidence_interval
                ]

            # Calculate trend if this is an update
            if existing:
                trend_data = await self._calculate_trend(existing, current_level)
                competency_data.update(trend_data)

                competency = await self.update(existing.id, competency_data)
            else:
                # New competency - default trend
                competency_data.update(
                    {"trend_direction": "stable", "trend_strength": Decimal("0")}
                )

                competency = await self.create(competency_data)

            # Record history entry
            if competency:
                await self._record_competency_history(competency, activity_id, change_reason)

            return competency

        except Exception as e:
            self.logger.error(f"Error creating/updating competency {competency_id}: {str(e)}")
            raise ReflectAIError(
                f"Failed to create/update competency: {str(e)}", ErrorSeverity.HIGH
            ) from e

    async def update_competency_target(
        self, user_id: uuid.UUID, competency_id: str, target_level: float
    ) -> Competency | None:
        """Update target level for a competency"""
        try:
            competency = await self.get_user_competency(user_id, competency_id)
            if not competency:
                return None

            return await self.update(competency.id, {"target_level": Decimal(str(target_level))})

        except Exception as e:
            self.logger.error(f"Error updating competency target: {str(e)}")
            raise ReflectAIError(
                f"Failed to update competency target: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    async def increment_evidence_count(
        self, user_id: uuid.UUID, competency_id: str, activity_id: uuid.UUID | None = None
    ) -> Competency | None:
        """Increment evidence count for a competency"""
        try:
            competency = await self.get_user_competency(user_id, competency_id)
            if not competency:
                return None

            updated_competency = await self.update(
                competency.id,
                {
                    "evidence_count": competency.evidence_count + 1,
                    "last_evidence_date": datetime.now(UTC),
                },
            )

            # Record history entry for evidence increase
            if updated_competency and activity_id:
                await self._record_competency_history(
                    updated_competency, activity_id, "evidence_added"
                )

            return updated_competency

        except Exception as e:
            self.logger.error(f"Error incrementing evidence count: {str(e)}")
            raise ReflectAIError(
                f"Failed to increment evidence count: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    # =====================
    # History Operations
    # =====================

    async def get_competency_history(
        self,
        user_id: uuid.UUID,
        competency_id: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 50,
    ) -> list[CompetencyHistory]:
        """Get competency history for trend analysis"""
        try:
            params = [user_id, competency_id]
            param_index = 3

            base_query = """
                SELECT * FROM competency_history
                WHERE user_id = $1 AND competency_id = $2
            """

            if start_time:
                base_query += f" AND timestamp >= ${param_index}"
                params.append(start_time)
                param_index += 1

            if end_time:
                base_query += f" AND timestamp <= ${param_index}"
                params.append(end_time)
                param_index += 1

            base_query += f" ORDER BY timestamp DESC LIMIT {limit}"

            result = await self.execute_raw_query(base_query, params, "all")

            return [CompetencyHistory(**dict(row)) for row in result] if result else []

        except Exception as e:
            self.logger.error(f"Error getting competency history: {str(e)}")
            raise ReflectAIError(
                f"Failed to get competency history: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    async def _record_competency_history(
        self,
        competency: Competency,
        activity_id: uuid.UUID | None = None,
        change_reason: str | None = None,
    ) -> CompetencyHistory:
        """Record a competency history entry"""
        try:
            # Create history repository instance for the insert

            history_data = {
                "user_id": competency.user_id,
                "competency_id": competency.competency_id,
                "level_value": competency.current_level,
                "evidence_count": competency.evidence_count,
                "activity_id": activity_id,
                "change_reason": change_reason,
                "timestamp": datetime.now(UTC),
            }

            # Calculate confidence score from current competency
            if competency.confidence_interval and len(competency.confidence_interval) >= 2:
                # Use interval width as inverse of confidence (narrower = more confident)
                interval_width = (
                    competency.confidence_interval[1] - competency.confidence_interval[0]
                )
                confidence_score = max(0.1, 1.0 - (float(interval_width) / 5.0))
                history_data["confidence_score"] = Decimal(str(confidence_score))

            # Direct database insert for history
            history_query = """
                INSERT INTO competency_history
                (id, user_id, competency_id, level_value, evidence_count, activity_id,
                 change_reason, confidence_score, timestamp)
                VALUES (gen_random_uuid(), $1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING *
            """

            params = [
                competency.user_id,
                competency.competency_id,
                competency.current_level,
                competency.evidence_count,
                activity_id,
                change_reason,
                history_data.get("confidence_score"),
                datetime.now(UTC),
            ]

            result = await self.execute_raw_query(history_query, params, "one")

            if result:
                return CompetencyHistory(**dict(result))
            else:
                raise ReflectAIError("Failed to create history record", ErrorSeverity.HIGH)

        except Exception as e:
            self.logger.error(f"Error recording competency history: {str(e)}")
            raise ReflectAIError(
                f"Failed to record competency history: {str(e)}", ErrorSeverity.HIGH
            ) from e

    # =====================
    # Trend Analysis
    # =====================

    async def _calculate_trend(
        self, existing_competency: Competency, new_level: float
    ) -> dict[str, Any]:
        """Calculate trend direction and strength"""
        try:
            # Get recent history for trend calculation
            history = await self.get_competency_history(
                existing_competency.user_id,
                existing_competency.competency_id,
                start_time=datetime.now(UTC) - timedelta(days=90),
                limit=10,
            )

            if len(history) < 2:
                # Not enough history for trend
                return {"trend_direction": "stable", "trend_strength": Decimal("0")}

            # Calculate trend using linear regression over recent points
            levels = [float(h.level_value) for h in reversed(history)]
            levels.append(new_level)  # Add the new level

            n = len(levels)
            x_values = list(range(n))

            # Simple linear regression
            sum_x = sum(x_values)
            sum_y = sum(levels)
            sum_xy = sum(x * y for x, y in zip(x_values, levels, strict=False))
            sum_x2 = sum(x * x for x in x_values)

            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)

            # Determine direction and strength
            if abs(slope) < 0.05:  # Nearly flat
                direction = "stable"
                strength = 0.0
            elif slope > 0:
                direction = "improving"
                strength = min(1.0, abs(slope) * 2)  # Scale slope to 0-1
            else:
                direction = "declining"
                strength = min(1.0, abs(slope) * 2)

            return {"trend_direction": direction, "trend_strength": Decimal(str(strength))}

        except Exception as e:
            self.logger.warning(f"Error calculating trend: {str(e)}")
            # Return safe defaults
            return {"trend_direction": "stable", "trend_strength": Decimal("0")}

    async def get_trending_competencies(
        self,
        user_id: uuid.UUID | None = None,
        trend_direction: str = "improving",
        min_strength: float = 0.3,
        limit: int = 20,
    ) -> list[Competency]:
        """Get competencies with strong trends"""
        try:
            filters = [
                FilterCriteria("trend_direction", "eq", trend_direction),
                FilterCriteria("trend_strength", "gte", Decimal(str(min_strength))),
            ]

            if user_id:
                filters.append(FilterCriteria("user_id", "eq", user_id))

            sorts = [SortCriteria("trend_strength", "desc")]

            pagination = PaginationParams(page=1, page_size=limit)
            result = await self.find_with_pagination(pagination, filters, sorts)

            return result.items

        except Exception as e:
            self.logger.error(f"Error getting trending competencies: {str(e)}")
            raise ReflectAIError(
                f"Failed to get trending competencies: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    async def get_competency_trend_analysis(
        self, user_id: uuid.UUID, competency_id: str, days: int = 90
    ) -> dict[str, Any]:
        """Get detailed trend analysis for a competency"""
        try:
            start_time = datetime.now(UTC) - timedelta(days=days)
            history = await self.get_competency_history(
                user_id, competency_id, start_time=start_time
            )

            if len(history) < 2:
                return {
                    "trend": "insufficient_data",
                    "data_points": len(history),
                    "analysis": "Need more historical data for trend analysis",
                }

            # Sort history by timestamp (oldest first for analysis)
            sorted_history = sorted(history, key=lambda h: h.timestamp)

            levels = [float(h.level_value) for h in sorted_history]
            [h.timestamp for h in sorted_history]

            # Calculate various trend metrics
            initial_level = levels[0]
            final_level = levels[-1]
            total_change = final_level - initial_level
            max_level = max(levels)
            min_level = min(levels)

            # Volatility (standard deviation)
            mean_level = sum(levels) / len(levels)
            volatility = (sum((level - mean_level) ** 2 for level in levels) / len(levels)) ** 0.5

            # Recent trend (last 30 days)
            recent_cutoff = datetime.now(UTC) - timedelta(days=30)
            recent_history = [h for h in sorted_history if h.timestamp >= recent_cutoff]
            recent_trend = "stable"

            if len(recent_history) >= 2:
                recent_change = float(recent_history[-1].level_value) - float(
                    recent_history[0].level_value
                )
                if recent_change > 0.1:
                    recent_trend = "improving"
                elif recent_change < -0.1:
                    recent_trend = "declining"

            return {
                "competency_id": competency_id,
                "analysis_period_days": days,
                "data_points": len(history),
                "initial_level": initial_level,
                "final_level": final_level,
                "total_change": total_change,
                "max_level": max_level,
                "min_level": min_level,
                "volatility": volatility,
                "recent_trend": recent_trend,
                "trend_direction": "improving"
                if total_change > 0.05
                else "declining"
                if total_change < -0.05
                else "stable",
                "historical_data": [
                    {
                        "timestamp": h.timestamp.isoformat(),
                        "level": float(h.level_value),
                        "evidence_count": h.evidence_count,
                        "change_reason": h.change_reason,
                    }
                    for h in sorted_history
                ],
            }

        except Exception as e:
            self.logger.error(f"Error getting trend analysis: {str(e)}")
            raise ReflectAIError(
                f"Failed to get trend analysis: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    # =====================
    # Analytics and Reporting
    # =====================

    async def get_competency_distribution(
        self, competency_id: str | None = None, user_ids: list[uuid.UUID] | None = None
    ) -> dict[str, Any]:
        """Get competency level distribution across users"""
        try:
            params = []
            param_index = 1
            where_conditions = []

            if competency_id:
                where_conditions.append(f"competency_id = ${param_index}")
                params.append(competency_id)
                param_index += 1

            if user_ids:
                placeholders = ",".join(
                    [f"${i}" for i in range(param_index, param_index + len(user_ids))]
                )
                where_conditions.append(f"user_id IN ({placeholders})")
                params.extend(user_ids)
                param_index += len(user_ids)

            where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""

            query = f"""
                SELECT
                    competency_id,
                    competency_name,
                    COUNT(*) as user_count,
                    AVG(current_level) as avg_level,
                    STDDEV(current_level) as std_deviation,
                    MIN(current_level) as min_level,
                    MAX(current_level) as max_level,
                    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY current_level) as q25,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY current_level) as median,
                    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY current_level) as q75,
                    COUNT(*) FILTER (WHERE trend_direction = 'improving') as improving_count,
                    COUNT(*) FILTER (WHERE trend_direction = 'declining') as declining_count
                FROM competencies
                {where_clause}
                GROUP BY competency_id, competency_name
                ORDER BY user_count DESC, avg_level DESC
            """

            result = await self.execute_raw_query(query, params, "all")

            distribution_data = []
            for row in result if result else []:
                distribution_data.append(
                    {
                        "competency_id": row[0],
                        "competency_name": row[1],
                        "user_count": row[2],
                        "statistics": {
                            "avg_level": float(row[3]) if row[3] else 0.0,
                            "std_deviation": float(row[4]) if row[4] else 0.0,
                            "min_level": float(row[5]) if row[5] else 0.0,
                            "max_level": float(row[6]) if row[6] else 0.0,
                            "quartiles": {
                                "q25": float(row[7]) if row[7] else 0.0,
                                "median": float(row[8]) if row[8] else 0.0,
                                "q75": float(row[9]) if row[9] else 0.0,
                            },
                        },
                        "trends": {
                            "improving_count": row[10] or 0,
                            "declining_count": row[11] or 0,
                            "stable_count": (row[2] or 0) - (row[10] or 0) - (row[11] or 0),
                        },
                    }
                )

            return {
                "total_competencies": len(distribution_data),
                "filter_competency_id": competency_id,
                "filter_user_count": len(user_ids) if user_ids else None,
                "distribution": distribution_data,
            }

        except Exception as e:
            self.logger.error(f"Error getting competency distribution: {str(e)}")
            raise ReflectAIError(
                f"Failed to get competency distribution: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    async def get_user_competency_summary(self, user_id: uuid.UUID) -> dict[str, Any]:
        """Get comprehensive competency summary for a user"""
        try:
            competencies = await self.get_user_competencies(user_id)

            if not competencies:
                return {
                    "user_id": str(user_id),
                    "total_competencies": 0,
                    "analysis": "No competencies found",
                }

            # Calculate summary statistics
            levels = [float(c.current_level) for c in competencies]
            evidence_counts = [c.evidence_count for c in competencies]

            avg_level = sum(levels) / len(levels)
            total_evidence = sum(evidence_counts)

            # Categorize competencies
            novice_count = len([lvl for lvl in levels if lvl < 1.0])
            beginner_count = len([lvl for lvl in levels if 1.0 <= lvl < 2.0])
            intermediate_count = len([lvl for lvl in levels if 2.0 <= lvl < 3.0])
            advanced_count = len([lvl for lvl in levels if 3.0 <= lvl < 4.0])
            expert_count = len([lvl for lvl in levels if lvl >= 4.0])

            # Trend analysis
            improving_count = len([c for c in competencies if c.trend_direction == "improving"])
            declining_count = len([c for c in competencies if c.trend_direction == "declining"])
            stable_count = len(competencies) - improving_count - declining_count

            # Target analysis
            with_targets = [c for c in competencies if c.target_level is not None]
            target_progress = []

            for comp in with_targets:
                progress = comp.progress_to_target()
                if progress is not None:
                    target_progress.append(progress)

            avg_target_progress = (
                sum(target_progress) / len(target_progress) if target_progress else 0
            )

            # Competencies needing attention
            needs_attention = [c for c in competencies if c.needs_attention()]

            return {
                "user_id": str(user_id),
                "total_competencies": len(competencies),
                "average_level": avg_level,
                "total_evidence": total_evidence,
                "level_distribution": {
                    "novice": novice_count,
                    "beginner": beginner_count,
                    "intermediate": intermediate_count,
                    "advanced": advanced_count,
                    "expert": expert_count,
                },
                "trend_analysis": {
                    "improving": improving_count,
                    "stable": stable_count,
                    "declining": declining_count,
                },
                "target_progress": {
                    "competencies_with_targets": len(with_targets),
                    "average_progress": avg_target_progress,
                },
                "needs_attention": {
                    "count": len(needs_attention),
                    "competencies": [c.competency_id for c in needs_attention],
                },
                "top_competencies": [
                    {
                        "competency_id": c.competency_id,
                        "competency_name": c.competency_name,
                        "current_level": float(c.current_level),
                        "evidence_count": c.evidence_count,
                    }
                    for c in sorted(competencies, key=lambda x: x.current_level, reverse=True)[:5]
                ],
            }

        except Exception as e:
            self.logger.error(f"Error getting user competency summary: {str(e)}")
            raise ReflectAIError(
                f"Failed to get user competency summary: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    # =====================
    # Bulk Operations
    # =====================

    async def bulk_recalculate_competencies(
        self,
        user_ids: list[uuid.UUID] | None = None,
        competency_ids: list[str] | None = None,
        recalculate_trends: bool = True,
    ) -> dict[str, int]:
        """Bulk recalculate competency levels and trends"""
        try:
            filters = []

            if user_ids:
                filters.append(FilterCriteria("user_id", "in", user_ids))

            if competency_ids:
                filters.append(FilterCriteria("competency_id", "in", competency_ids))

            competencies = await self.find_all(filters)

            recalc_stats = {"processed": 0, "updated": 0, "errors": 0}

            for competency in competencies:
                try:
                    update_data = {"last_calculated_at": datetime.now(UTC)}

                    # Recalculate evidence count from activities
                    evidence_query = """
                        SELECT COUNT(*) FROM activities
                        WHERE user_id = $1
                        AND competency_areas @> ARRAY[$2]::text[]
                        AND processing_status = 'complete'
                    """

                    evidence_count = await self.execute_raw_query(
                        evidence_query, [competency.user_id, competency.competency_id], "val"
                    )

                    if evidence_count != competency.evidence_count:
                        update_data["evidence_count"] = evidence_count or 0
                        update_data["last_evidence_date"] = datetime.now(UTC)

                    # Recalculate trends if requested
                    if recalculate_trends:
                        # Get current level for trend calculation
                        trend_data = await self._calculate_trend(
                            competency, float(competency.current_level)
                        )
                        update_data.update(trend_data)

                    # Update if there are changes
                    if len(update_data) > 1:  # More than just last_calculated_at
                        await self.update(competency.id, update_data)
                        recalc_stats["updated"] += 1

                    recalc_stats["processed"] += 1

                except Exception as e:
                    self.logger.warning(f"Error recalculating competency {competency.id}: {str(e)}")
                    recalc_stats["errors"] += 1

            self.logger.info(f"Bulk recalculation completed: {recalc_stats}")
            return recalc_stats

        except Exception as e:
            self.logger.error(f"Error in bulk recalculation: {str(e)}")
            raise ReflectAIError(
                f"Failed to bulk recalculate competencies: {str(e)}", ErrorSeverity.HIGH
            ) from e

    async def bulk_set_targets(self, target_mappings: dict[uuid.UUID, dict[str, float]]) -> int:
        """Bulk set target levels for competencies"""
        try:
            updated_count = 0

            for user_id, competency_targets in target_mappings.items():
                for competency_id, target_level in competency_targets.items():
                    try:
                        competency = await self.get_user_competency(user_id, competency_id)
                        if competency:
                            await self.update(
                                competency.id, {"target_level": Decimal(str(target_level))}
                            )
                            updated_count += 1
                    except Exception as e:
                        self.logger.warning(
                            f"Error setting target for {user_id}/{competency_id}: {str(e)}"
                        )

            self.logger.info(f"Bulk set targets for {updated_count} competencies")
            return updated_count

        except Exception as e:
            self.logger.error(f"Error in bulk set targets: {str(e)}")
            raise ReflectAIError(f"Failed to bulk set targets: {str(e)}", ErrorSeverity.HIGH) from e
