"""Pydantic DTOs for lab_web."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LabBrief(BaseModel):
    """Lab registry row for listing."""

    model_config = ConfigDict(from_attributes=True)

    lab_id: int
    lab_code: str
    lab_name: str
    lab_name_en: str | None = None
    institution: str
    country: str
    people_url: str
    collector_class: str | None = None
    fetch_mode: str
    is_active: bool
    last_collected_at: datetime | None = None


class CollectTaskResponse(BaseModel):
    """Collection task status for polling."""

    model_config = ConfigDict(from_attributes=True)

    task_id: int
    task_name: str
    lab_id: int
    status: str
    progress_percent: int
    current_step: str | None = None
    total_records: int
    processed_records: int
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None


class CollectStartResponse(BaseModel):
    task_id: int
    status: str
