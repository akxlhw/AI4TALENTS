"""Lab talent browse endpoints — list/search and detail."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.lab.schemas.lab_talent import (
    LabProfileResponse,
    LabTalentDetail,
    LabTalentSummary,
    LabWithTalents,
)
from app.domains.lab.services.lab_talent_service import LabTalentService
from app.domains.shared.api.auth import get_current_user
from app.domains.shared.schemas.common import PaginatedResponse

router = APIRouter(prefix="/lab", tags=["AI Lab Talent"])


@router.get(
    "/talents",
    response_model=PaginatedResponse[LabTalentSummary],
    summary="Search and list lab talents",
)
async def list_lab_talents(
    keyword: str | None = Query(None, description="Name keyword (fuzzy)"),
    parent_lab: str | None = Query(None, description="Top-level lab filter"),
    lab_name: str | None = Query(None, description="Sub-lab filter"),
    role_type: str | None = Query(
        None, description="Role filter (professor/student/graduate/unknown)"
    ),
    academic_level: str | None = Query(
        None, description="Degree level filter (phd/master/bachelor, students only)"
    ),
    research_area: str | None = Query(
        None, description="Research area (substring match in JSON array)"
    ),
    cohort_year_gte: int | None = Query(
        None, ge=1900, le=2100, description="Cohort year lower bound"
    ),
    sort_by: str = Query(
        "created_desc",
        description="Sort key: name_asc | name_desc | cohort_desc | cohort_asc | created_desc | created_asc",
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
    _user: dict = Depends(get_current_user),
) -> PaginatedResponse[LabTalentSummary]:
    """List lab talents with filtering, sorting, and pagination."""
    service = LabTalentService(session)
    items, total = await service.list_talents(
        keyword=keyword,
        parent_lab=parent_lab,
        lab_name=lab_name,
        role_type=role_type,
        academic_level=academic_level,
        research_area=research_area,
        cohort_year_gte=cohort_year_gte,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse.create(items=items, total=total, page=page, page_size=page_size)


@router.get(
    "/labs",
    response_model=list[LabWithTalents],
    summary="List parent labs with talent previews",
)
async def list_lab_groups(
    session: AsyncSession = Depends(get_async_session),
    _user: dict = Depends(get_current_user),
) -> list[LabWithTalents]:
    """Return parent labs ordered by headcount, each with a preview of talents."""
    service = LabTalentService(session)
    return await service.list_labs(preview_limit=6)


@router.get(
    "/labs/{parent_lab}/profile",
    response_model=LabProfileResponse,
    summary="Get lab profile (metadata + aggregated stats)",
)
async def get_lab_profile(
    parent_lab: str,
    session: AsyncSession = Depends(get_async_session),
    _user: dict = Depends(get_current_user),
) -> LabProfileResponse:
    """Return lab-level metadata and aggregated role/sub-lab stats."""
    service = LabTalentService(session)
    return await service.get_lab_profile(parent_lab)


@router.get(
    "/talents/{talent_id}",
    response_model=LabTalentDetail,
    summary="Get lab talent detail",
)
async def get_lab_talent_detail(
    talent_id: int,
    session: AsyncSession = Depends(get_async_session),
    _user: dict = Depends(get_current_user),
) -> LabTalentDetail:
    """Get full detail for a single lab talent."""
    service = LabTalentService(session)
    return await service.get_talent_detail(talent_id)
