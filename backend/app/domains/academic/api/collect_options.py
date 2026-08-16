"""
Collect options endpoints (task statuses, year options).
采集配置选项接口

Split from collect.py; routes keep the original /collect prefix.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter

from app.domains.academic.schemas.collect import (
    DEFAULT_START_YEAR,
    MIN_START_YEAR,
    TASK_STATUS_OPTIONS,
    YearOptionsResponse,
    get_current_year,
    get_year_options,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/collect", tags=["Collect Configuration"])


# ============ Options Endpoints ============


@router.get(
    "/options/task-statuses",
    response_model=list[dict[str, str]],
    summary="获取任务状态选项",
    description="获取所有可用的任务状态选项",
)
async def get_task_statuses():
    """Get task status options."""
    return TASK_STATUS_OPTIONS


@router.get(
    "/options/years",
    response_model=YearOptionsResponse,
    summary="获取年份选项",
    description="获取可用的年份选项列表",
)
async def get_years():
    """Get year options for time range selection."""
    return YearOptionsResponse(
        start_years=get_year_options(),
        min_year=MIN_START_YEAR,
        default_year=DEFAULT_START_YEAR,
        current_year=get_current_year(),
    )
