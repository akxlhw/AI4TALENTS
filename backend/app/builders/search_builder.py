"""
Search document builder.
Builds search projection documents for full-text search.
"""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.builders.base import BaseBuilder, BuildResult
from app.models.school import School
from app.models.search import SearchTalentDocument
from app.models.talent import Talent

logger = logging.getLogger(__name__)


class SearchBuilder(BaseBuilder):
    """
    Builder for search talent documents.

    Creates denormalized search documents for efficient
    full-text search and filtering.
    """

    def __init__(self, session: AsyncSession, batch_id: int):
        super().__init__(batch_id)
        self.session = session

    async def build(self) -> BuildResult:
        """
        Build search documents for all visible talents.

        Returns:
            BuildResult with statistics
        """
        started_at = datetime.now()
        records_processed = 0
        records_created = 0
        records_updated = 0
        records_failed = 0

        # Get all visible talents with their schools
        result = await self.session.execute(
            select(Talent, School)
            .join(School, Talent.school_id == School.school_id, isouter=True)
            .where(Talent.is_visible.is_(True))
        )
        talents_with_schools = result.all()

        logger.info(f"Building search documents for {len(talents_with_schools)} talents")

        for talent, school in talents_with_schools:
            try:
                doc = await self._build_search_document(talent, school)

                if doc:
                    records_created += 1

                records_processed += 1

                if records_processed % 100 == 0:
                    await self.session.commit()
                    logger.info(f"  Processed {records_processed} search documents")

            except Exception as e:
                records_failed += 1
                self.log_error(str(e), str(talent.talent_id))

        await self.session.commit()

        completed_at = datetime.now()

        return BuildResult(
            success=records_failed == 0,
            records_processed=records_processed,
            records_created=records_created,
            records_updated=records_updated,
            records_failed=records_failed,
            errors=self.errors,
            started_at=started_at,
            completed_at=completed_at,
        )

    async def _build_search_document(
        self,
        talent: Talent,
        school: School | None,
    ) -> SearchTalentDocument | None:
        """
        Build a search document for a talent.

        Args:
            talent: Talent object
            school: Associated school (can be None)

        Returns:
            Created or updated SearchTalentDocument
        """
        # Check if document exists
        result = await self.session.execute(
            select(SearchTalentDocument).where(SearchTalentDocument.talent_id == talent.talent_id)
        )
        doc = result.scalar_one_or_none()

        # Build search text
        search_text = self._build_search_text(talent, school)

        # Get country code directly from school
        country_code = school.country_code if school else None

        now = datetime.now()

        if doc:
            # Update existing document
            doc.name = talent.name
            doc.school_id = school.school_id if school else 0
            doc.school_name = school.school_name if school else None
            doc.country_code = country_code
            doc.search_text = search_text
            doc.role_type = talent.role_type
            doc.topic_tags = talent.topic_tags or []
            doc.works_count = talent.works_count
            doc.cited_by_count = talent.cited_by_count
            doc.h_index = talent.h_index
            doc.latest_active_year = talent.latest_active_year
            doc.orcid = talent.orcid
            doc.batch_id = self.batch_id
            doc.updated_at = now
            doc.is_active = True

            return doc

        # Create new document
        doc = SearchTalentDocument(
            talent_id=talent.talent_id,
            school_id=school.school_id if school else 0,
            name=talent.name,
            school_name=school.school_name if school else None,
            country_code=country_code,
            search_text=search_text,
            role_type=talent.role_type,
            topic_tags=talent.topic_tags or [],
            works_count=talent.works_count,
            cited_by_count=talent.cited_by_count,
            h_index=talent.h_index,
            latest_active_year=talent.latest_active_year,
            orcid=talent.orcid,
            batch_id=self.batch_id,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        self.session.add(doc)
        return doc

    def _build_search_text(
        self,
        talent: Talent,
        school: School | None,
    ) -> str:
        """
        Build searchable text from talent and school data.

        Args:
            talent: Talent object
            school: School object (can be None)

        Returns:
            Combined searchable text
        """
        parts = []

        # Add talent name
        if talent.name:
            parts.append(talent.name)

        if talent.name_en and talent.name_en != talent.name:
            parts.append(talent.name_en)

        # Add ORCID
        if talent.orcid:
            parts.append(talent.orcid)

        # Add school name
        if school:
            if school.school_name:
                parts.append(school.school_name)
            if school.school_alias and school.school_alias != school.school_name:
                parts.append(school.school_alias)

        # Add topics
        if talent.topic_tags:
            parts.extend(talent.topic_tags)

        # Add title if available
        if talent.current_title:
            parts.append(talent.current_title)

        # Join with spaces
        return " ".join(filter(None, parts))
