"""
Open Source Talent models.
All tables use 'os_' prefix for isolation from academic talent tables.
"""

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.sql import func

from app.core.database import Base
from app.domains.shared.models.base import TimestampMixin


class OSRepoConfig(Base, TimestampMixin):
    """Repository configuration - binds GitHub repos to tech elements."""

    __tablename__ = "os_repo_config"

    repo_config_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    repo_full_name = Column(String(255), nullable=False, unique=True, index=True)
    display_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    tech_element = Column(String(50), nullable=False, index=True)
    tech_direction_id = Column(Integer, ForeignKey("core_tech_direction.tech_direction_id"), nullable=True)
    language = Column(String(50), nullable=True)
    stars_count = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    collect_enabled = Column(Boolean, default=True, nullable=False)
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("iam_user_account.user_id"), nullable=True)


class OSDeveloper(Base, TimestampMixin):
    """Open source developer (serving layer)."""

    __tablename__ = "os_developer"

    developer_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    github_login = Column(String(100), nullable=False, unique=True, index=True)
    github_id = Column(BigInteger, nullable=True, unique=True, index=True)
    name = Column(String(255), nullable=True)
    bio = Column(Text, nullable=True)
    location = Column(String(255), nullable=True)
    company = Column(String(255), nullable=True)
    blog_url = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    avatar_url = Column(String(255), nullable=True)
    followers_count = Column(Integer, default=0, nullable=False)
    following_count = Column(Integer, default=0, nullable=False)
    public_repos_count = Column(Integer, default=0, nullable=False)
    total_stars_received = Column(Integer, default=0, nullable=False)
    total_forks_received = Column(Integer, default=0, nullable=False)
    primary_languages = Column(JSON, default=list)
    tech_tags = Column(JSON, default=list)
    is_visible = Column(Boolean, default=True, nullable=False)


class OSRepository(Base, TimestampMixin):
    """Developer repositories."""

    __tablename__ = "os_repository"

    repo_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    developer_id = Column(Integer, ForeignKey("os_developer.developer_id"), nullable=False, index=True)
    github_repo_id = Column(BigInteger, nullable=True, index=True)
    full_name = Column(String(255), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    language = Column(String(50), nullable=True, index=True)
    stars_count = Column(Integer, default=0, nullable=False)
    forks_count = Column(Integer, default=0, nullable=False)
    topics = Column(JSON, default=list)
    is_fork = Column(Boolean, default=False, nullable=False)


class OSContribution(Base, TimestampMixin):
    """Developer contributions to repositories."""

    __tablename__ = "os_contribution"

    contribution_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    developer_id = Column(Integer, ForeignKey("os_developer.developer_id"), nullable=False, index=True)
    repo_id = Column(Integer, ForeignKey("os_repository.repo_id"), nullable=False)
    commits_count = Column(Integer, default=0, nullable=False)
    prs_count = Column(Integer, default=0, nullable=False)
    issues_count = Column(Integer, default=0, nullable=False)
    code_reviews_count = Column(Integer, default=0, nullable=False)
    is_owner = Column(Boolean, default=False, nullable=False)
    is_maintainer = Column(Boolean, default=False, nullable=False)
    is_committer = Column(Boolean, default=False, nullable=False)


class OSLanguageSkill(Base, TimestampMixin):
    """Aggregated language skills per developer."""

    __tablename__ = "os_language_skill"

    skill_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    developer_id = Column(Integer, ForeignKey("os_developer.developer_id"), nullable=False, index=True)
    language = Column(String(50), nullable=False)
    repo_count = Column(Integer, default=0, nullable=False)
    total_commits = Column(Integer, default=0, nullable=False)
    total_lines_added = Column(Integer, default=0, nullable=False)
    total_lines_deleted = Column(Integer, default=0, nullable=False)
    proficiency_score = Column(Float, default=0.0, nullable=False)


class OSEmbedding(Base, TimestampMixin):
    """Vector embeddings for developers."""

    __tablename__ = "os_embedding"

    embedding_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    developer_id = Column(Integer, ForeignKey("os_developer.developer_id"), nullable=False)
    vector_type = Column(String(20), nullable=False, default="profile")
    embedding = Column(Text, nullable=False)  # pgvector vector(N) in PostgreSQL
    model_name = Column(String(50), nullable=True)
    source_text_hash = Column(String(64), nullable=True, index=True)


class OSFavourite(Base, TimestampMixin):
    """User favorites for open source developers."""

    __tablename__ = "os_favourite"

    favourite_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("iam_user_account.user_id"), nullable=False, index=True)
    developer_id = Column(Integer, ForeignKey("os_developer.developer_id"), nullable=False)
    notes = Column(Text, nullable=True)
    followup_status = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)


class OSTalentPool(Base, TimestampMixin):
    """Open source talent pools."""

    __tablename__ = "os_talent_pool"

    pool_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    owner_user_id = Column(Integer, ForeignKey("iam_user_account.user_id"), nullable=False, index=True)
    pool_name = Column(String(255), nullable=False)
    pool_type = Column(String(50), nullable=True)
    scope_desc = Column(Text, nullable=True)
    pool_status = Column(String(20), default="active", nullable=False)


class OSPoolMember(Base, TimestampMixin):
    """Members of open source talent pools."""

    __tablename__ = "os_pool_member"

    pool_member_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    pool_id = Column(Integer, ForeignKey("os_talent_pool.pool_id"), nullable=False)
    developer_id = Column(Integer, ForeignKey("os_developer.developer_id"), nullable=False)
    notes = Column(Text, nullable=True)


class OSCollectTask(Base):
    """Open source collection tasks."""

    __tablename__ = "os_collect_task"

    task_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    task_name = Column(String(255), nullable=False)
    status = Column(String(20), default="pending", nullable=False, index=True)
    progress_percent = Column(Integer, default=0, nullable=False)
    current_step = Column(String(100), nullable=True)
    total_records = Column(Integer, default=0, nullable=False)
    processed_records = Column(Integer, default=0, nullable=False)
    config_json = Column(JSON, default=dict)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey("iam_user_account.user_id"), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)


class OSRawDeveloper(Base):
    """Raw developer data from GitHub API."""

    __tablename__ = "os_raw_developer"

    raw_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    github_login = Column(String(100), nullable=False, index=True)
    raw_data = Column(JSON, default=dict)
    fetched_at = Column(DateTime, default=func.now(), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)


class OSRepoMapping(Base):
    """Repo to tech direction weight mapping."""

    __tablename__ = "os_repo_mapping"

    mapping_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    repo_full_name = Column(String(255), nullable=False, index=True)
    tech_direction_id = Column(Integer, ForeignKey("core_tech_direction.tech_direction_id"), nullable=False)
    weight = Column(Float, default=1.0, nullable=False)
    is_enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
