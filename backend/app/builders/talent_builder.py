"""
Talent object builder.
Transforms raw OpenAlex author data into Talent domain objects.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.builders.base import BaseBuilder, BuildResult, extract_openalex_id
from app.models.talent import Talent, RoleProfile, SelectedWork
from app.models.school import School
from app.models.enums import RoleType, VisibilityStatus
from app.models.sync import RawSourceRecord


logger = logging.getLogger(__name__)


class TalentBuilder(BaseBuilder):
    """
    Builder for Talent objects from OpenAlex author data.
    """

    def __init__(self, session: AsyncSession, batch_id: int):
        super().__init__(batch_id)
        self.session = session
        self._school_cache: Dict[str, int] = {}

    async def build(self) -> BuildResult:
        """
        Build Talent objects from raw author records.

        Process:
        1. Load pending author records
        2. Transform to Talent objects
        3. Create role profiles
        4. Mark records as processed

        Returns:
            BuildResult with statistics
        """
        started_at = datetime.now()
        records_processed = 0
        records_created = 0
        records_updated = 0
        records_failed = 0

        # Load pending author records
        result = await self.session.execute(
            select(RawSourceRecord)
            .where(
                RawSourceRecord.batch_id == self.batch_id,
                RawSourceRecord.source_type == "author",
                RawSourceRecord.processed_status == "pending",
            )
        )
        records = list(result.scalars().all())

        logger.info(f"Processing {len(records)} author records")

        for record in records:
            try:
                raw_data = record.raw_data
                source_id = extract_openalex_id(raw_data.get("id", ""))

                # Build talent object
                talent, is_new = await self._build_talent(raw_data, source_id)

                if talent:
                    # Create role profile
                    await self._create_role_profile(talent, raw_data)

                    # Create selected works
                    await self._create_selected_works(talent, raw_data)

                    if is_new:
                        records_created += 1
                    else:
                        records_updated += 1

                    # Mark record as processed
                    record.processed_status = "processed"
                    record.processed_at = datetime.now()

                records_processed += 1

                if records_processed % 50 == 0:
                    await self.session.commit()
                    logger.info(f"  Processed {records_processed} authors")

            except Exception as e:
                records_failed += 1
                self.log_error(str(e), record.source_id)
                record.processed_status = "error"
                record.error_info = str(e)

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

    async def _build_talent(
        self,
        raw_data: Dict[str, Any],
        source_id: str,
    ) -> tuple[Optional[Talent], bool]:
        """
        Build a Talent object from raw author data.

        Args:
            raw_data: Raw author data from OpenAlex
            source_id: OpenAlex author ID

        Returns:
            Tuple of (Talent object, is_new)
        """
        display_name = raw_data.get("display_name", "")
        if not display_name:
            return None, False

        # Get school affiliation
        school_id = await self._get_school_id(raw_data)

        # Check if talent already exists
        existing = await self._find_existing_talent(source_id)

        if existing:
            # Update existing talent
            existing.name = display_name
            existing.school_id = school_id
            existing.orcid = self._extract_orcid(raw_data.get("orcid"))
            existing.works_count = raw_data.get("works_count", 0)
            existing.cited_by_count = raw_data.get("cited_by_count", 0)
            existing.h_index = raw_data.get("summary_stats", {}).get("h_index", 0)
            existing.topic_tags = self._extract_topics(raw_data)
            existing.latest_active_year = self._extract_latest_year(raw_data)
            existing.role_type = self._identify_role_type(raw_data)
            existing.source_record_id = source_id
            existing.last_sync_batch_id = self.batch_id

            return existing, False

        # Create new talent
        talent = Talent(
            name=display_name,
            name_en=display_name,
            orcid=self._extract_orcid(raw_data.get("orcid")),
            school_id=school_id,
            current_title=None,
            role_type=self._identify_role_type(raw_data),
            role_confidence=0.0,
            topic_tags=self._extract_topics(raw_data),
            summary=self._build_summary(raw_data),
            works_count=raw_data.get("works_count", 0),
            cited_by_count=raw_data.get("cited_by_count", 0),
            h_index=raw_data.get("summary_stats", {}).get("h_index", 0),
            latest_active_year=self._extract_latest_year(raw_data),
            visibility_status=VisibilityStatus.ACTIVE.value,
            is_visible=True,
            source_type="openalex",
            source_record_id=source_id,
            last_sync_batch_id=self.batch_id,
        )

        self.session.add(talent)
        await self.session.flush()

        return talent, True

    async def _find_existing_talent(self, source_id: str) -> Optional[Talent]:
        """Find existing talent by source ID."""
        result = await self.session.execute(
            select(Talent).where(Talent.source_record_id == source_id)
        )
        return result.scalar_one_or_none()

    async def _get_school_id(self, raw_data: Dict[str, Any]) -> Optional[int]:
        """Get school ID from author's last known institution."""
        # OpenAlex now uses last_known_institutions (plural) or last_known_institution (singular)
        last_insts = raw_data.get("last_known_institutions") or []
        last_inst = raw_data.get("last_known_institution")

        # Prefer first from list, fallback to single
        if last_insts and len(last_insts) > 0:
            inst_data = last_insts[0]
            if isinstance(inst_data, dict):
                inst_id = extract_openalex_id(inst_data.get("id", ""))
            else:
                inst_id = extract_openalex_id(str(inst_data))
        elif last_inst:
            # Can be a dict or just an ID string
            if isinstance(last_inst, dict):
                inst_id = extract_openalex_id(last_inst.get("id", ""))
            else:
                inst_id = extract_openalex_id(str(last_inst))
        else:
            return None

        if not inst_id:
            return None

        # Check cache
        if inst_id in self._school_cache:
            return self._school_cache[inst_id]

        # Find school by source_record_id
        result = await self.session.execute(
            select(School.school_id).where(School.source_record_id == inst_id)
        )
        school_id = result.scalar_one_or_none()

        if school_id:
            self._school_cache[inst_id] = school_id

        return school_id

    def _identify_role_type(self, raw_data: Dict[str, Any]) -> str:
        """
        Identify role type based on author characteristics.

        Heuristics:
        - High works_count + high citations -> professor
        - Low works_count -> student
        - Medium works_count -> graduate/unknown
        """
        works_count = raw_data.get("works_count", 0)
        cited_by_count = raw_data.get("cited_by_count", 0)

        # Professor heuristics
        if works_count >= 30 and cited_by_count >= 500:
            return RoleType.PROFESSOR.value

        # Student heuristics
        if works_count < 5:
            return RoleType.STUDENT.value

        # Graduate heuristics
        if works_count >= 5 and works_count < 30:
            return RoleType.GRADUATED.value

        # Default to unknown
        return RoleType.UNKNOWN.value

    def _extract_orcid(self, orcid_url: Optional[str]) -> Optional[str]:
        """Extract ORCID ID from URL."""
        if not orcid_url:
            return None

        if "orcid.org" in orcid_url:
            return orcid_url.rstrip("/").split("/")[-1]

        return orcid_url

    def _extract_topics(self, raw_data: Dict[str, Any]) -> List[str]:
        """Extract research topics from author data."""
        topics = []

        # Get from x_concepts (OpenAlex concepts)
        concepts = raw_data.get("x_concepts", [])
        if isinstance(concepts, list):
            # Sort by score and take top 5
            sorted_concepts = sorted(
                concepts,
                key=lambda x: x.get("score", 0),
                reverse=True,
            )
            for concept in sorted_concepts[:5]:
                name = concept.get("display_name")
                if name:
                    topics.append(name)

        return topics

    def _extract_latest_year(self, raw_data: Dict[str, Any]) -> Optional[int]:
        """Extract latest active year from author data."""
        # Try to get from works API summary
        updated = raw_data.get("updated_date")
        if updated:
            try:
                return int(updated[:4])
            except (ValueError, TypeError):
                pass

        return None

    def _build_summary(self, raw_data: Dict[str, Any]) -> Optional[str]:
        """Build a brief summary for the talent."""
        parts = []

        if raw_data.get("works_count"):
            parts.append(f"{raw_data['works_count']} publications")

        if raw_data.get("cited_by_count"):
            parts.append(f"{raw_data['cited_by_count']} citations")

        topics = self._extract_topics(raw_data)
        if topics:
            parts.append(f"Research: {', '.join(topics[:3])}")

        return " | ".join(parts) if parts else None

    async def _create_role_profile(
        self,
        talent: Talent,
        raw_data: Dict[str, Any],
    ) -> None:
        """Create or update role profile for talent."""
        # Check if profile exists
        result = await self.session.execute(
            select(RoleProfile).where(RoleProfile.talent_id == talent.talent_id)
        )
        profile = result.scalar_one_or_none()

        role_type = self._identify_role_type(raw_data)
        confidence = self._calculate_role_confidence(raw_data, role_type)

        if profile:
            profile.role_type = role_type
            profile.role_confidence = confidence
            profile.role_reason = self._get_role_reason(raw_data, role_type)
        else:
            profile = RoleProfile(
                talent_id=talent.talent_id,
                role_type=role_type,
                role_confidence=confidence,
                role_reason=self._get_role_reason(raw_data, role_type),
                identification_method="heuristic",
                identified_at=datetime.now().isoformat(),
            )
            self.session.add(profile)

    def _calculate_role_confidence(
        self,
        raw_data: Dict[str, Any],
        role_type: str,
    ) -> float:
        """Calculate confidence score for role identification."""
        works_count = raw_data.get("works_count", 0)
        cited_by_count = raw_data.get("cited_by_count", 0)

        if role_type == RoleType.PROFESSOR.value:
            # High confidence if clear professor indicators
            if works_count >= 50 and cited_by_count >= 1000:
                return 0.9
            elif works_count >= 30 and cited_by_count >= 500:
                return 0.7
            return 0.5

        elif role_type == RoleType.STUDENT.value:
            if works_count <= 2:
                return 0.8
            return 0.6

        elif role_type == RoleType.GRADUATED.value:
            return 0.5

        return 0.3

    def _get_role_reason(
        self,
        raw_data: Dict[str, Any],
        role_type: str,
    ) -> str:
        """Get human-readable reason for role identification."""
        works_count = raw_data.get("works_count", 0)
        cited_by_count = raw_data.get("cited_by_count", 0)

        return f"Identified as {role_type} based on {works_count} works and {cited_by_count} citations"

    async def _create_selected_works(
        self,
        talent: Talent,
        raw_data: Dict[str, Any],
    ) -> None:
        """Create selected works for talent (placeholder - works come from separate API)."""
        # In a full implementation, this would fetch works from the works endpoint
        # For now, we just create a placeholder
        pass
