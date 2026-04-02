"""
School sync service for synchronizing StdSchool to School.
"""
from __future__ import annotations

import json
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.countries import get_country_name_cn, normalize_country_code
from app.models.school import School, SchoolAlias
from app.models.standardized import StdSchool

logger = logging.getLogger(__name__)


class SchoolSyncService:
    """Service for synchronizing standardized schools to serving layer"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def sync_school_to_school(
        self,
        std_school: StdSchool,
        update_existing: bool = True
    ) -> tuple[School, bool]:
        """
        Sync standardized school to serving layer School table

        Args:
            std_school: Standardized school object
            update_existing: Whether to update existing records

        Returns:
            Tuple[School, bool]: (School object, is_new)
        """
        # 1. Find existing School by OpenAlex ID
        result = await self.session.execute(
            select(School).where(
                School.source_record_id == std_school.openalex_institution_id
            )
        )
        existing_school = result.scalar_one_or_none()

        # 2. Normalize country code (TW -> CN)
        country_code = normalize_country_code(std_school.country_code)
        country_name = get_country_name_cn(country_code)

        if existing_school:
            # Update existing record
            if update_existing:
                existing_school.school_name = std_school.name_normalized
                existing_school.source_type = "openalex"
                existing_school.source_record_id = std_school.openalex_institution_id
                existing_school.country_code = country_code
                existing_school.country_name = country_name
                if std_school.homepage_url:
                    existing_school.homepage_url = std_school.homepage_url

            await self.session.flush()
            return existing_school, False

        # 3. Create new School
        new_school = School(
            school_name=std_school.name_normalized,
            country_code=country_code,
            country_name=country_name,
            source_type="openalex",
            source_record_id=std_school.openalex_institution_id,
            homepage_url=std_school.homepage_url,
            is_visible=True,
            status="active",
        )

        self.session.add(new_school)
        await self.session.flush()

        # Create school aliases
        if std_school.name_aliases:
            await self._create_school_aliases(new_school.school_id, std_school)

        logger.info(
            f"Created school: {new_school.school_id} - {new_school.school_name}"
        )

        return new_school, True

    async def _create_school_aliases(self, school_id: int, std_school: StdSchool) -> int:
        """Create school aliases"""
        created = 0

        try:
            aliases = json.loads(std_school.name_aliases)
            for alias in aliases:
                # Check if already exists
                existing = await self.session.execute(
                    select(SchoolAlias).where(
                        SchoolAlias.school_id == school_id,
                        SchoolAlias.alias_name == alias
                    )
                )
                if not existing.scalar_one_or_none():
                    school_alias = SchoolAlias(
                        school_id=school_id,
                        alias_name=alias,
                        alias_type="openalex",
                    )
                    self.session.add(school_alias)
                    created += 1
        except json.JSONDecodeError:
            pass

        if created > 0:
            await self.session.flush()

        return created
