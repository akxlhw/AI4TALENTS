"""
Data version schemas.
数据版本相关 DTO
"""
from typing import Optional, List, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ============ Data Version Schemas ============

class DataVersionResponse(BaseModel):
    """Data version response."""
    version_id: int
    version_code: str
    version_name: str
    version_type: str
    base_version_id: Optional[int] = None
    source_task_id: Optional[int] = None
    total_talents: int
    total_schools: int
    total_works: int
    is_active: bool
    is_published: bool
    published_at: Optional[datetime] = None
    published_by: Optional[int] = None
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DataVersionListResponse(BaseModel):
    """Data version list response."""
    items: List[DataVersionResponse]
    total: int
    page: int
    page_size: int


class CreateVersionRequest(BaseModel):
    """Create data version request."""
    version_code: str = Field(..., min_length=1, max_length=50)
    version_name: str = Field(..., min_length=1, max_length=100)
    version_type: str = Field(default="snapshot", pattern="^(snapshot|release)$")
    base_version_id: Optional[int] = None
    source_task_id: Optional[int] = None
    description: Optional[str] = None


class PublishVersionRequest(BaseModel):
    """Publish version request."""
    notes: Optional[str] = None


# ============ Publish Record Schemas ============

class PublishRecordResponse(BaseModel):
    """Publish record response."""
    publish_id: int
    version_id: int
    action: str
    previous_version_id: Optional[int] = None
    operated_by: int
    operated_at: datetime
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class PublishRecordListResponse(BaseModel):
    """Publish record list response."""
    items: List[PublishRecordResponse]
    total: int


# ============ Correction Schemas ============

class CreateCorrectionRequest(BaseModel):
    """Create correction request."""
    target_type: str = Field(..., pattern="^(talent|school|tech_tag)$")
    target_id: int
    field_name: str = Field(..., min_length=1, max_length=50)
    original_value: Optional[str] = None
    corrected_value: Optional[str] = None
    correction_type: str = Field(default="manual", pattern="^(manual|system|import)$")
    reason: Optional[str] = None
    source: Optional[str] = None


class CorrectionResponse(BaseModel):
    """Correction response."""
    correction_id: int
    target_type: str
    target_id: int
    field_name: str
    original_value: Optional[str] = None
    corrected_value: Optional[str] = None
    correction_type: str
    reason: Optional[str] = None
    source: Optional[str] = None
    corrected_by: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class CorrectionListResponse(BaseModel):
    """Correction list response."""
    items: List[CorrectionResponse]
    total: int
    page: int
    page_size: int


# ============ Quality Summary Schemas ============

class QualitySummaryResponse(BaseModel):
    """Quality summary response."""
    summary_id: int
    version_id: int
    summary_date: datetime

    # Talent metrics
    talent_total: int
    talent_with_orcid: int
    talent_with_affiliation: int
    talent_with_works: int
    talent_completeness_avg: int

    # School metrics
    school_total: int
    school_with_ror: int
    school_with_country: int

    # Work metrics
    work_total: int
    work_with_doi: int

    # Tech tag metrics
    tech_tag_total: int
    tech_tag_confirmed: int
    tech_tag_auto_identified: int
    tech_tag_pending_confirm: int

    # Issues
    issues_critical: int
    issues_warning: int
    issues_info: int

    details: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True


class QualityMetricsResponse(BaseModel):
    """Quality metrics for dashboard."""
    # Talent metrics with percentages
    talent_total: int
    talent_orcid_rate: float
    talent_affiliation_rate: float
    talent_works_rate: float
    talent_completeness_avg: float

    # School metrics
    school_total: int
    school_ror_rate: float
    school_country_rate: float

    # Work metrics
    work_total: int
    work_doi_rate: float

    # Tech tag metrics
    tech_tag_total: int
    tech_tag_confirmed_rate: float
    tech_tag_auto_rate: float
    tech_tag_pending: int

    # Issues
    issues_critical: int
    issues_warning: int
    issues_info: int


# ============ Options ============

VERSION_TYPE_OPTIONS = [
    {"value": "snapshot", "label": "快照"},
    {"value": "release", "label": "发布版"},
]

ACTION_TYPE_OPTIONS = [
    {"value": "publish", "label": "发布"},
    {"value": "rollback", "label": "回滚"},
    {"value": "activate", "label": "激活"},
    {"value": "deactivate", "label": "停用"},
]

CORRECTION_TYPE_OPTIONS = [
    {"value": "manual", "label": "手动修正"},
    {"value": "system", "label": "系统修正"},
    {"value": "import", "label": "导入修正"},
]

CORRECTION_STATUS_OPTIONS = [
    {"value": "pending", "label": "待处理"},
    {"value": "applied", "label": "已应用"},
    {"value": "reverted", "label": "已撤销"},
]

TARGET_TYPE_OPTIONS = [
    {"value": "talent", "label": "人才"},
    {"value": "school", "label": "学校"},
    {"value": "tech_tag", "label": "技术标签"},
]
