"""
Tests for database models.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.model_registry import (
    OverviewStatSnapshot,
    School,
    SyncBatch,
    Talent,
    UserAccount,
    UserSchoolScope,
)
from app.domains.shared.models.enums import RoleType, SyncJobStatus, UserRoleType


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


class TestSchoolModel:
    """Tests for School model."""

    def test_create_school(self, db_session):
        """Test creating a school."""
        school = School(
            school_name="MIT",
            country_code="US",
            country_name="美国",
            school_intro="Massachusetts Institute of Technology",
        )
        db_session.add(school)
        db_session.commit()

        assert school.school_id is not None
        assert school.school_name == "MIT"
        assert school.country_code == "US"
        assert school.is_visible is True
        assert school.status == "active"


class TestTalentModel:
    """Tests for Talent model."""

    def test_create_talent(self, db_session):
        """Test creating a talent."""
        school = School(
            school_name="MIT",
            country_code="US",
            country_name="美国",
        )
        db_session.add(school)
        db_session.commit()

        talent = Talent(
            name="John Doe",
            school_id=school.school_id,
            role_type=RoleType.PROFESSOR.value,
            works_count=50,
            cited_by_count=1000,
        )
        db_session.add(talent)
        db_session.commit()

        assert talent.talent_id is not None
        assert talent.name == "John Doe"
        assert talent.role_type == "professor"
        assert talent.is_visible is True


class TestUserModel:
    """Tests for User model."""

    def test_create_user(self, db_session):
        """Test creating a user."""
        user = UserAccount(
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password",
            role_type=UserRoleType.USER.value,
        )
        db_session.add(user)
        db_session.commit()

        assert user.user_id is not None
        assert user.username == "testuser"
        assert user.role_type == "user"
        assert user.is_active is True

    def test_user_school_scope(self, db_session):
        """Test user school scope."""
        from datetime import datetime

        user = UserAccount(
            username="admin",
            email="admin@example.com",
            password_hash="hashed",
            role_type=UserRoleType.ADMIN.value,
        )
        db_session.add(user)
        db_session.commit()

        scope = UserSchoolScope(
            user_id=user.user_id,
            scope_type="all",
            scope_value="*",
            granted_by=user.user_id,
            granted_at=datetime.now(),
        )
        db_session.add(scope)
        db_session.commit()

        assert scope.scope_id is not None
        assert scope.scope_type == "all"


class TestSyncModel:
    """Tests for Sync models."""

    def test_create_sync_batch(self, db_session):
        """Test creating a sync batch."""
        batch = SyncBatch(
            batch_code="batch_001",
            batch_type="full",
            source_type="openalex",
            status=SyncJobStatus.PENDING.value,
        )
        db_session.add(batch)
        db_session.commit()

        assert batch.batch_id is not None
        assert batch.batch_code == "batch_001"
        assert batch.status == "pending"


class TestStatisticsModel:
    """Tests for Statistics models."""

    def test_create_overview_snapshot(self, db_session):
        """Test creating an overview snapshot."""
        snapshot = OverviewStatSnapshot(
            stat_version="v1.0",
            generated_at="2026-01-01T00:00:00",
            school_count=100,
            professor_count=500,
            student_count=1000,
        )
        db_session.add(snapshot)
        db_session.commit()

        assert snapshot.snapshot_id is not None
        assert snapshot.school_count == 100
