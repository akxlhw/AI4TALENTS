"""
Country model.
"""
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class Country(Base, TimestampMixin):
    """Country/region model for school classification."""

    __tablename__ = "core_country"

    country_id = Column(Integer, primary_key=True, index=True)
    country_code = Column(String(10), unique=True, nullable=False, index=True)
    country_name_cn = Column(String(100), nullable=False)
    country_name_en = Column(String(100), nullable=True)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    schools = relationship("School", back_populates="country")

    def __repr__(self):
        return f"<Country(country_code={self.country_code}, name={self.country_name_cn})>"
