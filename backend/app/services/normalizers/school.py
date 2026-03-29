"""
School normalizer for the standardized layer.
"""
import re
from datetime import datetime
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.raw_data import RawInstitution
from app.models.standardized import StdSchool, SchoolNameAlias
from app.repositories.raw_data_repository import RawInstitutionRepository
from app.services.normalizers.base import NormalizationResult


class SchoolNormalizer:
    """学校归一化处理器"""

    def __init__(self, session: AsyncSession):
        self.session = session

    def normalize_school_name(self, name: str) -> str:
        """Normalize school name for matching"""
        if not name:
            return ""

        # Remove common suffixes
        name = name.strip()
        for suffix in ["University", "Institute", "College", "School"]:
            name = re.sub(rf"\b{suffix}\b", "", name, flags=re.IGNORECASE)

        # Remove punctuation and extra spaces
        name = re.sub(r"[^\w\s]", "", name)
        name = re.sub(r"\s+", " ", name)

        return name.strip().lower()

    async def find_matching_school(
        self,
        openalex_id: Optional[str],
        raw_name: str,
        country_code: Optional[str] = None
    ) -> Tuple[Optional[StdSchool], str]:
        """Find matching school by OpenAlex ID or name

        Returns: (matched_school, match_type)
        match_type: 'openalex_id', 'name', 'alias', 'none'
        """
        # Try OpenAlex ID first
        if openalex_id:
            result = await self.session.execute(
                select(StdSchool).where(StdSchool.openalex_institution_id == openalex_id)
            )
            school = result.scalar_one_or_none()
            if school:
                return school, "openalex_id"

        # Try exact name match
        if raw_name:
            result = await self.session.execute(
                select(StdSchool).where(StdSchool.name_normalized == raw_name)
            )
            school = result.scalar_one_or_none()
            if school:
                return school, "name"

            # Try alias match
            result = await self.session.execute(
                select(StdSchool)
                .join(SchoolNameAlias, StdSchool.std_school_id == SchoolNameAlias.std_school_id)
                .where(SchoolNameAlias.alias_name == raw_name)
            )
            school = result.scalar_one_or_none()
            if school:
                return school, "alias"

            # Try normalized name match
            normalized = self.normalize_school_name(raw_name)
            result = await self.session.execute(
                select(StdSchool).where(StdSchool.name_normalized.ilike(f"%{normalized}%"))
            )
            school = result.scalar_one_or_none()
            if school:
                return school, "normalized"

        return None, "none"

    async def create_std_school(
        self,
        raw_inst: RawInstitution,
        task_id: Optional[int] = None
    ) -> StdSchool:
        """Create a new StdSchool from RawInstitution"""
        std_school = StdSchool(
            openalex_institution_id=raw_inst.openalex_institution_id,
            name_normalized=raw_inst.display_name,
            country_code=raw_inst.country_code,
            country_name=raw_inst.country_name,
            ror=raw_inst.ror,
            inst_type=raw_inst.type,
            confirm_status="auto_identified",
            source_task_id=task_id,
            normalized_at=datetime.utcnow()
        )
        self.session.add(std_school)
        await self.session.flush()
        return std_school

    async def normalize_institution(
        self,
        raw_inst: RawInstitution,
        task_id: Optional[int] = None
    ) -> StdSchool:
        """Normalize a raw institution to StdSchool"""
        # Try to find existing match
        matched, match_type = await self.find_matching_school(
            raw_inst.openalex_institution_id,
            raw_inst.display_name,
            raw_inst.country_code
        )

        if matched:
            # Update existing
            matched.name_normalized = raw_inst.display_name
            matched.country_code = raw_inst.country_code
            matched.country_name = raw_inst.country_name
            matched.ror = raw_inst.ror
            matched.inst_type = raw_inst.type
            matched.normalized_at = datetime.utcnow()
            await self.session.flush()
            return matched
        else:
            # Create new
            return await self.create_std_school(raw_inst, task_id)

    async def normalize_all_institutions(
        self,
        task_id: Optional[int] = None,
        limit: int = 1000
    ) -> NormalizationResult:
        """Normalize all pending institutions"""
        result = NormalizationResult()

        # Get pending institutions
        raw_repo = RawInstitutionRepository(self.session)
        pending = await raw_repo.get_pending(limit)

        result.total = len(pending)

        for raw_inst in pending:
            try:
                std_school = await self.normalize_institution(raw_inst, task_id)
                await raw_repo.mark_processed(raw_inst.raw_institution_id, "processed", std_school.std_school_id)
                result.processed += 1
                if std_school.confirm_status == "pending_confirm":
                    result.pending_schools += 1
            except Exception as e:
                result.failed += 1

        # Also count existing normalized schools for accurate statistics
        if result.total == 0:
            from sqlalchemy import func
            count_result = await self.session.execute(
                select(func.count(StdSchool.std_school_id))
            )
            result.total = count_result.scalar() or 0
            result.processed = result.total  # All already normalized

        return result
