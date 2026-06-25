"""
⚠️ **ARCHITECTURAL NOTE**: This repository uses SQLAlchemy ORM patterns via BaseRepository,
but db_manager.py uses asyncpg. Current status: Implementation exists but may have compatibility issues.
Recommendation: Test thoroughly or rewrite to use asyncpg directly.

Event Repository Implementation for ReflectAI

Provides comprehensive event management with audit trail and correlation queries:
- System event tracking with TimescaleDB optimization
- Audit event management for compliance
- Event correlation and chain analysis
- Processing status management
- Time-series event analytics
- Compliance and security reporting
- Bulk operations for event processing
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from src.shared import ErrorSeverity, ReflectAIError, get_logger

from ..models.event import AuditEvent, Event
from .base_repository import (
    BaseRepository,
    FilterCriteria,
    PaginationParams,
    SortCriteria,
)


class EventRepository(BaseRepository[Event]):
    """
    Event-specific repository with audit trail and correlation capabilities

    Features:
    - System event tracking and processing
    - Event correlation and chain analysis
    - TimescaleDB time-series optimizations
    - Processing workflow management
    - Event analytics and metrics
    - Compliance and audit reporting
    - Bulk event processing operations
    """

    def __init__(self):
        super().__init__(Event)
        self.logger = get_logger("repository.event")

        # Event-specific caching - short TTL due to high frequency
        self.cache_ttl_seconds = 60  # 1 minute for events
        self.enable_query_cache = False  # Disable for high-frequency data

    # =====================
    # Event Creation and Processing
    # =====================

    async def create_event(
        self,
        event_type: str,
        event_source: str,
        event_data: dict[str, Any],
        user_id: uuid.UUID | None = None,
        correlation_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Event:
        """Create a new system event"""
        try:
            event_record_data = {
                "event_type": event_type,
                "event_source": event_source,
                "event_data": event_data,
                "metadata": metadata or {},
                "user_id": user_id,
                "correlation_id": correlation_id,
                "processing_status": "pending",
                "timestamp": datetime.now(UTC),
            }

            event = await self.create(event_record_data)
            self.logger.debug(f"Created event {event.id} of type {event_type} from {event_source}")

            return event

        except Exception as e:
            self.logger.error(f"Error creating event: {str(e)}")
            raise ReflectAIError(f"Failed to create event: {str(e)}", ErrorSeverity.HIGH) from e

    async def start_event_processing(self, event_id: uuid.UUID) -> Event | None:
        """Mark event as being processed"""
        try:
            update_data = {"processing_status": "processing"}

            event = await self.update(event_id, update_data)

            if event:
                self.logger.debug(f"Started processing event {event_id}")

            return event

        except Exception as e:
            self.logger.error(f"Error starting event processing: {str(e)}")
            raise ReflectAIError(
                f"Failed to start event processing: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    async def complete_event_processing(
        self, event_id: uuid.UUID, processing_metadata: dict[str, Any] | None = None
    ) -> Event | None:
        """Complete event processing"""
        try:
            update_data = {"processing_status": "processed", "processed_at": datetime.now(UTC)}

            if processing_metadata:
                # Merge with existing metadata
                event = await self.get_by_id(event_id)
                if event:
                    current_metadata = event.metadata or {}
                    current_metadata.update(processing_metadata)
                    update_data["metadata"] = current_metadata

            processed_event = await self.update(event_id, update_data)

            if processed_event:
                self.logger.debug(f"Completed processing event {event_id}")

            return processed_event

        except Exception as e:
            self.logger.error(f"Error completing event processing: {str(e)}")
            raise ReflectAIError(
                f"Failed to complete event processing: {str(e)}", ErrorSeverity.HIGH
            ) from e

    async def fail_event_processing(
        self, event_id: uuid.UUID, error_info: dict[str, Any]
    ) -> Event | None:
        """Mark event processing as failed"""
        try:
            # Get current event to merge error info
            event = await self.get_by_id(event_id)
            if not event:
                return None

            current_metadata = event.metadata or {}
            current_metadata["error"] = error_info

            update_data = {
                "processing_status": "failed",
                "processed_at": datetime.now(UTC),
                "metadata": current_metadata,
            }

            failed_event = await self.update(event_id, update_data)

            if failed_event:
                self.logger.warning(
                    f"Failed processing event {event_id}: {error_info.get('message', 'Unknown error')}"
                )

            return failed_event

        except Exception as e:
            self.logger.error(f"Error failing event processing: {str(e)}")
            raise ReflectAIError(
                f"Failed to mark event processing as failed: {str(e)}", ErrorSeverity.HIGH
            ) from e

    async def skip_event_processing(self, event_id: uuid.UUID, reason: str) -> Event | None:
        """Skip event processing with reason"""
        try:
            # Get current event to add skip reason
            event = await self.get_by_id(event_id)
            if not event:
                return None

            current_metadata = event.metadata or {}
            current_metadata["skip_reason"] = reason

            update_data = {
                "processing_status": "skipped",
                "processed_at": datetime.now(UTC),
                "metadata": current_metadata,
            }

            skipped_event = await self.update(event_id, update_data)

            if skipped_event:
                self.logger.debug(f"Skipped processing event {event_id}: {reason}")

            return skipped_event

        except Exception as e:
            self.logger.error(f"Error skipping event processing: {str(e)}")
            raise ReflectAIError(
                f"Failed to skip event processing: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    # =====================
    # Event Queries by Status
    # =====================

    async def get_events_by_status(
        self,
        status: str,
        event_type: str | None = None,
        event_source: str | None = None,
        user_id: uuid.UUID | None = None,
        limit: int = 100,
    ) -> list[Event]:
        """Get events by processing status"""
        try:
            filters = [FilterCriteria("processing_status", "eq", status)]

            if event_type:
                filters.append(FilterCriteria("event_type", "eq", event_type))

            if event_source:
                filters.append(FilterCriteria("event_source", "eq", event_source))

            if user_id:
                filters.append(FilterCriteria("user_id", "eq", user_id))

            sorts = [SortCriteria("timestamp", "asc")]  # Oldest first for processing

            pagination = PaginationParams(page=1, page_size=limit)
            result = await self.find_with_pagination(pagination, filters, sorts)

            return result.items

        except Exception as e:
            self.logger.error(f"Error getting events by status {status}: {str(e)}")
            raise ReflectAIError(
                f"Failed to get events by status: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    async def get_pending_events(
        self, event_type: str | None = None, older_than_minutes: int = 0, limit: int = 50
    ) -> list[Event]:
        """Get events pending processing"""
        try:
            filters = [FilterCriteria("processing_status", "eq", "pending")]

            if event_type:
                filters.append(FilterCriteria("event_type", "eq", event_type))

            if older_than_minutes > 0:
                cutoff_time = datetime.now(UTC) - timedelta(minutes=older_than_minutes)
                filters.append(FilterCriteria("timestamp", "lte", cutoff_time))

            sorts = [SortCriteria("timestamp", "asc")]  # Oldest first

            pagination = PaginationParams(page=1, page_size=limit)
            result = await self.find_with_pagination(pagination, filters, sorts)

            return result.items

        except Exception as e:
            self.logger.error(f"Error getting pending events: {str(e)}")
            raise ReflectAIError(
                f"Failed to get pending events: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    async def get_failed_events(
        self, since_hours: int = 24, event_type: str | None = None, limit: int = 100
    ) -> list[Event]:
        """Get recently failed events"""
        try:
            since_time = datetime.now(UTC) - timedelta(hours=since_hours)

            filters = [
                FilterCriteria("processing_status", "eq", "failed"),
                FilterCriteria("processed_at", "gte", since_time),
            ]

            if event_type:
                filters.append(FilterCriteria("event_type", "eq", event_type))

            sorts = [SortCriteria("processed_at", "desc")]

            pagination = PaginationParams(page=1, page_size=limit)
            result = await self.find_with_pagination(pagination, filters, sorts)

            return result.items

        except Exception as e:
            self.logger.error(f"Error getting failed events: {str(e)}")
            raise ReflectAIError(
                f"Failed to get failed events: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    # =====================
    # Event Correlation and Analysis
    # =====================

    async def get_correlated_events(
        self, correlation_id: str, exclude_event_id: uuid.UUID | None = None, limit: int = 50
    ) -> list[Event]:
        """Get events with the same correlation ID"""
        try:
            filters = [FilterCriteria("correlation_id", "eq", correlation_id)]

            if exclude_event_id:
                filters.append(FilterCriteria("id", "ne", exclude_event_id))

            sorts = [SortCriteria("timestamp", "asc")]

            pagination = PaginationParams(page=1, page_size=limit)
            result = await self.find_with_pagination(pagination, filters, sorts)

            return result.items

        except Exception as e:
            self.logger.error(f"Error getting correlated events: {str(e)}")
            raise ReflectAIError(
                f"Failed to get correlated events: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    async def get_event_chain_analysis(
        self, correlation_id: str, include_processing_times: bool = True
    ) -> dict[str, Any]:
        """Get detailed analysis of an event chain"""
        try:
            events = await self.get_correlated_events(correlation_id)

            if not events:
                return {
                    "correlation_id": correlation_id,
                    "total_events": 0,
                    "analysis": "No events found",
                }

            # Sort events by timestamp
            sorted_events = sorted(events, key=lambda e: e.timestamp)

            # Calculate chain metrics
            first_event = sorted_events[0]
            last_event = sorted_events[-1]

            chain_duration = (last_event.timestamp - first_event.timestamp).total_seconds()

            # Status distribution
            status_counts = {}
            event_types = set()
            sources = set()
            users = set()

            processing_times = []

            for event in events:
                status = event.processing_status
                status_counts[status] = status_counts.get(status, 0) + 1

                event_types.add(event.event_type)
                sources.add(event.event_source)

                if event.user_id:
                    users.add(str(event.user_id))

                if include_processing_times and event.get_processing_duration():
                    processing_times.append(event.get_processing_duration())

            # Processing analytics
            processing_analytics = {}
            if processing_times:
                processing_analytics = {
                    "avg_processing_time": sum(processing_times) / len(processing_times),
                    "min_processing_time": min(processing_times),
                    "max_processing_time": max(processing_times),
                    "total_processing_time": sum(processing_times),
                }

            return {
                "correlation_id": correlation_id,
                "total_events": len(events),
                "chain_duration_seconds": chain_duration,
                "first_event_timestamp": first_event.timestamp.isoformat(),
                "last_event_timestamp": last_event.timestamp.isoformat(),
                "status_distribution": status_counts,
                "unique_event_types": list(event_types),
                "unique_sources": list(sources),
                "unique_users": list(users),
                "processing_analytics": processing_analytics,
                "events": [event.summary for event in sorted_events],
            }

        except Exception as e:
            self.logger.error(f"Error getting event chain analysis: {str(e)}")
            raise ReflectAIError(
                f"Failed to get event chain analysis: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    # =====================
    # User and Time-based Queries
    # =====================

    async def get_user_events(
        self,
        user_id: uuid.UUID,
        event_type: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        pagination: PaginationParams | None = None,
    ) -> list[Event]:
        """Get events for a specific user"""
        try:
            filters = [FilterCriteria("user_id", "eq", user_id)]

            if event_type:
                filters.append(FilterCriteria("event_type", "eq", event_type))

            if start_time:
                filters.append(FilterCriteria("timestamp", "gte", start_time))

            if end_time:
                filters.append(FilterCriteria("timestamp", "lte", end_time))

            sorts = [SortCriteria("timestamp", "desc")]

            if pagination:
                result = await self.find_with_pagination(pagination, filters, sorts)
                return result.items
            else:
                return await self.find_all(filters, sorts)

        except Exception as e:
            self.logger.error(f"Error getting user events: {str(e)}")
            raise ReflectAIError(
                f"Failed to get user events: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    async def get_recent_events(
        self,
        hours: int = 1,
        event_type: str | None = None,
        event_source: str | None = None,
        processing_status: str | None = None,
        limit: int = 100,
    ) -> list[Event]:
        """Get recent events with optional filtering"""
        try:
            since_time = datetime.now(UTC) - timedelta(hours=hours)

            filters = [FilterCriteria("timestamp", "gte", since_time)]

            if event_type:
                filters.append(FilterCriteria("event_type", "eq", event_type))

            if event_source:
                filters.append(FilterCriteria("event_source", "eq", event_source))

            if processing_status:
                filters.append(FilterCriteria("processing_status", "eq", processing_status))

            sorts = [SortCriteria("timestamp", "desc")]

            pagination = PaginationParams(page=1, page_size=limit)
            result = await self.find_with_pagination(pagination, filters, sorts)

            return result.items

        except Exception as e:
            self.logger.error(f"Error getting recent events: {str(e)}")
            raise ReflectAIError(
                f"Failed to get recent events: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    # =====================
    # TimescaleDB Analytics
    # =====================

    async def get_event_time_series(
        self,
        start_time: datetime,
        end_time: datetime,
        bucket_interval: str = "1 hour",
        event_type: str | None = None,
        event_source: str | None = None,
        group_by_type: bool = False,
        group_by_source: bool = False,
    ) -> list[dict[str, Any]]:
        """Get time-bucketed event counts using TimescaleDB"""
        try:
            # Build base query with grouping
            if group_by_type and group_by_source:
                base_query = """
                    SELECT
                        time_bucket($1, timestamp) as time_bucket,
                        event_type,
                        event_source,
                        COUNT(*) as event_count
                    FROM events
                    WHERE timestamp >= $2 AND timestamp <= $3
                """
                params = [bucket_interval, start_time, end_time]
                param_index = 4
                group_by_clause = "GROUP BY time_bucket, event_type, event_source"
                order_by_clause = "ORDER BY time_bucket, event_type, event_source"
            elif group_by_type:
                base_query = """
                    SELECT
                        time_bucket($1, timestamp) as time_bucket,
                        event_type,
                        COUNT(*) as event_count
                    FROM events
                    WHERE timestamp >= $2 AND timestamp <= $3
                """
                params = [bucket_interval, start_time, end_time]
                param_index = 4
                group_by_clause = "GROUP BY time_bucket, event_type"
                order_by_clause = "ORDER BY time_bucket, event_type"
            elif group_by_source:
                base_query = """
                    SELECT
                        time_bucket($1, timestamp) as time_bucket,
                        event_source,
                        COUNT(*) as event_count
                    FROM events
                    WHERE timestamp >= $2 AND timestamp <= $3
                """
                params = [bucket_interval, start_time, end_time]
                param_index = 4
                group_by_clause = "GROUP BY time_bucket, event_source"
                order_by_clause = "ORDER BY time_bucket, event_source"
            else:
                base_query = """
                    SELECT
                        time_bucket($1, timestamp) as time_bucket,
                        COUNT(*) as event_count
                    FROM events
                    WHERE timestamp >= $2 AND timestamp <= $3
                """
                params = [bucket_interval, start_time, end_time]
                param_index = 4
                group_by_clause = "GROUP BY time_bucket"
                order_by_clause = "ORDER BY time_bucket"

            # Add filters
            if event_type:
                base_query += f" AND event_type = ${param_index}"
                params.append(event_type)
                param_index += 1

            if event_source:
                base_query += f" AND event_source = ${param_index}"
                params.append(event_source)
                param_index += 1

            # Complete query
            full_query = f"{base_query} {group_by_clause} {order_by_clause}"

            result = await self.execute_raw_query(full_query, params, "all")

            # Format results based on grouping
            if group_by_type and group_by_source:
                return (
                    [
                        {
                            "time_bucket": row[0],
                            "event_type": row[1],
                            "event_source": row[2],
                            "event_count": row[3],
                        }
                        for row in result
                    ]
                    if result
                    else []
                )
            elif group_by_type:
                return (
                    [
                        {"time_bucket": row[0], "event_type": row[1], "event_count": row[2]}
                        for row in result
                    ]
                    if result
                    else []
                )
            elif group_by_source:
                return (
                    [
                        {"time_bucket": row[0], "event_source": row[1], "event_count": row[2]}
                        for row in result
                    ]
                    if result
                    else []
                )
            else:
                return (
                    [{"time_bucket": row[0], "event_count": row[1]} for row in result]
                    if result
                    else []
                )

        except Exception as e:
            self.logger.error(f"Error getting event time series: {str(e)}")
            raise ReflectAIError(
                f"Failed to get event time series: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    async def get_event_statistics(
        self,
        start_time: datetime,
        end_time: datetime,
        event_type: str | None = None,
        user_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Get comprehensive event statistics for a period"""
        try:
            params = [start_time, end_time]
            param_index = 3
            where_conditions = ["timestamp >= $1 AND timestamp <= $2"]

            if event_type:
                where_conditions.append(f"event_type = ${param_index}")
                params.append(event_type)
                param_index += 1

            if user_id:
                where_conditions.append(f"user_id = ${param_index}")
                params.append(user_id)
                param_index += 1

            where_clause = "WHERE " + " AND ".join(where_conditions)

            query = f"""
                SELECT
                    COUNT(*) as total_events,
                    COUNT(DISTINCT user_id) FILTER (WHERE user_id IS NOT NULL) as unique_users,
                    COUNT(DISTINCT event_type) as unique_event_types,
                    COUNT(DISTINCT event_source) as unique_sources,
                    COUNT(DISTINCT correlation_id) FILTER (WHERE correlation_id IS NOT NULL) as unique_correlations,
                    COUNT(*) FILTER (WHERE processing_status = 'pending') as pending_count,
                    COUNT(*) FILTER (WHERE processing_status = 'processing') as processing_count,
                    COUNT(*) FILTER (WHERE processing_status = 'processed') as processed_count,
                    COUNT(*) FILTER (WHERE processing_status = 'failed') as failed_count,
                    COUNT(*) FILTER (WHERE processing_status = 'skipped') as skipped_count,
                    AVG(EXTRACT(EPOCH FROM (processed_at - timestamp))) FILTER (WHERE processed_at IS NOT NULL) as avg_processing_time
                FROM events
                {where_clause}
            """

            result = await self.execute_raw_query(query, params, "one")

            if result:
                total = result[0] or 0
                processed = result[7] or 0
                failed = result[8] or 0

                return {
                    "total_events": total,
                    "unique_users": result[1] or 0,
                    "unique_event_types": result[2] or 0,
                    "unique_sources": result[3] or 0,
                    "unique_correlations": result[4] or 0,
                    "processing_status": {
                        "pending": result[5] or 0,
                        "processing": result[6] or 0,
                        "processed": processed,
                        "failed": failed,
                        "skipped": result[9] or 0,
                    },
                    "processing_rate": (processed / total * 100) if total > 0 else 0,
                    "failure_rate": (failed / total * 100) if total > 0 else 0,
                    "avg_processing_time_seconds": float(result[10]) if result[10] else 0,
                    "period": {
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat(),
                    },
                }
            else:
                return {}

        except Exception as e:
            self.logger.error(f"Error getting event statistics: {str(e)}")
            raise ReflectAIError(
                f"Failed to get event statistics: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    # =====================
    # Bulk Operations
    # =====================

    async def bulk_update_processing_status(
        self,
        event_ids: list[uuid.UUID],
        new_status: str,
        processing_metadata: dict[str, Any] | None = None,
    ) -> int:
        """Bulk update processing status for multiple events"""
        try:
            update_data = {"processing_status": new_status}

            if new_status in ["processed", "failed", "skipped"]:
                update_data["processed_at"] = datetime.now(UTC)

            # Note: bulk metadata updates would require individual processing
            # For now, just update status
            filters = [FilterCriteria("id", "in", event_ids)]

            updated_count = await self.update_many(filters, update_data)

            self.logger.info(
                f"Bulk updated processing status to {new_status} for {updated_count} events"
            )
            return updated_count

        except Exception as e:
            self.logger.error(f"Error bulk updating processing status: {str(e)}")
            raise ReflectAIError(
                f"Failed to bulk update processing status: {str(e)}", ErrorSeverity.HIGH
            ) from e

    async def cleanup_old_events(
        self,
        older_than_days: int = 90,
        processing_statuses: list[str] | None = None,
        batch_size: int = 10000,
        dry_run: bool = False,
    ) -> dict[str, int]:
        """Cleanup old events to manage storage"""
        if processing_statuses is None:
            processing_statuses = ["processed", "skipped"]

        try:
            cutoff_date = datetime.now(UTC) - timedelta(days=older_than_days)

            # Count events to delete
            params = [cutoff_date]
            status_placeholders = ",".join([f"${i + 2}" for i in range(len(processing_statuses))])
            params.extend(processing_statuses)

            count_query = f"""
                SELECT COUNT(*) FROM events
                WHERE timestamp < $1
                AND processing_status IN ({status_placeholders})
            """

            total_count = await self.execute_raw_query(count_query, params, "val")

            if dry_run:
                return {"total_to_delete": total_count or 0, "deleted": 0, "dry_run": True}

            # Delete in batches
            deleted_count = 0

            while True:
                delete_query = f"""
                    DELETE FROM events
                    WHERE id IN (
                        SELECT id FROM events
                        WHERE timestamp < $1
                        AND processing_status IN ({status_placeholders})
                        LIMIT {batch_size}
                    )
                """

                result = await self.execute_raw_query(delete_query, params, "rowcount")

                batch_deleted = result if result else 0
                deleted_count += batch_deleted

                if batch_deleted == 0:
                    break

                self.logger.info(f"Deleted {deleted_count}/{total_count} old events")

            return {"total_to_delete": total_count or 0, "deleted": deleted_count, "dry_run": False}

        except Exception as e:
            self.logger.error(f"Error cleaning up old events: {str(e)}")
            raise ReflectAIError(
                f"Failed to cleanup old events: {str(e)}", ErrorSeverity.HIGH
            ) from e


class AuditEventRepository(BaseRepository[AuditEvent]):
    """
    Audit event repository for compliance and security tracking

    Features:
    - Database change tracking and auditing
    - Compliance reporting and analysis
    - User action tracking
    - Data change analysis
    - Security event monitoring
    """

    def __init__(self):
        super().__init__(AuditEvent)
        self.logger = get_logger("repository.audit_event")

        # Audit events need longer retention
        self.cache_ttl_seconds = 300  # 5 minutes
        self.enable_query_cache = True

    # =====================
    # Audit Event Creation
    # =====================

    async def create_audit_event(
        self,
        event_type: str,
        action: str,
        table_name: str | None = None,
        record_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        old_values: dict[str, Any] | None = None,
        new_values: dict[str, Any] | None = None,
        change_context: dict[str, Any] | None = None,
        client_info: dict[str, Any] | None = None,
    ) -> AuditEvent:
        """Create a new audit event"""
        try:
            audit_data = {
                "event_type": event_type,
                "action": action,
                "table_name": table_name,
                "record_id": record_id,
                "user_id": user_id,
                "old_values": old_values,
                "new_values": new_values,
                "change_context": change_context or {},
                "client_info": client_info or {},
                "timestamp": datetime.now(UTC),
            }

            audit_event = await self.create(audit_data)

            self.logger.debug(f"Created audit event {audit_event.id} for {action} on {table_name}")
            return audit_event

        except Exception as e:
            self.logger.error(f"Error creating audit event: {str(e)}")
            raise ReflectAIError(
                f"Failed to create audit event: {str(e)}", ErrorSeverity.HIGH
            ) from e

    # =====================
    # Audit Queries
    # =====================

    async def get_user_audit_trail(
        self,
        user_id: uuid.UUID,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        action: str | None = None,
        table_name: str | None = None,
        pagination: PaginationParams | None = None,
    ) -> list[AuditEvent]:
        """Get audit trail for a specific user"""
        try:
            filters = [FilterCriteria("user_id", "eq", user_id)]

            if start_time:
                filters.append(FilterCriteria("timestamp", "gte", start_time))

            if end_time:
                filters.append(FilterCriteria("timestamp", "lte", end_time))

            if action:
                filters.append(FilterCriteria("action", "eq", action))

            if table_name:
                filters.append(FilterCriteria("table_name", "eq", table_name))

            sorts = [SortCriteria("timestamp", "desc")]

            if pagination:
                result = await self.find_with_pagination(pagination, filters, sorts)
                return result.items
            else:
                return await self.find_all(filters, sorts)

        except Exception as e:
            self.logger.error(f"Error getting user audit trail: {str(e)}")
            raise ReflectAIError(
                f"Failed to get user audit trail: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    async def get_record_audit_history(
        self, table_name: str, record_id: uuid.UUID, limit: int = 50
    ) -> list[AuditEvent]:
        """Get audit history for a specific record"""
        try:
            filters = [
                FilterCriteria("table_name", "eq", table_name),
                FilterCriteria("record_id", "eq", record_id),
            ]

            sorts = [SortCriteria("timestamp", "desc")]

            pagination = PaginationParams(page=1, page_size=limit)
            result = await self.find_with_pagination(pagination, filters, sorts)

            return result.items

        except Exception as e:
            self.logger.error(f"Error getting record audit history: {str(e)}")
            raise ReflectAIError(
                f"Failed to get record audit history: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    async def get_data_changes_by_table(
        self,
        table_name: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        actions: list[str] | None = None,
        limit: int = 100,
    ) -> list[AuditEvent]:
        """Get data changes for a specific table"""
        try:
            filters = [FilterCriteria("table_name", "eq", table_name)]

            if start_time:
                filters.append(FilterCriteria("timestamp", "gte", start_time))

            if end_time:
                filters.append(FilterCriteria("timestamp", "lte", end_time))

            if actions:
                filters.append(FilterCriteria("action", "in", actions))
            else:
                # Default to data change actions
                filters.append(FilterCriteria("action", "in", ["CREATE", "UPDATE", "DELETE"]))

            sorts = [SortCriteria("timestamp", "desc")]

            pagination = PaginationParams(page=1, page_size=limit)
            result = await self.find_with_pagination(pagination, filters, sorts)

            return result.items

        except Exception as e:
            self.logger.error(f"Error getting data changes by table: {str(e)}")
            raise ReflectAIError(
                f"Failed to get data changes by table: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    # =====================
    # Compliance Reporting
    # =====================

    async def get_compliance_report(
        self,
        start_time: datetime,
        end_time: datetime,
        tables: list[str] | None = None,
        users: list[uuid.UUID] | None = None,
    ) -> dict[str, Any]:
        """Get compliance report for audit period"""
        try:
            params = [start_time, end_time]
            param_index = 3
            where_conditions = ["timestamp >= $1 AND timestamp <= $2"]

            if tables:
                table_placeholders = ",".join(
                    [f"${i}" for i in range(param_index, param_index + len(tables))]
                )
                where_conditions.append(f"table_name IN ({table_placeholders})")
                params.extend(tables)
                param_index += len(tables)

            if users:
                user_placeholders = ",".join(
                    [f"${i}" for i in range(param_index, param_index + len(users))]
                )
                where_conditions.append(f"user_id IN ({user_placeholders})")
                params.extend([str(u) for u in users])
                param_index += len(users)

            where_clause = "WHERE " + " AND ".join(where_conditions)

            # Main statistics query
            stats_query = f"""
                SELECT
                    COUNT(*) as total_events,
                    COUNT(DISTINCT user_id) FILTER (WHERE user_id IS NOT NULL) as unique_users,
                    COUNT(DISTINCT table_name) FILTER (WHERE table_name IS NOT NULL) as affected_tables,
                    COUNT(*) FILTER (WHERE action = 'CREATE') as create_count,
                    COUNT(*) FILTER (WHERE action = 'UPDATE') as update_count,
                    COUNT(*) FILTER (WHERE action = 'DELETE') as delete_count,
                    COUNT(*) FILTER (WHERE action = 'SELECT') as select_count,
                    COUNT(*) FILTER (WHERE action = 'LOGIN') as login_count,
                    COUNT(*) FILTER (WHERE action = 'LOGOUT') as logout_count
                FROM audit_events
                {where_clause}
            """

            stats_result = await self.execute_raw_query(stats_query, params, "one")

            # Table activity breakdown
            table_query = f"""
                SELECT
                    table_name,
                    action,
                    COUNT(*) as action_count
                FROM audit_events
                {where_clause}
                AND table_name IS NOT NULL
                GROUP BY table_name, action
                ORDER BY table_name, action
            """

            table_result = await self.execute_raw_query(table_query, params, "all")

            # User activity breakdown
            user_query = f"""
                SELECT
                    user_id,
                    COUNT(*) as total_actions,
                    COUNT(*) FILTER (WHERE action IN ('CREATE', 'UPDATE', 'DELETE')) as data_changes
                FROM audit_events
                {where_clause}
                AND user_id IS NOT NULL
                GROUP BY user_id
                ORDER BY total_actions DESC
                LIMIT 20
            """

            user_result = await self.execute_raw_query(user_query, params, "all")

            # Format results
            if stats_result:
                compliance_report = {
                    "period": {
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat(),
                    },
                    "summary": {
                        "total_audit_events": stats_result[0] or 0,
                        "unique_users": stats_result[1] or 0,
                        "affected_tables": stats_result[2] or 0,
                        "action_breakdown": {
                            "create": stats_result[3] or 0,
                            "update": stats_result[4] or 0,
                            "delete": stats_result[5] or 0,
                            "select": stats_result[6] or 0,
                            "login": stats_result[7] or 0,
                            "logout": stats_result[8] or 0,
                        },
                    },
                    "table_activity": {},
                    "top_users": [],
                }

                # Process table activity
                for row in table_result if table_result else []:
                    table = row[0]
                    action = row[1]
                    count = row[2]

                    if table not in compliance_report["table_activity"]:
                        compliance_report["table_activity"][table] = {}

                    compliance_report["table_activity"][table][action] = count

                # Process user activity
                for row in user_result if user_result else []:
                    compliance_report["top_users"].append(
                        {"user_id": str(row[0]), "total_actions": row[1], "data_changes": row[2]}
                    )

                return compliance_report
            else:
                return {}

        except Exception as e:
            self.logger.error(f"Error generating compliance report: {str(e)}")
            raise ReflectAIError(
                f"Failed to generate compliance report: {str(e)}", ErrorSeverity.MEDIUM
            ) from e
