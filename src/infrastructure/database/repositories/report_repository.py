"""
⚠️ **ARCHITECTURAL NOTE**: This repository uses SQLAlchemy ORM patterns via BaseRepository,
but db_manager.py uses asyncpg. Current status: Implementation exists but may have compatibility issues.
Recommendation: Test thoroughly or rewrite to use asyncpg directly.

Report Repository Implementation for ReflectAI

Provides comprehensive report management with delivery tracking and file management:
- Report generation lifecycle management
- File storage and metadata tracking
- Delivery status and method tracking
- Report expiration and cleanup
- Format-specific operations (Slack, PDF, CSV, JSON)
- Analytics and reporting metrics
- Bulk operations for report management
"""

import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from src.shared import ErrorSeverity, ReflectAIError, get_logger

from ..models.report import Report
from .base_repository import (
    BaseRepository,
    FilterCriteria,
    PaginationParams,
    SortCriteria,
)


class ReportRepository(BaseRepository[Report]):
    """
    Report-specific repository with delivery tracking and file management

    Features:
    - Report generation lifecycle management
    - File storage and metadata operations
    - Delivery tracking and status management
    - Format-specific report operations
    - Expiration and cleanup management
    - Analytics and performance metrics
    - Bulk operations for report management
    """

    def __init__(self):
        super().__init__(Report)
        self.logger = get_logger("repository.report")

        # Report-specific caching
        self.cache_ttl_seconds = 1800  # 30 minutes for reports
        self.enable_query_cache = True

    # =====================
    # Report Lifecycle Management
    # =====================

    async def create_report(
        self,
        user_id: uuid.UUID,
        report_type: str,
        title: str,
        format: str = "slack",
        parameters: dict[str, Any] | None = None,
        expires_in_days: int | None = 30,
    ) -> Report:
        """Create a new report request"""
        try:
            # Calculate expiration date if specified
            expires_at = None
            if expires_in_days:
                expires_at = datetime.now(UTC) + timedelta(days=expires_in_days)

            report_data = {
                "user_id": user_id,
                "report_type": report_type,
                "title": title,
                "format": format,
                "status": "pending",
                "parameters": parameters or {},
                "content": {},
                "delivery_metadata": {},
                "expires_at": expires_at,
            }

            report = await self.create(report_data)
            self.logger.info(f"Created report {report.id} of type {report_type} for user {user_id}")

            return report

        except Exception as e:
            self.logger.error(f"Error creating report: {str(e)}")
            raise ReflectAIError(f"Failed to create report: {str(e)}", ErrorSeverity.HIGH) from e

    async def start_report_generation(self, report_id: uuid.UUID) -> Report | None:
        """Mark report as generating"""
        try:
            update_data = {"status": "generating"}

            report = await self.update(report_id, update_data)

            if report:
                self.logger.info(f"Started generation for report {report_id}")

            return report

        except Exception as e:
            self.logger.error(f"Error starting report generation: {str(e)}")
            raise ReflectAIError(
                f"Failed to start report generation: {str(e)}", ErrorSeverity.HIGH
            ) from e

    async def complete_report_generation(
        self,
        report_id: uuid.UUID,
        content_data: dict[str, Any],
        file_info: dict[str, Any] | None = None,
    ) -> Report | None:
        """Complete report generation with content and optional file info"""
        try:
            update_data = {
                "status": "ready",
                "generated_at": datetime.now(UTC),
                "content": content_data,
            }

            if file_info:
                if "file_path" in file_info:
                    update_data["file_path"] = file_info["file_path"]
                if "file_size_bytes" in file_info:
                    update_data["file_size_bytes"] = file_info["file_size_bytes"]
                if "page_count" in file_info:
                    update_data["page_count"] = file_info["page_count"]

            report = await self.update(report_id, update_data)

            if report:
                self.logger.info(f"Completed generation for report {report_id}")

            return report

        except Exception as e:
            self.logger.error(f"Error completing report generation: {str(e)}")
            raise ReflectAIError(
                f"Failed to complete report generation: {str(e)}", ErrorSeverity.HIGH
            ) from e

    async def fail_report_generation(
        self, report_id: uuid.UUID, error_info: dict[str, Any]
    ) -> Report | None:
        """Mark report generation as failed"""
        try:
            # Get current report to merge error info
            report = await self.get_by_id(report_id)
            if not report:
                return None

            current_content = report.content or {}
            current_content["error"] = error_info

            update_data = {"status": "failed", "content": current_content}

            failed_report = await self.update(report_id, update_data)

            if failed_report:
                self.logger.warning(
                    f"Failed report generation {report_id}: {error_info.get('message', 'Unknown error')}"
                )

            return failed_report

        except Exception as e:
            self.logger.error(f"Error failing report generation: {str(e)}")
            raise ReflectAIError(
                f"Failed to mark report generation as failed: {str(e)}", ErrorSeverity.HIGH
            ) from e

    # =====================
    # Delivery Management
    # =====================

    async def mark_report_delivered(
        self,
        report_id: uuid.UUID,
        delivery_method: str,
        delivery_metadata: dict[str, Any] | None = None,
    ) -> Report | None:
        """Mark report as delivered"""
        try:
            update_data = {
                "status": "delivered",
                "delivery_method": delivery_method,
                "delivery_status": "sent",
            }

            if delivery_metadata:
                # Merge with existing delivery metadata
                report = await self.get_by_id(report_id)
                if report:
                    current_metadata = report.delivery_metadata or {}
                    current_metadata.update(delivery_metadata)
                    update_data["delivery_metadata"] = current_metadata

            delivered_report = await self.update(report_id, update_data)

            if delivered_report:
                self.logger.info(f"Marked report {report_id} as delivered via {delivery_method}")

            return delivered_report

        except Exception as e:
            self.logger.error(f"Error marking report as delivered: {str(e)}")
            raise ReflectAIError(
                f"Failed to mark report as delivered: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    async def update_delivery_status(
        self,
        report_id: uuid.UUID,
        delivery_status: str,
        delivery_metadata: dict[str, Any] | None = None,
    ) -> Report | None:
        """Update report delivery status"""
        try:
            update_data = {"delivery_status": delivery_status}

            if delivery_metadata:
                # Merge with existing delivery metadata
                report = await self.get_by_id(report_id)
                if report:
                    current_metadata = report.delivery_metadata or {}
                    current_metadata.update(delivery_metadata)
                    update_data["delivery_metadata"] = current_metadata

            return await self.update(report_id, update_data)

        except Exception as e:
            self.logger.error(f"Error updating delivery status: {str(e)}")
            raise ReflectAIError(
                f"Failed to update delivery status: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    # =====================
    # Status-Based Queries
    # =====================

    async def get_reports_by_status(
        self,
        status: str,
        user_id: uuid.UUID | None = None,
        report_type: str | None = None,
        format: str | None = None,
        limit: int = 100,
    ) -> list[Report]:
        """Get reports by status with optional filtering"""
        try:
            filters = [FilterCriteria("status", "eq", status)]

            if user_id:
                filters.append(FilterCriteria("user_id", "eq", user_id))

            if report_type:
                filters.append(FilterCriteria("report_type", "eq", report_type))

            if format:
                filters.append(FilterCriteria("format", "eq", format))

            sorts = [SortCriteria("created_at", "desc")]

            pagination = PaginationParams(page=1, page_size=limit)
            result = await self.find_with_pagination(pagination, filters, sorts)

            return result.items

        except Exception as e:
            self.logger.error(f"Error getting reports by status {status}: {str(e)}")
            raise ReflectAIError(
                f"Failed to get reports by status: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    async def get_pending_reports(
        self, user_id: uuid.UUID | None = None, report_type: str | None = None
    ) -> list[Report]:
        """Get pending reports for generation"""
        return await self.get_reports_by_status("pending", user_id, report_type)

    async def get_ready_reports(
        self, user_id: uuid.UUID | None = None, format: str | None = None
    ) -> list[Report]:
        """Get reports ready for delivery"""
        return await self.get_reports_by_status("ready", user_id, None, format)

    async def get_failed_reports(
        self, user_id: uuid.UUID | None = None, since_hours: int = 24
    ) -> list[Report]:
        """Get recently failed reports"""
        try:
            since_time = datetime.now(UTC) - timedelta(hours=since_hours)

            filters = [
                FilterCriteria("status", "eq", "failed"),
                FilterCriteria("updated_at", "gte", since_time),
            ]

            if user_id:
                filters.append(FilterCriteria("user_id", "eq", user_id))

            sorts = [SortCriteria("updated_at", "desc")]

            return await self.find_all(filters, sorts)

        except Exception as e:
            self.logger.error(f"Error getting failed reports: {str(e)}")
            raise ReflectAIError(
                f"Failed to get failed reports: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    # =====================
    # User and Type Queries
    # =====================

    async def get_user_reports(
        self,
        user_id: uuid.UUID,
        report_type: str | None = None,
        status: str | None = None,
        since_days: int | None = None,
        pagination: PaginationParams | None = None,
    ) -> list[Report]:
        """Get reports for a specific user"""
        try:
            filters = [FilterCriteria("user_id", "eq", user_id)]

            if report_type:
                filters.append(FilterCriteria("report_type", "eq", report_type))

            if status:
                filters.append(FilterCriteria("status", "eq", status))

            if since_days:
                since_time = datetime.now(UTC) - timedelta(days=since_days)
                filters.append(FilterCriteria("created_at", "gte", since_time))

            sorts = [SortCriteria("created_at", "desc")]

            if pagination:
                result = await self.find_with_pagination(pagination, filters, sorts)
                return result.items
            else:
                return await self.find_all(filters, sorts)

        except Exception as e:
            self.logger.error(f"Error getting user reports: {str(e)}")
            raise ReflectAIError(
                f"Failed to get user reports: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    async def get_reports_by_type(
        self,
        report_type: str,
        status: str | None = None,
        format: str | None = None,
        limit: int = 50,
    ) -> list[Report]:
        """Get reports by type with optional filtering"""
        try:
            filters = [FilterCriteria("report_type", "eq", report_type)]

            if status:
                filters.append(FilterCriteria("status", "eq", status))

            if format:
                filters.append(FilterCriteria("format", "eq", format))

            sorts = [SortCriteria("created_at", "desc")]

            pagination = PaginationParams(page=1, page_size=limit)
            result = await self.find_with_pagination(pagination, filters, sorts)

            return result.items

        except Exception as e:
            self.logger.error(f"Error getting reports by type {report_type}: {str(e)}")
            raise ReflectAIError(
                f"Failed to get reports by type: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    # =====================
    # File Management
    # =====================

    async def get_reports_with_files(
        self,
        format: str | None = None,
        min_size_mb: float | None = None,
        max_age_days: int | None = None,
    ) -> list[Report]:
        """Get reports that have associated files"""
        try:
            # Use raw query for file-specific filtering
            params = []
            param_index = 1
            where_conditions = ["file_path IS NOT NULL"]

            if format:
                where_conditions.append(f"format = ${param_index}")
                params.append(format)
                param_index += 1

            if min_size_mb:
                min_size_bytes = int(min_size_mb * 1024 * 1024)
                where_conditions.append(f"file_size_bytes >= ${param_index}")
                params.append(min_size_bytes)
                param_index += 1

            if max_age_days:
                cutoff_time = datetime.now(UTC) - timedelta(days=max_age_days)
                where_conditions.append(f"generated_at >= ${param_index}")
                params.append(cutoff_time)
                param_index += 1

            where_clause = "WHERE " + " AND ".join(where_conditions)

            query = f"""
                SELECT * FROM reports
                {where_clause}
                ORDER BY generated_at DESC
            """

            result = await self.execute_raw_query(query, params, "all")

            return [Report(**dict(row)) for row in result] if result else []

        except Exception as e:
            self.logger.error(f"Error getting reports with files: {str(e)}")
            raise ReflectAIError(
                f"Failed to get reports with files: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    async def update_file_info(
        self,
        report_id: uuid.UUID,
        file_path: str,
        file_size_bytes: int,
        page_count: int | None = None,
    ) -> Report | None:
        """Update file information for a report"""
        try:
            update_data = {"file_path": file_path, "file_size_bytes": file_size_bytes}

            if page_count is not None:
                update_data["page_count"] = page_count

            return await self.update(report_id, update_data)

        except Exception as e:
            self.logger.error(f"Error updating file info: {str(e)}")
            raise ReflectAIError(
                f"Failed to update file info: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    async def get_file_storage_stats(self) -> dict[str, Any]:
        """Get file storage statistics"""
        try:
            query = """
                SELECT
                    format,
                    COUNT(*) as file_count,
                    SUM(file_size_bytes) as total_size_bytes,
                    AVG(file_size_bytes) as avg_size_bytes,
                    MIN(file_size_bytes) as min_size_bytes,
                    MAX(file_size_bytes) as max_size_bytes,
                    SUM(page_count) as total_pages,
                    AVG(page_count) as avg_pages
                FROM reports
                WHERE file_path IS NOT NULL AND file_size_bytes IS NOT NULL
                GROUP BY format
                ORDER BY total_size_bytes DESC
            """

            result = await self.execute_raw_query(query, [], "all")

            format_stats = []
            total_files = 0
            total_size = 0

            for row in result if result else []:
                file_count = row[1] or 0
                size_bytes = row[2] or 0

                total_files += file_count
                total_size += size_bytes

                format_stats.append(
                    {
                        "format": row[0],
                        "file_count": file_count,
                        "total_size_bytes": size_bytes,
                        "total_size_mb": round(size_bytes / (1024 * 1024), 2),
                        "avg_size_bytes": row[3] or 0,
                        "avg_size_mb": round((row[3] or 0) / (1024 * 1024), 2),
                        "min_size_bytes": row[4] or 0,
                        "max_size_bytes": row[5] or 0,
                        "total_pages": row[6] or 0,
                        "avg_pages": round(row[7] or 0, 1),
                    }
                )

            return {
                "total_files": total_files,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "format_breakdown": format_stats,
            }

        except Exception as e:
            self.logger.error(f"Error getting file storage stats: {str(e)}")
            raise ReflectAIError(
                f"Failed to get file storage stats: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    # =====================
    # Expiration Management
    # =====================

    async def get_expired_reports(
        self, include_should_expire: bool = True, max_age_days: int = 30
    ) -> list[Report]:
        """Get reports that are expired or should be expired"""
        try:
            current_time = datetime.now(UTC)

            # Reports explicitly marked as expired
            [FilterCriteria("status", "eq", "expired")]

            if include_should_expire:
                # Also include reports that should be expired based on age
                cutoff_time = current_time - timedelta(days=max_age_days)
                [
                    FilterCriteria("created_at", "lte", cutoff_time),
                    FilterCriteria("status", "in", ["delivered", "ready"]),
                ]

                # Use raw query for OR logic between explicit expiration and age-based expiration
                params = [current_time, cutoff_time, max_age_days]

                query = """
                    SELECT * FROM reports
                    WHERE status = 'expired'
                    OR (expires_at IS NOT NULL AND expires_at <= $1)
                    OR (created_at <= $2 AND status IN ('delivered', 'ready'))
                    ORDER BY created_at ASC
                """

                result = await self.execute_raw_query(query, params, "all")
                return [Report(**dict(row)) for row in result] if result else []
            else:
                # Only explicitly expired reports and those past expires_at
                FilterCriteria("expires_at", "lte", current_time)

                # Combine with OR logic using raw query
                params = [current_time]

                query = """
                    SELECT * FROM reports
                    WHERE status = 'expired'
                    OR (expires_at IS NOT NULL AND expires_at <= $1)
                    ORDER BY created_at ASC
                """

                result = await self.execute_raw_query(query, params, "all")
                return [Report(**dict(row)) for row in result] if result else []

        except Exception as e:
            self.logger.error(f"Error getting expired reports: {str(e)}")
            raise ReflectAIError(
                f"Failed to get expired reports: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    async def expire_report(self, report_id: uuid.UUID) -> Report | None:
        """Mark a report as expired"""
        try:
            return await self.update(report_id, {"status": "expired"})

        except Exception as e:
            self.logger.error(f"Error expiring report: {str(e)}")
            raise ReflectAIError(f"Failed to expire report: {str(e)}", ErrorSeverity.MEDIUM) from e

    async def cleanup_expired_reports(
        self, delete_files: bool = True, dry_run: bool = False
    ) -> dict[str, int]:
        """Cleanup expired reports and optionally delete associated files"""
        try:
            expired_reports = await self.get_expired_reports()

            cleanup_stats = {
                "reports_found": len(expired_reports),
                "reports_deleted": 0,
                "files_deleted": 0,
                "files_failed": 0,
                "dry_run": dry_run,
            }

            if dry_run:
                # Count files that would be deleted
                files_count = len([r for r in expired_reports if r.file_path])
                cleanup_stats["files_to_delete"] = files_count
                return cleanup_stats

            for report in expired_reports:
                try:
                    # Delete associated file if it exists
                    if delete_files and report.file_path:
                        try:
                            file_path = Path(report.file_path)
                            if file_path.exists():
                                file_path.unlink()
                                cleanup_stats["files_deleted"] += 1
                                self.logger.debug(f"Deleted file: {report.file_path}")
                        except Exception as file_error:
                            self.logger.warning(
                                f"Failed to delete file {report.file_path}: {str(file_error)}"
                            )
                            cleanup_stats["files_failed"] += 1

                    # Delete the report record
                    deleted = await self.delete(report.id)
                    if deleted:
                        cleanup_stats["reports_deleted"] += 1

                except Exception as report_error:
                    self.logger.warning(
                        f"Failed to cleanup report {report.id}: {str(report_error)}"
                    )

            self.logger.info(f"Cleanup completed: {cleanup_stats}")
            return cleanup_stats

        except Exception as e:
            self.logger.error(f"Error cleaning up expired reports: {str(e)}")
            raise ReflectAIError(
                f"Failed to cleanup expired reports: {str(e)}", ErrorSeverity.HIGH
            ) from e

    # =====================
    # Analytics and Reporting
    # =====================

    async def get_report_statistics(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        user_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Get comprehensive report statistics"""
        try:
            params = []
            param_index = 1
            where_conditions = []

            if start_time:
                where_conditions.append(f"created_at >= ${param_index}")
                params.append(start_time)
                param_index += 1

            if end_time:
                where_conditions.append(f"created_at <= ${param_index}")
                params.append(end_time)
                param_index += 1

            if user_id:
                where_conditions.append(f"user_id = ${param_index}")
                params.append(user_id)
                param_index += 1

            where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""

            query = f"""
                SELECT
                    COUNT(*) as total_reports,
                    COUNT(*) FILTER (WHERE status = 'pending') as pending_count,
                    COUNT(*) FILTER (WHERE status = 'generating') as generating_count,
                    COUNT(*) FILTER (WHERE status = 'ready') as ready_count,
                    COUNT(*) FILTER (WHERE status = 'delivered') as delivered_count,
                    COUNT(*) FILTER (WHERE status = 'failed') as failed_count,
                    COUNT(*) FILTER (WHERE status = 'expired') as expired_count,
                    COUNT(DISTINCT user_id) as unique_users,
                    COUNT(DISTINCT report_type) as unique_types,
                    AVG(EXTRACT(EPOCH FROM (generated_at - created_at))) FILTER (WHERE generated_at IS NOT NULL) as avg_generation_time,
                    COUNT(*) FILTER (WHERE file_path IS NOT NULL) as reports_with_files,
                    SUM(file_size_bytes) FILTER (WHERE file_size_bytes IS NOT NULL) as total_file_size
                FROM reports
                {where_clause}
            """

            result = await self.execute_raw_query(query, params, "one")

            if result:
                total = result[0] or 0
                delivered = result[4] or 0
                failed = result[5] or 0

                return {
                    "total_reports": total,
                    "status_distribution": {
                        "pending": result[1] or 0,
                        "generating": result[2] or 0,
                        "ready": result[3] or 0,
                        "delivered": delivered,
                        "failed": failed,
                        "expired": result[6] or 0,
                    },
                    "success_rate": (delivered / total * 100) if total > 0 else 0,
                    "failure_rate": (failed / total * 100) if total > 0 else 0,
                    "unique_users": result[7] or 0,
                    "unique_types": result[8] or 0,
                    "avg_generation_time_seconds": float(result[9]) if result[9] else 0,
                    "reports_with_files": result[10] or 0,
                    "total_file_size_bytes": result[11] or 0,
                    "total_file_size_mb": round((result[11] or 0) / (1024 * 1024), 2),
                    "filter_period": {
                        "start_time": start_time.isoformat() if start_time else None,
                        "end_time": end_time.isoformat() if end_time else None,
                    },
                }
            else:
                return {}

        except Exception as e:
            self.logger.error(f"Error getting report statistics: {str(e)}")
            raise ReflectAIError(
                f"Failed to get report statistics: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    async def get_report_performance_by_type(self, days: int = 30) -> list[dict[str, Any]]:
        """Get report performance metrics by type"""
        try:
            start_time = datetime.now(UTC) - timedelta(days=days)

            query = """
                SELECT
                    report_type,
                    COUNT(*) as total_count,
                    COUNT(*) FILTER (WHERE status = 'delivered') as delivered_count,
                    COUNT(*) FILTER (WHERE status = 'failed') as failed_count,
                    AVG(EXTRACT(EPOCH FROM (generated_at - created_at))) FILTER (WHERE generated_at IS NOT NULL) as avg_generation_time,
                    MIN(EXTRACT(EPOCH FROM (generated_at - created_at))) FILTER (WHERE generated_at IS NOT NULL) as min_generation_time,
                    MAX(EXTRACT(EPOCH FROM (generated_at - created_at))) FILTER (WHERE generated_at IS NOT NULL) as max_generation_time,
                    COUNT(*) FILTER (WHERE file_path IS NOT NULL) as reports_with_files,
                    AVG(file_size_bytes) FILTER (WHERE file_size_bytes IS NOT NULL) as avg_file_size
                FROM reports
                WHERE created_at >= $1
                GROUP BY report_type
                ORDER BY total_count DESC
            """

            result = await self.execute_raw_query(query, [start_time], "all")

            performance_data = []
            for row in result if result else []:
                total = row[1] or 0
                delivered = row[2] or 0
                failed = row[3] or 0

                performance_data.append(
                    {
                        "report_type": row[0],
                        "total_count": total,
                        "delivered_count": delivered,
                        "failed_count": failed,
                        "success_rate": (delivered / total * 100) if total > 0 else 0,
                        "failure_rate": (failed / total * 100) if total > 0 else 0,
                        "performance": {
                            "avg_generation_time_seconds": float(row[4]) if row[4] else 0,
                            "min_generation_time_seconds": float(row[5]) if row[5] else 0,
                            "max_generation_time_seconds": float(row[6]) if row[6] else 0,
                            "reports_with_files": row[7] or 0,
                            "avg_file_size_bytes": row[8] or 0,
                            "avg_file_size_mb": round((row[8] or 0) / (1024 * 1024), 2),
                        },
                    }
                )

            return performance_data

        except Exception as e:
            self.logger.error(f"Error getting report performance by type: {str(e)}")
            raise ReflectAIError(
                f"Failed to get report performance: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    # =====================
    # Bulk Operations
    # =====================

    async def bulk_expire_reports(self, report_ids: list[uuid.UUID]) -> int:
        """Bulk expire multiple reports"""
        try:
            filters = [FilterCriteria("id", "in", report_ids)]
            update_data = {"status": "expired"}

            expired_count = await self.update_many(filters, update_data)

            self.logger.info(f"Bulk expired {expired_count} reports")
            return expired_count

        except Exception as e:
            self.logger.error(f"Error bulk expiring reports: {str(e)}")
            raise ReflectAIError(
                f"Failed to bulk expire reports: {str(e)}", ErrorSeverity.HIGH
            ) from e
