"""
Data version schemas.
数据版本相关 DTO
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

# ============ Data Version Schemas ============

class DataVersionResponse(BaseModel):
    """Data version response."""
    version_id: int = Field(description="版本ID")
    version_code: str = Field(description="版本编码")
    version_name: str = Field(description="版本名称")
    version_type: str = Field(description="版本类型: snapshot/release")
    base_version_id: int | None = Field(default=None, description="基线版本ID")
    source_task_id: int | None = Field(default=None, description="来源采集任务ID")
    total_talents: int = Field(description="人才总数")
    total_schools: int = Field(description="院校总数")
    total_works: int = Field(description="论文总数")
    is_active: bool = Field(description="是否激活")
    is_published: bool = Field(description="是否已发布")
    published_at: datetime | None = Field(default=None, description="发布时间")
    published_by: int | None = Field(default=None, description="发布人用户ID")
    description: str | None = Field(default=None, description="版本描述")
    created_at: datetime = Field(description="创建时间")

    class Config:
        from_attributes = True


class DataVersionListResponse(BaseModel):
    """Data version list response."""
    items: list[DataVersionResponse] = Field(description="版本列表")
    total: int = Field(description="总数")
    page: int = Field(description="当前页码")
    page_size: int = Field(description="每页数量")


class CreateVersionRequest(BaseModel):
    """Create data version request."""
    version_code: str = Field(..., min_length=1, max_length=50, description="版本编码")
    version_name: str = Field(..., min_length=1, max_length=100, description="版本名称")
    version_type: str = Field(default="snapshot", pattern="^(snapshot|release)$", description="版本类型: snapshot/release")
    base_version_id: int | None = Field(default=None, description="基线版本ID")
    source_task_id: int | None = Field(default=None, description="来源采集任务ID")
    description: str | None = Field(default=None, description="版本描述")


class PublishVersionRequest(BaseModel):
    """Publish version request."""
    notes: str | None = Field(default=None, description="发布备注")


# ============ Publish Record Schemas ============

class PublishRecordResponse(BaseModel):
    """Publish record response."""
    publish_id: int = Field(description="发布记录ID")
    version_id: int = Field(description="版本ID")
    action: str = Field(description="操作类型: publish/rollback/activate/deactivate")
    previous_version_id: int | None = Field(default=None, description="上一个版本ID")
    operated_by: int = Field(description="操作人用户ID")
    operated_at: datetime = Field(description="操作时间")
    notes: str | None = Field(default=None, description="备注")

    class Config:
        from_attributes = True


class PublishRecordListResponse(BaseModel):
    """Publish record list response."""
    items: list[PublishRecordResponse] = Field(description="发布记录列表")
    total: int = Field(description="总数")


# ============ Correction Schemas ============

class CreateCorrectionRequest(BaseModel):
    """Create correction request."""
    target_type: str = Field(..., pattern="^(talent|school|tech_tag)$", description="修正目标类型")
    target_id: int = Field(..., description="目标ID")
    field_name: str = Field(..., min_length=1, max_length=50, description="字段名称")
    original_value: str | None = Field(default=None, description="原始值")
    corrected_value: str | None = Field(default=None, description="修正值")
    correction_type: str = Field(default="manual", pattern="^(manual|system|import)$", description="修正类型")
    reason: str | None = Field(default=None, description="修正原因")
    source: str | None = Field(default=None, description="数据来源")


class CorrectionResponse(BaseModel):
    """Correction response."""
    correction_id: int = Field(description="修正记录ID")
    target_type: str = Field(description="目标类型")
    target_id: int = Field(description="目标ID")
    field_name: str = Field(description="字段名称")
    original_value: str | None = Field(default=None, description="原始值")
    corrected_value: str | None = Field(default=None, description="修正值")
    correction_type: str = Field(description="修正类型")
    reason: str | None = Field(default=None, description="修正原因")
    source: str | None = Field(default=None, description="数据来源")
    corrected_by: int = Field(description="修正人用户ID")
    status: str = Field(description="状态: pending/applied/reverted")
    created_at: datetime = Field(description="创建时间")

    class Config:
        from_attributes = True


class CorrectionListResponse(BaseModel):
    """Correction list response."""
    items: list[CorrectionResponse] = Field(description="修正记录列表")
    total: int = Field(description="总数")
    page: int = Field(description="当前页码")
    page_size: int = Field(description="每页数量")


# ============ Quality Summary Schemas ============

class QualitySummaryResponse(BaseModel):
    """Quality summary response."""
    summary_id: int = Field(description="摘要ID")
    version_id: int = Field(description="版本ID")
    summary_date: datetime = Field(description="摘要日期")

    # Talent metrics
    talent_total: int = Field(description="人才总数")
    talent_with_orcid: int = Field(description="有ORCID的人才数")
    talent_with_affiliation: int = Field(description="有机构归属的人才数")
    talent_with_works: int = Field(description="有论文的人才数")
    talent_completeness_avg: int = Field(description="平均完整度")

    # School metrics
    school_total: int = Field(description="院校总数")
    school_with_ror: int = Field(description="有ROR ID的院校数")
    school_with_country: int = Field(description="有国家信息的院校数")

    # Work metrics
    work_total: int = Field(description="论文总数")
    work_with_doi: int = Field(description="有DOI的论文数")

    # Tech tag metrics
    tech_tag_total: int = Field(description="技术标签总数")
    tech_tag_confirmed: int = Field(description="已确认标签数")
    tech_tag_auto_identified: int = Field(description="自动识别标签数")
    tech_tag_pending_confirm: int = Field(description="待确认标签数")

    # Issues
    issues_critical: int = Field(description="严重问题数")
    issues_warning: int = Field(description="警告数")
    issues_info: int = Field(description="信息数")

    details: dict | None = Field(default=None, description="详细数据")
    created_at: datetime = Field(description="创建时间")

    class Config:
        from_attributes = True


class QualityMetricsResponse(BaseModel):
    """Quality metrics for dashboard."""
    # Talent metrics with percentages
    talent_total: int = Field(description="人才总数")
    talent_orcid_rate: float = Field(description="ORCID覆盖率")
    talent_affiliation_rate: float = Field(description="机构归属覆盖率")
    talent_works_rate: float = Field(description="论文覆盖率")
    talent_completeness_avg: float = Field(description="平均完整度")

    # School metrics
    school_total: int = Field(description="院校总数")
    school_ror_rate: float = Field(description="ROR覆盖率")
    school_country_rate: float = Field(description="国家信息覆盖率")

    # Work metrics
    work_total: int = Field(description="论文总数")
    work_doi_rate: float = Field(description="DOI覆盖率")

    # Tech tag metrics
    tech_tag_total: int = Field(description="技术标签总数")
    tech_tag_confirmed_rate: float = Field(description="标签确认率")
    tech_tag_auto_rate: float = Field(description="自动识别率")
    tech_tag_pending: int = Field(description="待确认标签数")

    # Issues
    issues_critical: int = Field(description="严重问题数")
    issues_warning: int = Field(description="警告数")
    issues_info: int = Field(description="信息数")


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
