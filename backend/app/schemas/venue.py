"""
Venue and VenueTechBinding Pydantic schemas.
顶会顶刊配置相关DTO
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

# ============================================
# Venue Schemas
# ============================================


class VenueBase(BaseModel):
    """Venue base schema"""

    venue_code: str = Field(..., max_length=50, description="Venue代码")
    venue_name: str = Field(..., max_length=255, description="Venue名称")
    venue_name_en: str | None = Field(None, max_length=255, description="英文名称")
    openalex_source_id: str | None = Field(None, max_length=50, description="OpenAlex Source ID")
    venue_type: str = Field(
        default="conference", max_length=30, description="类型: conference/journal/workshop"
    )
    country_code: str | None = Field(None, max_length=10, description="国家代码")
    publisher: str | None = Field(None, max_length=100, description="出版商")
    description: str | None = Field(None, description="描述")
    is_enabled: bool = Field(default=True, description="是否启用")


class VenueCreate(VenueBase):
    """Venue creation schema"""

    pass


class VenueUpdate(BaseModel):
    """Venue update schema"""

    venue_name: str | None = Field(None, max_length=255, description="Venue名称")
    venue_name_en: str | None = Field(None, max_length=255, description="英文名称")
    openalex_source_id: str | None = Field(None, max_length=50, description="OpenAlex Source ID")
    venue_type: str | None = Field(
        None, max_length=30, description="类型: conference/journal/workshop"
    )
    country_code: str | None = Field(None, max_length=10, description="国家代码")
    publisher: str | None = Field(None, max_length=100, description="出版商")
    description: str | None = Field(None, description="描述")
    is_enabled: bool | None = Field(None, description="是否启用")


class VenueResponse(VenueBase):
    """Venue response schema"""

    venue_id: int = Field(description="Venue ID")
    h_index: int = Field(default=0, description="H-index")
    works_count: int = Field(default=0, description="作品数")
    cited_by_count: int = Field(default=0, description="被引次数")
    last_collect_at: datetime | None = Field(default=None, description="上次采集时间")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")

    model_config = {"from_attributes": True}


class VenueListResponse(BaseModel):
    """Venue list response with pagination"""

    total: int = Field(description="总数")
    items: list[VenueResponse] = Field(description="Venue列表")


# ============================================
# VenueTechBinding Schemas
# ============================================


class VenueTechBindingBase(BaseModel):
    """Venue-TechDomain binding base schema"""

    venue_id: int = Field(..., description="Venue ID")
    tech_domain_id: int = Field(..., description="技术领域ID")
    priority: int = Field(default=0, description="优先级")
    is_enabled: bool = Field(default=True, description="是否启用")


class VenueTechBindingCreate(VenueTechBindingBase):
    """Venue-TechDomain binding creation schema"""

    pass


class VenueTechBindingBatchCreate(BaseModel):
    """Batch create bindings for a tech domain"""

    tech_domain_id: int = Field(..., description="技术领域ID")
    venue_ids: list[int] = Field(..., description="Venue ID列表")


class VenueTechBindingUpdate(BaseModel):
    """Venue-TechDomain binding update schema"""

    priority: int | None = Field(None, description="优先级")
    is_enabled: bool | None = Field(None, description="是否启用")


class VenueTechBindingResponse(VenueTechBindingBase):
    """Venue-TechDomain binding response schema"""

    binding_id: int = Field(description="绑定ID")
    collect_status: str = Field(default="pending", description="采集状态")
    last_collect_at: datetime | None = Field(default=None, description="上次采集时间")
    author_count: int = Field(default=0, description="采集作者数")
    work_count: int = Field(default=0, description="采集作品数")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")

    # Related info
    venue: VenueResponse | None = Field(default=None, description="关联Venue信息")

    model_config = {"from_attributes": True}


class VenueTechBindingListResponse(BaseModel):
    """Venue-TechDomain binding list response"""

    total: int = Field(description="总数")
    items: list[VenueTechBindingResponse] = Field(description="绑定列表")


# ============================================
# VenueSubTask Schemas
# ============================================


class VenueSubTaskResponse(BaseModel):
    """Venue sub-task response schema"""

    sub_task_id: int = Field(description="子任务ID")
    task_id: int = Field(description="所属任务ID")
    venue_id: int = Field(description="Venue ID")
    status: str = Field(description="状态: pending/running/completed/failed")
    time_window_start: datetime | None = Field(default=None, description="时间窗口起始")
    time_window_end: datetime | None = Field(default=None, description="时间窗口结束")
    estimated_works: int = Field(default=0, description="预估论文数（采集前获取）")
    works_fetched: int = Field(default=0, description="已获取论文数")
    authors_fetched: int = Field(default=0, description="已获取作者数")
    new_authors: int = Field(default=0, description="新作者数")
    updated_authors: int = Field(default=0, description="更新作者数")
    started_at: datetime | None = Field(default=None, description="开始时间")
    completed_at: datetime | None = Field(default=None, description="完成时间")
    error_message: str | None = Field(default=None, description="错误信息")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")

    model_config = {"from_attributes": True}


class VenueSubTaskListResponse(BaseModel):
    """Venue sub-task list response"""

    total: int = Field(description="总数")
    items: list[VenueSubTaskResponse] = Field(description="子任务列表")


# ============================================
# Migration Schemas
# ============================================


class MigrateCollectSourcesRequest(BaseModel):
    """Request to migrate collect_sources JSON to Venue tables"""

    tech_domain_id: int = Field(..., description="技术领域ID")
    dry_run: bool = Field(default=False, description="是否只预览不执行")


class BatchUpdateBindingsResponse(BaseModel):
    """批量更新绑定响应"""

    message: str = Field(description="操作结果消息")
    total_bindings: int = Field(description="绑定总数")
    enabled_bindings: int = Field(description="已启用绑定数")
    updated_count: int = Field(description="更新记录数")


class MigrateCollectSourcesResponse(BaseModel):
    """Response for collect_sources migration"""

    tech_domain_id: int = Field(description="技术领域ID")
    tech_domain_name: str = Field(description="技术领域名称")
    venues_found: int = Field(description="发现的Venue数量")
    venues_created: int = Field(description="创建的Venue数量")
    bindings_created: int = Field(description="创建的绑定数量")
    venues: list[dict] = Field(description="Venue详情列表")
    message: str = Field(description="操作结果消息")
