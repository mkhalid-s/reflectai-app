"""
Database Query Tool for Analysis Agent

Implements database access part of
- Fetch user activities and profile data from PostgreSQL
- Optimized queries for activity analysis and competency assessment
- Connection pooling and query performance monitoring
- Read-only access with proper security validation

Used by Analysis Agent for accessing user activity and profile data.
"""

import asyncio
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import asyncpg
from pydantic import BaseModel, Field

from ..base_tool import Tool, ToolError, ToolPermission, ToolRequest


class QueryType(Enum):
    """Supported query types"""

    GET_USER_ACTIVITIES = "get_user_activities"
    GET_USER_PROFILE = "get_user_profile"
    GET_ACTIVITY_COUNTS = "get_activity_counts"
    GET_COMPETENCY_HISTORY = "get_competency_history"
    SEARCH_ACTIVITIES = "search_activities"


class DatabaseQueryRequest(BaseModel):
    """Request for database query"""

    query_type: QueryType = Field(..., description="Type of query to execute")
    user_id: str = Field(..., description="User ID for query context")
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Query-specific parameters"
    )
    limit: int | None = Field(100, description="Maximum records to return")
    offset: int | None = Field(0, description="Offset for pagination")


class ActivityRecord(BaseModel):
    """Activity record from database"""

    id: str = Field(..., description="Activity ID")
    user_id: str = Field(..., description="User ID")
    title: str = Field(..., description="Activity title")
    description: str | None = Field(None, description="Activity description")
    activity_type: str | None = Field(None, description="Activity type classification")
    created_at: datetime = Field(..., description="Activity creation timestamp")
    updated_at: datetime = Field(..., description="Activity update timestamp")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional activity metadata"
    )
    tags: list[str] = Field(default_factory=list, description="Activity tags")
    source: str | None = Field(None, description="Data source (slack, manual, etc.)")


class UserProfile(BaseModel):
    """User profile record from database"""

    user_id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    full_name: str | None = Field(None, description="User full name")
    role: str | None = Field(None, description="User role/title")
    department: str | None = Field(None, description="User department")
    manager_id: str | None = Field(None, description="Manager user ID")
    start_date: datetime | None = Field(None, description="Employment start date")
    skills: list[str] = Field(default_factory=list, description="User skills")
    competency_frameworks: list[str] = Field(
        default_factory=list, description="Applicable competency frameworks"
    )
    created_at: datetime = Field(..., description="Profile creation timestamp")
    updated_at: datetime = Field(..., description="Profile update timestamp")


class DatabaseQueryResult(BaseModel):
    """Result of database query"""

    query_type: QueryType = Field(..., description="Query type executed")
    user_id: str = Field(..., description="User ID queried")
    records_found: int = Field(..., description="Number of records found")
    query_time: float = Field(..., description="Query execution time in seconds")

    # Results based on query type
    activities: list[ActivityRecord] | None = Field(None, description="Activity records")
    user_profile: UserProfile | None = Field(None, description="User profile")
    activity_counts: dict[str, int] | None = Field(None, description="Activity count aggregations")
    competency_history: list[dict[str, Any]] | None = Field(
        None, description="Historical competency data"
    )


class DatabaseQueryTool(Tool):
    """
    Tool for querying PostgreSQL database for user activities and profiles

    Provides read-only access to user data with optimized queries for analysis.
    Includes connection pooling and performance monitoring.
    """

    def __init__(
        self,
        database_url: str | None = None,
        min_pool_size: int = 2,
        max_pool_size: int = 10,
        query_timeout: int = 30,
    ):
        super().__init__(
            name="database_query",
            description="Query PostgreSQL database for user activities and profile data",
            required_permissions=[ToolPermission.READ_ONLY],
            timeout=60,
        )

        self.database_url = database_url or "postgresql://user:pass@localhost/reflectai"
        self.min_pool_size = min_pool_size
        self.max_pool_size = max_pool_size
        self.query_timeout = query_timeout

        # Connection pool
        self._pool: asyncpg.Pool | None = None
        self._pool_lock = asyncio.Lock()

        # Query performance tracking
        self._query_stats = {
            "total_queries": 0,
            "total_time": 0.0,
            "avg_query_time": 0.0,
            "slowest_query": 0.0,
            "query_type_stats": {},
        }

    async def initialize_pool(self) -> bool:
        """Initialize database connection pool"""
        try:
            async with self._pool_lock:
                if self._pool is None:
                    self._pool = await asyncpg.create_pool(
                        self.database_url,
                        min_size=self.min_pool_size,
                        max_size=self.max_pool_size,
                        command_timeout=self.query_timeout,
                    )
                    self.logger.info(
                        f"Database pool initialized with {self.min_pool_size}-{self.max_pool_size} connections"
                    )
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize database pool: {str(e)}")
            return False

    async def _execute_operation(
        self, request: ToolRequest, agent_context: Any | None = None
    ) -> DatabaseQueryResult:
        """Execute database query operation"""

        if request.operation != "query_database":
            raise ToolError(
                message=f"Unknown operation: {request.operation}",
                tool_name=self.name,
                operation=request.operation,
            )

        # Parse request parameters
        try:
            query_request = DatabaseQueryRequest(**request.parameters)
        except Exception as e:
            raise ToolError(
                message=f"Invalid request parameters: {str(e)}",
                tool_name=self.name,
                operation=request.operation,
            ) from e

        # Ensure pool is initialized
        if not self._pool:
            if not await self.initialize_pool():
                raise ToolError(
                    message="Database connection pool not available",
                    tool_name=self.name,
                    operation=request.operation,
                )

        start_time = datetime.now(UTC)

        try:
            # Execute query based on type
            result = await self._execute_query(query_request)

            # Update performance stats
            query_time = (datetime.now(UTC) - start_time).total_seconds()
            self._update_query_stats(query_request.query_type, query_time)

            result.query_time = query_time
            return result

        except Exception as e:
            query_time = (datetime.now(UTC) - start_time).total_seconds()
            self._update_query_stats(query_request.query_type, query_time, failed=True)

            raise ToolError(
                message=f"Database query failed: {str(e)}",
                tool_name=self.name,
                operation=request.operation,
                details={
                    "query_type": query_request.query_type.value,
                    "user_id": query_request.user_id,
                },
            ) from e

    async def _execute_query(self, request: DatabaseQueryRequest) -> DatabaseQueryResult:
        """Execute the specific query type"""

        query_handlers = {
            QueryType.GET_USER_ACTIVITIES: self._get_user_activities,
            QueryType.GET_USER_PROFILE: self._get_user_profile,
            QueryType.GET_ACTIVITY_COUNTS: self._get_activity_counts,
            QueryType.GET_COMPETENCY_HISTORY: self._get_competency_history,
            QueryType.SEARCH_ACTIVITIES: self._search_activities,
        }

        handler = query_handlers.get(request.query_type)
        if not handler:
            raise ToolError(
                message=f"Unsupported query type: {request.query_type.value}",
                tool_name=self.name,
                operation="query_database",
            )

        return await handler(request)

    async def _get_user_activities(self, request: DatabaseQueryRequest) -> DatabaseQueryResult:
        """Get user activities with optional filtering"""

        # Build query parameters
        params = request.parameters

        # Base query
        query = """
            SELECT
                id, user_id, title, description, activity_type,
                created_at, updated_at, metadata, tags, source
            FROM user_activities
            WHERE user_id = $1
        """
        query_params = [request.user_id]
        param_count = 1

        # Add date filtering if specified
        if params.get("start_date"):
            param_count += 1
            query += f" AND created_at >= ${param_count}"
            query_params.append(params["start_date"])

        if params.get("end_date"):
            param_count += 1
            query += f" AND created_at <= ${param_count}"
            query_params.append(params["end_date"])

        # Add activity type filtering
        if params.get("activity_types"):
            param_count += 1
            query += f" AND activity_type = ANY(${param_count})"
            query_params.append(params["activity_types"])

        # Add ordering and pagination
        query += " ORDER BY created_at DESC"

        if request.limit:
            param_count += 1
            query += f" LIMIT ${param_count}"
            query_params.append(request.limit)

        if request.offset:
            param_count += 1
            query += f" OFFSET ${param_count}"
            query_params.append(request.offset)

        # Execute query
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *query_params)

        # Convert to ActivityRecord objects
        activities = []
        for row in rows:
            activity = ActivityRecord(
                id=row["id"],
                user_id=row["user_id"],
                title=row["title"],
                description=row["description"],
                activity_type=row["activity_type"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                metadata=row["metadata"] or {},
                tags=row["tags"] or [],
                source=row["source"],
            )
            activities.append(activity)

        return DatabaseQueryResult(
            query_type=request.query_type,
            user_id=request.user_id,
            records_found=len(activities),
            query_time=0.0,  # Will be set by caller
            activities=activities,
        )

    async def _get_user_profile(self, request: DatabaseQueryRequest) -> DatabaseQueryResult:
        """Get user profile information"""

        query = """
            SELECT
                user_id, email, full_name, role, department, manager_id,
                start_date, skills, competency_frameworks, created_at, updated_at
            FROM user_profiles
            WHERE user_id = $1
        """

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, request.user_id)

        if not row:
            return DatabaseQueryResult(
                query_type=request.query_type,
                user_id=request.user_id,
                records_found=0,
                query_time=0.0,
                user_profile=None,
            )

        user_profile = UserProfile(
            user_id=row["user_id"],
            email=row["email"],
            full_name=row["full_name"],
            role=row["role"],
            department=row["department"],
            manager_id=row["manager_id"],
            start_date=row["start_date"],
            skills=row["skills"] or [],
            competency_frameworks=row["competency_frameworks"] or [],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

        return DatabaseQueryResult(
            query_type=request.query_type,
            user_id=request.user_id,
            records_found=1,
            query_time=0.0,
            user_profile=user_profile,
        )

    async def _get_activity_counts(self, request: DatabaseQueryRequest) -> DatabaseQueryResult:
        """Get activity count aggregations"""

        params = request.parameters

        # Build aggregation query
        query = """
            SELECT
                activity_type,
                COUNT(*) as count,
                DATE_TRUNC('month', created_at) as month
            FROM user_activities
            WHERE user_id = $1
        """
        query_params = [request.user_id]
        param_count = 1

        # Add date filtering
        if params.get("start_date"):
            param_count += 1
            query += f" AND created_at >= ${param_count}"
            query_params.append(params["start_date"])

        if params.get("end_date"):
            param_count += 1
            query += f" AND created_at <= ${param_count}"
            query_params.append(params["end_date"])

        query += """
            GROUP BY activity_type, DATE_TRUNC('month', created_at)
            ORDER BY month DESC, count DESC
        """

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *query_params)

        # Process results
        activity_counts = {"by_type": {}, "by_month": {}, "total": 0}

        for row in rows:
            activity_type = row["activity_type"] or "unknown"
            count = row["count"]
            month = row["month"].strftime("%Y-%m")

            # By type
            activity_counts["by_type"][activity_type] = (
                activity_counts["by_type"].get(activity_type, 0) + count
            )

            # By month
            if month not in activity_counts["by_month"]:
                activity_counts["by_month"][month] = {}
            activity_counts["by_month"][month][activity_type] = count

            # Total
            activity_counts["total"] += count

        return DatabaseQueryResult(
            query_type=request.query_type,
            user_id=request.user_id,
            records_found=len(rows),
            query_time=0.0,
            activity_counts=activity_counts,
        )

    async def _get_competency_history(self, request: DatabaseQueryRequest) -> DatabaseQueryResult:
        """Get historical competency assessment data"""

        params = request.parameters

        query = """
            SELECT
                competency_category, raw_score, competency_level,
                evidence_strength, confidence, calculated_at, total_activities
            FROM competency_assessments
            WHERE user_id = $1
        """
        query_params = [request.user_id]
        param_count = 1

        # Add competency category filter
        if params.get("competency_category"):
            param_count += 1
            query += f" AND competency_category = ${param_count}"
            query_params.append(params["competency_category"])

        # Add date range filtering
        if params.get("start_date"):
            param_count += 1
            query += f" AND calculated_at >= ${param_count}"
            query_params.append(params["start_date"])

        query += " ORDER BY calculated_at DESC"

        if request.limit:
            param_count += 1
            query += f" LIMIT ${param_count}"
            query_params.append(request.limit)

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *query_params)

        # Convert to dictionaries
        competency_history = []
        for row in rows:
            history_item = {
                "competency_category": row["competency_category"],
                "raw_score": float(row["raw_score"]),
                "competency_level": row["competency_level"],
                "evidence_strength": row["evidence_strength"],
                "confidence": float(row["confidence"]),
                "calculated_at": row["calculated_at"].isoformat(),
                "total_activities": row["total_activities"],
            }
            competency_history.append(history_item)

        return DatabaseQueryResult(
            query_type=request.query_type,
            user_id=request.user_id,
            records_found=len(competency_history),
            query_time=0.0,
            competency_history=competency_history,
        )

    async def _search_activities(self, request: DatabaseQueryRequest) -> DatabaseQueryResult:
        """Search activities by text or criteria"""

        params = request.parameters
        search_term = params.get("search_term", "")

        if not search_term:
            raise ToolError(
                message="search_term parameter required for activity search",
                tool_name=self.name,
                operation="query_database",
            )

        # Full-text search query
        query = """
            SELECT
                id, user_id, title, description, activity_type,
                created_at, updated_at, metadata, tags, source,
                ts_rank(search_vector, plainto_tsquery($2)) as relevance
            FROM user_activities
            WHERE user_id = $1
            AND search_vector @@ plainto_tsquery($2)
            ORDER BY relevance DESC, created_at DESC
        """
        query_params = [request.user_id, search_term]

        if request.limit:
            query += f" LIMIT ${len(query_params) + 1}"
            query_params.append(request.limit)

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *query_params)

        # Convert to ActivityRecord objects
        activities = []
        for row in rows:
            activity = ActivityRecord(
                id=row["id"],
                user_id=row["user_id"],
                title=row["title"],
                description=row["description"],
                activity_type=row["activity_type"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                metadata=(row["metadata"] or {}) | {"relevance": float(row["relevance"])},
                tags=row["tags"] or [],
                source=row["source"],
            )
            activities.append(activity)

        return DatabaseQueryResult(
            query_type=request.query_type,
            user_id=request.user_id,
            records_found=len(activities),
            query_time=0.0,
            activities=activities,
        )

    def _update_query_stats(self, query_type: QueryType, query_time: float, failed: bool = False):
        """Update query performance statistics"""

        self._query_stats["total_queries"] += 1
        self._query_stats["total_time"] += query_time
        self._query_stats["avg_query_time"] = (
            self._query_stats["total_time"] / self._query_stats["total_queries"]
        )

        if query_time > self._query_stats["slowest_query"]:
            self._query_stats["slowest_query"] = query_time

        # Per-query-type stats
        query_type_str = query_type.value
        if query_type_str not in self._query_stats["query_type_stats"]:
            self._query_stats["query_type_stats"][query_type_str] = {
                "count": 0,
                "total_time": 0.0,
                "avg_time": 0.0,
                "failures": 0,
            }

        type_stats = self._query_stats["query_type_stats"][query_type_str]
        type_stats["count"] += 1
        type_stats["total_time"] += query_time
        type_stats["avg_time"] = type_stats["total_time"] / type_stats["count"]

        if failed:
            type_stats["failures"] += 1

    async def close_pool(self):
        """Close database connection pool"""
        if self._pool:
            await self._pool.close()
            self._pool = None
            self.logger.info("Database pool closed")

    def get_query_stats(self) -> dict[str, Any]:
        """Get query performance statistics"""
        return self._query_stats.copy()

    def get_supported_operations(self) -> list[str]:
        """Get list of supported operations"""
        return ["query_database"]

    def get_query_types(self) -> list[str]:
        """Get list of supported query types"""
        return [qt.value for qt in QueryType]


# Auto-register for tool discovery
DatabaseQueryTool._auto_register = True
DatabaseQueryTool._category = "database"
DatabaseQueryTool._version = None  # Version loaded from config
