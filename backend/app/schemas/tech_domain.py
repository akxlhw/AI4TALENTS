"""
Tech Domain Schemas.
技术领域相关DTO
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class TechDirectionResponse(BaseModel):
    """技术方向响应"""

    tech_direction_id: int = Field(description="技术方向ID")
    direction_code: str = Field(description="方向代码")
    direction_name: str = Field(description="方向名称")
    direction_name_en: str | None = Field(default=None, description="方向英文名")
    tech_domain_id: int = Field(description="所属技术领域ID")
    sort_order: int = Field(default=0, description="排序顺序")

    class Config:
        from_attributes = True


class TechDomainResponse(BaseModel):
    """技术领域响应"""

    tech_domain_id: int = Field(description="技术领域ID")
    domain_code: str = Field(description="领域代码")
    domain_name: str = Field(description="领域名称")
    domain_name_en: str | None = Field(default=None, description="领域英文名")
    domain_desc: str | None = Field(default=None, description="领域描述")
    sort_order: int = Field(default=0, description="排序顺序")
    directions: list[TechDirectionResponse] = Field(default=[], description="包含的技术方向列表")

    class Config:
        from_attributes = True


class TechDomainSummary(BaseModel):
    """技术领域概要"""

    domain_count: int = Field(description="技术领域数量")
    direction_count: int = Field(description="技术方向数量")
    talent_count: int = Field(description="人才数量")


class TechDomainStatsResponse(BaseModel):
    """技术领域统计响应"""

    talent_count: int = Field(description="人才总数")
    professor_count: int = Field(description="教授数量")
    student_count: int = Field(description="学生数量")
    direction_count: int = Field(description="技术方向数量")
    country_count: int = Field(description="覆盖国家数量")
    school_count: int = Field(description="覆盖院校数量")


class OverallStatsResponse(BaseModel):
    """总体统计响应（用户权限范围内）"""

    talent_count: int = Field(description="人才总数")
    professor_count: int = Field(description="教授数量")
    student_count: int = Field(description="学生数量")
    country_count: int = Field(description="覆盖国家数量")
    school_count: int = Field(description="覆盖院校数量")
    tech_domain_count: int = Field(description="技术领域数量")
    tech_direction_count: int = Field(description="技术方向数量")


class CountryDistributionItem(BaseModel):
    """国家分布项"""

    country_code: str = Field(description="国家代码")
    country_name: str = Field(description="国家名称")
    talent_count: int = Field(description="人才数量")


class SchoolDistributionItem(BaseModel):
    """院校分布项"""

    school_id: int = Field(description="院校ID")
    school_name: str = Field(description="院校名称")
    country_name: str | None = Field(default=None, description="所属国家")
    talent_count: int = Field(description="人才数量")


class TechDomainListResponse(BaseModel):
    """技术领域列表响应"""

    items: list[TechDomainResponse] = Field(description="技术领域列表")
    total: int = Field(description="总数")


class CountryDistributionResponse(BaseModel):
    """国家分布响应"""

    items: list[CountryDistributionItem] = Field(description="国家分布列表")


class SchoolDistributionResponse(BaseModel):
    """院校分布响应"""

    items: list[SchoolDistributionItem] = Field(description="院校分布列表")
    total: int = Field(description="总数")


# For talent list in tech domain page
class TalentInTechDomain(BaseModel):
    """技术领域页的人才项"""

    talent_id: int = Field(description="人才ID")
    name: str = Field(description="姓名")
    name_en: str | None = Field(default=None, description="英文名")
    role_type: str = Field(description="角色类型")
    school_name: str | None = Field(default=None, description="院校名称")
    current_title: str | None = Field(default=None, description="当前职称")
    h_index: int = Field(default=0, description="H指数")
    works_count: int = Field(default=0, description="论文数量")
    topic_tags: list[str] = Field(default=[], description="技术标签")
    openalex_topics: list[str] = Field(default=[], description="OpenAlex研究主题")

    class Config:
        from_attributes = True
