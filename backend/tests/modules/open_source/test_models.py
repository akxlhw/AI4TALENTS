"""
Tests for Open Source domain models.
Covers: field definitions, defaults, relationships, and basic CRUD.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.domains.open_source.models.open_source import (
    OSCollectTask,
    OSContribution,
    OSDeveloper,
    OSEmbedding,
    OSFavourite,
    OSLanguageSkill,
    OSPoolMember,
    OSRawDeveloper,
    OSRepoConfig,
    OSRepoMapping,
    OSRepository,
    OSTalentPool,
)


@pytest.fixture(scope="function")
def db_session():
    """Create a test database session."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


class TestOSRepoConfig:
    """Tests for OSRepoConfig model."""

    def test_create_repo_config(self, db_session):
        """Test creating a repo config with defaults."""
        config = OSRepoConfig(
            repo_full_name="test-org/test-repo",
            tech_element=["ai"],
            display_name="Test Repo",
            language="Python",
        )
        db_session.add(config)
        db_session.commit()

        assert config.repo_config_id is not None
        assert config.repo_full_name == "test-org/test-repo"
        assert config.tech_element == ["ai"]
        assert config.stars_count == 0
        assert config.is_active is True
        assert config.collect_enabled is True


class TestOSDeveloper:
    """Tests for OSDeveloper model."""

    def test_create_developer(self, db_session):
        """Test creating a developer with defaults."""
        dev = OSDeveloper(
            github_login="testdev",
            name="Test Developer",
            bio="A test bio",
            location="Beijing",
            company="Test Corp",
            total_stars_received=1000,
            primary_languages=["Python", "Go"],
            tech_tags=["ai"],
        )
        db_session.add(dev)
        db_session.commit()

        assert dev.developer_id is not None
        assert dev.github_login == "testdev"
        assert dev.followers_count == 0
        assert dev.following_count == 0
        assert dev.public_repos_count == 0
        assert dev.total_forks_received == 0
        assert dev.is_visible is True
        assert dev.primary_languages == ["Python", "Go"]
        assert dev.tech_tags == ["ai"]


class TestOSRepository:
    """Tests for OSRepository model."""

    def test_create_repository(self, db_session):
        """Test creating a repository linked to a developer."""
        dev = OSDeveloper(github_login="repoowner")
        db_session.add(dev)
        db_session.commit()

        repo = OSRepository(
            developer_id=dev.developer_id,
            full_name="repoowner/project",
            name="project",
            language="Rust",
            stars_count=500,
            forks_count=100,
            topics=["web", "async"],
        )
        db_session.add(repo)
        db_session.commit()

        assert repo.repo_id is not None
        assert repo.developer_id == dev.developer_id
        assert repo.is_fork is False
        assert repo.stars_count == 500


class TestOSContribution:
    """Tests for OSContribution model."""

    def test_create_contribution(self, db_session):
        """Test creating a contribution record."""
        dev = OSDeveloper(github_login="contributor")
        db_session.add(dev)
        db_session.commit()

        repo = OSRepository(
            developer_id=dev.developer_id,
            full_name="owner/repo",
            name="repo",
        )
        db_session.add(repo)
        db_session.commit()

        contrib = OSContribution(
            developer_id=dev.developer_id,
            repo_id=repo.repo_id,
            commits_count=42,
            prs_count=5,
            issues_count=3,
            is_committer=True,
        )
        db_session.add(contrib)
        db_session.commit()

        assert contrib.contribution_id is not None
        assert contrib.commits_count == 42
        assert contrib.is_owner is False
        assert contrib.is_committer is True


class TestOSLanguageSkill:
    """Tests for OSLanguageSkill model."""

    def test_create_language_skill(self, db_session):
        """Test creating a language skill record."""
        dev = OSDeveloper(github_login="polyglot")
        db_session.add(dev)
        db_session.commit()

        skill = OSLanguageSkill(
            developer_id=dev.developer_id,
            language="Python",
            repo_count=10,
            total_commits=500,
            total_lines_added=2000,
            proficiency_score=0.95,
        )
        db_session.add(skill)
        db_session.commit()

        assert skill.skill_id is not None
        assert skill.language == "Python"
        assert skill.proficiency_score == pytest.approx(0.95)


class TestOSEmbedding:
    """Tests for OSEmbedding model."""

    def test_create_embedding(self, db_session):
        """Test creating an embedding record."""
        dev = OSDeveloper(github_login="embeddev")
        db_session.add(dev)
        db_session.commit()

        emb = OSEmbedding(
            developer_id=dev.developer_id,
            vector_type="profile",
            embedding="[0.1,0.2,0.3]",
            model_name="text-embedding-3-small",
            source_text_hash="abc123",
        )
        db_session.add(emb)
        db_session.commit()

        assert emb.embedding_id is not None
        assert emb.vector_type == "profile"


class TestOSFavourite:
    """Tests for OSFavourite model."""

    def test_create_favourite(self, db_session):
        """Test creating a favourite with defaults."""
        dev = OSDeveloper(github_login="favdev")
        db_session.add(dev)
        db_session.commit()

        fav = OSFavourite(
            user_id=1,
            developer_id=dev.developer_id,
            notes="Great candidate",
            followup_status="contacted",
        )
        db_session.add(fav)
        db_session.commit()

        assert fav.favourite_id is not None
        assert fav.is_active is True
        assert fav.notes == "Great candidate"


class TestOSTalentPool:
    """Tests for OSTalentPool model."""

    def test_create_talent_pool(self, db_session):
        """Test creating a talent pool with defaults."""
        pool = OSTalentPool(
            owner_user_id=1,
            pool_name="AI Backend Pool",
            pool_type="custom",
        )
        db_session.add(pool)
        db_session.commit()

        assert pool.pool_id is not None
        assert pool.pool_status == "active"


class TestOSPoolMember:
    """Tests for OSPoolMember model."""

    def test_create_pool_member(self, db_session):
        """Test creating a pool member."""
        dev = OSDeveloper(github_login="member")
        db_session.add(dev)
        db_session.commit()

        pool = OSTalentPool(owner_user_id=1, pool_name="Test Pool")
        db_session.add(pool)
        db_session.commit()

        member = OSPoolMember(
            pool_id=pool.pool_id,
            developer_id=dev.developer_id,
            notes="Strong in algorithms",
        )
        db_session.add(member)
        db_session.commit()

        assert member.pool_member_id is not None
        assert member.pool_id == pool.pool_id


class TestOSCollectTask:
    """Tests for OSCollectTask model."""

    def test_create_collect_task(self, db_session):
        """Test creating a collect task with defaults."""
        task = OSCollectTask(
            task_name="collect-ai-repos",
            config_json={"repos": ["pytorch/pytorch"]},
        )
        db_session.add(task)
        db_session.commit()

        assert task.task_id is not None
        assert task.status == "pending"
        assert task.progress_percent == 0
        assert task.total_records == 0
        assert task.processed_records == 0


class TestOSRawDeveloper:
    """Tests for OSRawDeveloper model."""

    def test_create_raw_developer(self, db_session):
        """Test creating a raw developer record."""
        raw = OSRawDeveloper(
            github_login="rawdev",
            raw_data={"id": 123, "login": "rawdev"},
        )
        db_session.add(raw)
        db_session.commit()

        assert raw.raw_id is not None
        assert raw.github_login == "rawdev"


class TestOSRepoMapping:
    """Tests for OSRepoMapping model."""

    def test_create_repo_mapping(self, db_session):
        """Test creating a repo mapping with defaults."""
        mapping = OSRepoMapping(
            repo_full_name="owner/repo",
            tech_direction_id=1,
            weight=0.8,
        )
        db_session.add(mapping)
        db_session.commit()

        assert mapping.mapping_id is not None
        assert mapping.weight == pytest.approx(0.8)
        assert mapping.is_enabled is True
