"""
Base Repository with common CRUD operations.

Provides reusable patterns for:
- get_by_id: Single record lookup by primary key
- get_by_ids: Batch lookup by primary keys
- paginate: Apply pagination to a query
- list_paginated: Combined list with count and pagination
"""
from __future__ import annotations

from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql.selectable import Select

Model = TypeVar("Model", bound=DeclarativeBase)


class BaseRepository(Generic[Model]):
    """
    Base repository with common database operations.

    Usage:
        class UserRepository(BaseRepository[UserAccount]):
            def __init__(self, session: AsyncSession):
                super().__init__(session, UserAccount)
    """

    def __init__(self, session: AsyncSession, model: type[Model]):
        """
        Initialize repository with session and model class.

        Args:
            session: AsyncSession for database operations
            model: SQLAlchemy model class
        """
        self.session = session
        self.model = model

    async def get_by_id(self, id: int, id_column: str | None = None) -> Model | None:
        """
        Get a single record by primary key.

        Args:
            id: Primary key value
            id_column: Column name for ID (default: auto-detect from table)

        Returns:
            Model instance or None
        """
        if id_column:
            column = getattr(self.model, id_column)
        else:
            # Try common ID column names
            table_name = self.model.__tablename__
            if table_name.startswith("core_"):
                # core_talent -> talent_id
                entity = table_name[5:]  # Remove 'core_'
                id_column = f"{entity}_id"
            elif table_name.startswith("sync_"):
                entity = table_name[5:]
                id_column = f"{entity}_id"
            elif table_name.startswith("iam_"):
                entity = table_name[4:]
                id_column = f"{entity}_id"
            elif table_name.startswith("config_"):
                # config_venue -> venue_id
                entity = table_name[7:]  # Remove 'config_'
                id_column = f"{entity}_id"
            else:
                # Fallback: use first column as primary key
                id_column = list(self.model.__table__.columns.keys())[0]

            column = getattr(self.model, id_column)

        result = await self.session.execute(
            select(self.model).where(column == id)
        )
        return result.scalar_one_or_none()

    async def get_by_ids(
        self,
        ids: list[int],
        id_column: str | None = None
    ) -> dict[int, Model]:
        """
        Get multiple records by primary keys in batch.

        Args:
            ids: List of primary key values
            id_column: Column name for ID (default: auto-detect)

        Returns:
            Dictionary mapping id to Model instance
        """
        if not ids:
            return {}

        if id_column:
            column = getattr(self.model, id_column)
        else:
            # Use same logic as get_by_id
            table_name = self.model.__tablename__
            if table_name.startswith("core_"):
                entity = table_name[5:]
                id_column = f"{entity}_id"
            elif table_name.startswith("sync_"):
                entity = table_name[5:]
                id_column = f"{entity}_id"
            elif table_name.startswith("iam_"):
                entity = table_name[4:]
                id_column = f"{entity}_id"
            elif table_name.startswith("config_"):
                entity = table_name[7:]
                id_column = f"{entity}_id"
            else:
                id_column = list(self.model.__table__.columns.keys())[0]
            column = getattr(self.model, id_column)

        result = await self.session.execute(
            select(self.model).where(column.in_(ids))
        )
        return {getattr(row, id_column): row for row in result.scalars().all()}

    async def count(self, query: Select[Any] | None = None) -> int:
        """
        Count records in a query or table.

        Args:
            query: SQLAlchemy query (optional, defaults to count all)

        Returns:
            Number of records
        """
        if query is None:
            count_query = select(func.count()).select_from(self.model)
        else:
            count_query = select(func.count()).select_from(query.subquery())

        result = await self.session.execute(count_query)
        return result.scalar() or 0

    def paginate(self, query: Select[Any], page: int, page_size: int) -> Select[Any]:
        """
        Apply pagination to a query.

        Args:
            query: SQLAlchemy query
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Query with offset and limit applied
        """
        offset = (page - 1) * page_size
        return query.offset(offset).limit(page_size)

    async def list_paginated(
        self,
        query: Select[Any],
        page: int = 1,
        page_size: int = 20,
        order_by: Any = None,
    ) -> tuple[list[Model], int]:
        """
        Execute query with pagination and return items with total count.

        Args:
            query: SQLAlchemy query
            page: Page number (1-indexed)
            page_size: Number of items per page
            order_by: Optional order by column

        Returns:
            Tuple of (list of items, total count)
        """
        # Count first
        total = await self.count(query)

        # Apply order
        if order_by is not None:
            query = query.order_by(order_by)

        # Apply pagination
        query = self.paginate(query, page, page_size)

        # Execute
        result = await self.session.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def create(self, instance: Model) -> Model:
        """
        Create a new record.

        Args:
            instance: Model instance to create

        Returns:
            Created instance with refreshed data
        """
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def delete(self, instance: Model) -> None:
        """
        Delete a record.

        Args:
            instance: Model instance to delete
        """
        await self.session.delete(instance)
        await self.session.flush()
