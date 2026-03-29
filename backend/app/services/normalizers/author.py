"""
Author normalizer for the standardized layer.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.raw_data import RawAuthor
from app.models.standardized import StdAuthor, StdSchool
from app.repositories.raw_data_repository import RawAuthorRepository
from app.services.normalizers.base import NormalizationResult
from app.services.normalizers.school import SchoolNormalizer


class AuthorNormalizer:
    """作者归一化处理器"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.school_normalizer = SchoolNormalizer(session)

    def normalize_author_name(self, name: str) -> str:
        """Normalize author name"""
        if not name:
            return ""

        # Remove extra spaces
        name = " ".join(name.split())

        # Capitalize properly
        parts = name.split()
        normalized = []
        for part in parts:
            if len(part) > 1:
                normalized.append(part[0].upper() + part[1:].lower())
            else:
                normalized.append(part.upper())

        return " ".join(normalized)

    async def find_std_author(self, openalex_id: str) -> Optional[StdAuthor]:
        """Find StdAuthor by OpenAlex ID"""
        result = await self.session.execute(
            select(StdAuthor).where(StdAuthor.openalex_author_id == openalex_id)
        )
        return result.scalar_one_or_none()

    async def create_std_author(
        self,
        raw_author: RawAuthor,
        std_school_id: Optional[int] = None,
        task_id: Optional[int] = None
    ) -> StdAuthor:
        """Create a new StdAuthor from RawAuthor"""
        std_author = StdAuthor(
            openalex_author_id=raw_author.openalex_author_id,
            name_normalized=self.normalize_author_name(raw_author.display_name or ""),
            name_original=raw_author.display_name,
            orcid=raw_author.orcid,
            works_count=raw_author.works_count,
            cited_by_count=raw_author.cited_by_count,
            h_index=raw_author.h_index,
            i10_index=raw_author.i10_index,
            std_school_id=std_school_id,
            raw_institution_name=raw_author.last_known_institution_name,
            raw_institution_id=raw_author.last_known_institution_id,
            confirm_status="auto_identified",
            confidence_score=0.8 if std_school_id else 0.5,
            source_task_id=task_id,
            normalized_at=datetime.utcnow()
        )
        self.session.add(std_author)
        await self.session.flush()
        return std_author

    async def normalize_author(
        self,
        raw_author: RawAuthor,
        task_id: Optional[int] = None
    ) -> StdAuthor:
        """Normalize a raw author to StdAuthor"""
        # Find or create school linkage first
        std_school_id = None
        if raw_author.last_known_institution_id:
            # Try to find StdSchool by institution ID
            result = await self.session.execute(
                select(StdSchool).where(
                    StdSchool.openalex_institution_id == raw_author.last_known_institution_id
                )
            )
            std_school = result.scalar_one_or_none()
            if std_school:
                std_school_id = std_school.std_school_id

        # Check if already exists
        existing = await self.find_std_author(raw_author.openalex_author_id)
        if existing:
            # Update existing (including school linkage)
            existing.name_normalized = self.normalize_author_name(raw_author.display_name or "")
            existing.works_count = raw_author.works_count
            existing.cited_by_count = raw_author.cited_by_count
            existing.h_index = raw_author.h_index
            existing.i10_index = raw_author.i10_index
            existing.raw_institution_id = raw_author.last_known_institution_id
            existing.std_school_id = std_school_id
            existing.normalized_at = datetime.utcnow()
            await self.session.flush()
            return existing

        # Create new StdAuthor
        return await self.create_std_author(raw_author, std_school_id, task_id)

    async def normalize_all_authors(
        self,
        task_id: Optional[int] = None,
        limit: int = 1000
    ) -> NormalizationResult:
        """Normalize all pending authors"""
        result = NormalizationResult()

        # Get pending authors
        raw_repo = RawAuthorRepository(self.session)
        pending = await raw_repo.get_pending(limit)

        result.total = len(pending)

        for raw_author in pending:
            try:
                std_author = await self.normalize_author(raw_author, task_id)
                await raw_repo.mark_processed(
                    raw_author.raw_author_id,
                    "processed",
                    std_author.std_author_id
                )
                result.processed += 1
            except Exception as e:
                result.failed += 1

        # Also count existing normalized authors for accurate statistics
        if result.total == 0:
            from sqlalchemy import func
            count_result = await self.session.execute(
                select(func.count(StdAuthor.std_author_id))
            )
            result.total = count_result.scalar() or 0
            result.processed = result.total  # All already normalized

        return result
