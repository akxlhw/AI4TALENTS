"""
Venue and VenueTechBinding repository.
顶会顶刊配置数据访问层
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.venue import Venue, VenueSubTask, VenueTechBinding


class VenueRepository:
    """Venue repository for database operations"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, venue: Venue) -> Venue:
        """Create a new venue"""
        self.session.add(venue)
        await self.session.flush()
        await self.session.refresh(venue)
        return venue

    async def get_by_id(self, venue_id: int) -> Venue | None:
        """Get venue by ID"""
        result = await self.session.execute(
            select(Venue).where(Venue.venue_id == venue_id)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, venue_code: str) -> Venue | None:
        """Get venue by code"""
        result = await self.session.execute(
            select(Venue).where(Venue.venue_code == venue_code)
        )
        return result.scalar_one_or_none()

    async def get_by_openalex_id(self, openalex_source_id: str) -> Venue | None:
        """Get venue by OpenAlex source ID"""
        result = await self.session.execute(
            select(Venue).where(Venue.openalex_source_id == openalex_source_id)
        )
        return result.scalar_one_or_none()

    async def get_list(
        self,
        venue_type: str | None = None,
        is_enabled: bool | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[list[Venue], int]:
        """Get venue list with filters and pagination"""
        query = select(Venue)
        count_query = select(func.count(Venue.venue_id))

        # Filters
        if venue_type:
            query = query.where(Venue.venue_type == venue_type)
            count_query = count_query.where(Venue.venue_type == venue_type)
        if is_enabled is not None:
            query = query.where(Venue.is_enabled == is_enabled)
            count_query = count_query.where(Venue.is_enabled == is_enabled)
        if keyword:
            keyword_filter = or_(
                Venue.venue_name.contains(keyword),
                Venue.venue_name_en.contains(keyword),
                Venue.venue_code.contains(keyword)
            )
            query = query.where(keyword_filter)
            count_query = count_query.where(keyword_filter)

        # Count
        total_result = await self.session.execute(count_query)
        total = total_result.scalar()

        # Pagination
        query = query.order_by(Venue.venue_id.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(query)
        venues = result.scalars().all()

        return list(venues), total

    async def update(self, venue: Venue) -> Venue:
        """Update venue"""
        await self.session.flush()
        await self.session.refresh(venue)
        return venue

    async def delete(self, venue_id: int) -> bool:
        """Delete venue"""
        result = await self.session.execute(
            delete(Venue).where(Venue.venue_id == venue_id)
        )
        return result.rowcount > 0

    async def update_last_collect_at(self, venue_id: int, collect_at: datetime) -> None:
        """Update last collection time"""
        await self.session.execute(
            update(Venue)
            .where(Venue.venue_id == venue_id)
            .values(last_collect_at=collect_at)
        )


class VenueTechBindingRepository:
    """Venue-TechElement binding repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, binding: VenueTechBinding) -> VenueTechBinding:
        """Create a new binding"""
        self.session.add(binding)
        await self.session.flush()
        await self.session.refresh(binding)
        return binding

    async def get_by_id(self, binding_id: int) -> VenueTechBinding | None:
        """Get binding by ID"""
        result = await self.session.execute(
            select(VenueTechBinding).where(VenueTechBinding.binding_id == binding_id)
        )
        return result.scalar_one_or_none()

    async def get_by_venue_and_tech(self, venue_id: int, tech_element_id: int) -> VenueTechBinding | None:
        """Get binding by venue and tech element"""
        result = await self.session.execute(
            select(VenueTechBinding).where(
                VenueTechBinding.venue_id == venue_id,
                VenueTechBinding.tech_element_id == tech_element_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_tech_element(
        self,
        tech_element_id: int,
        is_enabled: bool | None = None
    ) -> list[VenueTechBinding]:
        """Get all bindings for a tech element with venue eagerly loaded"""
        query = select(VenueTechBinding).options(
            selectinload(VenueTechBinding.venue)
        ).where(
            VenueTechBinding.tech_element_id == tech_element_id
        )
        if is_enabled is not None:
            query = query.where(VenueTechBinding.is_enabled == is_enabled)
        query = query.order_by(VenueTechBinding.priority.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_venue(
        self,
        venue_id: int,
        is_enabled: bool | None = None
    ) -> list[VenueTechBinding]:
        """Get all bindings for a venue"""
        query = select(VenueTechBinding).where(
            VenueTechBinding.venue_id == venue_id
        )
        if is_enabled is not None:
            query = query.where(VenueTechBinding.is_enabled == is_enabled)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_list_with_venue(
        self,
        tech_element_id: int,
        is_enabled: bool | None = None
    ) -> list[VenueTechBinding]:
        """Get bindings with venue info for a tech element (venue eagerly loaded)"""
        query = select(VenueTechBinding).options(
            selectinload(VenueTechBinding.venue)
        ).where(
            VenueTechBinding.tech_element_id == tech_element_id
        )
        if is_enabled is not None:
            query = query.where(VenueTechBinding.is_enabled == is_enabled)
        query = query.order_by(VenueTechBinding.priority.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(self, binding: VenueTechBinding) -> VenueTechBinding:
        """Update binding"""
        await self.session.flush()
        await self.session.refresh(binding)
        return binding

    async def delete(self, binding_id: int) -> bool:
        """Delete binding"""
        result = await self.session.execute(
            delete(VenueTechBinding).where(VenueTechBinding.binding_id == binding_id)
        )
        return result.rowcount > 0

    async def delete_by_tech_element(self, tech_element_id: int) -> int:
        """Delete all bindings for a tech element"""
        result = await self.session.execute(
            delete(VenueTechBinding).where(
                VenueTechBinding.tech_element_id == tech_element_id
            )
        )
        return result.rowcount

    async def update_collect_status(
        self,
        venue_id: int,
        tech_element_id: int,
        status: str,
        author_count: int | None = None,
        work_count: int | None = None
    ) -> None:
        """Update collection status for a binding"""
        values = {
            "collect_status": status,
            "last_collect_at": datetime.utcnow()
        }
        if author_count is not None:
            values["author_count"] = author_count
        if work_count is not None:
            values["work_count"] = work_count

        await self.session.execute(
            update(VenueTechBinding)
            .where(
                VenueTechBinding.venue_id == venue_id,
                VenueTechBinding.tech_element_id == tech_element_id
            )
            .values(**values)
        )


class VenueSubTaskRepository:
    """Venue sub-task repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, sub_task: VenueSubTask) -> VenueSubTask:
        """Create a new sub-task"""
        self.session.add(sub_task)
        await self.session.flush()
        await self.session.refresh(sub_task)
        return sub_task

    async def get_by_id(self, sub_task_id: int) -> VenueSubTask | None:
        """Get sub-task by ID"""
        result = await self.session.execute(
            select(VenueSubTask).where(VenueSubTask.sub_task_id == sub_task_id)
        )
        return result.scalar_one_or_none()

    async def get_by_task(self, task_id: int) -> list[VenueSubTask]:
        """Get all sub-tasks for a task"""
        result = await self.session.execute(
            select(VenueSubTask)
            .where(VenueSubTask.task_id == task_id)
            .order_by(VenueSubTask.sub_task_id)
        )
        return list(result.scalars().all())

    async def update(self, sub_task: VenueSubTask) -> VenueSubTask:
        """Update sub-task"""
        await self.session.flush()
        await self.session.refresh(sub_task)
        return sub_task

    async def update_status(
        self,
        sub_task_id: int,
        status: str,
        works_fetched: int | None = None,
        authors_fetched: int | None = None,
        new_authors: int | None = None,
        error_message: str | None = None
    ) -> None:
        """Update sub-task status"""
        values = {"status": status}
        if status == "running":
            values["started_at"] = datetime.utcnow()
        elif status in ("completed", "failed"):
            values["completed_at"] = datetime.utcnow()
        if works_fetched is not None:
            values["works_fetched"] = works_fetched
        if authors_fetched is not None:
            values["authors_fetched"] = authors_fetched
        if new_authors is not None:
            values["new_authors"] = new_authors
        if error_message is not None:
            values["error_message"] = error_message

        await self.session.execute(
            update(VenueSubTask)
            .where(VenueSubTask.sub_task_id == sub_task_id)
            .values(**values)
        )
