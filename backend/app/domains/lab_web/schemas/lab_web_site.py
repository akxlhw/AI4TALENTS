"""Pydantic DTOs for lab_web_site (v2)."""

from __future__ import annotations

from datetime import datetime
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, field_validator


class ParsedPerson(BaseModel):
    """One person extracted by the LLM from a lab-site People page."""

    name: str
    role_section: str = "Unknown"
    homepage: str | None = None
    department: str | None = None

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("name must not be blank")
        return v.strip()

    @field_validator("homepage")
    @classmethod
    def valid_url_if_present(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        parsed = urlparse(v)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError(f"invalid homepage URL: {v}")
        return v


class SiteBrief(BaseModel):
    """Site config row for listing."""

    model_config = ConfigDict(from_attributes=True)

    site_id: int
    site_code: str
    site_name: str
    parent_lab_code: str
    people_url: str
    fetch_mode: str
    is_active: bool
    last_collected_at: datetime | None = None


class SiteCollectStartResponse(BaseModel):
    task_id: int
    status: str


class SiteCollectTaskResponse(BaseModel):
    """Reuses lw_collect_task; response fields mirror v1 shape."""

    model_config = ConfigDict(from_attributes=True)

    task_id: int
    task_name: str
    status: str
    progress_percent: int
    current_step: str | None = None
    total_records: int
    error_message: str | None = None
