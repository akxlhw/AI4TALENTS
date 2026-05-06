"""
Open Source Talent API endpoints.

Architecture: Endpoint -> Service -> Repository
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import verify_access_token
from app.core.database import get_async_session
from app.domains.open_source.schemas.open_source import (
    OSCollectTaskCreate,
    OSCollectTaskResponse,
    OSContributionItem,
    OSDeveloperCompareRequest,
    OSDeveloperDetail,
    OSDeveloperSummary,
    OSEmbeddingGenerateRequest,
    OSEmbeddingStatusResponse,
    OSFavoriteCreate,
    OSFavoriteIdsResponse,
    OSFavoriteResponse,
    OSFavoriteUpdate,
    OSJDMatchRequest,
    OSJDMatchResponse,
    OSJDMatchResultItem,
    OSLanguageSkillItem,
    OSPoolMemberResponse,
    OSRepoConfigCreate,
    OSRepoConfigResponse,
    OSRepoConfigUpdate,
    OSRepositoryItem,
    OSSearchRequest,
    OSStatsResponse,
    OSTalentPoolCreate,
    OSTalentPoolResponse,
    OSTalentPoolUpdate,
)
from app.domains.open_source.services.open_source_service import OpenSourceService
from app.domains.shared.models.enums import UserRoleType
from app.domains.shared.schemas.common import PaginatedResponse, SuccessResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/open-source", tags=["Open Source Talent"])

# Constants moved to OpenSourceService


# ============= Auth helpers =============

async def get_current_user(
    authorization: str | None = Header(None, alias="Authorization"),
) -> dict:
    """Extract current user from Bearer token in Authorization header."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authentication required")
    token = authorization
    if token.startswith("Bearer "):
        token = token[7:]
    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload


async def require_admin(
    authorization: str | None = Header(None, alias="Authorization"),
) -> dict:
    user = await get_current_user(authorization)
    if user.get("role") not in (UserRoleType.ADMIN.value, UserRoleType.SUPER_ADMIN.value):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# ============= Repo Config =============

@router.get("/repo-configs", response_model=PaginatedResponse[OSRepoConfigResponse])
async def list_repo_configs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    tech_element: str | None = Query(None),
    is_active: bool | None = Query(None),
    collect_enabled: bool | None = Query(None),
    sort_by: str = Query("id_desc", description="id_desc | stars"),
    collected_only: bool = Query(False, description="Only repos with completed collect tasks"),
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(require_admin),
):
    service = OpenSourceService(session)
    items, total = await service.list_repo_configs(
        page=page,
        page_size=page_size,
        tech_element=tech_element,
        is_active=is_active,
        collect_enabled=collect_enabled,
        sort_by=sort_by,
        collected_only=collected_only,
    )
    return PaginatedResponse.create(
        items=[OSRepoConfigResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/repo-configs", response_model=OSRepoConfigResponse, status_code=201)
async def create_repo_config(
    data: OSRepoConfigCreate,
    session: AsyncSession = Depends(get_async_session),
    user: dict = Depends(require_admin),
):
    service = OpenSourceService(session)
    try:
        config = await service.create_repo_config(
            repo_full_name=data.repo_full_name,
            tech_element=data.tech_element,
            display_name=data.display_name,
            description=data.description,
            tech_direction_id=data.tech_direction_id,
            language=data.language,
            notes=data.notes,
            created_by=int(user.get("sub")) if user.get("sub") else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400 if "format" in str(e) or "tech_element" in str(e) else 409, detail=str(e)) from e
    return OSRepoConfigResponse.model_validate(config)


@router.get("/repo-configs/{repo_config_id}", response_model=OSRepoConfigResponse)
async def get_repo_config(
    repo_config_id: int,
    session: AsyncSession = Depends(get_async_session),
    _user: dict = Depends(require_admin),
):
    service = OpenSourceService(session)
    config = await service.get_repo_config(repo_config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Repo config not found")
    return OSRepoConfigResponse.model_validate(config)


@router.put("/repo-configs/{repo_config_id}", response_model=OSRepoConfigResponse)
async def update_repo_config(
    repo_config_id: int,
    data: OSRepoConfigUpdate,
    session: AsyncSession = Depends(get_async_session),
    _user: dict = Depends(require_admin),
):
    service = OpenSourceService(session)
    try:
        config = await service.update_repo_config(repo_config_id, data.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if not config:
        raise HTTPException(status_code=404, detail="Repo config not found")
    return OSRepoConfigResponse.model_validate(config)


@router.delete("/repo-configs/{repo_config_id}")
async def delete_repo_config(
    repo_config_id: int,
    session: AsyncSession = Depends(get_async_session),
    _user: dict = Depends(require_admin),
):
    service = OpenSourceService(session)
    success = await service.delete_repo_config(repo_config_id)
    if not success:
        raise HTTPException(status_code=404, detail="Repo config not found")
    return SuccessResponse(message="Deleted")


# ============= Repo Collection =============

CANCELLED_TASK_IDS: set[int] = set()


@router.post("/repo-configs/{repo_config_id}/collect", response_model=OSCollectTaskResponse)
async def collect_single_repo(
    repo_config_id: int,
    contributors_per_repo: int = Query(0, ge=0, le=2000),
    session: AsyncSession = Depends(get_async_session),
    user: dict = Depends(require_admin),
):
    """Start a background collection task for a single repository."""
    service = OpenSourceService(session)
    try:
        task, repo_full_name, tech_element = await service.collect_single_repo(
            repo_config_id=repo_config_id,
            contributors_per_repo=contributors_per_repo,
            created_by=int(user.get("sub", 0)),
        )
    except ValueError as e:
        status_code = 404 if "not found" in str(e).lower() else 400 if "disabled" in str(e).lower() else 409
        raise HTTPException(status_code=status_code, detail=str(e)) from e

    # Start background collection
    asyncio.create_task(
        service.run_repo_collection_background(
            task_id=task.task_id,
            repo_config_id=repo_config_id,
            repo_full_name=repo_full_name,
            tech_element=tech_element,
            contributors_per_repo=contributors_per_repo,
        )
    )
    return OSCollectTaskResponse.model_validate(task)


# ============= Developers =============

@router.get("/developers", response_model=PaginatedResponse[OSDeveloperSummary])
async def list_developers(
    q: str = Query("", description="Keyword search"),
    tech_elements: list[str] | None = Query(None),
    languages: list[str] | None = Query(None),
    location: str | None = Query(None),
    company: str | None = Query(None),
    min_stars: int | None = Query(None, ge=0),
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
        sort_by=sort_by,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse.create(
        items=[OSDeveloperSummary.model_validate(i) for i in items],
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
    try:
        return await service.get_developer_detail(developer_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


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
    try:
        result = await service.compare_developers(data.developer_ids)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/developers/{developer_id}/recommend", response_model=list[OSDeveloperSummary])
async def recommend_similar_developers(
    developer_id: int,
    limit: int = Query(10, ge=1, le=50),
    session: AsyncSession = Depends(get_async_session),
):
    service = OpenSourceService(session)
    items = await service.recommend_similar(developer_id, limit=limit)
    return [OSDeveloperSummary.model_validate(i) for i in items]


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


# ============= Favorites =============

@router.post("/favourites", response_model=OSFavoriteResponse)
async def add_favorite(
    data: OSFavoriteCreate,
    session: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_current_user),
):
    user_id = int(user.get("sub", 0))
    service = OpenSourceService(session)
    try:
        favorite = await service.add_favourite(user_id, data.developer_id, notes=data.notes)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    dev = await service.get_developer(data.developer_id)
    resp = OSFavoriteResponse.model_validate(favorite)
    resp.developer = OSDeveloperSummary.model_validate(dev) if dev else None
    return resp


@router.get("/favourites", response_model=PaginatedResponse[OSFavoriteResponse])
async def list_favorites(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = Query(None),
    session: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_current_user),
):
    user_id = int(user.get("sub", 0))
    service = OpenSourceService(session)
    favourites, total = await service.list_favourites(
        user_id=user_id, page=page, page_size=page_size, keyword=keyword
    )
    # Load developer details for each favourite
    dev_ids = [f.developer_id for f in favourites]
    developers = {d.developer_id: d for d in await service.get_developers_by_ids(dev_ids)}
    items = []
    for fav in favourites:
        resp = OSFavoriteResponse.model_validate(fav)
        dev = developers.get(fav.developer_id)
        resp.developer = OSDeveloperSummary.model_validate(dev) if dev else None
        items.append(resp)

    return PaginatedResponse.create(items=items, total=total, page=page, page_size=page_size)


@router.get("/favourites/ids", response_model=OSFavoriteIdsResponse)
async def get_favorite_ids(
    session: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_current_user),
):
    user_id = int(user.get("sub", 0))
    service = OpenSourceService(session)
    ids = await service.get_favourite_ids(user_id)
    return OSFavoriteIdsResponse(developer_ids=ids)


@router.put("/favourites/{developer_id}", response_model=OSFavoriteResponse)
async def update_favorite(
    developer_id: int,
    data: OSFavoriteUpdate,
    session: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_current_user),
):
    user_id = int(user.get("sub", 0))
    service = OpenSourceService(session)
    favourite = await service.update_favourite(
        user_id=user_id,
        developer_id=developer_id,
        notes=data.notes,
        followup_status=data.followup_status,
    )
    if not favourite:
        raise HTTPException(status_code=404, detail="Favorite not found")
    dev = await service.get_developer(developer_id)
    resp = OSFavoriteResponse.model_validate(favourite)
    resp.developer = OSDeveloperSummary.model_validate(dev) if dev else None
    return resp


@router.delete("/favourites/{developer_id}")
async def remove_favorite(
    developer_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_current_user),
):
    user_id = int(user.get("sub", 0))
    service = OpenSourceService(session)
    success = await service.remove_favourite(user_id, developer_id)
    if not success:
        raise HTTPException(status_code=404, detail="Favorite not found")
    return SuccessResponse(message="Removed from favorites")


# ============= Talent Pools =============

@router.get("/talent-pools", response_model=list[OSTalentPoolResponse])
async def list_talent_pools(
    session: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_current_user),
):
    user_id = int(user.get("sub", 0))
    service = OpenSourceService(session)
    pools = await service.list_talent_pools(user_id)
    return [OSTalentPoolResponse.model_validate(i) for i in pools]


@router.post("/talent-pools", response_model=OSTalentPoolResponse, status_code=201)
async def create_talent_pool(
    data: OSTalentPoolCreate,
    session: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_current_user),
):
    user_id = int(user.get("sub", 0))
    service = OpenSourceService(session)
    pool = await service.create_talent_pool(
        user_id=user_id,
        pool_name=data.pool_name,
        pool_type=data.pool_type,
        scope_desc=data.scope_desc,
    )
    return OSTalentPoolResponse.model_validate(pool)


@router.put("/talent-pools/{pool_id}", response_model=OSTalentPoolResponse)
async def update_talent_pool(
    pool_id: int,
    data: OSTalentPoolUpdate,
    session: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_current_user),
):
    user_id = int(user.get("sub", 0))
    service = OpenSourceService(session)
    # Verify ownership
    pool = await service.get_talent_pool(pool_id)
    if not pool or pool.owner_user_id != user_id:
        raise HTTPException(status_code=404, detail="Pool not found")

    updated = await service.update_talent_pool(pool_id, data.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Pool not found")
    return OSTalentPoolResponse.model_validate(updated)


@router.delete("/talent-pools/{pool_id}")
async def delete_talent_pool(
    pool_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_current_user),
):
    user_id = int(user.get("sub", 0))
    service = OpenSourceService(session)
    pool = await service.get_talent_pool(pool_id)
    if not pool or pool.owner_user_id != user_id:
        raise HTTPException(status_code=404, detail="Pool not found")
    success = await service.delete_talent_pool(pool_id)
    if not success:
        raise HTTPException(status_code=404, detail="Pool not found")
    return SuccessResponse(message="Deleted")


@router.post("/talent-pools/{pool_id}/members/{developer_id}")
async def add_pool_member(
    pool_id: int,
    developer_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_current_user),
):
    user_id = int(user.get("sub", 0))
    service = OpenSourceService(session)
    pool = await service.get_talent_pool(pool_id)
    if not pool or pool.owner_user_id != user_id:
        raise HTTPException(status_code=404, detail="Pool not found")

    try:
        await service.add_pool_member(pool_id, developer_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return SuccessResponse(message="Added to pool")


@router.delete("/talent-pools/{pool_id}/members/{developer_id}")
async def remove_pool_member(
    pool_id: int,
    developer_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_current_user),
):
    user_id = int(user.get("sub", 0))
    service = OpenSourceService(session)
    pool = await service.get_talent_pool(pool_id)
    if not pool or pool.owner_user_id != user_id:
        raise HTTPException(status_code=404, detail="Pool not found")

    success = await service.remove_pool_member(pool_id, developer_id)
    if not success:
        raise HTTPException(status_code=404, detail="Member not found")
    return SuccessResponse(message="Removed from pool")


@router.get("/talent-pools/{pool_id}/members", response_model=PaginatedResponse[OSPoolMemberResponse])
async def list_pool_members(
    pool_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_current_user),
):
    user_id = int(user.get("sub", 0))
    service = OpenSourceService(session)
    pool = await service.get_talent_pool(pool_id)
    if not pool or pool.owner_user_id != user_id:
        raise HTTPException(status_code=404, detail="Pool not found")

    members, total = await service.list_pool_members(pool_id, page=page, page_size=page_size)
    dev_ids = [m.developer_id for m in members]
    developers = {d.developer_id: d for d in await service.get_developers_by_ids(dev_ids)}
    items = []
    for member in members:
        resp = OSPoolMemberResponse.model_validate(member)
        dev = developers.get(member.developer_id)
        resp.developer = OSDeveloperSummary.model_validate(dev) if dev else None
        items.append(resp)

    return PaginatedResponse.create(items=items, total=total, page=page, page_size=page_size)


# ============= Collect Tasks =============

@router.get("/collect/tasks", response_model=PaginatedResponse[OSCollectTaskResponse])
async def list_collect_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
    _user: dict = Depends(require_admin),
):
    service = OpenSourceService(session)
    items, total = await service.list_collect_tasks(page=page, page_size=page_size)
    return PaginatedResponse.create(
        items=[OSCollectTaskResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/collect/tasks", response_model=OSCollectTaskResponse, status_code=201)
async def create_collect_task(
    data: OSCollectTaskCreate,
    session: AsyncSession = Depends(get_async_session),
    user: dict = Depends(require_admin),
):
    task_name = data.task_name or f"Collection_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    config_json = data.model_dump(exclude_unset=True)
    service = OpenSourceService(session)
    task = await service.create_collect_task(
        task_name=task_name,
        config_json=config_json,
        created_by=int(user.get("sub", 0)),
    )
    return OSCollectTaskResponse.model_validate(task)


@router.get("/collect/tasks/{task_id}", response_model=OSCollectTaskResponse)
async def get_collect_task(
    task_id: int,
    session: AsyncSession = Depends(get_async_session),
    _user: dict = Depends(require_admin),
):
    service = OpenSourceService(session)
    task = await service.get_collect_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return OSCollectTaskResponse.model_validate(task)


@router.post("/collect/tasks/{task_id}/cancel")
async def cancel_collect_task(
    task_id: int,
    session: AsyncSession = Depends(get_async_session),
    _user: dict = Depends(require_admin),
):
    service = OpenSourceService(session)
    try:
        task = await service.cancel_collect_task(task_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    CANCELLED_TASK_IDS.add(task_id)
    return SuccessResponse(message="Task cancelled")


@router.delete("/collect/tasks/{task_id}")
async def delete_collect_task(
    task_id: int,
    session: AsyncSession = Depends(get_async_session),
    _user: dict = Depends(require_admin),
):
    service = OpenSourceService(session)
    try:
        success = await service.delete_collect_task(task_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return SuccessResponse(message="Task deleted")


# ============= Stats =============

@router.get("/stats", response_model=OSStatsResponse)
async def get_stats(
    session: AsyncSession = Depends(get_async_session),
    current_user: dict = Depends(get_current_user),
):
    service = OpenSourceService(session)
    stats = await service.get_stats()
    return OSStatsResponse(**stats)


# ============= JD Match =============

@router.post("/jd-match", response_model=OSJDMatchResponse)
async def jd_match(
    data: OSJDMatchRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """JD matching. Returns keyword-based candidates."""
    service = OpenSourceService(session)
    result = await service.jd_match(
        jd_text=data.jd_text,
        filters=data.filters,
        top_k=data.top_k,
    )
    # Fallback to keyword search if service returns empty
    if not result.get("matches"):
        items, _ = await service.list_developers(
            q=data.jd_text[:50],
            page=1,
            page_size=data.top_k,
        )
        results = []
        for dev in items:
            score = min(95, 50 + (dev.total_stars_received // 100))
            results.append(
                OSJDMatchResultItem(
                    developer_id=dev.developer_id,
                    github_login=dev.github_login,
                    name=dev.name,
                    avatar_url=dev.avatar_url,
                    match_score=score,
                    tech_score=score + 5,
                    activity_score=score - 5,
                    reason=f"Strong open source contributor with {dev.total_stars_received} stars",
                )
            )
        return OSJDMatchResponse(
            results=results,
            total=len(results),
            query_summary=data.jd_text[:50] + "..." if len(data.jd_text) > 50 else data.jd_text,
        )
    return OSJDMatchResponse(**result)


# ============= Embeddings =============

_os_embedding_progress = {
    "status": "idle",
    "processed": 0,
    "total": 0,
    "failed": 0,
    "started_at": None,
    "completed_at": None,
    "error_message": None,
}


@router.get("/embeddings/status", response_model=OSEmbeddingStatusResponse)
async def get_embedding_status(
    session: AsyncSession = Depends(get_async_session),
    _user: dict = Depends(require_admin),
):
    service = OpenSourceService(session)
    status = await service.get_embedding_status_with_config()
    return OSEmbeddingStatusResponse(
        total_developers=status["total_developers"],
        embedded_count=status["embedded_count"],
        pending_count=status["pending_count"],
        progress_percent=status["progress_percent"],
        dimension=status["dimension"],
        model_name=status["model_name"],
    )


@router.post("/embeddings/generate")
async def generate_embeddings(
    req: OSEmbeddingGenerateRequest,
    session: AsyncSession = Depends(get_async_session),
    _user: dict = Depends(require_admin),
):
    """Trigger batch embedding generation for all visible developers."""
    global _os_embedding_progress

    if _os_embedding_progress["status"] == "running":
        raise HTTPException(status_code=400, detail="Embedding generation is already running")

    service = OpenSourceService(session)
    try:
        total = await service.trigger_batch_embedding(batch_size=req.batch_size, force=req.force)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    dev_ids = await service.get_visible_developer_ids()
    _os_embedding_progress["status"] = "running"
    _os_embedding_progress["processed"] = 0
    _os_embedding_progress["total"] = total
    _os_embedding_progress["failed"] = 0
    _os_embedding_progress["started_at"] = datetime.utcnow().isoformat()
    _os_embedding_progress["completed_at"] = None
    _os_embedding_progress["error_message"] = None

    asyncio.create_task(
        OpenSourceService.run_embedding_generation_background(
            developer_ids=dev_ids,
            batch_size=req.batch_size,
            force=req.force,
            progress_dict=_os_embedding_progress,
        )
    )

    return SuccessResponse(
        message=f"Embedding generation started for {total} developers"
    )


@router.get("/embeddings/progress")
async def get_embedding_progress(
    _user: dict = Depends(require_admin),
):
    """Get current embedding generation progress."""
    global _os_embedding_progress
    return {
        "status": _os_embedding_progress["status"],
        "processed": _os_embedding_progress["processed"],
        "total": _os_embedding_progress["total"],
        "failed": _os_embedding_progress["failed"],
        "started_at": _os_embedding_progress["started_at"],
        "completed_at": _os_embedding_progress["completed_at"],
        "error_message": _os_embedding_progress["error_message"],
    }


@router.post("/embeddings/cancel")
async def cancel_embedding_generation(
    _user: dict = Depends(require_admin),
):
    """Cancel running embedding generation."""
    global _os_embedding_progress

    if _os_embedding_progress["status"] != "running":
        raise HTTPException(status_code=400, detail="No generation task is running")

    _os_embedding_progress["status"] = "cancelled"
    _os_embedding_progress["completed_at"] = datetime.utcnow().isoformat()

    return SuccessResponse(message="Generation task cancelled")


@router.post("/embeddings/generate/{developer_id}")
async def generate_single_embedding(
    developer_id: int,
    session: AsyncSession = Depends(get_async_session),
    _user: dict = Depends(require_admin),
):
    service = OpenSourceService(session)
    dev = await service.get_developer(developer_id)
    if not dev:
        raise HTTPException(status_code=404, detail="Developer not found")

    try:
        await service.generate_single_embedding(developer_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Single embedding generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e

    return SuccessResponse(message=f"Embedding generated for developer {developer_id}")
