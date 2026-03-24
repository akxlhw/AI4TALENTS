"""
Collect configuration schemas.
采集配置相关 DTO
"""
from typing import Optional, List, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ============ Collect Scope Schemas ============

class CollectScopeBase(BaseModel):
    """Base schema for collect scope."""
    scope_code: str = Field(..., min_length=1, max_length=50)
    scope_name: str = Field(..., min_length=1, max_length=100)
    scope_type: str = Field(..., pattern="^(tech_element|country|school|custom)$")
    scope_value: List[Any]
    description: Optional[str] = None


class CreateScopeRequest(CollectScopeBase):
    """Create collect scope request."""
    pass


class UpdateScopeRequest(BaseModel):
    """Update collect scope request."""
    scope_name: Optional[str] = None
    scope_value: Optional[List[Any]] = None
    is_enabled: Optional[bool] = None
    description: Optional[str] = None


class CollectScopeResponse(BaseModel):
    """Collect scope response."""
    scope_id: int
    scope_code: str
    scope_name: str
    scope_type: str
    scope_value: List[Any]
    is_enabled: bool
    description: Optional[str] = None
    created_by: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ScopeListResponse(BaseModel):
    """Scope list response."""
    items: List[CollectScopeResponse]
    total: int


# ============ Collect Strategy Schemas ============

class CollectStrategyBase(BaseModel):
    """Base schema for collect strategy."""
    strategy_code: str = Field(..., min_length=1, max_length=50)
    strategy_name: str = Field(..., min_length=1, max_length=100)
    strategy_type: str = Field(default="manual", pattern="^(scheduled|manual|event_triggered)$")
    schedule_cron: Optional[str] = None
    scope_ids: Optional[List[int]] = None
    data_types: List[str] = Field(..., min_items=1)
    fetch_config: Optional[dict] = None
    description: Optional[str] = None


class CreateStrategyRequest(CollectStrategyBase):
    """Create collect strategy request."""
    pass


class UpdateStrategyRequest(BaseModel):
    """Update collect strategy request."""
    strategy_name: Optional[str] = None
    scope_ids: Optional[List[int]] = None
    data_types: Optional[List[str]] = None
    schedule_cron: Optional[str] = None
    fetch_config: Optional[dict] = None
    is_enabled: Optional[bool] = None
    description: Optional[str] = None


class CollectStrategyResponse(BaseModel):
    """Collect strategy response."""
    strategy_id: int
    strategy_code: str
    strategy_name: str
    strategy_type: str
    schedule_cron: Optional[str] = None
    scope_ids: Optional[List[int]] = None
    data_types: List[str]
    fetch_config: Optional[dict] = None
    is_enabled: bool
    description: Optional[str] = None
    created_by: Optional[int] = None
    last_run_at: Optional[datetime] = None
    last_run_status: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class StrategyListResponse(BaseModel):
    """Strategy list response."""
    items: List[CollectStrategyResponse]
    total: int


# ============ Collect Task Schemas ============

class CreateTaskRequest(BaseModel):
    """Create/trigger collect task request."""
    strategy_id: Optional[int] = None
    task_type: str = Field(default="manual", pattern="^(scheduled|manual|retry)$")


class CollectTaskResponse(BaseModel):
    """Collect task response."""
    task_id: int
    task_code: str
    strategy_id: Optional[int] = None
    task_type: str
    triggered_by: Optional[int] = None
    triggered_at: datetime
    status: str
    progress_percent: int
    current_step: Optional[str] = None
    total_records: int
    processed_records: int
    success_records: int
    failed_records: int
    skipped_records: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    error_details: Optional[dict] = None
    result_summary: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    """Task list response."""
    items: List[CollectTaskResponse]
    total: int
    page: int
    page_size: int


# ============ Scope Type Options ============

SCOPE_TYPE_OPTIONS = [
    {"value": "tech_element", "label": "技术要素"},
    {"value": "country", "label": "国家"},
    {"value": "school", "label": "学校"},
    {"value": "custom", "label": "自定义"},
]

STRATEGY_TYPE_OPTIONS = [
    {"value": "scheduled", "label": "定时任务"},
    {"value": "manual", "label": "手动触发"},
    {"value": "event_triggered", "label": "事件触发"},
]

TASK_STATUS_OPTIONS = [
    {"value": "pending", "label": "待执行"},
    {"value": "running", "label": "执行中"},
    {"value": "completed", "label": "已完成"},
    {"value": "failed", "label": "失败"},
    {"value": "cancelled", "label": "已取消"},
]

DATA_TYPE_OPTIONS = [
    {"value": "authors", "label": "学者数据"},
    {"value": "works", "label": "论文数据"},
    {"value": "institutions", "label": "机构数据"},
]
