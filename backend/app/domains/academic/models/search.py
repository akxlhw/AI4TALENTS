"""
Search projection model.
"""

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class SearchTalentDocument(Base):
    """Search projection for talent full-text search."""

    __tablename__ = "search_talent_document"

    document_id = Column(Integer, primary_key=True, index=True)
    talent_id = Column(Integer, unique=True, nullable=False, index=True)
    school_id = Column(Integer, nullable=False, index=True)

    # Search fields
    name = Column(String(255), nullable=False)
    school_name = Column(String(255), nullable=True)
    country_code = Column(String(10), nullable=True, index=True)
    search_text = Column(Text, nullable=False)  # Full-text search field

    # Filter fields (stored as JSON array for compatibility)
    role_type = Column(String(20), nullable=False, index=True)
    topic_tags = Column(JSON().with_variant(JSONB, "postgresql"), default=[])

    # Sort fields
    works_count = Column(Integer, default=0)
    cited_by_count = Column(Integer, default=0)
    h_index = Column(Integer, default=0)
    latest_active_year = Column(Integer, nullable=True)

    # Additional indexed fields
    orcid = Column(String(50), nullable=True)

    # Metadata
    batch_id = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    # Extended data (JSON for flexibility)
    extra_data = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    def __repr__(self) -> str:
        return f"<SearchTalentDocument(talent_id={self.talent_id}, name={self.name})>"
