"""
Raw data layer repository.
原始数据层数据访问
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sqlalchemy import func, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.academic.models.raw_data import (
    AuthorTechBelong,
    RawAuthor,
    RawInstitution,
    RawWork,
)

logger = logging.getLogger(__name__)


class RawWorkRepository:
    """Raw work repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, work: RawWork) -> RawWork:
        """Create a raw work record"""
        self.session.add(work)
        await self.session.flush()
        await self.session.refresh(work)
        return work

    async def upsert(self, work: RawWork) -> RawWork:
        """Create or update a raw work record.

        First checks if the work exists, then updates or creates accordingly.
        This approach avoids transaction state issues with exception handling.
        """
        # Check if work already exists
        existing = await self.get_by_openalex_id(work.openalex_work_id)
        if existing:
            # Update existing record
            existing.raw_json = work.raw_json
            existing.title = work.title
            existing.doi = work.doi
            existing.publication_year = work.publication_year
            existing.source_id = work.source_id
            existing.source_name = work.source_name
            existing.author_count = work.author_count
            existing.author_ids = work.author_ids
            existing.fetched_at = datetime.now(timezone.utc).replace(tzinfo=None)
            existing.fetch_task_id = work.fetch_task_id
            existing.sub_task_id = work.sub_task_id
            await self.session.flush()
            return existing
        else:
            # Create new record
            return await self.create(work)

    async def get_by_openalex_id(self, openalex_id: str) -> RawWork | None:
        """Get raw work by OpenAlex ID"""
        result = await self.session.execute(
            select(RawWork).where(RawWork.openalex_work_id == openalex_id)
        )
        return result.scalar_one_or_none()

    async def get_by_source(
        self,
        source_id: str,
        year_from: int | None = None,
        year_to: int | None = None,
        limit: int = 10000,
    ) -> list[RawWork]:
        """Get works by source (venue) ID"""
        query = select(RawWork).where(RawWork.source_id == source_id)
        if year_from:
            query = query.where(RawWork.publication_year >= year_from)
        if year_to:
            query = query.where(RawWork.publication_year <= year_to)
        query = query.order_by(RawWork.publication_year.desc()).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_author_ids_by_source(
        self, source_id: str, year_from: int | None = None, year_to: int | None = None
    ) -> set[str]:
        """Extract unique author IDs from works of a source"""
        works = await self.get_by_source(source_id, year_from, year_to)
        author_ids = set()
        for work in works:
            if work.author_ids:
                try:
                    ids = json.loads(work.author_ids)
                    author_ids.update(ids)
                except (json.JSONDecodeError, TypeError):
                    pass
        return author_ids

    async def get_author_ids_by_task(self, task_id: int) -> set[str]:
        """Extract unique author IDs from works collected in a specific task.

        Args:
            task_id: The fetch task ID to filter by

        Returns:
            Set of unique OpenAlex author IDs
        """
        result = await self.session.execute(
            select(RawWork.author_ids).where(RawWork.fetch_task_id == task_id)
        )
        author_ids = set()
        for row in result.fetchall():
            if row[0]:
                try:
                    ids = json.loads(row[0])
                    author_ids.update(ids)
                except (json.JSONDecodeError, TypeError):
                    pass
        return author_ids

    async def get_all_author_ids(self, limit: int = 10000) -> set[str]:
        """Extract unique author IDs from all works.

        Args:
            limit: Maximum number of works to process

        Returns:
            Set of unique OpenAlex author IDs
        """
        result = await self.session.execute(select(RawWork.author_ids).limit(limit))
        author_ids = set()
        for row in result.fetchall():
            if row[0]:
                try:
                    ids = json.loads(row[0])
                    author_ids.update(ids)
                except (json.JSONDecodeError, TypeError):
                    pass
        return author_ids

    async def get_pending(self, limit: int = 100) -> list[RawWork]:
        """Get pending works for processing"""
        result = await self.session.execute(
            select(RawWork).where(RawWork.processed_status == "pending").limit(limit)
        )
        return list(result.scalars().all())

    async def mark_processed(
        self, work_id: int, status: str = "processed", error: str | None = None
    ) -> None:
        """Mark work as processed"""
        values = {"processed_status": status, "processed_at": datetime.now(timezone.utc).replace(tzinfo=None)}
        if error:
            values["error_info"] = error
        await self.session.execute(
            update(RawWork).where(RawWork.raw_work_id == work_id).values(**values)
        )

    async def batch_upsert(self, works: list[RawWork]) -> int:
        """Batch create or update works using PostgreSQL INSERT ON CONFLICT.

        This eliminates N+1 queries from individual upserts.
        """
        if not works:
            return 0

        values = []
        for work in works:
            values.append(
                {
                    "openalex_work_id": work.openalex_work_id,
                    "raw_json": work.raw_json,
                    "title": work.title,
                    "doi": work.doi,
                    "publication_year": work.publication_year,
                    "publication_date": work.publication_date,
                    "source_id": work.source_id,
                    "source_name": work.source_name,
                    "author_count": work.author_count,
                    "author_ids": work.author_ids,
                    "fetch_task_id": work.fetch_task_id,
                    "sub_task_id": work.sub_task_id,
                    "fetched_at": work.fetched_at,
                }
            )

        stmt = pg_insert(RawWork).values(values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["openalex_work_id"],
            set_={
                "raw_json": stmt.excluded.raw_json,
                "title": stmt.excluded.title,
                "doi": stmt.excluded.doi,
                "publication_year": stmt.excluded.publication_year,
                "publication_date": stmt.excluded.publication_date,
                "source_id": stmt.excluded.source_id,
                "source_name": stmt.excluded.source_name,
                "author_count": stmt.excluded.author_count,
                "author_ids": stmt.excluded.author_ids,
                "fetched_at": stmt.excluded.fetched_at,
                "fetch_task_id": stmt.excluded.fetch_task_id,
                "sub_task_id": stmt.excluded.sub_task_id,
            },
        )
        await self.session.execute(stmt)
        return len(works)


class RawAuthorRepository:
    """Raw author repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, author: RawAuthor) -> RawAuthor:
        """Create a raw author record"""
        self.session.add(author)
        await self.session.flush()
        await self.session.refresh(author)
        return author

    async def upsert(self, author: RawAuthor) -> RawAuthor:
        """Create or update a raw author record.

        First checks if the author exists, then updates or creates accordingly.
        This approach avoids transaction state issues with exception handling.
        """
        # Check if author already exists
        existing = await self.get_by_openalex_id(author.openalex_author_id)
        if existing:
            # Update existing record
            existing.raw_json = author.raw_json
            existing.display_name = author.display_name
            existing.orcid = author.orcid
            existing.works_count = author.works_count
            existing.cited_by_count = author.cited_by_count
            existing.h_index = author.h_index
            existing.i10_index = author.i10_index
            existing.last_known_institution_id = author.last_known_institution_id
            existing.last_known_institution_name = author.last_known_institution_name
            existing.fetched_at = datetime.now(timezone.utc).replace(tzinfo=None)
            existing.fetch_task_id = author.fetch_task_id
            await self.session.flush()
            return existing
        else:
            # Create new record
            return await self.create(author)

    async def batch_upsert(self, authors: list[RawAuthor]) -> int:
        """
        Batch create or update authors using PostgreSQL INSERT ON CONFLICT.

        This is much faster than individual upserts as it:
        1. Uses a single SQL statement
        2. Avoids N+1 queries
        3. Reduces round-trips to database

        Args:
            authors: List of RawAuthor objects to upsert

        Returns:
            Number of authors processed
        """
        if not authors:
            return 0

        # Prepare data for bulk insert
        values = []
        for author in authors:
            values.append(
                {
                    "openalex_author_id": author.openalex_author_id,
                    "raw_json": author.raw_json,
                    "display_name": author.display_name,
                    "orcid": author.orcid,
                    "works_count": author.works_count,
                    "cited_by_count": author.cited_by_count,
                    "h_index": author.h_index,
                    "i10_index": author.i10_index,
                    "last_known_institution_id": author.last_known_institution_id,
                    "last_known_institution_name": author.last_known_institution_name,
                    "primary_education_id": author.primary_education_id,
                    "primary_education_name": author.primary_education_name,
                    "primary_company_id": author.primary_company_id,
                    "primary_company_name": author.primary_company_name,
                    "fetch_task_id": author.fetch_task_id,
                    "fetched_at": datetime.now(timezone.utc).replace(tzinfo=None),
                }
            )

        # Use PostgreSQL INSERT ON CONFLICT for efficient upsert
        stmt = pg_insert(RawAuthor).values(values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["openalex_author_id"],
            set_={
                "raw_json": stmt.excluded.raw_json,
                "display_name": stmt.excluded.display_name,
                "orcid": stmt.excluded.orcid,
                "works_count": stmt.excluded.works_count,
                "cited_by_count": stmt.excluded.cited_by_count,
                "h_index": stmt.excluded.h_index,
                "i10_index": stmt.excluded.i10_index,
                "last_known_institution_id": stmt.excluded.last_known_institution_id,
                "last_known_institution_name": stmt.excluded.last_known_institution_name,
                "primary_education_id": stmt.excluded.primary_education_id,
                "primary_education_name": stmt.excluded.primary_education_name,
                "primary_company_id": stmt.excluded.primary_company_id,
                "primary_company_name": stmt.excluded.primary_company_name,
                "fetch_task_id": stmt.excluded.fetch_task_id,
                "fetched_at": stmt.excluded.fetched_at,
            },
        )

        await self.session.execute(stmt)
        return len(authors)

    async def get_by_openalex_id(self, openalex_id: str) -> RawAuthor | None:
        """Get raw author by OpenAlex ID"""
        result = await self.session.execute(
            select(RawAuthor).where(RawAuthor.openalex_author_id == openalex_id)
        )
        return result.scalar_one_or_none()

    async def get_by_openalex_ids(
        self, openalex_ids: list[str], batch_size: int = 500
    ) -> list[RawAuthor]:
        """Get raw authors by multiple OpenAlex IDs.

        Args:
            openalex_ids: List of OpenAlex author IDs
            batch_size: Number of IDs to query per batch
        """
        if not openalex_ids:
            return []

        # Batch queries to avoid large IN clauses
        results = []
        for i in range(0, len(openalex_ids), batch_size):
            batch = openalex_ids[i : i + batch_size]
            result = await self.session.execute(
                select(RawAuthor).where(RawAuthor.openalex_author_id.in_(batch))
            )
            results.extend(result.scalars().all())

        return results

    async def get_missing_author_ids(
        self, author_ids: list[str], batch_size: int = 500
    ) -> list[str]:
        """Find author IDs that are not yet in the database.

        Args:
            author_ids: List of OpenAlex author IDs to check
            batch_size: Number of IDs to query per batch
        """
        if not author_ids:
            return []

        # Batch queries to avoid large IN clauses
        existing_ids = set()
        for i in range(0, len(author_ids), batch_size):
            batch = author_ids[i : i + batch_size]
            existing = await self.session.execute(
                select(RawAuthor.openalex_author_id).where(RawAuthor.openalex_author_id.in_(batch))
            )
            existing_ids.update(row[0] for row in existing.all())

        return [aid for aid in author_ids if aid not in existing_ids]

    async def get_pending(self, task_id: int | None = None, limit: int | None = None) -> list[RawAuthor]:
        """Get pending authors for processing.

        Args:
            task_id: Optional task ID to filter by. If provided, only returns
                     authors from the specified task.
            limit: Optional batch size limit to avoid loading all pending
                   authors into memory at once.
        """
        query = select(RawAuthor).where(RawAuthor.processed_status == "pending")
        if task_id is not None:
            query = query.where(RawAuthor.fetch_task_id == task_id)
        if limit is not None:
            query = query.limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def mark_processed(
        self, author_id: int, status: str = "processed", std_author_id: int | None = None
    ) -> None:
        """Mark author as processed"""
        values = {"processed_status": status, "processed_at": datetime.now(timezone.utc).replace(tzinfo=None)}
        if std_author_id:
            values["std_author_id"] = std_author_id
        await self.session.execute(
            update(RawAuthor).where(RawAuthor.raw_author_id == author_id).values(**values)
        )

    async def batch_mark_processed(
        self,
        author_ids: list[int],
        status: str = "processed",
        std_author_id_map: dict[int, int] | None = None,
    ) -> None:
        """Mark multiple authors as processed in a single UPDATE.

        Args:
            author_ids: List of RawAuthor IDs to mark.
            status: New processed_status value.
            std_author_id_map: Optional dict mapping raw_author_id -> std_author_id.
        """
        if not author_ids:
            return

        # For authors with the same std_author_id, we can use a simple UPDATE ... WHERE IN
        # For authors with different std_author_id values, we use CASE WHEN.
        if std_author_id_map and len(set(std_author_id_map.values())) > 1:
            # Multiple different std_author_ids: use CASE WHEN
            case_stmt = "CASE raw_author_id "
            for raw_id, std_id in std_author_id_map.items():
                if raw_id in author_ids:
                    case_stmt += f"WHEN {raw_id} THEN {std_id} "
            case_stmt += "END"
            await self.session.execute(
                update(RawAuthor)
                .where(RawAuthor.raw_author_id.in_(author_ids))
                .values(
                    processed_status=status,
                    processed_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    std_author_id=text(case_stmt),
                )
            )
        elif std_author_id_map and len(set(std_author_id_map.values())) == 1:
            # All same std_author_id (unlikely but optimize for it)
            std_author_id = list(std_author_id_map.values())[0]
            await self.session.execute(
                update(RawAuthor)
                .where(RawAuthor.raw_author_id.in_(author_ids))
                .values(
                    processed_status=status,
                    processed_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    std_author_id=std_author_id,
                )
            )
        else:
            await self.session.execute(
                update(RawAuthor)
                .where(RawAuthor.raw_author_id.in_(author_ids))
                .values(
                    processed_status=status,
                    processed_at=datetime.now(timezone.utc).replace(tzinfo=None),
                )
            )

    async def count_by_status(self) -> dict:
        """Count authors by processing status"""
        result = await self.session.execute(
            select(RawAuthor.processed_status, func.count(RawAuthor.raw_author_id)).group_by(
                RawAuthor.processed_status
            )
        )
        return {row[0]: row[1] for row in result.all()}


class RawInstitutionRepository:
    """Raw institution repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, institution: RawInstitution) -> RawInstitution:
        """Create a raw institution record"""
        self.session.add(institution)
        await self.session.flush()
        await self.session.refresh(institution)
        return institution

    async def upsert(self, institution: RawInstitution) -> RawInstitution:
        """Create or update a raw institution record.

        First checks if the institution exists, then updates or creates accordingly.
        This approach avoids transaction state issues with exception handling.
        """
        # Check if institution already exists
        existing = await self.get_by_openalex_id(institution.openalex_institution_id)
        if existing:
            # Update existing record
            existing.raw_json = institution.raw_json
            existing.display_name = institution.display_name
            existing.country_code = institution.country_code
            existing.country_name = institution.country_name
            existing.ror = institution.ror
            existing.type = institution.type
            existing.fetched_at = datetime.now(timezone.utc).replace(tzinfo=None)
            existing.fetch_task_id = institution.fetch_task_id
            await self.session.flush()
            return existing
        else:
            # Create new record
            return await self.create(institution)

    async def get_by_openalex_id(self, openalex_id: str) -> RawInstitution | None:
        """Get raw institution by OpenAlex ID"""
        result = await self.session.execute(
            select(RawInstitution).where(RawInstitution.openalex_institution_id == openalex_id)
        )
        return result.scalar_one_or_none()

    async def get_by_openalex_ids(
        self, openalex_ids: list[str], batch_size: int = 500
    ) -> list[RawInstitution]:
        """Get raw institutions by multiple OpenAlex IDs.

        Args:
            openalex_ids: List of OpenAlex institution IDs
            batch_size: Number of IDs to query per batch
        """
        if not openalex_ids:
            return []

        # Batch queries to avoid large IN clauses
        results = []
        for i in range(0, len(openalex_ids), batch_size):
            batch = openalex_ids[i : i + batch_size]
            result = await self.session.execute(
                select(RawInstitution).where(RawInstitution.openalex_institution_id.in_(batch))
            )
            results.extend(result.scalars().all())

        return results

    async def get_missing_ids(self, institution_ids: list[str], batch_size: int = 500) -> list[str]:
        """Find institution IDs that are not yet in the database.

        Args:
            institution_ids: List of OpenAlex institution IDs to check
            batch_size: Number of IDs to query per batch
        """
        if not institution_ids:
            return []

        # Batch queries to avoid large IN clauses
        existing_ids = set()
        for i in range(0, len(institution_ids), batch_size):
            batch = institution_ids[i : i + batch_size]
            existing = await self.session.execute(
                select(RawInstitution.openalex_institution_id).where(
                    RawInstitution.openalex_institution_id.in_(batch)
                )
            )
            existing_ids.update(row[0] for row in existing.all())

        return [iid for iid in institution_ids if iid not in existing_ids]

    async def get_pending(self, task_id: int | None = None) -> list[RawInstitution]:
        """Get pending institutions for processing.

        Args:
            task_id: Optional task ID to filter by. If provided, only returns
                     institutions from the specified task.
        """
        query = select(RawInstitution).where(RawInstitution.processed_status == "pending")
        if task_id is not None:
            query = query.where(RawInstitution.fetch_task_id == task_id)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def mark_processed(
        self, inst_id: int, status: str = "processed", std_school_id: int | None = None
    ) -> None:
        """Mark institution as processed"""
        values = {"processed_status": status, "processed_at": datetime.now(timezone.utc).replace(tzinfo=None)}
        if std_school_id:
            values["std_school_id"] = std_school_id
        await self.session.execute(
            update(RawInstitution)
            .where(RawInstitution.raw_institution_id == inst_id)
            .values(**values)
        )

    async def batch_upsert(self, institutions: list[RawInstitution]) -> int:
        """Batch create or update institutions using PostgreSQL INSERT ON CONFLICT.

        This eliminates N+1 queries from individual upserts.
        """
        if not institutions:
            return 0

        values = []
        for inst in institutions:
            values.append(
                {
                    "openalex_institution_id": inst.openalex_institution_id,
                    "raw_json": inst.raw_json,
                    "display_name": inst.display_name,
                    "country_code": inst.country_code,
                    "country_name": inst.country_name,
                    "ror": inst.ror,
                    "type": inst.type,
                    "fetch_task_id": inst.fetch_task_id,
                    "fetched_at": inst.fetched_at,
                }
            )

        stmt = pg_insert(RawInstitution).values(values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["openalex_institution_id"],
            set_={
                "raw_json": stmt.excluded.raw_json,
                "display_name": stmt.excluded.display_name,
                "country_code": stmt.excluded.country_code,
                "country_name": stmt.excluded.country_name,
                "ror": stmt.excluded.ror,
                "type": stmt.excluded.type,
                "fetch_task_id": stmt.excluded.fetch_task_id,
                "fetched_at": stmt.excluded.fetched_at,
            },
        )
        await self.session.execute(stmt)
        return len(institutions)


class AuthorTechBelongRepository:
    """Author-TechDomain relationship repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, belong: AuthorTechBelong) -> AuthorTechBelong:
        """Create an author-tech belong relationship"""
        self.session.add(belong)
        await self.session.flush()
        await self.session.refresh(belong)
        return belong

    async def upsert(self, belong: AuthorTechBelong) -> AuthorTechBelong:
        """Create or update an author-tech belong relationship"""
        existing = await self.get_by_author_tech_venue(
            belong.openalex_author_id,
            belong.tech_domain_id,
            belong.source_venue_id,
        )
        if existing:
            existing.work_count_in_venue = belong.work_count_in_venue
            existing.first_work_year = belong.first_work_year
            existing.last_work_year = belong.last_work_year
            existing.source_task_id = belong.source_task_id
            await self.session.flush()
            return existing
        else:
            return await self.create(belong)

    async def get_by_author_tech_venue(
        self, openalex_author_id: str, tech_domain_id: int, source_venue_id: int | None
    ) -> AuthorTechBelong | None:
        """Get relationship by author, tech domain and venue"""
        result = await self.session.execute(
            select(AuthorTechBelong).where(
                AuthorTechBelong.openalex_author_id == openalex_author_id,
                AuthorTechBelong.tech_domain_id == tech_domain_id,
                AuthorTechBelong.source_venue_id == source_venue_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_tech_domain(self, tech_domain_id: int) -> list[AuthorTechBelong]:
        """Get all relationships for a tech domain"""
        result = await self.session.execute(
            select(AuthorTechBelong).where(AuthorTechBelong.tech_domain_id == tech_domain_id)
        )
        return list(result.scalars().all())

    async def get_by_author(self, openalex_author_id: str) -> list[AuthorTechBelong]:
        """Get all tech domains for an author"""
        result = await self.session.execute(
            select(AuthorTechBelong).where(
                AuthorTechBelong.openalex_author_id == openalex_author_id
            )
        )
        return list(result.scalars().all())

    async def count_by_tech_domain(self, tech_domain_id: int) -> int:
        """Count authors for a tech domain"""
        result = await self.session.execute(
            select(func.count(AuthorTechBelong.belong_id)).where(
                AuthorTechBelong.tech_domain_id == tech_domain_id
            )
        )
        return result.scalar() or 0

    async def batch_create(self, belongs: list[AuthorTechBelong]) -> int:
        """Batch create relationships"""
        count = 0
        for belong in belongs:
            await self.upsert(belong)
            count += 1
        return count
