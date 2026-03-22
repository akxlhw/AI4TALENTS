"""
School object builder.
Transforms raw OpenAlex institution data into School domain objects.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.builders.base import BaseBuilder, BuildResult, extract_openalex_id, normalize_name
from app.models.school import School, SchoolAlias
from app.models.country import Country
from app.models.sync import RawSourceRecord


logger = logging.getLogger(__name__)


# Known institution name mappings
INSTITUTION_NAME_MAPPING = {
    "massachusetts institute of technology": "MIT",
    "massachusetts institute of technology (mit)": "MIT",
    "stanford university": "Stanford",
    "harvard university": "Harvard",
    "university of cambridge": "Cambridge",
    "university of oxford": "Oxford",
    "california institute of technology": "Caltech",
    "princeton university": "Princeton",
    "yale university": "Yale",
    "columbia university": "Columbia",
    "university of chicago": "UChicago",
    "university of california, berkeley": "UC Berkeley",
    "tsinghua university": "Tsinghua University",
    "peking university": "Peking University",
}


class SchoolBuilder(BaseBuilder):
    """
    Builder for School objects from OpenAlex institution data.
    """

    def __init__(self, session: AsyncSession, batch_id: int):
        super().__init__(batch_id)
        self.session = session
        self._country_cache: Dict[str, int] = {}

    async def build(self) -> BuildResult:
        """
        Build School objects from raw institution records.

        Process:
        1. Load pending institution records
        2. Transform to School objects
        3. Create aliases for name variants
        4. Mark records as processed

        Returns:
            BuildResult with statistics
        """
        started_at = datetime.now()
        records_processed = 0
        records_created = 0
        records_updated = 0
        records_failed = 0

        # Load pending institution records
        result = await self.session.execute(
            select(RawSourceRecord)
            .where(
                RawSourceRecord.batch_id == self.batch_id,
                RawSourceRecord.source_type == "institution",
                RawSourceRecord.processed_status == "pending",
            )
        )
        records = list(result.scalars().all())

        logger.info(f"Processing {len(records)} institution records")

        for record in records:
            try:
                raw_data = record.raw_data
                source_id = extract_openalex_id(raw_data.get("id", ""))

                # Build school object
                school, is_new = await self._build_school(raw_data, source_id)

                if school:
                    # Create aliases
                    await self._create_aliases(school, raw_data)

                    if is_new:
                        records_created += 1
                    else:
                        records_updated += 1

                    # Mark record as processed
                    record.processed_status = "processed"
                    record.processed_at = datetime.now()

                records_processed += 1

                # Commit in batches
                if records_processed % 100 == 0:
                    await self.session.commit()
                    logger.info(f"  Processed {records_processed} institutions")

            except Exception as e:
                records_failed += 1
                self.log_error(str(e), record.source_id)
                record.processed_status = "error"
                record.error_info = str(e)

        # Final commit
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

    async def _build_school(
        self,
        raw_data: Dict[str, Any],
        source_id: str,
    ) -> tuple[Optional[School], bool]:
        """
        Build a School object from raw data.

        Args:
            raw_data: Raw institution data from OpenAlex
            source_id: OpenAlex institution ID

        Returns:
            Tuple of (School object, is_new)
        """
        display_name = raw_data.get("display_name", "")
        if not display_name:
            return None, False

        # Normalize name
        normalized = normalize_name(display_name)
        school_name = INSTITUTION_NAME_MAPPING.get(normalized, display_name)

        # Get country
        country_code = raw_data.get("country_code", "")
        country_id = await self._get_country_id(country_code)

        # Check if school already exists
        existing = await self._find_existing_school(source_id, display_name)

        if existing:
            # Update existing school
            existing.school_name = school_name
            existing.school_alias = display_name
            if country_id:
                existing.country_id = country_id
            existing.homepage_url = raw_data.get("homepage_url")
            existing.source_record_id = source_id
            existing.last_sync_batch_id = self.batch_id

            return existing, False

        # Create new school
        school = School(
            school_name=school_name,
            school_alias=display_name,
            country_id=country_id,
            school_intro=self._build_intro(raw_data),
            homepage_url=raw_data.get("homepage_url"),
            professor_count=0,
            student_count=0,
            is_visible=True,
            status="active",
            source_type="openalex",
            source_record_id=source_id,
            last_sync_batch_id=self.batch_id,
        )

        self.session.add(school)
        await self.session.flush()

        return school, True

    async def _find_existing_school(
        self,
        source_id: str,
        display_name: str,
    ) -> Optional[School]:
        """Find existing school by source ID or name."""
        # First try by source ID
        result = await self.session.execute(
            select(School).where(School.source_record_id == source_id)
        )
        school = result.scalar_one_or_none()

        if school:
            return school

        # Try by name alias
        result = await self.session.execute(
            select(SchoolAlias).where(SchoolAlias.alias_name == display_name)
        )
        alias = result.scalar_one_or_none()

        if alias:
            return await self.session.get(School, alias.school_id)

        return None

    async def _get_country_id(self, country_code: str) -> Optional[int]:
        """Get country ID by code, with caching."""
        if not country_code:
            return None

        if country_code in self._country_cache:
            return self._country_cache[country_code]

        result = await self.session.execute(
            select(Country.country_id).where(Country.country_code == country_code)
        )
        country_id = result.scalar_one_or_none()

        if country_id:
            self._country_cache[country_code] = country_id

        return country_id

    def _build_intro(self, raw_data: Dict[str, Any]) -> Optional[str]:
        """Build school introduction from available data."""
        parts = []

        if raw_data.get("display_name"):
            parts.append(f"{raw_data['display_name']}")

        if raw_data.get("type"):
            parts.append(f"Type: {raw_data['type']}")

        # Add geographic info
        geo = raw_data.get("geo", {})
        if geo.get("city"):
            parts.append(f"Location: {geo['city']}")
            if geo.get("region"):
                parts.append(f", {geo['region']}")

        if parts:
            return " | ".join(parts)

        return None

    async def _create_aliases(
        self,
        school: School,
        raw_data: Dict[str, Any],
    ) -> None:
        """Create aliases for a school."""
        aliases_to_create = []

        # Add display name as alias
        display_name = raw_data.get("display_name", "")
        if display_name and display_name != school.school_name:
            aliases_to_create.append((display_name, "primary"))

        # Add abbreviated names
        acronym = raw_data.get("abbreviations", [])
        if isinstance(acronym, list):
            for abbr in acronym[:3]:  # Limit to 3 abbreviations
                if abbr:
                    aliases_to_create.append((abbr, "abbreviation"))

        # Add alternative names
        alt_names = raw_data.get("display_name_alternatives", [])
        if isinstance(alt_names, list):
            for alt in alt_names[:3]:  # Limit to 3 alternatives
                if alt:
                    aliases_to_create.append((alt, "alternative"))

        # Create aliases
        for alias_name, alias_type in aliases_to_create:
            # Check if alias exists
            result = await self.session.execute(
                select(SchoolAlias).where(
                    SchoolAlias.school_id == school.school_id,
                    SchoolAlias.alias_name == alias_name,
                )
            )
            if not result.scalar_one_or_none():
                alias = SchoolAlias(
                    school_id=school.school_id,
                    alias_name=alias_name,
                    alias_type=alias_type,
                )
                self.session.add(alias)
