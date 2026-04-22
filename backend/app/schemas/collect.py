"""
Collect configuration schemas - MVP v1.2
采集配置相关 DTO

采集逻辑：
- 采集最小单位：技术领域
- 数据类型：固定为学者+论文+机构
- 时间范围：用户可配置年份范围（2015年至今）
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


def get_current_year() -> int:
    """Get current year."""
    from datetime import date
    return date.today().year


# 时间范围配置常量
MIN_START_YEAR = 2015
DEFAULT_START_YEAR = 2020


# ============ Venue (顶会顶刊) Schema ============

class VenueItem(BaseModel):
    """顶会顶刊项"""
    id: str = Field(..., description="OpenAlex venue ID 或简称，如 NeurIPS")
    name: str = Field(..., description="完整名称")
    type: str = Field(default="conference", description="类型: conference/journal")


# ============ Tech Domain with Collect Config ============

class TechDomainCollectResponse(BaseModel):
    """技术领域采集配置响应"""
    tech_domain_id: int
    domain_code: str
    domain_name: str
    domain_name_en: str | None = None
    # collect_sources is computed from VenueTechBinding table
    # This field is kept for backward compatibility with frontend
    collect_sources: list[VenueItem] | None = None
    last_collect_at: datetime | None = None
    is_enabled: bool
    venue_count: int = Field(default=0, description="关联顶会顶刊数量")

    class Config:
        from_attributes = True


class TechDomainCollectListResponse(BaseModel):
    """技术领域采集配置列表响应"""
    items: list[TechDomainCollectResponse]
    total: int


class UpdateCollectSourcesRequest(BaseModel):
    """更新技术领域的采集源配置"""
    collect_sources: list[VenueItem] = Field(..., min_items=1, description="关联的顶会顶刊列表")


# ============ Collect Task Schemas ============

class TriggerCollectTaskRequest(BaseModel):
    """触发采集任务请求"""
    tech_domain_id: int = Field(..., description="技术领域ID")
    start_year: int = Field(
        default=DEFAULT_START_YEAR,
        ge=MIN_START_YEAR,
        description=f"起始年份，最小{MIN_START_YEAR}年"
    )
    end_year: int | None = Field(
        default=None,
        description="截止年份，None表示至今"
    )


class CollectTaskResponse(BaseModel):
    """采集任务响应"""
    task_id: int
    task_code: str
    tech_domain_id: int | None = None
    tech_domain_name: str | None = None
    start_year: int = Field(default=DEFAULT_START_YEAR, description="起始年份")
    end_year: int | None = Field(default=None, description="截止年份，None表示至今")
    triggered_by: Any | None = None  # Can be user ID (int) or username (str)
    triggered_at: datetime
    status: str
    progress_percent: int = 0
    current_step: str | None = None
    total_records: int = 0
    processed_records: int = 0
    success_records: int = 0
    failed_records: int = 0
    skipped_records: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    error_details: dict | None = None
    result_summary: dict | None = None
    execution_logs: list[dict] | None = None
    venue_snapshot: list[VenueItem] | None = None  # 创建时的顶会顶刊快照
    created_at: datetime

    class Config:
        from_attributes = True


class CollectTaskListResponse(BaseModel):
    """采集任务列表响应"""
    items: list[CollectTaskResponse]
    total: int
    page: int
    page_size: int


# ============ Task Status Options ============

TASK_STATUS_OPTIONS = [
    {"value": "pending", "label": "待执行"},
    {"value": "running", "label": "执行中"},
    {"value": "completed", "label": "已完成"},
    {"value": "failed", "label": "失败"},
    {"value": "cancelled", "label": "已取消"},
]


# ============ Year Options ============

def get_year_options() -> list[dict]:
    """获取年份选项列表"""
    current_year = get_current_year()
    return [
        {"value": year, "label": f"{year}年"}
        for year in range(current_year, MIN_START_YEAR - 1, -1)
    ]


def get_end_year_options(start_year: int) -> list[dict]:
    """获取截止年份选项列表（包含"至今"选项）"""
    current_year = get_current_year()
    options = [
        {"value": year, "label": f"{year}年"}
        for year in range(current_year, start_year - 1, -1)
    ]
    options.insert(0, {"value": None, "label": "至今"})
    return options
