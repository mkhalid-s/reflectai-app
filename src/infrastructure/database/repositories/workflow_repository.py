"""
⚠️ **ARCHITECTURAL NOTE**: This repository uses SQLAlchemy ORM patterns via BaseRepository,
but db_manager.py uses asyncpg. Current status: Implementation exists but may have compatibility issues.
Recommendation: Test thoroughly or rewrite to use asyncpg directly.

Workflow Repository Implementation for ReflectAI

Provides comprehensive workflow management with status orchestration:
- Workflow lifecycle management and status tracking
- Parent-child workflow relationships
- Temporal workflow integration support
- Error handling and retry logic
- Workflow analytics and performance monitoring
- Status-based querying and filtering
- Bulk operations for workflow management
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from src.shared import ErrorSeverity, ReflectAIError, get_logger

from ..models.workflow import Workflow
from .base_repository import (
    BaseRepository,
    FilterCriteria,
    PaginationParams,
    SortCriteria,
)


class WorkflowRepository(BaseRepository[Workflow]):
    """
    Workflow-specific repository with advanced orchestration and status management

    Features:
    - Workflow lifecycle management
    - Status-based querying and filtering
    - Parent-child workflow relationships
    - Error tracking and retry management
    - Temporal workflow integration
    - Performance analytics and monitoring
    - Bulk operations for workflow management
    """

    def __init__(self):
        super().__init__(Workflow)
        self.logger = get_logger("repository.workflow")

        # Workflow-specific caching
        self.cache_ttl_seconds = 300  # 5 minutes for workflows
        self.enable_query_cache = True

    # =====================
    # Workflow Lifecycle Management
    # =====================

    async def create_workflow(
        self,
        user_id: uuid.UUID,
        workflow_type: str,
        input_data: dict[str, Any],
        context_data: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        parent_workflow_id: uuid.UUID | None = None,
    ) -> Workflow:
        """Create a new workflow instance"""
        try:
            workflow_data = {
                "user_id": user_id,
                "workflow_type": workflow_type,
                "workflow_status": "pending",
                "stage": "initial",
                "input_data": input_data,
                "context_data": context_data or {},
                "output_data": {},
                "correlation_id": correlation_id,
                "parent_workflow_id": parent_workflow_id,
                "started_at": datetime.now(UTC),
                "error_count": 0,
            }

            workflow = await self.create(workflow_data)
            self.logger.info(f"Created workflow {workflow.id} of type {workflow_type}")

            return workflow

        except Exception as e:
            self.logger.error(f"Error creating workflow: {str(e)}")
            raise ReflectAIError(f"Failed to create workflow: {str(e)}", ErrorSeverity.HIGH) from e

    async def start_workflow(
        self, workflow_id: uuid.UUID, temporal_workflow_id: str | None = None
    ) -> Workflow | None:
        """Start a pending workflow"""
        try:
            update_data = {"workflow_status": "running", "started_at": datetime.now(UTC)}

            if temporal_workflow_id:
                update_data["temporal_workflow_id"] = temporal_workflow_id

            workflow = await self.update(workflow_id, update_data)

            if workflow:
                self.logger.info(f"Started workflow {workflow_id}")

            return workflow

        except Exception as e:
            self.logger.error(f"Error starting workflow {workflow_id}: {str(e)}")
            raise ReflectAIError(f"Failed to start workflow: {str(e)}", ErrorSeverity.HIGH) from e

    async def update_workflow_stage(
        self, workflow_id: uuid.UUID, new_stage: str, stage_data: dict[str, Any] | None = None
    ) -> Workflow | None:
        """Update workflow stage and optional stage data"""
        try:
            update_data = {"stage": new_stage}

            if stage_data:
                # Get current workflow to merge context data
                workflow = await self.get_by_id(workflow_id)
                if workflow:
                    current_context = workflow.context_data or {}
                    current_context.update(stage_data)
                    update_data["context_data"] = current_context

            workflow = await self.update(workflow_id, update_data)

            if workflow:
                self.logger.debug(f"Updated workflow {workflow_id} stage to {new_stage}")

            return workflow

        except Exception as e:
            self.logger.error(f"Error updating workflow stage: {str(e)}")
            raise ReflectAIError(
                f"Failed to update workflow stage: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    async def complete_workflow(
        self, workflow_id: uuid.UUID, output_data: dict[str, Any] | None = None
    ) -> Workflow | None:
        """Complete a workflow with optional output data"""
        try:
            update_data = {"workflow_status": "completed", "completed_at": datetime.now(UTC)}

            if output_data:
                # Get current workflow to merge output data
                workflow = await self.get_by_id(workflow_id)
                if workflow:
                    current_output = workflow.output_data or {}
                    current_output.update(output_data)
                    update_data["output_data"] = current_output

            workflow = await self.update(workflow_id, update_data)

            if workflow:
                self.logger.info(f"Completed workflow {workflow_id}")

            return workflow

        except Exception as e:
            self.logger.error(f"Error completing workflow {workflow_id}: {str(e)}")
            raise ReflectAIError(
                f"Failed to complete workflow: {str(e)}", ErrorSeverity.HIGH
            ) from e

    async def fail_workflow(
        self, workflow_id: uuid.UUID, error_info: dict[str, Any]
    ) -> Workflow | None:
        """Mark workflow as failed with error information"""
        try:
            # Get current workflow to increment error count
            workflow = await self.get_by_id(workflow_id)
            if not workflow:
                return None

            update_data = {
                "workflow_status": "failed",
                "completed_at": datetime.now(UTC),
                "error_count": workflow.error_count + 1,
                "last_error": error_info,
            }

            failed_workflow = await self.update(workflow_id, update_data)

            if failed_workflow:
                self.logger.warning(
                    f"Failed workflow {workflow_id}: {error_info.get('message', 'Unknown error')}"
                )

            return failed_workflow

        except Exception as e:
            self.logger.error(f"Error failing workflow {workflow_id}: {str(e)}")
            raise ReflectAIError(
                f"Failed to mark workflow as failed: {str(e)}", ErrorSeverity.HIGH
            ) from e

    async def cancel_workflow(self, workflow_id: uuid.UUID) -> Workflow | None:
        """Cancel a workflow"""
        try:
            update_data = {"workflow_status": "cancelled", "completed_at": datetime.now(UTC)}

            workflow = await self.update(workflow_id, update_data)

            if workflow:
                self.logger.info(f"Cancelled workflow {workflow_id}")

            return workflow

        except Exception as e:
            self.logger.error(f"Error cancelling workflow {workflow_id}: {str(e)}")
            raise ReflectAIError(f"Failed to cancel workflow: {str(e)}", ErrorSeverity.HIGH) from e

    # =====================
    # Status-Based Queries
    # =====================

    async def get_workflows_by_status(
        self,
        status: str,
        user_id: uuid.UUID | None = None,
        workflow_type: str | None = None,
        limit: int = 100,
    ) -> list[Workflow]:
        """Get workflows by status with optional filtering"""
        try:
            filters = [FilterCriteria("workflow_status", "eq", status)]

            if user_id:
                filters.append(FilterCriteria("user_id", "eq", user_id))

            if workflow_type:
                filters.append(FilterCriteria("workflow_type", "eq", workflow_type))

            sorts = [SortCriteria("started_at", "desc")]

            pagination = PaginationParams(page=1, page_size=limit)
            result = await self.find_with_pagination(pagination, filters, sorts)

            return result.items

        except Exception as e:
            self.logger.error(f"Error getting workflows by status {status}: {str(e)}")
            raise ReflectAIError(
                f"Failed to get workflows by status: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    async def get_running_workflows(
        self, user_id: uuid.UUID | None = None, workflow_type: str | None = None
    ) -> list[Workflow]:
        """Get currently running workflows"""
        return await self.get_workflows_by_status("running", user_id, workflow_type)

    async def get_pending_workflows(
        self,
        user_id: uuid.UUID | None = None,
        workflow_type: str | None = None,
        older_than_minutes: int = 0,
    ) -> list[Workflow]:
        """Get pending workflows, optionally older than specified minutes"""
        try:
            filters = [FilterCriteria("workflow_status", "eq", "pending")]

            if user_id:
                filters.append(FilterCriteria("user_id", "eq", user_id))

            if workflow_type:
                filters.append(FilterCriteria("workflow_type", "eq", workflow_type))

            if older_than_minutes > 0:
                cutoff_time = datetime.now(UTC) - timedelta(minutes=older_than_minutes)
                filters.append(FilterCriteria("created_at", "lte", cutoff_time))

            sorts = [SortCriteria("created_at", "asc")]  # Oldest first for processing

            return await self.find_all(filters, sorts)

        except Exception as e:
            self.logger.error(f"Error getting pending workflows: {str(e)}")
            raise ReflectAIError(
                f"Failed to get pending workflows: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    async def get_failed_workflows(
        self,
        user_id: uuid.UUID | None = None,
        workflow_type: str | None = None,
        retryable_only: bool = False,
    ) -> list[Workflow]:
        """Get failed workflows, optionally only retryable ones"""
        try:
            filters = [FilterCriteria("workflow_status", "eq", "failed")]

            if user_id:
                filters.append(FilterCriteria("user_id", "eq", user_id))

            if workflow_type:
                filters.append(FilterCriteria("workflow_type", "eq", workflow_type))

            if retryable_only:
                filters.append(FilterCriteria("error_count", "lt", 3))

            sorts = [SortCriteria("completed_at", "desc")]

            return await self.find_all(filters, sorts)

        except Exception as e:
            self.logger.error(f"Error getting failed workflows: {str(e)}")
            raise ReflectAIError(
                f"Failed to get failed workflows: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    async def get_stalled_workflows(self, stall_minutes: int = 60) -> list[Workflow]:
        """Get workflows that appear to be stalled (running too long)"""
        try:
            cutoff_time = datetime.now(UTC) - timedelta(minutes=stall_minutes)

            filters = [
                FilterCriteria("workflow_status", "eq", "running"),
                FilterCriteria("started_at", "lte", cutoff_time),
            ]

            sorts = [SortCriteria("started_at", "asc")]

            stalled_workflows = await self.find_all(filters, sorts)

            self.logger.info(f"Found {len(stalled_workflows)} potentially stalled workflows")
            return stalled_workflows

        except Exception as e:
            self.logger.error(f"Error getting stalled workflows: {str(e)}")
            raise ReflectAIError(
                f"Failed to get stalled workflows: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    # =====================
    # Parent-Child Workflow Management
    # =====================

    async def get_child_workflows(
        self, parent_workflow_id: uuid.UUID, status: str | None = None
    ) -> list[Workflow]:
        """Get child workflows for a parent workflow"""
        try:
            filters = [FilterCriteria("parent_workflow_id", "eq", parent_workflow_id)]

            if status:
                filters.append(FilterCriteria("workflow_status", "eq", status))

            sorts = [SortCriteria("created_at", "asc")]

            return await self.find_all(filters, sorts)

        except Exception as e:
            self.logger.error(f"Error getting child workflows: {str(e)}")
            raise ReflectAIError(
                f"Failed to get child workflows: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    async def create_child_workflow(
        self,
        parent_workflow_id: uuid.UUID,
        workflow_type: str,
        input_data: dict[str, Any],
        context_data: dict[str, Any] | None = None,
    ) -> Workflow:
        """Create a child workflow under a parent"""
        try:
            # Get parent workflow to inherit user_id and correlation_id
            parent = await self.get_by_id(parent_workflow_id)
            if not parent:
                raise ReflectAIError(
                    f"Parent workflow {parent_workflow_id} not found", ErrorSeverity.HIGH
                )

            child_workflow = await self.create_workflow(
                user_id=parent.user_id,
                workflow_type=workflow_type,
                input_data=input_data,
                context_data=context_data,
                correlation_id=parent.correlation_id,
                parent_workflow_id=parent_workflow_id,
            )

            self.logger.info(
                f"Created child workflow {child_workflow.id} for parent {parent_workflow_id}"
            )
            return child_workflow

        except Exception as e:
            self.logger.error(f"Error creating child workflow: {str(e)}")
            raise ReflectAIError(
                f"Failed to create child workflow: {str(e)}", ErrorSeverity.HIGH
            ) from e

    async def get_workflow_tree(self, root_workflow_id: uuid.UUID) -> dict[str, Any]:
        """Get complete workflow tree starting from root"""
        try:
            root_workflow = await self.get_by_id(root_workflow_id)
            if not root_workflow:
                return {}

            async def build_tree(workflow: Workflow) -> dict[str, Any]:
                children = await self.get_child_workflows(workflow.id)

                workflow_data = {"workflow": workflow.summary, "children": []}

                for child in children:
                    child_tree = await build_tree(child)
                    workflow_data["children"].append(child_tree)

                return workflow_data

            return await build_tree(root_workflow)

        except Exception as e:
            self.logger.error(f"Error getting workflow tree: {str(e)}")
            raise ReflectAIError(
                f"Failed to get workflow tree: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    async def check_parent_completion(self, parent_workflow_id: uuid.UUID) -> bool:
        """Check if all child workflows are complete and update parent if needed"""
        try:
            children = await self.get_child_workflows(parent_workflow_id)

            if not children:
                return True

            # Check if all children are in terminal states
            all_complete = all(
                child.workflow_status in ["completed", "failed", "cancelled"] for child in children
            )

            if all_complete:
                # Check if any children failed
                any_failed = any(child.workflow_status == "failed" for child in children)

                # Update parent status based on children
                if any_failed:
                    await self.fail_workflow(
                        parent_workflow_id, {"message": "One or more child workflows failed"}
                    )
                else:
                    # Collect outputs from successful children
                    child_outputs = {}
                    for child in children:
                        if child.workflow_status == "completed":
                            child_outputs[str(child.id)] = child.output_data

                    await self.complete_workflow(
                        parent_workflow_id, {"child_outputs": child_outputs}
                    )

            return all_complete

        except Exception as e:
            self.logger.error(f"Error checking parent completion: {str(e)}")
            raise ReflectAIError(
                f"Failed to check parent completion: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    # =====================
    # Analytics and Monitoring
    # =====================

    async def get_workflow_statistics(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        user_id: uuid.UUID | None = None,
        workflow_type: str | None = None,
    ) -> dict[str, Any]:
        """Get comprehensive workflow statistics"""
        try:
            params = []
            param_index = 1
            where_conditions = []

            if start_time:
                where_conditions.append(f"started_at >= ${param_index}")
                params.append(start_time)
                param_index += 1

            if end_time:
                where_conditions.append(f"started_at <= ${param_index}")
                params.append(end_time)
                param_index += 1

            if user_id:
                where_conditions.append(f"user_id = ${param_index}")
                params.append(user_id)
                param_index += 1

            if workflow_type:
                where_conditions.append(f"workflow_type = ${param_index}")
                params.append(workflow_type)
                param_index += 1

            where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""

            query = f"""
                SELECT
                    COUNT(*) as total_workflows,
                    COUNT(*) FILTER (WHERE workflow_status = 'completed') as completed_count,
                    COUNT(*) FILTER (WHERE workflow_status = 'failed') as failed_count,
                    COUNT(*) FILTER (WHERE workflow_status = 'running') as running_count,
                    COUNT(*) FILTER (WHERE workflow_status = 'pending') as pending_count,
                    COUNT(*) FILTER (WHERE workflow_status = 'cancelled') as cancelled_count,
                    COUNT(DISTINCT user_id) as unique_users,
                    COUNT(DISTINCT workflow_type) as unique_types,
                    AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) FILTER (WHERE completed_at IS NOT NULL) as avg_duration_seconds,
                    AVG(error_count) as avg_error_count,
                    COUNT(*) FILTER (WHERE parent_workflow_id IS NULL) as root_workflows,
                    COUNT(*) FILTER (WHERE parent_workflow_id IS NOT NULL) as child_workflows
                FROM workflows
                {where_clause}
            """

            result = await self.execute_raw_query(query, params, "one")

            if result:
                total = result[0] or 0
                completed = result[1] or 0
                failed = result[2] or 0

                return {
                    "total_workflows": total,
                    "status_distribution": {
                        "completed": completed,
                        "failed": failed,
                        "running": result[3] or 0,
                        "pending": result[4] or 0,
                        "cancelled": result[5] or 0,
                    },
                    "success_rate": (completed / total * 100) if total > 0 else 0,
                    "failure_rate": (failed / total * 100) if total > 0 else 0,
                    "unique_users": result[6] or 0,
                    "unique_types": result[7] or 0,
                    "avg_duration_seconds": float(result[8]) if result[8] else 0,
                    "avg_error_count": float(result[9]) if result[9] else 0,
                    "workflow_hierarchy": {
                        "root_workflows": result[10] or 0,
                        "child_workflows": result[11] or 0,
                    },
                    "filter_period": {
                        "start_time": start_time.isoformat() if start_time else None,
                        "end_time": end_time.isoformat() if end_time else None,
                    },
                }
            else:
                return {}

        except Exception as e:
            self.logger.error(f"Error getting workflow statistics: {str(e)}")
            raise ReflectAIError(
                f"Failed to get workflow statistics: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    async def get_workflow_performance_by_type(self, days: int = 30) -> list[dict[str, Any]]:
        """Get workflow performance metrics by type"""
        try:
            start_time = datetime.now(UTC) - timedelta(days=days)

            query = """
                SELECT
                    workflow_type,
                    COUNT(*) as total_count,
                    COUNT(*) FILTER (WHERE workflow_status = 'completed') as completed_count,
                    COUNT(*) FILTER (WHERE workflow_status = 'failed') as failed_count,
                    AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) FILTER (WHERE completed_at IS NOT NULL) as avg_duration,
                    MIN(EXTRACT(EPOCH FROM (completed_at - started_at))) FILTER (WHERE completed_at IS NOT NULL) as min_duration,
                    MAX(EXTRACT(EPOCH FROM (completed_at - started_at))) FILTER (WHERE completed_at IS NOT NULL) as max_duration,
                    AVG(error_count) as avg_errors
                FROM workflows
                WHERE started_at >= $1
                GROUP BY workflow_type
                ORDER BY total_count DESC
            """

            result = await self.execute_raw_query(query, [start_time], "all")

            performance_data = []
            for row in result if result else []:
                total = row[1] or 0
                completed = row[2] or 0
                failed = row[3] or 0

                performance_data.append(
                    {
                        "workflow_type": row[0],
                        "total_count": total,
                        "completed_count": completed,
                        "failed_count": failed,
                        "success_rate": (completed / total * 100) if total > 0 else 0,
                        "failure_rate": (failed / total * 100) if total > 0 else 0,
                        "performance": {
                            "avg_duration_seconds": float(row[4]) if row[4] else 0,
                            "min_duration_seconds": float(row[5]) if row[5] else 0,
                            "max_duration_seconds": float(row[6]) if row[6] else 0,
                            "avg_error_count": float(row[7]) if row[7] else 0,
                        },
                    }
                )

            return performance_data

        except Exception as e:
            self.logger.error(f"Error getting workflow performance by type: {str(e)}")
            raise ReflectAIError(
                f"Failed to get workflow performance: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    # =====================
    # Correlation and Integration
    # =====================

    async def get_workflows_by_correlation(
        self, correlation_id: str, exclude_workflow_id: uuid.UUID | None = None
    ) -> list[Workflow]:
        """Get workflows with the same correlation ID"""
        try:
            filters = [FilterCriteria("correlation_id", "eq", correlation_id)]

            if exclude_workflow_id:
                filters.append(FilterCriteria("id", "ne", exclude_workflow_id))

            sorts = [SortCriteria("started_at", "asc")]

            return await self.find_all(filters, sorts)

        except Exception as e:
            self.logger.error(f"Error getting workflows by correlation: {str(e)}")
            raise ReflectAIError(
                f"Failed to get correlated workflows: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    async def get_workflow_by_temporal_id(self, temporal_workflow_id: str) -> Workflow | None:
        """Get workflow by Temporal workflow ID"""
        try:
            filters = [FilterCriteria("temporal_workflow_id", "eq", temporal_workflow_id)]

            return await self.find_one(filters)

        except Exception as e:
            self.logger.error(f"Error getting workflow by temporal ID: {str(e)}")
            raise ReflectAIError(
                f"Failed to get workflow by temporal ID: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    # =====================
    # Bulk Operations
    # =====================

    async def bulk_cancel_workflows(
        self, workflow_ids: list[uuid.UUID], reason: str | None = None
    ) -> int:
        """Bulk cancel multiple workflows"""
        try:
            update_data = {"workflow_status": "cancelled", "completed_at": datetime.now(UTC)}

            filters = [
                FilterCriteria("id", "in", workflow_ids),
                FilterCriteria("workflow_status", "in", ["pending", "running", "paused"]),
            ]

            cancelled_count = await self.update_many(filters, update_data)

            self.logger.info(f"Bulk cancelled {cancelled_count} workflows")
            return cancelled_count

        except Exception as e:
            self.logger.error(f"Error bulk cancelling workflows: {str(e)}")
            raise ReflectAIError(
                f"Failed to bulk cancel workflows: {str(e)}", ErrorSeverity.HIGH
            ) from e

    async def cleanup_old_workflows(
        self,
        older_than_days: int = 90,
        statuses: list[str] | None = None,
        batch_size: int = 1000,
        dry_run: bool = False,
    ) -> dict[str, int]:
        """Clean up old workflows by deleting them"""
        if statuses is None:
            statuses = ["completed", "failed", "cancelled"]

        try:
            cutoff_date = datetime.now(UTC) - timedelta(days=older_than_days)

            # Count workflows to delete
            params = [cutoff_date]
            status_placeholders = ",".join([f"${i + 2}" for i in range(len(statuses))])
            params.extend(statuses)

            count_query = f"""
                SELECT COUNT(*) FROM workflows
                WHERE completed_at < $1
                AND workflow_status IN ({status_placeholders})
                AND parent_workflow_id IS NULL  -- Only delete root workflows
            """

            total_count = await self.execute_raw_query(count_query, params, "val")

            if dry_run:
                return {"total_to_delete": total_count or 0, "deleted": 0, "dry_run": True}

            # Delete in batches
            deleted_count = 0

            while True:
                # Delete a batch (cascade will handle children)
                delete_query = f"""
                    DELETE FROM workflows
                    WHERE id IN (
                        SELECT id FROM workflows
                        WHERE completed_at < $1
                        AND workflow_status IN ({status_placeholders})
                        AND parent_workflow_id IS NULL
                        LIMIT {batch_size}
                    )
                """

                result = await self.execute_raw_query(delete_query, params, "rowcount")

                batch_deleted = result if result else 0
                deleted_count += batch_deleted

                if batch_deleted == 0:
                    break

                self.logger.info(f"Deleted {deleted_count}/{total_count} old workflows")

            return {"total_to_delete": total_count or 0, "deleted": deleted_count, "dry_run": False}

        except Exception as e:
            self.logger.error(f"Error cleaning up old workflows: {str(e)}")
            raise ReflectAIError(
                f"Failed to cleanup old workflows: {str(e)}", ErrorSeverity.HIGH
            ) from e
