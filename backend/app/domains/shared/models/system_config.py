"""
System configuration model.
"""

from sqlalchemy import Boolean, Column, Integer, String, Text

from app.core.database import Base
from app.models.base import TimestampMixin


class SystemConfig(Base, TimestampMixin):
    """System configuration key-value store."""

    __tablename__ = "sys_config"

    config_id = Column(Integer, primary_key=True, index=True)
    config_key = Column(String(100), unique=True, nullable=False, index=True)
    config_value = Column(Text, nullable=True)
    config_type = Column(
        String(20), default="string", nullable=False
    )  # string, int, float, bool, json
    is_sensitive = Column(Boolean, default=False, nullable=False)
    description = Column(String(500), nullable=True)

    def __repr__(self) -> str:
        return f"<SystemConfig(key={self.config_key}, type={self.config_type})>"
