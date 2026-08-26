"""
Open-API key model — hashed storage, per-domain read/write scopes.
"""

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base
from app.domains.shared.models.base import TimestampMixin


class ApiKey(Base, TimestampMixin):
    """API key for external tools / skills calling the open API."""

    __tablename__ = "shared_api_key"

    api_key_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    key_name = Column(String(100), nullable=False)
    # sha256 hex of the full key; plaintext is never stored
    key_hash = Column(String(64), nullable=False, unique=True, index=True)
    # first 8 chars of the plaintext key, for list-page recognition only
    key_prefix = Column(String(8), nullable=False)
    # e.g. ["academic:read", "industry:write"]
    scopes = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=list)
    is_active = Column(Boolean, default=True, nullable=False)
    # optional per-key rate limit override (requests/min); NULL = global default
    rate_limit_per_minute = Column(Integer, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, nullable=True)

    def __repr__(self) -> str:
        return f"<ApiKey(id={self.api_key_id}, name={self.key_name}, prefix={self.key_prefix})>"
