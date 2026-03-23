"""
Tech Element Schemas.
技术要素相关DTO
"""
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime


class TechDirectionResponse(BaseModel):
    """技术方向响应"""
    tech_direction_id: int
    direction_code: str
    direction_name: str
    direction_name_en: Optional[str] = None
    tech_element_id: int
    sort_order: int = 0

    class Config:
        from_attributes = True


class TechElementResponse(BaseModel):
    """技术要素响应"""
    tech_element_id: int
    element_code: str
    element_name: str
    element_name_en: Optional[str] = None
    element_desc: Optional[str] = None
    sort_order: int = 0
    directions: List[TechDirectionResponse] = []

    class Config:
        from_attributes = True


class TechElementSummary(BaseModel):
    """技术要素概要"""
    element_count: int
    direction_count: int
    talent_count: int


class TechElementStatsResponse(BaseModel):
    """技术要素统计响应"""
    talent_count: int
    direction_count: int
    country_count: int
    school_count: int


class CountryDistributionItem(BaseModel):
    """国家分布项"""
    country_id: int
    country_name: str
    country_code: Optional[str] = None
    talent_count: int


class SchoolDistributionItem(BaseModel):
    """院校分布项"""
    school_id: int
    school_name: str
    country_name: Optional[str] = None
    talent_count: int


class TechElementListResponse(BaseModel):
    """技术要素列表响应"""
    items: List[TechElementResponse]
    total: int


class CountryDistributionResponse(BaseModel):
    """国家分布响应"""
    items: List[CountryDistributionItem]


class SchoolDistributionResponse(BaseModel):
    """院校分布响应"""
    items: List[SchoolDistributionItem]
    total: int


# For talent list in tech element page
class TalentInTechElement(BaseModel):
    """技术要素页的人才项"""
    talent_id: int
    name: str
    name_en: Optional[str] = None
    role_type: str
    school_name: Optional[str] = None
    current_title: Optional[str] = None
    h_index: int = 0
    works_count: int = 0
    topic_tags: List[str] = []

    class Config:
        from_attributes = True
