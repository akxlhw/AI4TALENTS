"""
Open Source — Developer, Repository, and Search endpoints.
"""

from __future__ import annotations

from typing import cast

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.open_source.api.auth import get_current_user
from app.domains.open_source.schemas.open_source import (
    OSContributionItem,
    OSDeveloperCompareRequest,
    OSDeveloperCompareResponse,
    OSDeveloperDetail,
    OSDeveloperSummary,
    OSLanguageSkillItem,
    OSRepoConfigResponse,
    OSRepositoryContributor,
    OSRepositoryDetailResponse,
    OSRepositoryItem,
    OSSearchRequest,
)
from app.domains.open_source.services.open_source_service import OpenSourceService
from app.domains.open_source.services.os_developer_exporter import OSDeveloperExporter
from app.domains.shared.api.auth import require_admin
from app.domains.shared.schemas.common import PaginatedResponse

router = APIRouter(prefix="/open-source", tags=["Open Source Talent"])


# ============= Developers =============


@router.get("/developers", response_model=PaginatedResponse[OSDeveloperSummary])
async def list_developers(
    q: str = Query("", description="Keyword search"),
    tech_elements: list[str] | None = Query(None),
    languages: list[str] | None = Query(None),
    location: str | None = Query(None),
    company: str | None = Query(None),
    min_stars: int | None = Query(None, ge=0),
    is_committer: bool | None = Query(None, description="Filter developers who are committers"),
    is_student: bool | None = Query(None, description="Filter developers who are students"),
    has_contact: bool | None = Query(
        None, description="Filter developers with valid contact info (homepage/email/social)"
    ),
    repo_full_names: list[str] | None = Query(None, description="Filter by repository full names"),
    sort_by: str = Query("stars_desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
) -> PaginatedResponse[OSDeveloperSummary]:
    service = OpenSourceService(session)
    items, total = await service.list_developers(
        q=q,
        tech_elements=tech_elements,
        languages=languages,
        location=location,
        company=company,
        min_stars=min_stars,
        is_committer=is_committer,
        is_student=is_student,
        has_contact=has_contact,
        repo_full_names=repo_full_names,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
    )

    # Enrich summaries with aggregated role tags from contributions (single batch query)
    dev_ids = [cast(int, dev.developer_id) for dev in items]
    roles_map = await service.get_developer_roles_map(dev_ids)
    summaries: list[OSDeveloperSummary] = []
    for dev, dev_id in zip(items, dev_ids, strict=True):
        summary = OSDeveloperSummary.model_validate(dev)
        summary.roles = roles_map.get(dev_id, [])
        summaries.append(summary)

    return PaginatedResponse.create(
        items=summaries,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/developers/ids", response_model=list[int])
async def list_all_developer_ids(
    q: str = Query("", description="Keyword search"),
    tech_elements: list[str] | None = Query(None),
    languages: list[str] | None = Query(None),
    location: str | None = Query(None),
    company: str | None = Query(None),
    min_stars: int | None = Query(None, ge=0),
    is_committer: bool | None = Query(None, description="Filter developers who are committers"),
    is_student: bool | None = Query(None, description="Filter developers who are students"),
    has_contact: bool | None = Query(
        None, description="Filter developers with valid contact info (homepage/email/social)"
    ),
    repo_full_names: list[str] | None = Query(None, description="Filter by repository full names"),
    sort_by: str = Query("stars_desc"),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
) -> list[int]:
    """Return all developer IDs matching the current filters (no pagination).
    Used for frontend 'select all' feature.
    """
    service = OpenSourceService(session)
    items, _total = await service.list_developers(
        q=q,
        tech_elements=tech_elements,
        languages=languages,
        location=location,
        company=company,
        min_stars=min_stars,
        is_committer=is_committer,
        is_student=is_student,
        has_contact=has_contact,
        repo_full_names=repo_full_names,
        sort_by=sort_by,
        page=1,
        page_size=100000,
    )
    return [cast(int, dev.developer_id) for dev in items]


@router.get("/developers/{developer_id}", response_model=OSDeveloperDetail)
async def get_developer(
    developer_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
) -> OSDeveloperDetail:
    service = OpenSourceService(session)
    return await service.get_developer_detail(developer_id)


@router.get(
    "/developers/{developer_id}/repositories", response_model=PaginatedResponse[OSRepositoryItem]
)
async def list_developer_repositories(
    developer_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("stars"),
    session: AsyncSession = Depends(get_async_session),
) -> PaginatedResponse[OSRepositoryItem]:
    service = OpenSourceService(session)
    items = await service.get_developer_repositories(developer_id)
    # Simple in-memory sort/paginate
    reverse = sort_by != "name"
    items = sorted(
        items,
        key=lambda r: getattr(
            r,
            (
                (sort_by.replace("_desc", "").replace("_asc", "") + "_count")
                if sort_by in ("stars", "forks")
                else "name"
            ),
        ),
        reverse=reverse,
    )
    total = len(items)
    start = (page - 1) * page_size
    items = items[start : start + page_size]
    return PaginatedResponse.create(
        items=[OSRepositoryItem.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/developers/{developer_id}/contributions", response_model=list[OSContributionItem])
async def list_developer_contributions(
    developer_id: int,
    session: AsyncSession = Depends(get_async_session),
) -> list[OSContributionItem]:
    service = OpenSourceService(session)
    result = await service.get_developer_contributions(developer_id)
    return [
        OSContributionItem(
            contribution_id=cast(int, c.contribution_id),
            repo_id=cast(int, c.repo_id),
            repo_full_name=full_name,
            commits_count=cast(int, c.commits_count),
            prs_count=cast(int, c.prs_count),
            issues_count=cast(int, c.issues_count),
            code_reviews_count=cast(int, c.code_reviews_count),
            is_owner=cast(bool, c.is_owner),
            is_maintainer=cast(bool, c.is_maintainer),
            is_committer=cast(bool, c.is_committer),
        )
        for c, full_name in result
    ]


@router.get("/developers/{developer_id}/languages", response_model=list[OSLanguageSkillItem])
async def list_developer_languages(
    developer_id: int,
    session: AsyncSession = Depends(get_async_session),
) -> list[OSLanguageSkillItem]:
    service = OpenSourceService(session)
    items = await service.get_developer_languages(developer_id)
    return [OSLanguageSkillItem.model_validate(i) for i in items]


@router.post("/developers/compare", response_model=OSDeveloperCompareRequest)
async def compare_developers(
    data: OSDeveloperCompareRequest,
    session: AsyncSession = Depends(get_async_session),
) -> OSDeveloperCompareResponse:
    service = OpenSourceService(session)
    return await service.compare_developers(data.developer_ids)


@router.get("/developers/{developer_id}/recommend", response_model=list[OSDeveloperSummary])
async def recommend_similar_developers(
    developer_id: int,
    limit: int = Query(10, ge=1, le=50),
    session: AsyncSession = Depends(get_async_session),
) -> list[OSDeveloperSummary]:
    service = OpenSourceService(session)
    items = await service.recommend_similar(developer_id, limit=limit)
    return [OSDeveloperSummary.model_validate(i) for i in items]


class ExportDevelopersRequest(BaseModel):
    developer_ids: list[int]
    format: str = "csv"


@router.post("/developers/export", response_model=None)
async def export_developers(
    data: ExportDevelopersRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_admin),
    request: Request = None,  # type: ignore[assignment]
) -> StreamingResponse:
    """Export selected developers to CSV or Excel format."""
    service = OpenSourceService(session)
    exporter = OSDeveloperExporter(service)
    return await exporter.export(
        developer_ids=data.developer_ids,
        fmt=data.format,
        current_user=current_user,
        request=request,
    )


# ============= Public Repository List =============


@router.get("/repositories", response_model=PaginatedResponse[OSRepoConfigResponse])
async def list_public_repositories(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tech_elements: list[str] | None = Query(None, description="Filter by tech elements"),
    q: str | None = Query(None, description="Search by repo name or description"),
    sort_by: str = Query("stars", description="stars | id_desc"),
    collected_only: bool = Query(True, description="Only repos with completed collect tasks"),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
) -> PaginatedResponse[OSRepoConfigResponse]:
    """List all public repositories (collected repo configs)."""
    service = OpenSourceService(session)
    items, total = await service.list_repo_configs(
        page=page,
        page_size=page_size,
        tech_elements=tech_elements,
        is_active=True,
        collect_enabled=None,
        sort_by=sort_by,
        collected_only=collected_only,
        q=q,
    )
    return PaginatedResponse.create(
        items=[OSRepoConfigResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


# ============= Repository (Project) Detail =============


@router.get("/repositories/{owner}/{name}", response_model=OSRepositoryDetailResponse)
async def get_repository(
    owner: str,
    name: str,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
) -> OSRepositoryDetailResponse:
    """Get repository detail with contributor count by full name."""
    service = OpenSourceService(session)
    return cast(OSRepositoryDetailResponse, await service.get_repository_detail(f"{owner}/{name}"))


@router.get(
    "/repositories/{owner}/{name}/contributors",
    response_model=PaginatedResponse[OSRepositoryContributor],
)
async def get_repository_contributors(
    owner: str,
    name: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
) -> PaginatedResponse[OSRepositoryContributor]:
    """Get contributors for a repository by full name."""
    service = OpenSourceService(session)
    items, total = await service.get_repository_contributors(f"{owner}/{name}", page, page_size)
    return PaginatedResponse.create(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


# ============= Search (v2 unified) =============


@router.post("/search", response_model=PaginatedResponse[OSDeveloperSummary])
async def search_developers(
    req: OSSearchRequest,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
) -> PaginatedResponse[OSDeveloperSummary]:
    """Unified search endpoint supporting keyword/semantic/hybrid modes."""
    service = OpenSourceService(session)
    items, total = await service.search_developers(req)
    return PaginatedResponse.create(
        items=[OSDeveloperSummary.model_validate(i) for i in items],
        total=total,
        page=req.page,
        page_size=req.page_size,
    )
