"""
Open Source Talent API schemas.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ============= Repo Config =============


class OSRepoConfigCreate(BaseModel):
    """Create repo config request."""

    repo_full_name: str = Field(..., description="GitHub repo full name, e.g. 'pytorch/pytorch'")
    display_name: str | None = Field(default=None, description="Display name")
    description: str | None = Field(default=None, description="Repository description")
    tech_element: str = Field(
        ..., description="Tech element code: ai/robotics/data_science/networks/systems/security"
    )
    tech_direction_id: int | None = Field(default=None, description="Optional tech direction ID")
    language: str | None = Field(default=None, description="Primary programming language")
    notes: str | None = Field(default=None, description="Admin notes")


class OSRepoConfigUpdate(BaseModel):
    """Update repo config request."""

    display_name: str | None = Field(default=None)
    description: str | None = Field(default=None)
    tech_element: str | None = Field(default=None)
    tech_direction_id: int | None = Field(default=None)
    language: str | None = Field(default=None)
    is_active: bool | None = Field(default=None)
    collect_enabled: bool | None = Field(default=None)
    notes: str | None = Field(default=None)


class OSRepoConfigResponse(BaseModel):
    """Repo config response."""

    repo_config_id: int
    repo_full_name: str
    display_name: str | None
    description: str | None
    tech_element: str
    tech_direction_id: int | None
    language: str | None
    stars_count: int
    is_active: bool
    collect_enabled: bool
    notes: str | None
    created_by: int | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OSPurgePreview(BaseModel):
    """Repo collected-data purge preview / execution result."""

    repo_full_name: str
    repo_found: bool = Field(..., description="os_repository 中是否存在对应采集数据")
    contributions: int = Field(..., description="将/已删除的贡献记录数")
    developers_total: int = Field(..., description="涉及人才总数")
    developers_exclusive: int = Field(..., description="将/已删除的独占人才数")
    developers_protected: int = Field(..., description="因收藏/人才池被保护而保留的人数")
    developers_shared: int = Field(..., description="因被其他已配置仓库共享而保留的人数")
    skills: int = Field(..., description="级联删除的语言技能记录数")
    embeddings: int = Field(..., description="级联删除的向量记录数")
    raw: int = Field(..., description="级联删除的原始数据记录数")
    config_deleted: bool = Field(default=False, description="是否同时删除了仓库配置行")


# ============= Developer =============


class OSDeveloperSummary(BaseModel):
    """Developer summary for list views."""

    developer_id: int
    github_login: str
    name: str | None
    bio: str | None
    location: str | None
    company: str | None
    avatar_url: str | None
    total_stars_received: int
    primary_languages: list[str]
    tech_tags: list[str]
    is_visible: bool
    is_student: bool
    roles: list[str] = Field(default_factory=list, description="角色标签 (Owner, Committer)")

    model_config = ConfigDict(from_attributes=True)


class OSRepositoryItem(BaseModel):
    """Repository item in detail view."""

    repo_id: int
    github_repo_id: int | None
    full_name: str
    name: str
    language: str | None
    stars_count: int
    forks_count: int
    topics: list[str]
    is_fork: bool

    model_config = ConfigDict(from_attributes=True)


class OSContributionItem(BaseModel):
    """Contribution item in detail view."""

    contribution_id: int
    repo_id: int
    repo_full_name: str
    commits_count: int
    prs_count: int
    issues_count: int
    code_reviews_count: int
    is_owner: bool
    is_maintainer: bool
    is_committer: bool

    model_config = ConfigDict(from_attributes=True)


class OSLanguageSkillItem(BaseModel):
    """Language skill item."""

    skill_id: int
    language: str
    repo_count: int
    total_commits: int
    proficiency_score: float

    model_config = ConfigDict(from_attributes=True)


class OSDeveloperDetail(OSDeveloperSummary):
    """Developer detail response."""

    github_id: int | None
    blog_url: str | None
    email: str | None
    followers_count: int
    following_count: int
    public_repos_count: int
    total_forks_received: int
    repositories: list[OSRepositoryItem] = []
    language_skills: list[OSLanguageSkillItem] = []
    contributions: list[OSContributionItem] = []
    similar_developers: list[OSDeveloperSummary] = []


class OSDeveloperCompareRequest(BaseModel):
    """Developer compare request."""

    developer_ids: list[int] = Field(..., min_length=2, max_length=5)


class OSDeveloperCompareResponse(BaseModel):
    """Developer compare response."""

    developers: list[OSDeveloperDetail]
    radar: dict[str, Any]


# ============= Search =============


class OSSearchFilters(BaseModel):
    """Search filters."""

    tech_elements: list[str] | None = Field(default=None)
    languages: list[str] | None = Field(default=None)
    location: str | None = Field(default=None)
    company: str | None = Field(default=None)
    min_stars: int | None = Field(default=None, ge=0)
    repo_full_names: list[str] | None = Field(default=None)
    is_student: bool | None = Field(default=None)


class OSSearchRequest(BaseModel):
    """Search request body."""

    q: str = Field(default="", description="Search query")
    mode: str = Field(default="hybrid", description="keyword/semantic/hybrid")
    filters: OSSearchFilters | None = Field(default=None)
    sort_by: str = Field(default="stars_desc", description="stars_desc/stars_asc/name_asc")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


# ============= Favorite =============


class OSFavoriteCreate(BaseModel):
    """Create favorite request."""

    developer_id: int
    notes: str | None = Field(default=None)


class OSFavoriteUpdate(BaseModel):
    """Update favorite request."""

    notes: str | None = Field(default=None)
    followup_status: str | None = Field(default=None)


class OSFavoriteResponse(BaseModel):
    """Favorite response."""

    favourite_id: int
    user_id: int
    developer_id: int
    developer: OSDeveloperSummary | None = None
    notes: str | None
    followup_status: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OSFavoriteIdsResponse(BaseModel):
    """Favorite IDs response."""

    developer_ids: list[int]


# ============= Talent Pool =============


class OSTalentPoolCreate(BaseModel):
    """Create talent pool request."""

    pool_name: str
    pool_type: str | None = Field(default="custom")
    scope_desc: str | None = Field(default=None)


class OSTalentPoolUpdate(BaseModel):
    """Update talent pool request."""

    pool_name: str | None = Field(default=None)
    scope_desc: str | None = Field(default=None)
    pool_status: str | None = Field(default=None)


class OSTalentPoolResponse(BaseModel):
    """Talent pool response."""

    pool_id: int
    owner_user_id: int
    pool_name: str
    pool_type: str | None
    scope_desc: str | None
    pool_status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OSPoolMemberResponse(BaseModel):
    """Pool member response."""

    pool_member_id: int
    pool_id: int
    developer_id: int
    developer: OSDeveloperSummary | None = None
    notes: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============= Collect Task =============


class OSCollectTaskCreate(BaseModel):
    """Create collect task request."""

    task_name: str | None = Field(default=None, description="Auto-generated if not provided")
    tech_elements: list[str] | None = Field(default=None, description="Filter by tech elements")
    contributors_per_repo: int = Field(default=30, ge=1, le=100)
    # Manual mode fields
    orgs: list[str] | None = Field(default=None)
    topics: list[str] | None = Field(default=None)
    min_stars: int | None = Field(default=None)
    max_repos: int | None = Field(default=None)
    languages: list[str] | None = Field(default=None)


class OSCollectTaskResponse(BaseModel):
    """Collect task response."""

    task_id: int
    task_name: str
    status: str
    progress_percent: int
    current_step: str | None
    total_records: int
    processed_records: int
    config_json: dict
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OSBatchCollectRequest(BaseModel):
    """Batch collect request."""

    repo_config_ids: list[int] = Field(..., min_length=1)
    contributors_per_repo: int = Field(default=0, ge=0, le=2000)


class OSBatchCollectSkippedItem(BaseModel):
    """Skipped item in batch collect response."""

    repo_config_id: int
    repo_full_name: str | None
    reason: str


class OSBatchCollectResponse(BaseModel):
    """Batch collect response."""

    created: list[OSCollectTaskResponse]
    skipped: list[OSBatchCollectSkippedItem]


# ============= Stats =============


class OSStatsResponse(BaseModel):
    """Open source stats response."""

    total_developers: int
    total_repositories: int
    total_organizations: int
    active_developers_30d: int
    language_distribution: dict[str, int]
    tech_element_distribution: dict[str, int]


class OSTrendingRepoItem(BaseModel):
    """Trending repository item."""

    repo_id: int
    full_name: str
    language: str | None
    stars_count: int
    forks_count: int
    trend_score: float


# ============= JD Match =============


class OSJDMatchRequest(BaseModel):
    """JD match request."""

    jd_text: str
    filters: OSSearchFilters | None = Field(default=None)
    top_k: int = Field(default=20, ge=1, le=100)


class OSJDMatchResultItem(BaseModel):
    """JD match result item."""

    developer_id: int
    github_login: str
    name: str | None
    avatar_url: str | None
    match_score: float
    tech_score: float
    activity_score: float
    reason: str


class OSJDMatchResponse(BaseModel):
    """JD match response."""

    results: list[OSJDMatchResultItem]
    total: int
    query_summary: str


# ============= Embedding =============


class OSEmbeddingStatusResponse(BaseModel):
    """Embedding status response."""

    total_developers: int
    embedded_count: int
    pending_count: int
    progress_percent: float
    dimension: int
    model_name: str


class OSEmbeddingGenerateRequest(BaseModel):
    """Embedding generate request."""

    batch_size: int = Field(default=50, ge=1, le=200)
    force: bool = Field(default=False, description="强制重新生成，忽略已有向量")


# ============= Repository Detail =============


class OSRepositoryDetailResponse(BaseModel):
    """Repository detail response."""

    repo_id: int
    full_name: str
    display_name: str | None
    description: str | None
    language: str | None
    stars_count: int
    forks_count: int
    topics: list[str] = Field(default_factory=list)
    tech_element: str
    contributor_count: int

    model_config = ConfigDict(from_attributes=True)


class OSRepositoryContributor(BaseModel):
    """Contributor of a repository."""

    developer_id: int
    github_login: str
    name: str | None
    avatar_url: str | None
    company: str | None
    location: str | None
    commits_count: int
    prs_count: int
    issues_count: int
    is_owner: bool
    is_committer: bool
    roles: list[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# ============ Batch Repo Create ============


class OSBatchRepoCreateRequest(BaseModel):
    """Request body for batch creating repo configs from GitHub URLs."""

    repo_inputs: list[str] = Field(..., description="GitHub URLs or owner/repo strings")
    tech_element: str = Field(..., description="Tech element applied to all repos")


class OSBatchRepoCreatedItem(BaseModel):
    """One successfully created repo config."""

    repo_config_id: int
    repo_full_name: str
    display_name: str | None = None
    language: str | None = None
    stars_count: int = 0


class OSBatchRepoSkipItem(BaseModel):
    """One skipped or failed repo."""

    repo_input: str
    reason: str


class OSBatchRepoCreateResponse(BaseModel):
    """Response for batch repo creation."""

    created: list[OSBatchRepoCreatedItem] = Field(default_factory=list)
    skipped: list[OSBatchRepoSkipItem] = Field(default_factory=list)
    failed: list[OSBatchRepoSkipItem] = Field(default_factory=list)
