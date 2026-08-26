"""Shared response envelopes for the open API."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class OpenApiPage(BaseModel, Generic[T]):
    """Unified paginated envelope for /open-api list endpoints."""

    items: list[T] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20
