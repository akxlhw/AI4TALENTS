"""lab_web_site domain ORM models (v2): site config + raw page snapshots."""

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.sql import func

from app.core.database import Base
from app.domains.shared.models.base import TimestampMixin


class LWSiteConfig(Base, TimestampMixin):
    """Registry of lab sites whose People pages we LLM-parse."""

    __tablename__ = "lw_site_config"

    site_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    site_code = Column(String(50), nullable=False, unique=True, index=True)
    site_name = Column(String(255), nullable=False)
    parent_lab_code = Column(String(50), nullable=False, index=True)
    people_url = Column(String(500), nullable=False)
    fetch_mode = Column(String(20), nullable=False, default="static")
    is_active = Column(Boolean, nullable=False, default=True)
    last_collected_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<LWSiteConfig(site_id={self.site_id}, site_code={self.site_code})>"


class LWSiteRawPage(Base):
    """Append-only snapshot of a site People page + LLM parse result (cached by html_hash)."""

    __tablename__ = "lw_site_raw_page"

    page_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    site_code = Column(
        String(50), ForeignKey("lw_site_config.site_code"), nullable=False, index=True
    )
    people_url = Column(String(500), nullable=False)
    html_content = Column(Text, nullable=False)
    html_hash = Column(String(64), nullable=False, index=True)
    parsed_persons = Column(JSON, nullable=True)
    parse_status = Column(String(20), nullable=False, default="pending", index=True)
    parse_error = Column(Text, nullable=True)
    llm_model = Column(String(100), nullable=True)
    llm_tokens_used = Column(Integer, nullable=True)
    fetched_at = Column(DateTime, default=func.now(), nullable=False)
    parsed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<LWSiteRawPage(page_id={self.page_id}, site_code={self.site_code}, status={self.parse_status})>"
