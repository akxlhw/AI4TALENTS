"""
Author sync service for synchronizing StdAuthor to Talent.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import VisibilityStatus
from app.models.school import School
from app.models.standardized import StdAuthor
from app.models.talent import RoleProfile, Talent
from app.services.common.cs_concepts import CS_SCORE_THRESHOLD
from app.services.role_identifier import RoleIdentifier

logger = logging.getLogger(__name__)

# Log module load to verify code version
logger.info(f"[AUTHOR_SYNC] Module loaded. CS_SCORE_THRESHOLD: {CS_SCORE_THRESHOLD}")


class AuthorSyncService:
    """Service for synchronizing standardized authors to serving layer"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def sync_author_to_talent(
        self,
        std_author: StdAuthor,
        update_existing: bool = True
    ) -> tuple[Talent | None, bool]:
        """
        Sync standardized author to serving layer Talent table

        Args:
            std_author: Standardized author object
            update_existing: Whether to update existing records

        Returns:
            Tuple[Optional[Talent], bool]: (Talent object or None, is_new)
            Returns (None, False) if author's CS score is below threshold
        """
        # Filter non-CS background authors
        # Handle None value as 0.0 (filtered)
        cs_score = std_author.cs_concepts_score or 0.0
        if cs_score < CS_SCORE_THRESHOLD:
            logger.debug(
                f"[CS_FILTER] Skipping {std_author.name_normalized}: "
                f"CS score {cs_score:.2f} < {CS_SCORE_THRESHOLD}"
            )
            return None, False

        logger.debug(f"[CS_PASS] {std_author.name_normalized}: CS score {cs_score:.2f}")

        # 1. Find existing Talent by source ID
        result = await self.session.execute(
            select(Talent).where(
                Talent.source_record_id == std_author.openalex_author_id
            )
        )
        existing_talent = result.scalar_one_or_none()

        # 2. Role identification
        role_result = RoleIdentifier.identify(
            works_count=std_author.works_count or 0,
            cited_by_count=std_author.cited_by_count or 0,
            h_index=std_author.h_index or 0
        )

        # 3. Get or create school association
        school_id = await self._get_school_id(std_author)

        if existing_talent:
            # Update existing record
            if update_existing:
                await self._update_talent(existing_talent, std_author, role_result, school_id)

            await self.session.flush()
            return existing_talent, False

        # 4. Create new Talent
        new_talent = await self._create_talent(std_author, role_result, school_id)

        logger.debug(
            f"Created talent: {new_talent.talent_id} - {new_talent.name} "
            f"(role: {role_result.role_type}, confidence: {role_result.confidence})"
        )

        return new_talent, True

    async def _get_school_id(self, std_author: StdAuthor) -> int | None:
        """Get school ID for author"""
        if not std_author.std_school_id:
            return None

        # Find associated serving layer school
        if std_author.school:
            school_result = await self.session.execute(
                select(School).where(
                    School.source_record_id == std_author.school.openalex_institution_id
                )
            )
            school = school_result.scalar_one_or_none()
            if school:
                return school.school_id

        return None

    async def _update_talent(
        self,
        talent: Talent,
        std_author: StdAuthor,
        role_result,
        school_id: int | None
    ):
        """Update existing talent record"""
        talent.name = std_author.name_normalized
        talent.name_en = std_author.name_original
        talent.orcid = std_author.orcid
        talent.std_author_id = std_author.std_author_id
        talent.school_id = school_id
        talent.role_type = role_result.role_type
        talent.role_confidence = role_result.confidence
        talent.works_count = std_author.works_count or 0
        talent.cited_by_count = std_author.cited_by_count or 0
        talent.h_index = std_author.h_index or 0
        talent.openalex_topics = std_author.openalex_topics or []
        talent.source_type = "openalex"
        talent.source_record_id = std_author.openalex_author_id

        # Update role profile
        await self._update_role_profile(talent, role_result)

    async def _create_talent(
        self,
        std_author: StdAuthor,
        role_result,
        school_id: int | None
    ) -> Talent:
        """Create new talent record"""
        new_talent = Talent(
            std_author_id=std_author.std_author_id,
            source_type="openalex",
            source_record_id=std_author.openalex_author_id,
            name=std_author.name_normalized,
            name_en=std_author.name_original,
            orcid=std_author.orcid,
            school_id=school_id,
            role_type=role_result.role_type,
            role_confidence=role_result.confidence,
            works_count=std_author.works_count or 0,
            cited_by_count=std_author.cited_by_count or 0,
            h_index=std_author.h_index or 0,
            openalex_topics=std_author.openalex_topics or [],
            visibility_status=VisibilityStatus.ACTIVE.value,
            is_visible=True,
        )

        self.session.add(new_talent)
        await self.session.flush()

        # Create role profile
        await self._create_role_profile(new_talent, role_result)

        return new_talent

    async def _create_role_profile(self, talent: Talent, role_result) -> RoleProfile:
        """Create role profile"""
        profile = RoleProfile(
            talent_id=talent.talent_id,
            role_type=role_result.role_type,
            role_confidence=role_result.confidence,
            role_reason=role_result.reason,
            identification_method="heuristic",
            identified_at=datetime.utcnow().isoformat(),
        )
        self.session.add(profile)
        await self.session.flush()
        return profile

    async def _update_role_profile(self, talent: Talent, role_result) -> RoleProfile | None:
        """Update role profile"""
        result = await self.session.execute(
            select(RoleProfile).where(RoleProfile.talent_id == talent.talent_id)
        )
        profile = result.scalar_one_or_none()

        if profile:
            profile.role_type = role_result.role_type
            profile.role_confidence = role_result.confidence
            profile.role_reason = role_result.reason
            profile.identification_method = "heuristic"
            profile.identified_at = datetime.utcnow().isoformat()
        else:
            profile = await self._create_role_profile(talent, role_result)

        return profile

    # ========================================
    # Bulk Operations (PostgreSQL optimized)
    # ========================================

    async def bulk_sync_authors(
        self,
        std_authors: list[StdAuthor],
        school_id_map: dict[str, int] | None = None,
    ) -> dict:
        """
        Bulk sync standardized authors to serving layer Talent table.

        Uses PostgreSQL INSERT ON CONFLICT for efficient bulk upsert.

        Args:
            std_authors: List of standardized author objects
            school_id_map: Optional mapping from openalex_institution_id to school_id

        Returns:
            dict: {
                "synced": int,      # Total processed (passed CS filter)
                "created": int,     # New records created
                "updated": int,     # Existing records updated
                "filtered": int,    # Filtered due to low CS score
                "new_talents": list # List of new talent dicts for work fetching
            }
        """
        result = {
            "synced": 0,
            "created": 0,
            "updated": 0,
            "filtered": 0,
            "new_talents": [],
        }

        if not std_authors:
            return result

        # Filter by CS score first
        eligible_authors = [
            a for a in std_authors
            if (a.cs_concepts_score or 0.0) >= CS_SCORE_THRESHOLD
        ]
        result["filtered"] = len(std_authors) - len(eligible_authors)

        if not eligible_authors:
            logger.info(f"[BULK_SYNC] All {len(std_authors)} authors filtered by CS score")
            return result

        logger.info(
            f"[BULK_SYNC] Processing {len(eligible_authors)} authors "
            f"({result['filtered']} filtered)"
        )

        # Use PostgreSQL bulk upsert
        return await self._bulk_upsert_postgres(eligible_authors, school_id_map, result)

    async def _bulk_upsert_postgres(
        self,
        std_authors: list[StdAuthor],
        school_id_map: dict[str, int] | None,
        result: dict,
    ) -> dict:
        """PostgreSQL-optimized bulk upsert using ON CONFLICT."""

        # Get existing talents in batches to avoid parameter limit
        author_ids = [a.openalex_author_id for a in std_authors]
        existing_map = {}

        # Process IN query in batches
        BATCH_SIZE = 5000
        for i in range(0, len(author_ids), BATCH_SIZE):
            batch_ids = author_ids[i:i + BATCH_SIZE]
            existing_result = await self.session.execute(
                select(Talent.source_record_id, Talent.talent_id).where(
                    Talent.source_record_id.in_(batch_ids)
                )
            )
            for row in existing_result.all():
                existing_map[row.source_record_id] = row.talent_id

        # Prepare bulk data
        now = datetime.utcnow().isoformat()
        talent_data = []
        profile_data = []

        for std_author in std_authors:
            # Get school ID
            school_id = None
            if school_id_map and std_author.school:
                school_id = school_id_map.get(std_author.school.openalex_institution_id)

            # Role identification
            role_result = RoleIdentifier.identify(
                works_count=std_author.works_count or 0,
                cited_by_count=std_author.cited_by_count or 0,
                h_index=std_author.h_index or 0
            )

            talent_dict = {
                "std_author_id": std_author.std_author_id,
                "source_type": "openalex",
                "source_record_id": std_author.openalex_author_id,
                "name": std_author.name_normalized,
                "name_en": std_author.name_original,
                "orcid": std_author.orcid,
                "school_id": school_id,
                "role_type": role_result.role_type,
                "role_confidence": role_result.confidence,
                "works_count": std_author.works_count or 0,
                "cited_by_count": std_author.cited_by_count or 0,
                "h_index": std_author.h_index or 0,
                "openalex_topics": std_author.openalex_topics or [],
                "visibility_status": VisibilityStatus.ACTIVE.value,
                "is_visible": True,
            }
            talent_data.append(talent_dict)

            # Track if this is a new talent
            is_new = std_author.openalex_author_id not in existing_map
            if is_new:
                result["created"] += 1
            else:
                result["updated"] += 1

        # Execute bulk upsert in batches (PostgreSQL has 32767 parameter limit)
        # Each talent has ~16 parameters, so batch size of 1000 is safe
        BATCH_SIZE = 1000
        for i in range(0, len(talent_data), BATCH_SIZE):
            batch = talent_data[i:i + BATCH_SIZE]
            stmt = pg_insert(Talent).values(batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=["source_record_id"],
                set_={
                    "name": stmt.excluded.name,
                    "name_en": stmt.excluded.name_en,
                    "orcid": stmt.excluded.orcid,
                    "std_author_id": stmt.excluded.std_author_id,
                    "school_id": stmt.excluded.school_id,
                    "role_type": stmt.excluded.role_type,
                    "role_confidence": stmt.excluded.role_confidence,
                    "works_count": stmt.excluded.works_count,
                    "cited_by_count": stmt.excluded.cited_by_count,
                    "h_index": stmt.excluded.h_index,
                    "openalex_topics": stmt.excluded.openalex_topics,
                    "updated_at": stmt.excluded.updated_at,
                }
            )
            await self.session.execute(stmt)
            logger.debug(f"[BULK_SYNC] Upserted batch {i // BATCH_SIZE + 1}: {len(batch)} records")

        result["synced"] = len(std_authors)

        # Bulk create role profiles (separate query for new talents)
        if result["created"] > 0:
            # Get newly created talent IDs in batches
            new_author_ids = [
                a.openalex_author_id for a in std_authors
                if a.openalex_author_id not in existing_map
            ]

            for i in range(0, len(new_author_ids), BATCH_SIZE):
                batch_ids = new_author_ids[i:i + BATCH_SIZE]
                new_result = await self.session.execute(
                    select(Talent.talent_id, Talent.source_record_id, Talent.role_type,
                           Talent.role_confidence).where(
                        Talent.source_record_id.in_(batch_ids)
                    )
                )

                for row in new_result.all():
                    # Get role reason from original author
                    author = next(
                        (a for a in std_authors if a.openalex_author_id == row.source_record_id),
                        None
                    )
                    if author:
                        role_result = RoleIdentifier.identify(
                            works_count=author.works_count or 0,
                            cited_by_count=author.cited_by_count or 0,
                            h_index=author.h_index or 0
                        )
                        profile_data.append({
                            "talent_id": row.talent_id,
                            "role_type": row.role_type,
                            "role_confidence": row.role_confidence,
                            "role_reason": role_result.reason,
                            "identification_method": "heuristic",
                            "identified_at": now,
                        })

                        # Track new professors for work fetching
                        if row.role_type == "professor":
                            result["new_talents"].append({
                                "talent_id": row.talent_id,
                                "openalex_author_id": row.source_record_id,
                                "works_count": author.works_count or 0 if author else 0,
                            })

            if profile_data:
                # Batch insert profiles as well
                for i in range(0, len(profile_data), BATCH_SIZE):
                    batch = profile_data[i:i + BATCH_SIZE]
                    profile_stmt = pg_insert(RoleProfile).values(batch)
                    profile_stmt = profile_stmt.on_conflict_do_update(
                        index_elements=["talent_id"],
                        set_={
                            "role_type": profile_stmt.excluded.role_type,
                            "role_confidence": profile_stmt.excluded.role_confidence,
                            "role_reason": profile_stmt.excluded.role_reason,
                            "identification_method": profile_stmt.excluded.identification_method,
                            "identified_at": profile_stmt.excluded.identified_at,
                        }
                    )
                    await self.session.execute(profile_stmt)

        logger.info(
            f"[BULK_SYNC] PostgreSQL upsert complete: "
            f"{result['created']} created, {result['updated']} updated"
        )

        return result
