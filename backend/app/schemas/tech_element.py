"""
Tech Element Schemas.
技术要素相关DTO
"""

from __future__ import annotations

from pydantic import BaseModel


class TechDirectionResponse(BaseModel):
    """技术方向响应"""
    tech_direction_id: int
    direction_code: str
    direction_name: str
    direction_name_en: str | None = None
    tech_element_id: int
    sort_order: int = 0

    class Config:
        from_attributes = True


class TechElementResponse(BaseModel):
    """技术要素响应"""
    tech_element_id: int
    element_code: str
    element_name: str
    element_name_en: str | None = None
    element_desc: str | None = None
    sort_order: int = 0
    directions: list[TechDirectionResponse] = []

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
    professor_count: int
    student_count: int
    direction_count: int
    country_count: int
    school_count: int


class OverallStatsResponse(BaseModel):
    """总体统计响应（用户权限范围内）"""
    talent_count: int
    professor_count: int
    student_count: int
    country_count: int
    school_count: int
    tech_element_count: int
    tech_direction_count: int


class CountryDistributionItem(BaseModel):
    """国家分布项"""
    country_code: str
    country_name: str
    talent_count: int


class SchoolDistributionItem(BaseModel):
    """院校分布项"""
    school_id: int
    school_name: str
    country_name: str | None = None
    talent_count: int


class TechElementListResponse(BaseModel):
    """技术要素列表响应"""
    items: list[TechElementResponse]
    total: int


class CountryDistributionResponse(BaseModel):
    """国家分布响应"""
    items: list[CountryDistributionItem]


class SchoolDistributionResponse(BaseModel):
    """院校分布响应"""
    items: list[SchoolDistributionItem]
    total: int


# For talent list in tech element page
class TalentInTechElement(BaseModel):
    """技术要素页的人才项"""
    talent_id: int
    name: str
    name_en: str | None = None
    role_type: str
    school_name: str | None = None
    current_title: str | None = None
    h_index: int = 0
    works_count: int = 0
    topic_tags: list[str] = []
    openalex_topics: list[str] = []  # OpenAlex研究主题

    class Config:
        from_attributes = True
