"""
Author normalizer for the standardized layer.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.academic.models.raw_data import RawAuthor
from app.domains.academic.models.standardized import StdAuthor, StdSchool
from app.domains.academic.repositories.raw_data_repository import RawAuthorRepository
from app.domains.academic.services.common.cs_concepts import CORE_CS_CONCEPTS, CS_SCORE_THRESHOLD
from app.domains.academic.services.normalizers.base import NormalizationResult
from app.domains.academic.services.normalizers.school import SchoolNormalizer

logger = logging.getLogger(__name__)

# Log module load to verify code version
logger.info(
    f"[AUTHOR_NORMALIZER] Module loaded. CORE_CS_CONCEPTS count: {len(CORE_CS_CONCEPTS)}, THRESHOLD: {CS_SCORE_THRESHOLD}"
)


# Default batch size for normalize_all_authors
DEFAULT_BATCH_SIZE = 500


class AuthorNormalizer:
    """作者归一化处理器"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self._school_normalizer: SchoolNormalizer | None = None

    @property
    def school_normalizer(self) -> SchoolNormalizer:
        """Lazy-init SchoolNormalizer for single-record path only."""
        if self._school_normalizer is None:
            self._school_normalizer = SchoolNormalizer(self.session)
        return self._school_normalizer

    def _parse_raw_json(self, raw_json: str) -> tuple[list[str], float]:
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
            matched_concepts = []
            for concept in concepts:
                concept_id = str(concept.get("id", ""))
                if concept_id in CORE_CS_CONCEPTS:
                    score = concept.get("score", 0)
                    cs_score += score
                    matched_concepts.append(concept_id)

            cs_score = min(cs_score, 1.0)

            # Debug log for CS score calculation (only log if concepts exist)
            if concepts and len(matched_concepts) > 0:
                logger.debug(
                    f"CS score calculated: {cs_score:.3f} (matched {len(matched_concepts)}/{len(concepts)} concepts)"
                )

        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Failed to parse raw_json: {e}")

        return topics, cs_score

    def _extract_topics(self, raw_json: str) -> list[str]:
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

    async def find_std_author(self, openalex_id: str) -> StdAuthor | None:
        """Find StdAuthor by OpenAlex ID"""
        result = await self.session.execute(
            select(StdAuthor).where(StdAuthor.openalex_author_id == openalex_id)
        )
        return result.scalar_one_or_none()

    async def _find_std_school_id(self, openalex_institution_id: str | None) -> int | None:
        """Find StdSchool ID by OpenAlex institution ID"""
        if not openalex_institution_id:
            return None
        result = await self.session.execute(
            select(StdSchool).where(StdSchool.openalex_institution_id == openalex_institution_id)
        )
        std_school = result.scalar_one_or_none()
        return std_school.std_school_id if std_school else None

    async def create_std_author(
        self, raw_author: RawAuthor, std_school_id: int | None = None, task_id: int | None = None
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
            # Legacy fields
            std_school_id=std_school_id,
            raw_institution_name=raw_author.last_known_institution_name,
            raw_institution_id=raw_author.last_known_institution_id,
            # Primary institutions (by publication count)
            primary_education_id=raw_author.primary_education_id,
            primary_education_name=raw_author.primary_education_name,
            primary_company_id=raw_author.primary_company_id,
            primary_company_name=raw_author.primary_company_name,
            confirm_status="auto_identified",
            confidence_score=0.8 if std_school_id else 0.5,
            openalex_topics=topics,
            cs_concepts_score=cs_score,
            source_task_id=task_id,
            normalized_at=datetime.utcnow(),
        )
        self.session.add(std_author)
        await self.session.flush()
        return std_author

    async def normalize_author(
        self, raw_author: RawAuthor, task_id: int | None = None
    ) -> StdAuthor:
        """Normalize a raw author to StdAuthor"""
        # Find or create school linkage first (legacy field)
        std_school_id = None
        if raw_author.last_known_institution_id:
            std_school_id = await self._find_std_school_id(raw_author.last_known_institution_id)

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
            # Legacy fields
            existing.raw_institution_id = raw_author.last_known_institution_id
            existing.std_school_id = std_school_id
            # Primary institutions (by publication count)
            existing.primary_education_id = raw_author.primary_education_id
            existing.primary_education_name = raw_author.primary_education_name
            existing.primary_company_id = raw_author.primary_company_id
            existing.primary_company_name = raw_author.primary_company_name
            existing.openalex_topics = topics
            existing.cs_concepts_score = cs_score
            existing.source_task_id = task_id
            existing.normalized_at = datetime.utcnow()
            await self.session.flush()
            return existing

        # Create new StdAuthor
        return await self.create_std_author(raw_author, std_school_id, task_id)

    async def _batch_find_std_authors(
        self, openalex_author_ids: list[str]
    ) -> dict[str, StdAuthor]:
        """Batch preload existing StdAuthors by OpenAlex IDs."""
        if not openalex_author_ids:
            return {}
        result = await self.session.execute(
            select(StdAuthor).where(StdAuthor.openalex_author_id.in_(openalex_author_ids))
        )
        return {a.openalex_author_id: a for a in result.scalars().all()}

    async def _batch_find_std_schools(
        self, openalex_institution_ids: list[str]
    ) -> dict[str, int]:
        """Batch preload StdSchool IDs by OpenAlex institution IDs."""
        if not openalex_institution_ids:
            return {}
        result = await self.session.execute(
            select(StdSchool).where(StdSchool.openalex_institution_id.in_(openalex_institution_ids))
        )
        return {s.openalex_institution_id: s.std_school_id for s in result.scalars().all()}

    def _build_std_author_values(
        self,
        raw_author: RawAuthor,
        topics: list[str],
        cs_score: float,
        std_school_id: int | None,
        task_id: int | None,
    ) -> dict:
        """Build a dict suitable for pg_insert(StdAuthor).values()."""
        return {
            "openalex_author_id": raw_author.openalex_author_id,
            "name_normalized": self.normalize_author_name(raw_author.display_name or ""),
            "name_original": raw_author.display_name,
            "orcid": raw_author.orcid,
            "works_count": raw_author.works_count,
            "cited_by_count": raw_author.cited_by_count,
            "h_index": raw_author.h_index,
            "i10_index": raw_author.i10_index,
            "std_school_id": std_school_id,
            "raw_institution_name": raw_author.last_known_institution_name,
            "raw_institution_id": raw_author.last_known_institution_id,
            "primary_education_id": raw_author.primary_education_id,
            "primary_education_name": raw_author.primary_education_name,
            "primary_company_id": raw_author.primary_company_id,
            "primary_company_name": raw_author.primary_company_name,
            "confirm_status": "auto_identified",
            "confidence_score": 0.8 if std_school_id else 0.5,
            "openalex_topics": topics,
            "cs_concepts_score": cs_score,
            "source_task_id": task_id,
            "normalized_at": datetime.utcnow(),
        }

    async def _batch_upsert_std_authors(
        self, values: list[dict], task_id: int | None = None
    ) -> dict[str, int]:
        """Bulk upsert StdAuthors and return {openalex_author_id: std_author_id}.

        Uses PostgreSQL INSERT ON CONFLICT DO UPDATE.
        """
        if not values:
            return {}

        stmt = pg_insert(StdAuthor).values(values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["openalex_author_id"],
            set_={
                "name_normalized": stmt.excluded.name_normalized,
                "name_original": stmt.excluded.name_original,
                "orcid": stmt.excluded.orcid,
                "works_count": stmt.excluded.works_count,
                "cited_by_count": stmt.excluded.cited_by_count,
                "h_index": stmt.excluded.h_index,
                "i10_index": stmt.excluded.i10_index,
                "std_school_id": stmt.excluded.std_school_id,
                "raw_institution_name": stmt.excluded.raw_institution_name,
                "raw_institution_id": stmt.excluded.raw_institution_id,
                "primary_education_id": stmt.excluded.primary_education_id,
                "primary_education_name": stmt.excluded.primary_education_name,
                "primary_company_id": stmt.excluded.primary_company_id,
                "primary_company_name": stmt.excluded.primary_company_name,
                "confirm_status": stmt.excluded.confirm_status,
                "confidence_score": stmt.excluded.confidence_score,
                "openalex_topics": stmt.excluded.openalex_topics,
                "cs_concepts_score": stmt.excluded.cs_concepts_score,
                "source_task_id": stmt.excluded.source_task_id,
                "normalized_at": stmt.excluded.normalized_at,
            },
        ).returning(StdAuthor.std_author_id, StdAuthor.openalex_author_id)

        result = await self.session.execute(stmt)
        return {row.openalex_author_id: row.std_author_id for row in result.all()}

    async def normalize_all_authors(self, task_id: int | None = None) -> NormalizationResult:
        """Normalize all pending authors for a specific task using batch processing.

        Args:
            task_id: The collection task ID. Only authors from this task
                     will be processed. If None, processes all pending authors.

        Returns:
            NormalizationResult with statistics
        """
        result = NormalizationResult()
        raw_repo = RawAuthorRepository(self.session)

        while True:
            # 1. Fetch next batch of pending authors
            pending = await raw_repo.get_pending(task_id, limit=DEFAULT_BATCH_SIZE)
            if not pending:
                break

            result.total += len(pending)

            # 2. Batch preload existing StdAuthors and StdSchools
            author_ids = [r.openalex_author_id for r in pending]
            existing_map = await self._batch_find_std_authors(author_ids)

            inst_ids = list({r.last_known_institution_id for r in pending if r.last_known_institution_id})
            school_map = await self._batch_find_std_schools(inst_ids)

            # 3. Parse raw_json once per author; isolate failures
            parsed: dict[int, tuple[list[str], float]] = {}
            failed_ids: list[int] = []
            for raw in pending:
                try:
                    # Pre-validate JSON before _parse_raw_json to catch malformed data
                    if raw.raw_json:
                        json.loads(raw.raw_json)
                    parsed[raw.raw_author_id] = self._parse_raw_json(raw.raw_json)
                except Exception as e:
                    logger.warning(
                        f"JSON parse failed for author {raw.openalex_author_id}: {e}"
                    )
                    failed_ids.append(raw.raw_author_id)

            # 4. Build values for batch upsert
            values = []
            raw_id_to_alex_id: dict[int, str] = {}
            for raw in pending:
                if raw.raw_author_id in failed_ids:
                    continue
                topics, cs_score = parsed[raw.raw_author_id]
                std_school_id = school_map.get(raw.last_known_institution_id)
                values.append(
                    self._build_std_author_values(raw, topics, cs_score, std_school_id, task_id)
                )
                raw_id_to_alex_id[raw.raw_author_id] = raw.openalex_author_id

            # 5. Bulk upsert StdAuthor
            author_id_map: dict[str, int] = {}
            if values:
                try:
                    author_id_map = await self._batch_upsert_std_authors(values, task_id)
                except Exception as e:
                    logger.error(f"Batch upsert failed: {e}. Falling back to single-record.")
                    # Fallback: process one by one to isolate the bad record
                    for raw in pending:
                        if raw.raw_author_id in failed_ids:
                            continue
                        try:
                            std_author = await self.normalize_author(raw, task_id)
                            author_id_map[raw.openalex_author_id] = std_author.std_author_id
                        except Exception as e2:
                            logger.warning(
                                f"Single-record fallback failed for {raw.openalex_author_id}: {e2}"
                            )
                            failed_ids.append(raw.raw_author_id)

            # 6. Bulk mark successful RawAuthors as processed
            ok_raw_ids = [
                raw_id
                for raw_id in raw_id_to_alex_id.keys()
                if raw_id not in failed_ids
            ]
            if ok_raw_ids and author_id_map:
                std_id_map = {
                    raw_id: author_id_map[raw_id_to_alex_id[raw_id]]
                    for raw_id in ok_raw_ids
                    if raw_id_to_alex_id[raw_id] in author_id_map
                }
                await raw_repo.batch_mark_processed(ok_raw_ids, "processed", std_id_map)

            # Mark failed RawAuthors so they are not re-fetched in the next loop
            if failed_ids:
                await raw_repo.batch_mark_processed(failed_ids, "failed")

            result.processed += len(ok_raw_ids)
            result.failed += len(failed_ids)

            # Commit per batch to release locks
            await self.session.commit()
            logger.info(
                f"Author normalization batch: processed={result.processed}, "
                f"failed={result.failed}, total_so_far={result.total}"
            )

        return result
