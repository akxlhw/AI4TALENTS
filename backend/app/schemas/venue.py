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
    venue_type: str = Field(default="conference", max_length=30, description="类型: conference/journal/workshop")
    country_code: str | None = Field(None, max_length=10, description="国家代码")
    publisher: str | None = Field(None, max_length=100, description="出版商")
    description: str | None = Field(None, description="描述")
    is_enabled: bool = Field(default=True, description="是否启用")


class VenueCreate(VenueBase):
    """Venue creation schema"""
    pass


class VenueUpdate(BaseModel):
    """Venue update schema"""
    venue_name: str | None = Field(None, max_length=255)
    venue_name_en: str | None = Field(None, max_length=255)
    openalex_source_id: str | None = Field(None, max_length=50)
    venue_type: str | None = Field(None, max_length=30)
    country_code: str | None = Field(None, max_length=10)
    publisher: str | None = Field(None, max_length=100)
    description: str | None = None
    is_enabled: bool | None = None


class VenueResponse(VenueBase):
    """Venue response schema"""
    venue_id: int
    h_index: int = Field(default=0, description="H-index")
    works_count: int = Field(default=0, description="作品数")
    cited_by_count: int = Field(default=0, description="被引次数")
    last_collect_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class VenueListResponse(BaseModel):
    """Venue list response with pagination"""
    total: int
    items: list[VenueResponse]


# ============================================
# VenueTechBinding Schemas
# ============================================

class VenueTechBindingBase(BaseModel):
    """Venue-TechElement binding base schema"""
    venue_id: int = Field(..., description="Venue ID")
    tech_element_id: int = Field(..., description="技术要素ID")
    priority: int = Field(default=0, description="优先级")
    is_enabled: bool = Field(default=True, description="是否启用")


class VenueTechBindingCreate(VenueTechBindingBase):
    """Venue-TechElement binding creation schema"""
    pass


class VenueTechBindingBatchCreate(BaseModel):
    """Batch create bindings for a tech element"""
    tech_element_id: int = Field(..., description="技术要素ID")
    venue_ids: list[int] = Field(..., description="Venue ID列表")


class VenueTechBindingUpdate(BaseModel):
    """Venue-TechElement binding update schema"""
    priority: int | None = None
    is_enabled: bool | None = None


class VenueTechBindingResponse(VenueTechBindingBase):
    """Venue-TechElement binding response schema"""
    binding_id: int
    collect_status: str = Field(default="pending", description="采集状态")
    last_collect_at: datetime | None = None
    author_count: int = Field(default=0, description="采集作者数")
    work_count: int = Field(default=0, description="采集作品数")
    created_at: datetime
    updated_at: datetime

    # Related info
    venue: VenueResponse | None = None

    model_config = {"from_attributes": True}


class VenueTechBindingListResponse(BaseModel):
    """Venue-TechElement binding list response"""
    total: int
    items: list[VenueTechBindingResponse]


# ============================================
# VenueSubTask Schemas
# ============================================

class VenueSubTaskResponse(BaseModel):
    """Venue sub-task response schema"""
    sub_task_id: int
    task_id: int
    venue_id: int
    status: str
    time_window_start: datetime | None = None
    time_window_end: datetime | None = None
    estimated_works: int = 0  # 预估论文数（采集前获取）
    works_fetched: int = 0
    authors_fetched: int = 0
    new_authors: int = 0
    updated_authors: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class VenueSubTaskListResponse(BaseModel):
    """Venue sub-task list response"""
    total: int
    items: list[VenueSubTaskResponse]


# ============================================
# Migration Schemas
# ============================================

class MigrateCollectSourcesRequest(BaseModel):
    """Request to migrate collect_sources JSON to Venue tables"""
    tech_element_id: int = Field(..., description="技术要素ID")
    dry_run: bool = Field(default=False, description="是否只预览不执行")


class MigrateCollectSourcesResponse(BaseModel):
    """Response for collect_sources migration"""
    tech_element_id: int
    tech_element_name: str
    venues_found: int
    venues_created: int
    bindings_created: int
    venues: list[dict]
    message: str
