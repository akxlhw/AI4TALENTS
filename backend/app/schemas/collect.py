"""
Collect configuration schemas - Simplified for MVP v1.1
采集配置相关 DTO - 简化版

采集逻辑：
- 采集最小单位：技术要素
- 数据类型：固定为学者+论文+机构
- 时间范围：固定为2010.1.1至今
- 采集模式：全量/增量
"""
from typing import Optional, List, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ============ Venue (顶会顶刊) Schema ============

class VenueItem(BaseModel):
    """顶会顶刊项"""
    id: str = Field(..., description="OpenAlex venue ID 或简称，如 NeurIPS")
    name: str = Field(..., description="完整名称")
    type: str = Field(default="conference", description="类型: conference/journal")


# ============ Tech Element with Collect Config ============

class TechElementCollectResponse(BaseModel):
    """技术要素采集配置响应"""
    tech_element_id: int
    element_code: str
    element_name: str
    element_name_en: Optional[str] = None
    # collect_sources is computed from VenueTechBinding table
    # This field is kept for backward compatibility with frontend
    collect_sources: Optional[List[VenueItem]] = None
    last_collect_at: Optional[datetime] = None
    is_enabled: bool
    venue_count: int = Field(default=0, description="关联顶会顶刊数量")

    class Config:
        from_attributes = True


class TechElementCollectListResponse(BaseModel):
    """技术要素采集配置列表响应"""
    items: List[TechElementCollectResponse]
    total: int


class UpdateCollectSourcesRequest(BaseModel):
    """更新技术要素的采集源配置"""
    collect_sources: List[VenueItem] = Field(..., min_items=1, description="关联的顶会顶刊列表")


# ============ Collect Task Schemas ============

class TriggerCollectTaskRequest(BaseModel):
    """触发采集任务请求"""
    tech_element_id: int = Field(..., description="技术要素ID")
    collect_mode: str = Field(default="full", pattern="^(full|incremental)$", description="采集模式：full=全量, incremental=增量")


class CollectTaskResponse(BaseModel):
    """采集任务响应"""
    task_id: int
    task_code: str
    tech_element_id: Optional[int] = None
    tech_element_name: Optional[str] = None
    collect_mode: str
    triggered_by: Optional[Any] = None  # Can be user ID (int) or username (str)
    triggered_at: datetime
    status: str
    progress_percent: int = 0
    current_step: Optional[str] = None
    total_records: int = 0
    processed_records: int = 0
    success_records: int = 0
    failed_records: int = 0
    skipped_records: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    error_details: Optional[dict] = None
    result_summary: Optional[dict] = None
    execution_logs: Optional[List[dict]] = None  # 新增：执行日志
    created_at: datetime

    class Config:
        from_attributes = True


class CollectTaskListResponse(BaseModel):
    """采集任务列表响应"""
    items: List[CollectTaskResponse]
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

COLLECT_MODE_OPTIONS = [
    {"value": "full", "label": "全量采集"},
    {"value": "incremental", "label": "增量采集"},
]
