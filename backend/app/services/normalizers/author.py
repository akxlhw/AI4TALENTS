"""
Author normalizer for the standardized layer.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.raw_data import RawAuthor
from app.models.standardized import StdAuthor, StdSchool
from app.repositories.raw_data_repository import RawAuthorRepository
from app.services.normalizers.base import NormalizationResult
from app.services.normalizers.school import SchoolNormalizer
from app.services.common.cs_concepts import CORE_CS_CONCEPTS

logger = logging.getLogger(__name__)


class AuthorNormalizer:
    """作者归一化处理器"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.school_normalizer = SchoolNormalizer(session)

    def _parse_raw_json(self, raw_json: str) -> tuple[List[str], float]:
        """
        Parse raw_json once to extract both topics and CS score.

        Returns:
            Tuple of (topics_list, cs_score)
        """
        topics = []
        cs_score = 0.0

        if not raw_json:
            return topics, cs_score

        try:
            data = json.loads(raw_json)

            # Extract topics
            topics_data = data.get("topics", [])
            for topic in topics_data[:10]:
                if topic.get("count", 0) >= 3:
                    display_name = topic.get("display_name")
                    if display_name:
                        topics.append(display_name)

            # Calculate CS score
            concepts = data.get("x_concepts", [])
            for concept in concepts:
                concept_url = concept.get("id", "")
                concept_id = concept_url.split("/")[-1] if concept_url else ""
                if concept_id in CORE_CS_CONCEPTS:
                    score = concept.get("score", 0)
                    cs_score += score

            cs_score = min(cs_score, 1.0)

        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Failed to parse raw_json: {e}")

        return topics, cs_score

    def _extract_topics(self, raw_json: str) -> List[str]:
        """Extract research topics from OpenAlex raw_json."""
        topics, _ = self._parse_raw_json(raw_json)
        return topics

    def _calculate_cs_score(self, raw_json: str) -> float:
        """Calculate CS background score from OpenAlex x_concepts."""
        _, cs_score = self._parse_raw_json(raw_json)
        return cs_score

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
        # Parse raw_json once to extract both topics and CS score
        topics, cs_score = self._parse_raw_json(raw_author.raw_json)

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
            openalex_topics=topics,
            cs_concepts_score=cs_score,
            source_task_id=task_id,
            normalized_at=datetime.now(timezone.utc)
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
            # Extract topics from raw_json
            topics = self._extract_topics(raw_author.raw_json)
            # Calculate CS background score
            cs_score = self._calculate_cs_score(raw_author.raw_json)

            # Update existing (including school linkage and topics)
            existing.name_normalized = self.normalize_author_name(raw_author.display_name or "")
            existing.works_count = raw_author.works_count
            existing.cited_by_count = raw_author.cited_by_count
            existing.h_index = raw_author.h_index
            existing.i10_index = raw_author.i10_index
            existing.raw_institution_id = raw_author.last_known_institution_id
            existing.std_school_id = std_school_id
            existing.openalex_topics = topics
            existing.cs_concepts_score = cs_score
            existing.normalized_at = datetime.now(timezone.utc)
            await self.session.flush()
            return existing

        # Create new StdAuthor
        return await self.create_std_author(raw_author, std_school_id, task_id)

    async def normalize_all_authors(
        self,
        task_id: Optional[int] = None
    ) -> NormalizationResult:
        """Normalize all pending authors for a specific task.

        Args:
            task_id: The collection task ID. Only authors from this task
                     will be processed. If None, processes all pending authors.

        Returns:
            NormalizationResult with statistics
        """
        result = NormalizationResult()

        # Get pending authors for this task
        raw_repo = RawAuthorRepository(self.session)
        pending = await raw_repo.get_pending(task_id)

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

        return result
