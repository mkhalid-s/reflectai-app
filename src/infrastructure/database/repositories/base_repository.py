"""
Base Repository Implementation for ReflectAI

Provides comprehensive base repository with:
- Generic CRUD operations using SQLAlchemy 2.0 async patterns
- Type hints and generics for type safety
- Filtering, pagination, and sorting capabilities
- Batch operations and bulk operations
- Transaction management and error handling
- Caching strategies integration
- TimescaleDB optimizations for time-series data
- Dependency injection support
"""

import uuid
from abc import ABC
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import (
    Any,
    Generic,
    TypeVar,
)

from sqlalchemy import (
    Select,
    and_,
    asc,
    delete,
    desc,
    func,
    insert,
    select,
    update,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncConnection
from sqlalchemy.orm import selectinload

from src.shared import ErrorSeverity, ReflectAIError, get_logger

from ..db_manager import get_database_manager
from ..models.base import Base

# Generic type variable for model types
ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")


class FilterCriteria:
    """Structured filter criteria for queries"""

    def __init__(
        self,
        field: str,
        operator: str = "eq",
        value: Any = None,
        values: list[Any] | None = None,
    ):
        self.field = field
        self.operator = (
            operator  # eq, ne, gt, gte, lt, lte, in, not_in, like, ilike, is_null, is_not_null
        )
        self.value = value
        self.values = values or []

    def __repr__(self) -> str:
        return (
            f"FilterCriteria(field='{self.field}', operator='{self.operator}', value={self.value})"
        )


class SortCriteria:
    """Structured sort criteria for queries"""

    def __init__(self, field: str, direction: str = "asc"):
        self.field = field
        self.direction = direction.lower()  # asc, desc

        if self.direction not in ["asc", "desc"]:
            raise ValueError("Direction must be 'asc' or 'desc'")

    def __repr__(self) -> str:
        return f"SortCriteria(field='{self.field}', direction='{self.direction}')"


class PaginationParams:
    """Pagination parameters"""

    def __init__(self, page: int = 1, page_size: int = 50, max_page_size: int = 1000):
        if page < 1:
            raise ValueError("Page must be >= 1")
        if page_size < 1:
            raise ValueError("Page size must be >= 1")
        if page_size > max_page_size:
            raise ValueError(f"Page size cannot exceed {max_page_size}")

        self.page = page
        self.page_size = page_size
        self.offset = (page - 1) * page_size

    def __repr__(self) -> str:
        return f"PaginationParams(page={self.page}, page_size={self.page_size})"


class PaginatedResult(Generic[ModelType]):
    """Paginated query result"""

    def __init__(
        self,
        items: list[ModelType],
        total_count: int,
        page: int,
        page_size: int,
        has_next: bool = False,
        has_previous: bool = False,
    ):
        self.items = items
        self.total_count = total_count
        self.page = page
        self.page_size = page_size
        self.has_next = has_next
        self.has_previous = has_previous
        self.total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 0

    def __repr__(self) -> str:
        return f"PaginatedResult(items={len(self.items)}, total={self.total_count}, page={self.page}/{self.total_pages})"


class BaseRepository(Generic[ModelType], ABC):
    """
    Abstract base repository providing common CRUD operations and utilities

    Features:
    - Generic type safety with SQLAlchemy models
    - Async/await patterns with proper transaction handling
    - Comprehensive filtering, sorting, and pagination
    - Bulk operations for performance
    - Caching integration hooks
    - TimescaleDB optimizations
    - Dependency injection ready
    """

    def __init__(self, model_class: type[ModelType]):
        self.model_class = model_class
        self.table_name = model_class.__tablename__
        self.logger = get_logger(f"repository.{self.table_name}")
        self._db_manager = get_database_manager()

        # Cache configuration (can be overridden in subclasses)
        self.cache_ttl_seconds = 300  # 5 minutes default
        self.enable_query_cache = True

        self.logger.debug(f"Initialized repository for {model_class.__name__}")

    @property
    def db_manager(self):
        """Get database manager instance"""
        return self._db_manager

    @property
    def timescale_manager(self):
        """Get TimescaleDB manager for direct queries"""
        return self.db_manager.get_timescale_manager()

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[AsyncConnection, None]:
        """Get database connection with proper cleanup"""
        async with self.timescale_manager.get_connection() as conn:
            yield conn

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[AsyncConnection, None]:
        """Get database connection within a transaction"""
        async with self.get_connection() as conn:
            async with conn.begin():
                yield conn

    # =====================
    # CRUD Operations
    # =====================

    async def create(self, obj_data: dict[str, Any] | CreateSchemaType) -> ModelType:
        """Create a new record"""
        try:
            # Convert to dict if needed
            if not isinstance(obj_data, dict):
                if hasattr(obj_data, "model_dump"):
                    obj_data = obj_data.model_dump()
                elif hasattr(obj_data, "dict"):
                    obj_data = obj_data.dict()
                else:
                    obj_data = dict(obj_data)

            async with self.transaction() as conn:
                stmt = insert(self.model_class).values(**obj_data).returning(self.model_class)
                result = await conn.execute(stmt)
                record = result.fetchone()

                if not record:
                    raise ReflectAIError(
                        f"Failed to create {self.model_class.__name__}", ErrorSeverity.HIGH
                    )

                # Convert Row to model instance
                model_instance = self.model_class(**dict(record._mapping))

                self.logger.debug(
                    f"Created {self.model_class.__name__} with id: {model_instance.id}"
                )
                await self._invalidate_cache_for_record(model_instance)

                return model_instance

        except IntegrityError as e:
            self.logger.warning(f"Integrity error creating {self.model_class.__name__}: {str(e)}")
            raise ReflectAIError(f"Data integrity violation: {str(e)}", ErrorSeverity.MEDIUM) from e
        except Exception as e:
            self.logger.error(f"Error creating {self.model_class.__name__}: {str(e)}")
            raise ReflectAIError(f"Failed to create record: {str(e)}", ErrorSeverity.HIGH) from e

    async def get_by_id(
        self, record_id: uuid.UUID, with_relations: list[str] = None
    ) -> ModelType | None:
        """Get record by ID with optional relation loading"""
        try:
            # Check cache first
            cache_key = f"{self.table_name}:id:{record_id}"
            if self.enable_query_cache:
                cached_result = await self._get_from_cache(cache_key)
                if cached_result is not None:
                    return cached_result

            async with self.get_connection() as conn:
                stmt = select(self.model_class).where(self.model_class.id == record_id)

                # Add relation loading if specified
                if with_relations:
                    for relation in with_relations:
                        if hasattr(self.model_class, relation):
                            stmt = stmt.options(selectinload(getattr(self.model_class, relation)))

                result = await conn.execute(stmt)
                record = result.fetchone()

                if not record:
                    return None

                model_instance = self.model_class(**dict(record._mapping))

                # Cache the result
                if self.enable_query_cache:
                    await self._set_cache(cache_key, model_instance, self.cache_ttl_seconds)

                return model_instance

        except Exception as e:
            self.logger.error(
                f"Error getting {self.model_class.__name__} by id {record_id}: {str(e)}"
            )
            raise ReflectAIError(f"Failed to get record: {str(e)}", ErrorSeverity.MEDIUM) from e

    async def update(
        self, record_id: uuid.UUID, update_data: dict[str, Any] | UpdateSchemaType
    ) -> ModelType | None:
        """Update a record by ID"""
        try:
            # Convert to dict if needed
            if not isinstance(update_data, dict):
                if hasattr(update_data, "model_dump"):
                    update_data = update_data.model_dump(exclude_unset=True)
                elif hasattr(update_data, "dict"):
                    update_data = update_data.dict(exclude_unset=True)
                else:
                    update_data = dict(update_data)

            # Remove None values and empty strings
            update_data = {k: v for k, v in update_data.items() if v is not None}

            if not update_data:
                # No data to update, return existing record
                return await self.get_by_id(record_id)

            async with self.transaction() as conn:
                stmt = (
                    update(self.model_class)
                    .where(self.model_class.id == record_id)
                    .values(**update_data)
                    .returning(self.model_class)
                )

                result = await conn.execute(stmt)
                record = result.fetchone()

                if not record:
                    return None

                model_instance = self.model_class(**dict(record._mapping))

                self.logger.debug(f"Updated {self.model_class.__name__} with id: {record_id}")
                await self._invalidate_cache_for_record(model_instance)

                return model_instance

        except Exception as e:
            self.logger.error(
                f"Error updating {self.model_class.__name__} with id {record_id}: {str(e)}"
            )
            raise ReflectAIError(f"Failed to update record: {str(e)}", ErrorSeverity.HIGH) from e

    async def delete(self, record_id: uuid.UUID) -> bool:
        """Delete a record by ID"""
        try:
            async with self.transaction() as conn:
                stmt = delete(self.model_class).where(self.model_class.id == record_id)
                result = await conn.execute(stmt)

                deleted = result.rowcount > 0

                if deleted:
                    self.logger.debug(f"Deleted {self.model_class.__name__} with id: {record_id}")
                    await self._invalidate_cache_for_id(record_id)

                return deleted

        except Exception as e:
            self.logger.error(
                f"Error deleting {self.model_class.__name__} with id {record_id}: {str(e)}"
            )
            raise ReflectAIError(f"Failed to delete record: {str(e)}", ErrorSeverity.HIGH) from e

    # =====================
    # Query Operations
    # =====================

    async def find_all(
        self,
        filters: list[FilterCriteria] | None = None,
        sorts: list[SortCriteria] | None = None,
        with_relations: list[str] | None = None,
    ) -> list[ModelType]:
        """Find all records matching criteria"""
        try:
            async with self.get_connection() as conn:
                stmt = select(self.model_class)

                # Apply filters
                if filters:
                    stmt = self._apply_filters(stmt, filters)

                # Apply sorting
                if sorts:
                    stmt = self._apply_sorting(stmt, sorts)

                # Add relation loading if specified
                if with_relations:
                    for relation in with_relations:
                        if hasattr(self.model_class, relation):
                            stmt = stmt.options(selectinload(getattr(self.model_class, relation)))

                result = await conn.execute(stmt)
                records = result.fetchall()

                return [self.model_class(**dict(record._mapping)) for record in records]

        except Exception as e:
            self.logger.error(f"Error finding all {self.model_class.__name__}: {str(e)}")
            raise ReflectAIError(f"Failed to query records: {str(e)}", ErrorSeverity.MEDIUM) from e

    async def find_with_pagination(
        self,
        pagination: PaginationParams,
        filters: list[FilterCriteria] | None = None,
        sorts: list[SortCriteria] | None = None,
        with_relations: list[str] | None = None,
    ) -> PaginatedResult[ModelType]:
        """Find records with pagination"""
        try:
            async with self.get_connection() as conn:
                # Base query for data
                stmt = select(self.model_class)

                # Apply filters
                if filters:
                    stmt = self._apply_filters(stmt, filters)

                # Count query (before pagination)
                count_stmt = select(func.count()).select_from(stmt.subquery())
                count_result = await conn.execute(count_stmt)
                total_count = count_result.scalar()

                # Apply sorting
                if sorts:
                    stmt = self._apply_sorting(stmt, sorts)

                # Apply pagination
                stmt = stmt.offset(pagination.offset).limit(pagination.page_size)

                # Add relation loading if specified
                if with_relations:
                    for relation in with_relations:
                        if hasattr(self.model_class, relation):
                            stmt = stmt.options(selectinload(getattr(self.model_class, relation)))

                result = await conn.execute(stmt)
                records = result.fetchall()

                items = [self.model_class(**dict(record._mapping)) for record in records]

                return PaginatedResult(
                    items=items,
                    total_count=total_count,
                    page=pagination.page,
                    page_size=pagination.page_size,
                    has_next=pagination.offset + len(items) < total_count,
                    has_previous=pagination.page > 1,
                )

        except Exception as e:
            self.logger.error(f"Error paginating {self.model_class.__name__}: {str(e)}")
            raise ReflectAIError(
                f"Failed to paginate records: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    async def find_one(
        self,
        filters: list[FilterCriteria] | None = None,
        with_relations: list[str] | None = None,
    ) -> ModelType | None:
        """Find single record matching criteria"""
        try:
            async with self.get_connection() as conn:
                stmt = select(self.model_class)

                # Apply filters
                if filters:
                    stmt = self._apply_filters(stmt, filters)

                # Limit to one result
                stmt = stmt.limit(1)

                # Add relation loading if specified
                if with_relations:
                    for relation in with_relations:
                        if hasattr(self.model_class, relation):
                            stmt = stmt.options(selectinload(getattr(self.model_class, relation)))

                result = await conn.execute(stmt)
                record = result.fetchone()

                if not record:
                    return None

                return self.model_class(**dict(record._mapping))

        except Exception as e:
            self.logger.error(f"Error finding one {self.model_class.__name__}: {str(e)}")
            raise ReflectAIError(f"Failed to find record: {str(e)}", ErrorSeverity.MEDIUM) from e

    async def count(self, filters: list[FilterCriteria] | None = None) -> int:
        """Count records matching criteria"""
        try:
            async with self.get_connection() as conn:
                stmt = select(func.count()).select_from(self.model_class)

                # Apply filters
                if filters:
                    stmt = self._apply_filters(stmt, filters)

                result = await conn.execute(stmt)
                return result.scalar()

        except Exception as e:
            self.logger.error(f"Error counting {self.model_class.__name__}: {str(e)}")
            raise ReflectAIError(f"Failed to count records: {str(e)}", ErrorSeverity.MEDIUM) from e

    async def exists(self, filters: list[FilterCriteria]) -> bool:
        """Check if any record exists matching criteria"""
        try:
            count = await self.count(filters)
            return count > 0
        except Exception as e:
            self.logger.error(f"Error checking existence for {self.model_class.__name__}: {str(e)}")
            raise ReflectAIError(
                f"Failed to check record existence: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    # =====================
    # Batch Operations
    # =====================

    async def create_many(
        self, objects_data: list[dict[str, Any] | CreateSchemaType]
    ) -> list[ModelType]:
        """Create multiple records in a single transaction"""
        if not objects_data:
            return []

        try:
            # Convert all to dicts
            processed_data = []
            for obj_data in objects_data:
                if not isinstance(obj_data, dict):
                    if hasattr(obj_data, "model_dump"):
                        obj_data = obj_data.model_dump()
                    elif hasattr(obj_data, "dict"):
                        obj_data = obj_data.dict()
                    else:
                        obj_data = dict(obj_data)
                processed_data.append(obj_data)

            async with self.transaction() as conn:
                stmt = insert(self.model_class).returning(self.model_class)
                result = await conn.execute(stmt, processed_data)
                records = result.fetchall()

                created_records = [self.model_class(**dict(record._mapping)) for record in records]

                self.logger.info(
                    f"Created {len(created_records)} {self.model_class.__name__} records"
                )

                # Invalidate relevant cache
                await self._invalidate_bulk_cache()

                return created_records

        except Exception as e:
            self.logger.error(f"Error creating multiple {self.model_class.__name__}: {str(e)}")
            raise ReflectAIError(
                f"Failed to create multiple records: {str(e)}", ErrorSeverity.HIGH
            ) from e

    async def update_many(
        self, filters: list[FilterCriteria], update_data: dict[str, Any] | UpdateSchemaType
    ) -> int:
        """Update multiple records matching criteria"""
        try:
            # Convert to dict if needed
            if not isinstance(update_data, dict):
                if hasattr(update_data, "model_dump"):
                    update_data = update_data.model_dump(exclude_unset=True)
                elif hasattr(update_data, "dict"):
                    update_data = update_data.dict(exclude_unset=True)
                else:
                    update_data = dict(update_data)

            # Remove None values
            update_data = {k: v for k, v in update_data.items() if v is not None}

            if not update_data:
                return 0

            async with self.transaction() as conn:
                stmt = update(self.model_class).values(**update_data)

                # Apply filters
                if filters:
                    stmt = self._apply_filters(stmt, filters)

                result = await conn.execute(stmt)
                updated_count = result.rowcount

                self.logger.debug(f"Updated {updated_count} {self.model_class.__name__} records")

                # Invalidate relevant cache
                await self._invalidate_bulk_cache()

                return updated_count

        except Exception as e:
            self.logger.error(f"Error updating multiple {self.model_class.__name__}: {str(e)}")
            raise ReflectAIError(
                f"Failed to update multiple records: {str(e)}", ErrorSeverity.HIGH
            ) from e

    async def delete_many(self, filters: list[FilterCriteria]) -> int:
        """Delete multiple records matching criteria"""
        try:
            async with self.transaction() as conn:
                stmt = delete(self.model_class)

                # Apply filters
                if filters:
                    stmt = self._apply_filters(stmt, filters)

                result = await conn.execute(stmt)
                deleted_count = result.rowcount

                self.logger.debug(f"Deleted {deleted_count} {self.model_class.__name__} records")

                # Invalidate relevant cache
                await self._invalidate_bulk_cache()

                return deleted_count

        except Exception as e:
            self.logger.error(f"Error deleting multiple {self.model_class.__name__}: {str(e)}")
            raise ReflectAIError(
                f"Failed to delete multiple records: {str(e)}", ErrorSeverity.HIGH
            ) from e

    # =====================
    # TimescaleDB Operations
    # =====================

    async def get_time_series_data(
        self,
        time_column: str,
        start_time: datetime,
        end_time: datetime,
        bucket_interval: str = "1 hour",
        aggregation: str = "count",
        filters: list[FilterCriteria] | None = None,
    ) -> list[dict[str, Any]]:
        """Get time-bucketed aggregation data (TimescaleDB specific)"""
        try:
            # Build the time_bucket query
            time_bucket_func = f"time_bucket('{bucket_interval}', {time_column})"

            if aggregation == "count":
                agg_func = "COUNT(*)"
            elif aggregation == "avg":
                agg_func = "AVG(value)" if hasattr(self.model_class, "value") else "COUNT(*)"
            elif aggregation == "sum":
                agg_func = "SUM(value)" if hasattr(self.model_class, "value") else "COUNT(*)"
            elif aggregation == "max":
                agg_func = "MAX(value)" if hasattr(self.model_class, "value") else "COUNT(*)"
            elif aggregation == "min":
                agg_func = "MIN(value)" if hasattr(self.model_class, "value") else "COUNT(*)"
            else:
                agg_func = "COUNT(*)"

            # Build query
            base_query = f"""
                SELECT
                    {time_bucket_func} as time_bucket,
                    {agg_func} as value
                FROM {self.table_name}
                WHERE {time_column} >= $1 AND {time_column} <= $2
            """

            params = [start_time, end_time]
            param_index = 3

            # Add filters
            if filters:
                for filter_criteria in filters:
                    if hasattr(self.model_class, filter_criteria.field):
                        if filter_criteria.operator == "eq":
                            base_query += f" AND {filter_criteria.field} = ${param_index}"
                            params.append(filter_criteria.value)
                            param_index += 1
                        elif filter_criteria.operator == "in":
                            placeholders = ",".join(
                                [
                                    f"${i}"
                                    for i in range(
                                        param_index, param_index + len(filter_criteria.values)
                                    )
                                ]
                            )
                            base_query += f" AND {filter_criteria.field} IN ({placeholders})"
                            params.extend(filter_criteria.values)
                            param_index += len(filter_criteria.values)

            base_query += " GROUP BY time_bucket ORDER BY time_bucket"

            result = await self.timescale_manager.execute_query(
                base_query, params, fetch="all", query_type="time_series_aggregation"
            )

            return [{"time_bucket": row[0], "value": row[1]} for row in result] if result else []

        except Exception as e:
            self.logger.error(
                f"Error getting time series data for {self.model_class.__name__}: {str(e)}"
            )
            raise ReflectAIError(
                f"Failed to get time series data: {str(e)}", ErrorSeverity.MEDIUM
            ) from e

    # =====================
    # Helper Methods
    # =====================

    def _apply_filters(self, stmt: Select, filters: list[FilterCriteria]) -> Select:
        """Apply filter criteria to a SQLAlchemy select statement"""
        conditions = []

        for filter_criteria in filters:
            if not hasattr(self.model_class, filter_criteria.field):
                continue

            field = getattr(self.model_class, filter_criteria.field)

            if filter_criteria.operator == "eq":
                conditions.append(field == filter_criteria.value)
            elif filter_criteria.operator == "ne":
                conditions.append(field != filter_criteria.value)
            elif filter_criteria.operator == "gt":
                conditions.append(field > filter_criteria.value)
            elif filter_criteria.operator == "gte":
                conditions.append(field >= filter_criteria.value)
            elif filter_criteria.operator == "lt":
                conditions.append(field < filter_criteria.value)
            elif filter_criteria.operator == "lte":
                conditions.append(field <= filter_criteria.value)
            elif filter_criteria.operator == "in":
                conditions.append(field.in_(filter_criteria.values))
            elif filter_criteria.operator == "not_in":
                conditions.append(~field.in_(filter_criteria.values))
            elif filter_criteria.operator == "like":
                conditions.append(field.like(filter_criteria.value))
            elif filter_criteria.operator == "ilike":
                conditions.append(field.ilike(filter_criteria.value))
            elif filter_criteria.operator == "is_null":
                conditions.append(field.is_(None))
            elif filter_criteria.operator == "is_not_null":
                conditions.append(field.is_not(None))

        if conditions:
            stmt = stmt.where(and_(*conditions))

        return stmt

    def _apply_sorting(self, stmt: Select, sorts: list[SortCriteria]) -> Select:
        """Apply sort criteria to a SQLAlchemy select statement"""
        order_clauses = []

        for sort_criteria in sorts:
            if not hasattr(self.model_class, sort_criteria.field):
                continue

            field = getattr(self.model_class, sort_criteria.field)

            if sort_criteria.direction == "desc":
                order_clauses.append(desc(field))
            else:
                order_clauses.append(asc(field))

        if order_clauses:
            stmt = stmt.order_by(*order_clauses)

        return stmt

    # =====================
    # Cache Management (hooks for subclasses)
    # =====================

    async def _get_from_cache(self, cache_key: str) -> ModelType | None:
        """Get record from cache (to be implemented by subclasses if needed)"""
        # Base implementation does nothing - subclasses can override
        return None

    async def _set_cache(self, cache_key: str, record: ModelType, ttl_seconds: int):
        """Set record in cache (to be implemented by subclasses if needed)"""
        # Base implementation does nothing - subclasses can override
        pass

    async def _invalidate_cache_for_record(self, record: ModelType):
        """Invalidate cache for specific record (to be implemented by subclasses if needed)"""
        # Base implementation does nothing - subclasses can override
        pass

    async def _invalidate_cache_for_id(self, record_id: uuid.UUID):
        """Invalidate cache for specific record ID (to be implemented by subclasses if needed)"""
        # Base implementation does nothing - subclasses can override
        pass

    async def _invalidate_bulk_cache(self):
        """Invalidate cache for bulk operations (to be implemented by subclasses if needed)"""
        # Base implementation does nothing - subclasses can override
        pass

    # =====================
    # Raw Query Support
    # =====================

    async def execute_raw_query(
        self, query: str, params: list[Any] | None = None, fetch_type: str = "all"
    ) -> Any:
        """Execute raw SQL query with parameters"""
        try:
            result = await self.timescale_manager.execute_query(
                query, params or [], fetch=fetch_type, query_type="raw_query"
            )
            return result

        except Exception as e:
            self.logger.error(
                f"Error executing raw query for {self.model_class.__name__}: {str(e)}"
            )
            raise ReflectAIError(
                f"Failed to execute raw query: {str(e)}", ErrorSeverity.MEDIUM
            ) from e
