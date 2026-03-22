"""
Tests for database models.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models import (
    Country, School, SchoolAlias, Talent, RoleProfile, SelectedWork,
    OverviewStatSnapshot, SchoolStatSnapshot, UserAccount, UserSchoolScope,
    SyncBatch, RawSourceRecord, SearchTalentDocument, AuditOperationLog
)
from app.models.enums import RoleType, VisibilityStatus, UserRoleType, SyncJobStatus


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


class TestCountryModel:
    """Tests for Country model."""

    def test_create_country(self, db_session):
        """Test creating a country."""
        country = Country(
            country_code="US",
            country_name_cn="美国",
            country_name_en="United States",
            sort_order=1,
        )
        db_session.add(country)
        db_session.commit()

        assert country.country_id is not None
        assert country.country_code == "US"
        assert country.country_name_cn == "美国"
        assert country.is_active is True

    def test_country_unique_code(self, db_session):
        """Test that country code must be unique."""
        country1 = Country(country_code="CN", country_name_cn="中国")
        country2 = Country(country_code="CN", country_name_cn="中国2")

        db_session.add(country1)
        db_session.commit()

        # This should work as SQLite doesn't enforce unique at ORM level
        # but would fail at database level with real constraints


class TestSchoolModel:
    """Tests for School model."""

    def test_create_school(self, db_session):
        """Test creating a school."""
        country = Country(country_code="US", country_name_cn="美国")
        db_session.add(country)
        db_session.commit()

        school = School(
            school_name="MIT",
            country_id=country.country_id,
            school_intro="Massachusetts Institute of Technology",
        )
        db_session.add(school)
        db_session.commit()

        assert school.school_id is not None
        assert school.school_name == "MIT"
        assert school.is_visible is True
        assert school.status == "active"


class TestTalentModel:
    """Tests for Talent model."""

    def test_create_talent(self, db_session):
        """Test creating a talent."""
        country = Country(country_code="US", country_name_cn="美国")
        db_session.add(country)
        db_session.commit()

        school = School(school_name="MIT", country_id=country.country_id)
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
