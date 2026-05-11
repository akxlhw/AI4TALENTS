"""
Collect configuration schemas
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

    tech_domain_id: int = Field(description="技术领域ID")
    domain_code: str = Field(description="领域代码")
    domain_name: str = Field(description="领域名称")
    domain_name_en: str | None = Field(default=None, description="领域英文名")
    # collect_sources is computed from VenueTechBinding table
    # This field is kept for backward compatibility with frontend
    collect_sources: list[VenueItem] | None = Field(default=None, description="关联的顶会顶刊列表")
    last_collect_at: datetime | None = Field(default=None, description="上次采集时间")
    is_enabled: bool = Field(description="是否启用")
    venue_count: int = Field(default=0, description="关联顶会顶刊数量")

    class Config:
        from_attributes = True


class TechDomainCollectListResponse(BaseModel):
    """技术领域采集配置列表响应"""

    items: list[TechDomainCollectResponse] = Field(description="技术领域列表")
    total: int = Field(description="总数")


# ============ Collect Task Schemas ============


class TriggerCollectTaskRequest(BaseModel):
    """触发采集任务请求"""

    tech_domain_id: int = Field(..., description="技术领域ID")
    start_year: int = Field(
        default=DEFAULT_START_YEAR,
        ge=MIN_START_YEAR,
        description=f"起始年份，最小{MIN_START_YEAR}年",
    )
    end_year: int | None = Field(default=None, description="截止年份，None表示至今")


class CollectTaskResponse(BaseModel):
    """采集任务响应"""

    task_id: int = Field(description="任务ID")
    task_code: str = Field(description="任务编码")
    tech_domain_id: int | None = Field(default=None, description="技术领域ID")
    tech_domain_name: str | None = Field(default=None, description="技术领域名称")
    start_year: int = Field(default=DEFAULT_START_YEAR, description="起始年份")
    end_year: int | None = Field(default=None, description="截止年份，None表示至今")
    triggered_by: Any | None = None  # Can be user ID (int) or username (str)
    triggered_at: datetime = Field(description="触发时间")
    status: str = Field(description="任务状态: pending/running/completed/failed/cancelled")
    progress_percent: int = Field(default=0, description="进度百分比")
    current_step: str | None = Field(default=None, description="当前执行步骤")
    total_records: int = Field(default=0, description="总记录数")
    processed_records: int = Field(default=0, description="已处理记录数")
    success_records: int = Field(default=0, description="成功记录数")
    failed_records: int = Field(default=0, description="失败记录数")
    skipped_records: int = Field(default=0, description="跳过记录数")
    started_at: datetime | None = Field(default=None, description="开始时间")
    completed_at: datetime | None = Field(default=None, description="完成时间")
    error_message: str | None = Field(default=None, description="错误信息")
    error_details: dict | None = Field(default=None, description="错误详情")
    result_summary: dict | None = Field(default=None, description="结果摘要")
    execution_logs: list[dict] | None = Field(default=None, description="执行日志")
    venue_snapshot: list[VenueItem] | None = Field(default=None, description="创建时的顶会顶刊快照")
    created_at: datetime = Field(description="创建时间")

    class Config:
        from_attributes = True


class CollectTaskListResponse(BaseModel):
    """采集任务列表响应"""

    items: list[CollectTaskResponse] = Field(description="任务列表")
    total: int = Field(description="总数")
    page: int = Field(description="当前页码")
    page_size: int = Field(description="每页数量")


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


class TaskActionResponse(BaseModel):
    """采集任务操作响应"""

    message: str = Field(description="操作结果消息")
    task_id: int = Field(description="任务ID")


class YearOptionsResponse(BaseModel):
    """年份选项响应"""

    start_years: list[dict] = Field(description="起始年份选项列表")
    min_year: int = Field(description="最小可选年份")
    default_year: int = Field(description="默认起始年份")
    current_year: int = Field(description="当前年份")


class SubTaskActionResponse(BaseModel):
    """子任务操作响应"""

    message: str = Field(description="操作结果消息")
    sub_task_id: int = Field(description="子任务ID")


def get_end_year_options(start_year: int) -> list[dict]:
    """获取截止年份选项列表（包含"至今"选项）"""
    current_year = get_current_year()
    options = [
        {"value": year, "label": f"{year}年"} for year in range(current_year, start_year - 1, -1)
    ]
    options.insert(0, {"value": None, "label": "至今"})
    return options
