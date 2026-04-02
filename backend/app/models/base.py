"""
Base model with common fields.
"""
from sqlalchemy import Boolean, Column, DateTime, Integer
from sqlalchemy.orm import declared_attr
from sqlalchemy.sql import func


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""

    @declared_attr
    def created_at(cls):
        return Column(DateTime, default=func.now(), nullable=False)

    @declared_attr
    def updated_at(cls):
        return Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)


class BaseModel:
    """Base model with common fields."""

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    is_active = Column(Boolean, default=True, nullable=False)
