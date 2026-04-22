"""
Tech Domain Schemas.
技术领域相关DTO
"""

from __future__ import annotations

from pydantic import BaseModel


class TechDirectionResponse(BaseModel):
    """技术方向响应"""
    tech_direction_id: int
    direction_code: str
    direction_name: str
    direction_name_en: str | None = None
    tech_domain_id: int
    sort_order: int = 0

    class Config:
        from_attributes = True


class TechDomainResponse(BaseModel):
    """技术领域响应"""
    tech_domain_id: int
    domain_code: str
    domain_name: str
    domain_name_en: str | None = None
    domain_desc: str | None = None
    sort_order: int = 0
    directions: list[TechDirectionResponse] = []

    class Config:
        from_attributes = True


class TechDomainSummary(BaseModel):
    """技术领域概要"""
    domain_count: int
    direction_count: int
    talent_count: int


class TechDomainStatsResponse(BaseModel):
    """技术领域统计响应"""
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
    tech_domain_count: int
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


class TechDomainListResponse(BaseModel):
    """技术领域列表响应"""
    items: list[TechDomainResponse]
    total: int


class CountryDistributionResponse(BaseModel):
    """国家分布响应"""
    items: list[CountryDistributionItem]


class SchoolDistributionResponse(BaseModel):
    """院校分布响应"""
    items: list[SchoolDistributionItem]
    total: int


# For talent list in tech domain page
class TalentInTechDomain(BaseModel):
    """技术领域页的人才项"""
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
