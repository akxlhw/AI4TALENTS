"""
School normalizer for the standardized layer.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.academic.models.raw_data import RawInstitution
from app.domains.academic.models.standardized import SchoolNameAlias, StdSchool
from app.domains.academic.repositories.raw_data_repository import RawInstitutionRepository
from app.domains.academic.services.normalizers.base import NormalizationResult


class SchoolNormalizer:
    """学校归一化处理器"""

    def __init__(self, session: AsyncSession):
        self.session = session

    def normalize_school_name(self, name: str) -> str:
        """Normalize school name for matching.

        Returns a lowercase string with common suffixes removed.
        If removing suffixes leaves nothing, falls back to the cleaned original
        to avoid returning an empty string that would match the entire table.
        """
        if not name:
            return ""

        original = name.strip()

        # Remove common suffixes
        name = original
        for suffix in ["University", "Institute", "College", "School"]:
            name = re.sub(rf"\b{suffix}\b", "", name, flags=re.IGNORECASE)

        # Remove punctuation and extra spaces
        name = re.sub(r"[^\w\s]", "", name)
        name = re.sub(r"\s+", " ", name)
        result = name.strip().lower()

        # Guard: if stripping suffixes leaves nothing (e.g. "University School"),
        # fall back to the cleaned original so we never return "".
        if not result:
            fallback = re.sub(r"[^\w\s]", "", original)
            fallback = re.sub(r"\s+", " ", fallback)
            return fallback.strip().lower()

        return result

    async def find_matching_school(
        self, openalex_id: str | None, raw_name: str, country_code: str | None = None
    ) -> tuple[StdSchool | None, str]:
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
            # Guard: empty or too-short normalized strings would match the whole table
            if normalized and len(normalized) >= 2:
                result = await self.session.execute(
                    select(StdSchool)
                    .where(StdSchool.name_normalized.ilike(f"%{normalized}%"))
                    .limit(1)  # 只取第一条匹配记录
                )
                school = result.scalars().first()
                if school:
                    return school, "normalized"

        return None, "none"

    def _normalize_country_code(self, country_code: str | None) -> str | None:
        """Normalize country code.

        Note: Taiwan (TW) is mapped to China (CN) as Taiwan is part of China.
        """
        if not country_code:
            return None

        code = country_code.upper()
        # Taiwan is part of China - map TW to CN
        if code == "TW":
            return "CN"
        return code

    async def create_std_school(
        self, raw_inst: RawInstitution, task_id: int | None = None
    ) -> StdSchool:
        """Create a new StdSchool from RawInstitution"""
        # Normalize country code (TW -> CN)
        country_code = self._normalize_country_code(raw_inst.country_code)

        std_school = StdSchool(
            openalex_institution_id=raw_inst.openalex_institution_id,
            name_normalized=raw_inst.display_name,
            country_code=country_code,
            country_name=raw_inst.country_name,
            ror=raw_inst.ror,
            inst_type=raw_inst.type,
            confirm_status="auto_identified",
            source_task_id=task_id,
            normalized_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        self.session.add(std_school)
        await self.session.flush()
        return std_school

    async def normalize_institution(
        self, raw_inst: RawInstitution, task_id: int | None = None
    ) -> StdSchool:
        """Normalize a raw institution to StdSchool"""
        # Try to find existing match
        matched, match_type = await self.find_matching_school(
            raw_inst.openalex_institution_id, raw_inst.display_name, raw_inst.country_code
        )

        if matched:
            # Safety: only update in-place when the match is reliable.
            # openalex_id match is definitive; name/alias/normalized matches are
            # heuristic and must have the same openalex_id to avoid merging
            # unrelated institutions (e.g. "University School" overwriting MIT).
            can_update = match_type == "openalex_id" or (
                raw_inst.openalex_institution_id
                and raw_inst.openalex_institution_id == matched.openalex_institution_id
            )
            if can_update:
                matched.name_normalized = raw_inst.display_name
                matched.country_code = self._normalize_country_code(raw_inst.country_code)
                matched.country_name = raw_inst.country_name
                matched.ror = raw_inst.ror
                matched.inst_type = raw_inst.type
                matched.source_task_id = task_id
                matched.normalized_at = datetime.now(timezone.utc).replace(tzinfo=None)
                await self.session.flush()
                return matched
            # Matched but not safe to update: create a new record to prevent
            # data pollution of the existing school.
            return await self.create_std_school(raw_inst, task_id)

        # Create new
        return await self.create_std_school(raw_inst, task_id)

    async def normalize_all_institutions(
        self, task_id: int | None = None, *, commit_per_batch: bool = True
    ) -> NormalizationResult:
        """Normalize all pending institutions for a specific task.

        Args:
            task_id: The collection task ID. Only institutions from this task
                     will be processed. If None, processes all pending institutions.
            commit_per_batch: If True (default), commits every 50 records.
                Set to False when called inside a parent transaction (e.g. collection
                phase orchestrator) so the caller can commit/rollback atomically.

        Returns:
            NormalizationResult with statistics
        """
        import logging

        logger = logging.getLogger(__name__)

        result = NormalizationResult()

        # Get pending institutions for this task
        raw_repo = RawInstitutionRepository(self.session)
        pending = await raw_repo.get_pending(task_id)

        result.total = len(pending)

        # Commit or flush every 50 institutions to release database lock
        commit_interval = 50

        for i, raw_inst in enumerate(pending):
            try:
                std_school = await self.normalize_institution(raw_inst, task_id)
                await raw_repo.mark_processed(
                    raw_inst.raw_institution_id, "processed", std_school.std_school_id
                )
                result.processed += 1
                if std_school.confirm_status == "pending_confirm":
                    result.pending_schools += 1

                # Commit/flush periodically to release database lock
                if (i + 1) % commit_interval == 0:
                    if commit_per_batch:
                        await self.session.commit()
                    else:
                        await self.session.flush()
                    logger.debug(
                        f"School normalization progress: {result.processed}/{result.total}"
                    )

            except Exception:
                result.failed += 1
                await raw_repo.mark_processed(raw_inst.raw_institution_id, "failed")

        return result
