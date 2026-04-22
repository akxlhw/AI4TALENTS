"""
User and permission models.
"""
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin
from app.models.enums import UserRoleType


class UserAccount(Base, TimestampMixin):
    """User account model."""

    __tablename__ = "iam_user_account"

    user_id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)

    # Role
    role_type = Column(String(20), default=UserRoleType.USER.value, nullable=False)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    status = Column(String(20), default="active", nullable=False)

    # Profile
    display_name = Column(String(100), nullable=True)
    department = Column(String(255), nullable=True)

    # User preferences
    default_view = Column(String(30), default="tech_domain", nullable=False)  # tech_domain / country_school

    # Last login
    last_login_at = Column(DateTime, nullable=True)
    last_login_ip = Column(String(50), nullable=True)

    # Relationships
    school_scopes = relationship("UserSchoolScope", back_populates="user")
    favorites = relationship("FavoriteTalent", back_populates="user", lazy="dynamic")
    talent_pools = relationship("TalentPool", back_populates="owner")

    def __repr__(self):
        return f"<UserAccount(user_id={self.user_id}, username={self.username}, role={self.role_type})>"


class UserSchoolScope(Base, TimestampMixin):
    """User permission scope - supports school/country/tech_domain dimensions."""

    __tablename__ = "iam_user_school_scope"

    scope_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("iam_user_account.user_id"), nullable=False, index=True)

    # Scope definition - three dimensions:
    # - 'school': scope_value = school_id
    # - 'country': scope_value = country_code
    # - 'tech_domain': scope_value = tech_domain_id
    # - 'all': scope_value = '*'
    scope_type = Column(String(20), nullable=False)
    scope_value = Column(String(100), nullable=True)

    # Grant info
    granted_by = Column(Integer, nullable=False)  # user_id who granted
    granted_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    notes = Column(Text, nullable=True)

    # Relationships
    user = relationship("UserAccount", back_populates="school_scopes")

    def __repr__(self):
        return f"<UserSchoolScope(user_id={self.user_id}, scope={self.scope_type}:{self.scope_value})>"


class FavoriteTalent(Base, TimestampMixin):
    """User's favorite talents."""

    __tablename__ = "iam_favorite_talent"

    favorite_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("iam_user_account.user_id"), nullable=False, index=True)
    talent_id = Column(Integer, ForeignKey("core_talent.talent_id"), nullable=False, index=True)
    notes = Column(Text, nullable=True)  # User's notes about this talent
    followup_status = Column(String(30), default="new_found", nullable=False)  # 跟进状态
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    user = relationship("UserAccount", back_populates="favorites")
    talent = relationship("Talent")

    __table_args__ = (
        UniqueConstraint('user_id', 'talent_id', name='uq_user_favorite_talent'),
    )

    def __repr__(self):
        return f"<FavoriteTalent(user_id={self.user_id}, talent_id={self.talent_id})>"


class TalentPool(Base, TimestampMixin):
    """人才池"""

    __tablename__ = "iam_talent_pool"

    pool_id = Column(Integer, primary_key=True, index=True)
    pool_name = Column(String(100), nullable=False)
    pool_type = Column(String(30), default="custom", nullable=False)  # tech_domain/country/campaign/custom
    owner_user_id = Column(Integer, ForeignKey("iam_user_account.user_id"), nullable=False, index=True)
    scope_desc = Column(Text, nullable=True)
    pool_status = Column(String(20), default="active", nullable=False)  # active/archived

    # Relationships
    owner = relationship("UserAccount", back_populates="talent_pools")
    members = relationship("TalentPoolMember", back_populates="pool", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<TalentPool(pool_id={self.pool_id}, name={self.pool_name})>"


class TalentPoolMember(Base, TimestampMixin):
    """人才池成员"""

    __tablename__ = "iam_talent_pool_member"

    member_id = Column(Integer, primary_key=True, index=True)
    pool_id = Column(Integer, ForeignKey("iam_talent_pool.pool_id"), nullable=False, index=True)
    talent_id = Column(Integer, ForeignKey("core_talent.talent_id"), nullable=False, index=True)
    added_by = Column(Integer, nullable=False)  # user_id who added
    notes = Column(Text, nullable=True)

    # Relationships
    pool = relationship("TalentPool", back_populates="members")
    talent = relationship("Talent")

    __table_args__ = (
        UniqueConstraint('pool_id', 'talent_id', name='uq_pool_talent'),
    )

    def __repr__(self):
        return f"<TalentPoolMember(pool_id={self.pool_id}, talent_id={self.talent_id})>"
