"""
Open Source — Developer, Repository, and Search endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.domains.open_source.api.auth import get_current_user
from app.domains.open_source.schemas.open_source import (
    OSContributionItem,
    OSDeveloperCompareRequest,
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
    sort_by: str = Query("stars_desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    service = OpenSourceService(session)
    items, total = await service.list_developers(
        q=q,
        tech_elements=tech_elements,
        languages=languages,
        location=location,
        company=company,
        min_stars=min_stars,
        is_committer=is_committer,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
    )

    # Enrich each summary with aggregated role tags from contributions
    summaries: list[OSDeveloperSummary] = []
    for dev in items:
        summary = OSDeveloperSummary.model_validate(dev)
        contributions = await service.get_developer_contributions(dev.developer_id)
        role_set: set[str] = set()
        for c, _ in contributions:
            if c.is_owner:
                role_set.add("Owner")
            if c.is_committer:
                role_set.add("Committer")
        summary.roles = sorted(role_set)
        summaries.append(summary)

    return PaginatedResponse.create(
        items=summaries,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/developers/{developer_id}", response_model=OSDeveloperDetail)
async def get_developer(
    developer_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    service = OpenSourceService(session)
    return await service.get_developer_detail(developer_id)


@router.get("/developers/{developer_id}/repositories", response_model=PaginatedResponse[OSRepositoryItem])
async def list_developer_repositories(
    developer_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("stars"),
    session: AsyncSession = Depends(get_async_session),
):
    service = OpenSourceService(session)
    items = await service.get_developer_repositories(developer_id)
    # Simple in-memory sort/paginate
    reverse = sort_by != "name"
    items = sorted(
        items,
        key=lambda r: getattr(
            r,
            (sort_by.replace("_desc", "").replace("_asc", "") + "_count")
            if sort_by in ("stars", "forks")
            else "name",
        ),
        reverse=reverse,
    )
    total = len(items)
    start = (page - 1) * page_size
    items = items[start:start + page_size]
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
):
    service = OpenSourceService(session)
    result = await service.get_developer_contributions(developer_id)
    return [
        OSContributionItem(
            contribution_id=c.contribution_id,
            repo_id=c.repo_id,
            repo_full_name=full_name,
            commits_count=c.commits_count,
            prs_count=c.prs_count,
            issues_count=c.issues_count,
            code_reviews_count=c.code_reviews_count,
            is_owner=c.is_owner,
            is_maintainer=c.is_maintainer,
            is_committer=c.is_committer,
        )
        for c, full_name in result
    ]


@router.get("/developers/{developer_id}/languages", response_model=list[OSLanguageSkillItem])
async def list_developer_languages(
    developer_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    service = OpenSourceService(session)
    items = await service.get_developer_languages(developer_id)
    return [OSLanguageSkillItem.model_validate(i) for i in items]


@router.post("/developers/compare", response_model=OSDeveloperCompareRequest)
async def compare_developers(
    data: OSDeveloperCompareRequest,
    session: AsyncSession = Depends(get_async_session),
):
    service = OpenSourceService(session)
    return await service.compare_developers(data.developer_ids)


@router.get("/developers/{developer_id}/recommend", response_model=list[OSDeveloperSummary])
async def recommend_similar_developers(
    developer_id: int,
    limit: int = Query(10, ge=1, le=50),
    session: AsyncSession = Depends(get_async_session),
):
    service = OpenSourceService(session)
    items = await service.recommend_similar(developer_id, limit=limit)
    return [OSDeveloperSummary.model_validate(i) for i in items]


# ============= Public Repository List =============


@router.get("/repositories", response_model=PaginatedResponse[OSRepoConfigResponse])
async def list_public_repositories(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tech_element: str | None = Query(None),
    q: str | None = Query(None, description="Search by repo name or description"),
    sort_by: str = Query("stars", description="stars | id_desc"),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    """List all public repositories (collected repo configs)."""
    service = OpenSourceService(session)
    items, total = await service.list_repo_configs(
        page=page,
        page_size=page_size,
        tech_element=tech_element,
        is_active=True,
        collect_enabled=None,
        sort_by=sort_by,
        collected_only=True,
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
):
    """Get repository detail with contributor count by full name."""
    service = OpenSourceService(session)
    return await service.get_repository_detail(f"{owner}/{name}")


@router.get("/repositories/{owner}/{name}/contributors", response_model=PaginatedResponse[OSRepositoryContributor])
async def get_repository_contributors(
    owner: str,
    name: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
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
):
    """Unified search endpoint supporting keyword/semantic/hybrid modes."""
    service = OpenSourceService(session)
    items, total = await service.search_developers(req)
    return PaginatedResponse.create(
        items=[OSDeveloperSummary.model_validate(i) for i in items],
        total=total,
        page=req.page,
        page_size=req.page_size,
    )
