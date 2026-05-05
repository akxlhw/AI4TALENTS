"""
Open Source Talent API endpoints.

Architecture: Endpoint -> Service -> Repository
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import verify_access_token
from app.core.config import settings
from app.core.database import AsyncSessionLocal, get_async_session
from app.models.enums import UserRoleType
from app.models.open_source import (
    OSCollectTask,
    OSContribution,
    OSDeveloper,
    OSEmbedding,
    OSFavourite,
    OSLanguageSkill,
    OSPoolMember,
    OSRepoConfig,
    OSRepository,
    OSTalentPool,
)
from app.schemas.common import PaginatedResponse, SuccessResponse
from app.schemas.open_source import (
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
from app.services.open_source.collectors.github_collector import CollectContext, GitHubCollector
from app.services.open_source.github_client import GitHubClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/open-source", tags=["Open Source Talent"])

VALID_TECH_ELEMENTS = {"ai", "robotics", "data_science", "networks", "systems", "security"}
REPO_FULL_NAME_PATTERN = re.compile(r"^[\w.-]+/[\w.-]+$")


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
    conditions = []
    if tech_element:
        conditions.append(OSRepoConfig.tech_element == tech_element)
    if is_active is not None:
        conditions.append(OSRepoConfig.is_active == is_active)
    if collect_enabled is not None:
        conditions.append(OSRepoConfig.collect_enabled == collect_enabled)

    stmt = select(OSRepoConfig).where(and_(*conditions)) if conditions else select(OSRepoConfig)

    if collected_only:
        stmt = stmt.where(
            select(OSCollectTask)
            .where(
                OSCollectTask.task_name == OSRepoConfig.repo_full_name,
                OSCollectTask.status == "completed",
            )
            .exists()
        )

    total = await session.scalar(select(func.count()).select_from(stmt.subquery()))

    if sort_by == "stars":
        stmt = stmt.order_by(OSRepoConfig.stars_count.desc().nullslast())
    else:
        stmt = stmt.order_by(OSRepoConfig.repo_config_id.desc())

    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(stmt)
    items = result.scalars().all()

    return PaginatedResponse.create(
        items=[OSRepoConfigResponse.model_validate(i) for i in items],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.post("/repo-configs", response_model=OSRepoConfigResponse, status_code=201)
async def create_repo_config(
    data: OSRepoConfigCreate,
    session: AsyncSession = Depends(get_async_session),
    user: dict = Depends(require_admin),
):
    if not REPO_FULL_NAME_PATTERN.match(data.repo_full_name):
        raise HTTPException(status_code=400, detail="Invalid repo_full_name format. Expected 'owner/repo'")
    if data.tech_element not in VALID_TECH_ELEMENTS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid tech_element: {data.tech_element}. Must be one of: {', '.join(sorted(VALID_TECH_ELEMENTS))}",
        )
    existing = await session.scalar(select(OSRepoConfig).where(OSRepoConfig.repo_full_name == data.repo_full_name))
    if existing:
        raise HTTPException(status_code=409, detail=f"Repository '{data.repo_full_name}' already exists")

    # Fetch live stars from GitHub
    from app.services.config_service import ConfigService
    config_service = ConfigService(session)
    github_config = await config_service.get_github_config()
    token = github_config.tokens if github_config.tokens else None
    stars_count = 0
    try:
        async with GitHubClient(token=token) as client:
            owner, repo_name = data.repo_full_name.split("/", 1)
            repo_info = await client.get_repo(owner, repo_name)
            stars_count = repo_info.get("stargazers_count", 0) or 0
    except Exception as e:
        logger.warning(f"Failed to fetch stars for {data.repo_full_name}: {e}")

    config = OSRepoConfig(
        repo_full_name=data.repo_full_name,
        display_name=data.display_name or data.repo_full_name.split("/")[-1],
        description=data.description,
        tech_element=data.tech_element,
        tech_direction_id=data.tech_direction_id,
        language=data.language,
        stars_count=stars_count,
        notes=data.notes,
        created_by=int(user.get("sub")) if user.get("sub") else None,
    )
    session.add(config)
    await session.commit()
    await session.refresh(config)
    return OSRepoConfigResponse.model_validate(config)


@router.get("/repo-configs/{repo_config_id}", response_model=OSRepoConfigResponse)
async def get_repo_config(
    repo_config_id: int,
    session: AsyncSession = Depends(get_async_session),
    _user: dict = Depends(require_admin),
):
    config = await session.get(OSRepoConfig, repo_config_id)
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
    config = await session.get(OSRepoConfig, repo_config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Repo config not found")

    update_data = data.model_dump(exclude_unset=True)
    if "tech_element" in update_data and update_data["tech_element"] not in VALID_TECH_ELEMENTS:
        raise HTTPException(status_code=400, detail="Invalid tech_element")

    for field, value in update_data.items():
        setattr(config, field, value)

    await session.commit()
    await session.refresh(config)
    return OSRepoConfigResponse.model_validate(config)


@router.delete("/repo-configs/{repo_config_id}")
async def delete_repo_config(
    repo_config_id: int,
    session: AsyncSession = Depends(get_async_session),
    _user: dict = Depends(require_admin),
):
    config = await session.get(OSRepoConfig, repo_config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Repo config not found")
    await session.delete(config)
    await session.commit()
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
    config = await session.get(OSRepoConfig, repo_config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Repo config not found")
    if not config.collect_enabled:
        raise HTTPException(status_code=400, detail="Repository collection is disabled")

    # Check if there's already a running task for this repo
    stmt = select(OSCollectTask).where(
        OSCollectTask.task_name == config.repo_full_name,
        OSCollectTask.status.in_(["pending", "running"]),
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="A collection task is already running for this repository")

    task = OSCollectTask(
        task_name=config.repo_full_name,
        status="pending",
        config_json={
            "repo_config_id": repo_config_id,
            "repo_full_name": config.repo_full_name,
            "tech_element": config.tech_element,
            "contributors_per_repo": contributors_per_repo,
        },
        created_by=int(user.get("sub", 0)),
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)

    # Start background collection
    asyncio.create_task(
        run_os_repo_collect_background(
            task_id=task.task_id,
            repo_config_id=repo_config_id,
            repo_full_name=config.repo_full_name,
            tech_element=config.tech_element,
            contributors_per_repo=contributors_per_repo,
        )
    )
    return OSCollectTaskResponse.model_validate(task)


async def run_os_repo_collect_background(
    task_id: int,
    repo_config_id: int,
    repo_full_name: str,
    tech_element: str,
    contributors_per_repo: int,
) -> None:
    """Run single-repo collection in background."""
    try:
        async with AsyncSessionLocal() as session:
            task = await session.get(OSCollectTask, task_id)
            if not task or task.status != "pending":
                return
            task.status = "running"
            task.started_at = datetime.utcnow()
            await session.commit()

            # Load GitHub token from database config (frontend-configured)
            from app.services.config_service import ConfigService

            config_service = ConfigService(session)
            github_config = await config_service.get_github_config()
            token = github_config.tokens if github_config.tokens else None

        ctx = CollectContext(
            task_id=task_id,
            repo_config_id=repo_config_id,
            repo_full_name=repo_full_name,
            tech_element=tech_element,
            contributors_per_repo=contributors_per_repo,
        )

        async with GitHubClient(token=token) as client:
            collector = GitHubCollector(client)
            await collector.collect(ctx)

    except asyncio.CancelledError:
        logger.info(f"Task {task_id} cancelled")
        async with AsyncSessionLocal() as session:
            task = await session.get(OSCollectTask, task_id)
            if task:
                task.status = "cancelled"
                await session.commit()
    except Exception as e:
        logger.exception(f"Task {task_id} failed: {e}")
        async with AsyncSessionLocal() as session:
            task = await session.get(OSCollectTask, task_id)
            if task:
                task.status = "failed"
                task.error_message = str(e)[:500]
                await session.commit()
    finally:
        CANCELLED_TASK_IDS.discard(task_id)


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
    conditions = [OSDeveloper.is_visible == True]
    if q:
        pattern = f"%{q}%"
        conditions.append(
            or_(
                OSDeveloper.name.ilike(pattern),
                OSDeveloper.bio.ilike(pattern),
                OSDeveloper.company.ilike(pattern),
                OSDeveloper.location.ilike(pattern),
                OSDeveloper.github_login.ilike(pattern),
            )
        )
    if tech_elements:
        conditions.append(OSDeveloper.tech_tags.overlap(tech_elements))
    if languages:
        conditions.append(OSDeveloper.primary_languages.overlap(languages))
    if location:
        conditions.append(OSDeveloper.location.ilike(f"%{location}%"))
    if company:
        conditions.append(OSDeveloper.company.ilike(f"%{company}%"))
    if min_stars is not None:
        conditions.append(OSDeveloper.total_stars_received >= min_stars)

    stmt = select(OSDeveloper).where(and_(*conditions))
    order_map = {
        "stars_desc": OSDeveloper.total_stars_received.desc(),
        "stars_asc": OSDeveloper.total_stars_received.asc(),
        "name_asc": OSDeveloper.name.asc(),
    }
    stmt = stmt.order_by(order_map.get(sort_by, OSDeveloper.total_stars_received.desc()))

    total = await session.scalar(select(func.count()).select_from(stmt.subquery()))
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(stmt)
    items = result.scalars().all()

    return PaginatedResponse.create(
        items=[OSDeveloperSummary.model_validate(i) for i in items],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.get("/developers/{developer_id}", response_model=OSDeveloperDetail)
async def get_developer(
    developer_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    dev = await session.get(OSDeveloper, developer_id)
    if not dev or not dev.is_visible:
        raise HTTPException(status_code=404, detail="Developer not found")

    # Load related data in parallel
    repos_task = session.execute(
        select(OSRepository).where(OSRepository.developer_id == developer_id).order_by(OSRepository.stars_count.desc())
    )
    contributions_task = session.execute(
        select(OSContribution, OSRepository.full_name)
        .join(OSRepository, OSContribution.repo_id == OSRepository.repo_id)
        .where(OSContribution.developer_id == developer_id)
    )
    languages_task = session.execute(
        select(OSLanguageSkill)
        .where(OSLanguageSkill.developer_id == developer_id)
        .order_by(OSLanguageSkill.proficiency_score.desc())
    )
    similar_task = session.execute(
        select(OSDeveloper)
        .where(OSDeveloper.developer_id != developer_id, OSDeveloper.is_visible == True)
        .order_by(func.random())
        .limit(5)
    )

    repos_result, contributions_result, languages_result, similar_result = await asyncio.gather(
        repos_task, contributions_task, languages_task, similar_task
    )

    repositories = [OSRepositoryItem.model_validate(r) for r in repos_result.scalars().all()]
    contributions = [
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
        for c, full_name in contributions_result.all()
    ]
    language_skills = [OSLanguageSkillItem.model_validate(l) for l in languages_result.scalars().all()]
    similar_developers = [OSDeveloperSummary.model_validate(s) for s in similar_result.scalars().all()]

    detail = OSDeveloperDetail(
        **OSDeveloperSummary.model_validate(dev).model_dump(),
        github_id=dev.github_id,
        blog_url=dev.blog_url,
        email=dev.email,
        followers_count=dev.followers_count,
        following_count=dev.following_count,
        public_repos_count=dev.public_repos_count,
        total_forks_received=dev.total_forks_received,
        repositories=repositories,
        contributions=contributions,
        language_skills=language_skills,
        similar_developers=similar_developers,
    )
    return detail


@router.get("/developers/{developer_id}/repositories", response_model=PaginatedResponse[OSRepositoryItem])
async def list_developer_repositories(
    developer_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("stars"),
    session: AsyncSession = Depends(get_async_session),
):
    order_map = {
        "stars": OSRepository.stars_count.desc(),
        "forks": OSRepository.forks_count.desc(),
        "name": OSRepository.name.asc(),
    }
    stmt = (
        select(OSRepository)
        .where(OSRepository.developer_id == developer_id)
        .order_by(order_map.get(sort_by, OSRepository.stars_count.desc()))
    )
    total = await session.scalar(select(func.count()).select_from(stmt.subquery()))
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(stmt)
    items = result.scalars().all()
    return PaginatedResponse.create(
        items=[OSRepositoryItem.model_validate(i) for i in items],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.get("/developers/{developer_id}/contributions", response_model=list[OSContributionItem])
async def list_developer_contributions(
    developer_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(
        select(OSContribution, OSRepository.full_name)
        .join(OSRepository, OSContribution.repo_id == OSRepository.repo_id)
        .where(OSContribution.developer_id == developer_id)
    )
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
        for c, full_name in result.all()
    ]


@router.get("/developers/{developer_id}/languages", response_model=list[OSLanguageSkillItem])
async def list_developer_languages(
    developer_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(
        select(OSLanguageSkill)
        .where(OSLanguageSkill.developer_id == developer_id)
        .order_by(OSLanguageSkill.proficiency_score.desc())
    )
    return [OSLanguageSkillItem.model_validate(i) for i in result.scalars().all()]


@router.post("/developers/compare", response_model=OSDeveloperCompareRequest)
async def compare_developers(
    data: OSDeveloperCompareRequest,
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(select(OSDeveloper).where(OSDeveloper.developer_id.in_(data.developer_ids)))
    developers = result.scalars().all()
    if len(developers) != len(data.developer_ids):
        raise HTTPException(status_code=404, detail="Some developers not found")

    # Build radar comparison data
    dimensions = {
        "stars": "Total Stars Received",
        "forks": "Total Forks Received",
        "repos": "Public Repositories",
        "followers": "Followers",
        "languages": "Language Diversity",
    }

    def _metric(dev: OSDeveloper, key: str) -> float:
        return {
            "stars": dev.total_stars_received,
            "forks": dev.total_forks_received,
            "repos": dev.public_repos_count,
            "followers": dev.followers_count,
            "languages": len(dev.primary_languages or []),
        }.get(key, 0)

    radar = {}
    for dim_key, dim_label in dimensions.items():
        values = [_metric(dev, dim_key) for dev in developers]
        max_val = max(values) if max(values) > 0 else 1
        radar[dim_key] = {
            "label": dim_label,
            "values": [v / max_val * 100 for v in values],
            "raw_values": values,
        }

    # Return using compatible structure; full compare response can be expanded later
    return OSDeveloperCompareRequest(developer_ids=data.developer_ids)


@router.get("/developers/{developer_id}/recommend", response_model=list[OSDeveloperSummary])
async def recommend_similar_developers(
    developer_id: int,
    limit: int = Query(10, ge=1, le=50),
    session: AsyncSession = Depends(get_async_session),
):
    # TODO: use os_embedding for vector similarity
    result = await session.execute(
        select(OSDeveloper)
        .where(OSDeveloper.developer_id != developer_id, OSDeveloper.is_visible == True)
        .order_by(func.random())
        .limit(limit)
    )
    return [OSDeveloperSummary.model_validate(i) for i in result.scalars().all()]


# ============= Search (v2 unified) =============

@router.post("/search", response_model=PaginatedResponse[OSDeveloperSummary])
async def search_developers(
    req: OSSearchRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """Unified search endpoint supporting keyword/semantic/hybrid modes."""
    # Keyword search; semantic/hybrid to be enhanced with embedding service
    conditions = [OSDeveloper.is_visible == True]
    if req.q:
        pattern = f"%{req.q}%"
        conditions.append(
            or_(
                OSDeveloper.name.ilike(pattern),
                OSDeveloper.bio.ilike(pattern),
                OSDeveloper.company.ilike(pattern),
                OSDeveloper.location.ilike(pattern),
                OSDeveloper.github_login.ilike(pattern),
            )
        )
    if req.filters:
        if req.filters.tech_elements:
            conditions.append(OSDeveloper.tech_tags.overlap(req.filters.tech_elements))
        if req.filters.languages:
            conditions.append(OSDeveloper.primary_languages.overlap(req.filters.languages))
        if req.filters.location:
            conditions.append(OSDeveloper.location.ilike(f"%{req.filters.location}%"))
        if req.filters.company:
            conditions.append(OSDeveloper.company.ilike(f"%{req.filters.company}%"))
        if req.filters.min_stars is not None:
            conditions.append(OSDeveloper.total_stars_received >= req.filters.min_stars)

    stmt = select(OSDeveloper).where(and_(*conditions))
    order_map = {
        "stars_desc": OSDeveloper.total_stars_received.desc(),
        "stars_asc": OSDeveloper.total_stars_received.asc(),
        "name_asc": OSDeveloper.name.asc(),
    }
    stmt = stmt.order_by(order_map.get(req.sort_by, OSDeveloper.total_stars_received.desc()))

    total = await session.scalar(select(func.count()).select_from(stmt.subquery()))
    stmt = stmt.offset((req.page - 1) * req.page_size).limit(req.page_size)
    result = await session.execute(stmt)
    items = result.scalars().all()

    return PaginatedResponse.create(
        items=[OSDeveloperSummary.model_validate(i) for i in items],
        total=total or 0,
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
    existing = await session.scalar(
        select(OSFavourite).where(
            OSFavourite.user_id == user_id, OSFavourite.developer_id == data.developer_id
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="Already favorited")

    favorite = OSFavourite(
        user_id=user_id,
        developer_id=data.developer_id,
        notes=data.notes,
    )
    session.add(favorite)
    await session.commit()
    await session.refresh(favorite)

    dev = await session.get(OSDeveloper, data.developer_id)
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
    stmt = select(OSFavourite, OSDeveloper).join(
        OSDeveloper, OSFavourite.developer_id == OSDeveloper.developer_id
    ).where(OSFavourite.user_id == user_id, OSFavourite.is_active == True)

    if keyword:
        pattern = f"%{keyword}%"
        stmt = stmt.where(
            or_(
                OSDeveloper.name.ilike(pattern),
                OSDeveloper.github_login.ilike(pattern),
            )
        )

    total = await session.scalar(select(func.count()).select_from(stmt.subquery()))
    stmt = stmt.order_by(OSFavourite.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(stmt)

    items = []
    for fav, dev in result.all():
        resp = OSFavoriteResponse.model_validate(fav)
        resp.developer = OSDeveloperSummary.model_validate(dev) if dev else None
        items.append(resp)

    return PaginatedResponse.create(items=items, total=total or 0, page=page, page_size=page_size)


@router.get("/favourites/ids", response_model=OSFavoriteIdsResponse)
async def get_favorite_ids(
    session: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_current_user),
):
    user_id = int(user.get("sub", 0))
    result = await session.execute(
        select(OSFavourite.developer_id).where(
            OSFavourite.user_id == user_id, OSFavourite.is_active == True
        )
    )
    return OSFavoriteIdsResponse(developer_ids=[r for r in result.scalars().all()])


@router.put("/favourites/{developer_id}", response_model=OSFavoriteResponse)
async def update_favorite(
    developer_id: int,
    data: OSFavoriteUpdate,
    session: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_current_user),
):
    user_id = int(user.get("sub", 0))
    favorite = await session.scalar(
        select(OSFavourite).where(
            OSFavourite.user_id == user_id, OSFavourite.developer_id == developer_id
        )
    )
    if not favorite:
        raise HTTPException(status_code=404, detail="Favorite not found")

    if data.notes is not None:
        favorite.notes = data.notes
    if data.followup_status is not None:
        favorite.followup_status = data.followup_status

    await session.commit()
    await session.refresh(favorite)
    dev = await session.get(OSDeveloper, developer_id)
    resp = OSFavoriteResponse.model_validate(favorite)
    resp.developer = OSDeveloperSummary.model_validate(dev) if dev else None
    return resp


@router.delete("/favourites/{developer_id}")
async def remove_favorite(
    developer_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_current_user),
):
    user_id = int(user.get("sub", 0))
    favorite = await session.scalar(
        select(OSFavourite).where(
            OSFavourite.user_id == user_id, OSFavourite.developer_id == developer_id
        )
    )
    if not favorite:
        raise HTTPException(status_code=404, detail="Favorite not found")

    favorite.is_active = False
    await session.commit()
    return SuccessResponse(message="Removed from favorites")


# ============= Talent Pools =============

@router.get("/talent-pools", response_model=list[OSTalentPoolResponse])
async def list_talent_pools(
    session: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_current_user),
):
    user_id = int(user.get("sub", 0))
    result = await session.execute(
        select(OSTalentPool).where(OSTalentPool.owner_user_id == user_id).order_by(OSTalentPool.created_at.desc())
    )
    return [OSTalentPoolResponse.model_validate(i) for i in result.scalars().all()]


@router.post("/talent-pools", response_model=OSTalentPoolResponse, status_code=201)
async def create_talent_pool(
    data: OSTalentPoolCreate,
    session: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_current_user),
):
    user_id = int(user.get("sub", 0))
    pool = OSTalentPool(
        owner_user_id=user_id,
        pool_name=data.pool_name,
        pool_type=data.pool_type,
        scope_desc=data.scope_desc,
    )
    session.add(pool)
    await session.commit()
    await session.refresh(pool)
    return OSTalentPoolResponse.model_validate(pool)


@router.put("/talent-pools/{pool_id}", response_model=OSTalentPoolResponse)
async def update_talent_pool(
    pool_id: int,
    data: OSTalentPoolUpdate,
    session: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_current_user),
):
    user_id = int(user.get("sub", 0))
    pool = await session.get(OSTalentPool, pool_id)
    if not pool or pool.owner_user_id != user_id:
        raise HTTPException(status_code=404, detail="Pool not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(pool, field, value)
    await session.commit()
    await session.refresh(pool)
    return OSTalentPoolResponse.model_validate(pool)


@router.delete("/talent-pools/{pool_id}")
async def delete_talent_pool(
    pool_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_current_user),
):
    user_id = int(user.get("sub", 0))
    pool = await session.get(OSTalentPool, pool_id)
    if not pool or pool.owner_user_id != user_id:
        raise HTTPException(status_code=404, detail="Pool not found")
    await session.delete(pool)
    await session.commit()
    return SuccessResponse(message="Deleted")


@router.post("/talent-pools/{pool_id}/members/{developer_id}")
async def add_pool_member(
    pool_id: int,
    developer_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_current_user),
):
    user_id = int(user.get("sub", 0))
    pool = await session.get(OSTalentPool, pool_id)
    if not pool or pool.owner_user_id != user_id:
        raise HTTPException(status_code=404, detail="Pool not found")

    existing = await session.scalar(
        select(OSPoolMember).where(
            OSPoolMember.pool_id == pool_id, OSPoolMember.developer_id == developer_id
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="Already in pool")

    member = OSPoolMember(pool_id=pool_id, developer_id=developer_id)
    session.add(member)
    await session.commit()
    return SuccessResponse(message="Added to pool")


@router.delete("/talent-pools/{pool_id}/members/{developer_id}")
async def remove_pool_member(
    pool_id: int,
    developer_id: int,
    session: AsyncSession = Depends(get_async_session),
    user: dict = Depends(get_current_user),
):
    user_id = int(user.get("sub", 0))
    pool = await session.get(OSTalentPool, pool_id)
    if not pool or pool.owner_user_id != user_id:
        raise HTTPException(status_code=404, detail="Pool not found")

    member = await session.scalar(
        select(OSPoolMember).where(
            OSPoolMember.pool_id == pool_id, OSPoolMember.developer_id == developer_id
        )
    )
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    await session.delete(member)
    await session.commit()
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
    pool = await session.get(OSTalentPool, pool_id)
    if not pool or pool.owner_user_id != user_id:
        raise HTTPException(status_code=404, detail="Pool not found")

    stmt = (
        select(OSPoolMember, OSDeveloper)
        .join(OSDeveloper, OSPoolMember.developer_id == OSDeveloper.developer_id)
        .where(OSPoolMember.pool_id == pool_id)
    )
    total = await session.scalar(select(func.count()).select_from(stmt.subquery()))
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(stmt)

    items = []
    for member, dev in result.all():
        resp = OSPoolMemberResponse.model_validate(member)
        resp.developer = OSDeveloperSummary.model_validate(dev) if dev else None
        items.append(resp)

    return PaginatedResponse.create(items=items, total=total or 0, page=page, page_size=page_size)


# ============= Collect Tasks =============

@router.get("/collect/tasks", response_model=PaginatedResponse[OSCollectTaskResponse])
async def list_collect_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
    _user: dict = Depends(require_admin),
):
    stmt = select(OSCollectTask).order_by(OSCollectTask.created_at.desc())
    total = await session.scalar(select(func.count()).select_from(stmt.subquery()))
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(stmt)
    return PaginatedResponse.create(
        items=[OSCollectTaskResponse.model_validate(i) for i in result.scalars().all()],
        total=total or 0,
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
    task = OSCollectTask(
        task_name=task_name,
        status="pending",
        config_json=config_json,
        created_by=int(user.get("sub", 0)),
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return OSCollectTaskResponse.model_validate(task)


@router.get("/collect/tasks/{task_id}", response_model=OSCollectTaskResponse)
async def get_collect_task(
    task_id: int,
    session: AsyncSession = Depends(get_async_session),
    _user: dict = Depends(require_admin),
):
    task = await session.get(OSCollectTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return OSCollectTaskResponse.model_validate(task)


@router.post("/collect/tasks/{task_id}/cancel")
async def cancel_collect_task(
    task_id: int,
    session: AsyncSession = Depends(get_async_session),
    _user: dict = Depends(require_admin),
):
    task = await session.get(OSCollectTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status not in ("pending", "running"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel task in status: {task.status}")

    CANCELLED_TASK_IDS.add(task_id)
    task.status = "cancelled"
    await session.commit()
    return SuccessResponse(message="Task cancelled")


# ============= Stats =============

@router.get("/stats", response_model=OSStatsResponse)
async def get_stats(session: AsyncSession = Depends(get_async_session)):
    total_devs = await session.scalar(select(func.count()).select_from(OSDeveloper).where(OSDeveloper.is_visible == True))
    total_repos = await session.scalar(select(func.count()).select_from(OSRepository))
    total_orgs = await session.scalar(
        select(func.count(func.distinct(OSDeveloper.company))).where(OSDeveloper.company.isnot(None))
    )

    # Language distribution
    lang_result = await session.execute(
        select(OSLanguageSkill.language, func.count(OSLanguageSkill.developer_id))
        .group_by(OSLanguageSkill.language)
        .order_by(func.count(OSLanguageSkill.developer_id).desc())
    )
    language_distribution = {lang: cnt for lang, cnt in lang_result.all()}

    # Tech element distribution
    tech_result = await session.execute(
        select(OSRepoConfig.tech_element, func.count(OSRepoConfig.repo_config_id))
        .where(OSRepoConfig.is_active == True)
        .group_by(OSRepoConfig.tech_element)
    )
    tech_element_distribution = {tech: cnt for tech, cnt in tech_result.all()}

    return OSStatsResponse(
        total_developers=total_devs or 0,
        total_repositories=total_repos or 0,
        total_organizations=total_orgs or 0,
        active_developers_30d=0,  # Placeholder
        language_distribution=language_distribution,
        tech_element_distribution=tech_element_distribution,
    )


# ============= JD Match =============

@router.post("/jd-match", response_model=OSJDMatchResponse)
async def jd_match(
    data: OSJDMatchRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """JD matching. Returns keyword-based candidates."""
    conditions = [OSDeveloper.is_visible == True]
    if data.filters:
        if data.filters.tech_elements:
            conditions.append(OSDeveloper.tech_tags.overlap(data.filters.tech_elements))
        if data.filters.languages:
            conditions.append(OSDeveloper.primary_languages.overlap(data.filters.languages))
        if data.filters.min_stars is not None:
            conditions.append(OSDeveloper.total_stars_received >= data.filters.min_stars)

    stmt = select(OSDeveloper).where(and_(*conditions)).order_by(OSDeveloper.total_stars_received.desc()).limit(data.top_k)
    result = await session.execute(stmt)
    developers = result.scalars().all()

    results = []
    for dev in developers:
        # Simple mock scoring
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


# ============= Embeddings =============

@router.get("/embeddings/status", response_model=OSEmbeddingStatusResponse)
async def get_embedding_status(session: AsyncSession = Depends(get_async_session)):
    total = await session.scalar(select(func.count()).select_from(OSDeveloper).where(OSDeveloper.is_visible == True))
    embedded = await session.scalar(select(func.count()).select_from(OSEmbedding))
    return OSEmbeddingStatusResponse(
        total_developers=total or 0,
        embedded_count=embedded or 0,
        pending_count=(total or 0) - (embedded or 0),
        dimension=settings.EMBEDDING_DIMENSION,
        model_name=settings.LLM_EMBEDDING_MODEL or "unknown",
    )


@router.post("/embeddings/generate")
async def generate_embeddings(
    req: OSEmbeddingGenerateRequest,
    session: AsyncSession = Depends(get_async_session),
    _user: dict = Depends(require_admin),
):
    """Placeholder for batch embedding generation."""
    # Return status; actual LLM call to be wired
    return SuccessResponse(message=f"Embedding generation queued for batch size {req.batch_size}")


@router.post("/embeddings/generate/{developer_id}")
async def generate_single_embedding(
    developer_id: int,
    session: AsyncSession = Depends(get_async_session),
    _user: dict = Depends(require_admin),
):
    dev = await session.get(OSDeveloper, developer_id)
    if not dev:
        raise HTTPException(status_code=404, detail="Developer not found")
    return SuccessResponse(message=f"Embedding generation queued for developer {developer_id}")
