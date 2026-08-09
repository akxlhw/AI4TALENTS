"""Industry position service — position CRUD business logic."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, NotFoundError
from app.domains.industry.constants.status_config import NULL_BATCH_SENTINEL, POSITION_STATUSES
from app.domains.industry.models.industry import IndustryPosition
from app.domains.industry.repositories.industry_repository import IndustryRepository
from app.domains.industry.schemas.industry import (
    IndustryPositionCreate,
    IndustryPositionResponse,
    IndustryPositionUpdate,
)


class IndustryPositionService:
    """Service for position lifecycle management (no physical delete)."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = IndustryRepository(session)

    @staticmethod
    def _to_response(
        position: IndustryPosition,
        candidate_count: int = 0,
        avg_match_score: float | None = None,
    ) -> IndustryPositionResponse:
        data = position.to_dict()
        data["candidate_count"] = candidate_count
        data["avg_match_score"] = round(avg_match_score, 2) if avg_match_score is not None else None
        return IndustryPositionResponse(**data)

    @staticmethod
    def _validate(data: dict[str, Any]) -> None:
        status = data.get("status")
        if status is not None and status not in POSITION_STATUSES:
            raise BadRequestError(
                f"invalid status: {status!r} (expected one of {POSITION_STATUSES})"
            )
        level_min = data.get("level_min")
        level_max = data.get("level_max")
        if level_min is not None and level_max is not None and level_min > level_max:
            raise BadRequestError("level_min must be <= level_max")

    async def create_position(
        self, data: IndustryPositionCreate, created_by: int | None
    ) -> IndustryPositionResponse:
        """Create a new position."""
        values = data.model_dump()
        self._validate(values)
        values["created_by"] = created_by
        position = await self.repo.create_position(values)
        await self.session.commit()
        return self._to_response(position)

    async def update_position(
        self, position_id: int, data: IndustryPositionUpdate
    ) -> IndustryPositionResponse:
        """Update a position, including status transitions (open/closed/archived)."""
        position = await self.repo.get_position(position_id)
        if position is None:
            raise NotFoundError("IndustryPosition", position_id)
        values = data.model_dump(exclude_unset=True)
        self._validate({**self._current_levels(position), **values})
        for field, value in values.items():
            setattr(position, field, value)
        await self.session.commit()
        await self.session.refresh(position)  # onupdate server value expired at flush
        count, avg = await self.repo.get_position_stats(position_id)
        return self._to_response(position, count, avg)

    @staticmethod
    def _current_levels(position: IndustryPosition) -> dict[str, Any]:
        return {"level_min": position.level_min, "level_max": position.level_max}

    async def get_position(self, position_id: int) -> IndustryPositionResponse:
        """Get one position with candidate aggregates."""
        position = await self.repo.get_position(position_id)
        if position is None:
            raise NotFoundError("IndustryPosition", position_id)
        count, avg = await self.repo.get_position_stats(position_id)
        return self._to_response(position, count, avg)

    async def list_positions(self, *, status: str | None = None) -> list[IndustryPositionResponse]:
        """List positions with candidate count and average match score."""
        if status is not None and status not in POSITION_STATUSES:
            raise BadRequestError(
                f"invalid status: {status!r} (expected one of {POSITION_STATUSES})"
            )
        rows = await self.repo.list_positions(status=status)
        return [self._to_response(position, count, avg) for position, count, avg in rows]

    async def list_batches(self, position_id: int) -> list[dict[str, Any]]:
        """List import batches for a position."""
        position = await self.repo.get_position(position_id)
        if position is None:
            raise NotFoundError("IndustryPosition", position_id)
        return await self.repo.list_batches(position_id)

    async def delete_batch(self, position_id: int, batch: str) -> dict[str, int]:
        """Delete all candidate links for a batch. Also cleans up orphan talents.

        ``batch`` may be the NULL_BATCH_SENTINEL to target rows imported
        without a batch identifier.
        """
        position = await self.repo.get_position(position_id)
        if position is None:
            raise NotFoundError("IndustryPosition", position_id)
        batch_value = None if batch == NULL_BATCH_SENTINEL else batch
        links_deleted, orphans_deleted = await self.repo.delete_batch(position_id, batch_value)
        await self.session.commit()
        return {"links_deleted": links_deleted, "talents_deleted": orphans_deleted}
