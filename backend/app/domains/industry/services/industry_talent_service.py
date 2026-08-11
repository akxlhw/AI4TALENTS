"""Industry talent service — list/detail/status business logic."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, NotFoundError
from app.domains.industry.constants.status_config import CANDIDATE_STATUSES
from app.domains.industry.models.industry import IndustryTalent
from app.domains.industry.repositories.industry_repository import IndustryRepository
from app.domains.industry.schemas.industry import (
    CandidateStatusPatch,
    IndustryPositionMatchDetail,
    IndustryTalentDetail,
    IndustryTalentSummary,
    PositionHit,
)

_SORT_KEYS = {"match_score_desc", "match_score_asc", "created_desc", "name_asc"}


class IndustryTalentService:
    """Service for browsing talents and managing recruiting state."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = IndustryRepository(session)

    async def list_talents(
        self,
        *,
        keyword: str | None = None,
        position_id: int | None = None,
        min_score: float | None = None,
        status: str | None = None,
        source_platform: str | None = None,
        tech_direction: str | None = None,
        sort_by: str = "match_score_desc",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[IndustryTalentSummary], int]:
        """List talents with filters. Returns (summaries, total)."""
        if sort_by not in _SORT_KEYS:
            raise BadRequestError(
                f"invalid sort_by: {sort_by!r} (expected one of {sorted(_SORT_KEYS)})"
            )
        if status is not None and status not in CANDIDATE_STATUSES:
            raise BadRequestError(
                f"invalid status: {status!r} (expected one of {CANDIDATE_STATUSES})"
            )
        rows, total = await self.repo.list_talents(
            keyword=keyword,
            position_id=position_id,
            min_score=min_score,
            status=status,
            source_platform=source_platform,
            tech_direction=tech_direction,
            sort_by=sort_by,
            page=page,
            page_size=page_size,
        )
        summaries = [
            self._to_summary(talent, best_score, hits) for talent, best_score, hits in rows
        ]
        return summaries, total

    @staticmethod
    def _to_summary(talent: IndustryTalent, best_score: Any, hits: Any) -> IndustryTalentSummary:
        positions = [PositionHit(**hit) for hit in (hits or [])]
        positions.sort(key=lambda h: (h.match_score is not None, h.match_score or 0), reverse=True)
        data = talent.to_summary_dict()
        data["best_match_score"] = round(best_score, 2) if best_score is not None else None
        data["positions"] = positions
        return IndustryTalentSummary(**data)

    async def get_talent_detail(self, talent_id: int) -> IndustryTalentDetail:
        """Full profile plus per-position match comparison."""
        talent = await self.repo.get_talent(talent_id)
        if talent is None:
            raise NotFoundError("IndustryTalent", talent_id)
        matches = await self._list_matches(talent_id)
        data = talent.to_detail_dict()
        data["best_match_score"] = max(
            (m.match_score for m in matches if m.match_score is not None),
            default=None,
        )
        data["positions"] = matches
        return IndustryTalentDetail(**data)

    async def get_talent_positions(self, talent_id: int) -> list[IndustryPositionMatchDetail]:
        """Which positions this talent matched, with per-position scores."""
        talent = await self.repo.get_talent(talent_id)
        if talent is None:
            raise NotFoundError("IndustryTalent", talent_id)
        return await self._list_matches(talent_id)

    async def _list_matches(self, talent_id: int) -> list[IndustryPositionMatchDetail]:
        rows = await self.repo.get_talent_links(talent_id)
        return [IndustryPositionMatchDetail(**link.to_match_dict(title)) for link, title in rows]

    async def patch_candidate_status(
        self, talent_id: int, position_id: int, patch: CandidateStatusPatch
    ) -> IndustryPositionMatchDetail:
        """Update recruiting state and/or scores on one link."""
        if patch.status is not None and patch.status not in CANDIDATE_STATUSES:
            raise BadRequestError(
                f"invalid status: {patch.status!r} (expected one of {CANDIDATE_STATUSES})"
            )
        link = await self.repo.get_link(talent_id, position_id)
        if link is None:
            raise NotFoundError("IndustryPositionTalent", f"{position_id}/{talent_id}")
        values = patch.model_dump(exclude_unset=True)
        for field, value in values.items():
            setattr(link, field, value)
        await self.session.commit()
        await self.session.refresh(link)  # onupdate server value expired at flush
        position = await self.repo.get_position(position_id)
        title = str(position.title) if position is not None else ""
        return IndustryPositionMatchDetail(**link.to_match_dict(title))

    async def remove_from_position(self, talent_id: int, position_id: int) -> tuple[bool, bool]:
        """Remove a talent from a position (delete the link).

        Returns (link_deleted, orphan_talent_deleted). Raises NotFoundError
        if the link does not exist.
        """
        link_deleted, orphan_deleted = await self.repo.delete_link(talent_id, position_id)
        if not link_deleted:
            raise NotFoundError("IndustryPositionTalent", f"{position_id}/{talent_id}")
        await self.session.commit()
        return link_deleted, orphan_deleted

    async def export_jsonl(self, position_id: int, batch: str | None = None) -> tuple[str, int]:
        """Export (position_id, batch) talents as JSONL for cross-server migration.

        Each line is a JSON object matching the import contract (the exact
        fields that ``IndustryImportService._upsert_talent`` and
        ``_upsert_link`` read). Operational state (touched/status/notes) is
        deliberately omitted — the importer preserves the target server's
        values, so exporting them would be misleading.

        Returns (jsonl_content, row_count). Caller raises 404 on row_count=0.
        """
        rows = await self.repo.list_for_export(position_id, batch)
        lines: list[str] = []
        for talent, link in rows:
            record: dict[str, Any] = {
                # talent profile fields (read by _upsert_talent)
                "name": talent.name,
                "current_org": talent.current_org,
                "current_title": talent.current_title,
                "degree": talent.degree,
                "years_of_exp": talent.years_of_exp,
                "experiences": talent.experiences,
                "expect": talent.expect,
                "location": talent.location,
                "profile_url": talent.profile_url,
                "photo_url": talent.photo_url,
                "source": talent.source,
                # link fields (read by _upsert_link)
                "position_id": link.position_id,
                "match_score": link.match_score,
                "score_school": link.score_school,
                "score_company": link.score_company,
                "score_direction": link.score_direction,
                "match_tags": link.match_tags,
                "match_reason": link.match_reason,
                "batch": link.batch,
            }
            lines.append(json.dumps(record, ensure_ascii=False))
        return "\n".join(lines), len(lines)
