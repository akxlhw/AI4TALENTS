"""
Homepage API schemas.
首页数据响应模型
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class HotTechElementItem(BaseModel):
    """热门技术要素项"""

    tech_element_id: int = Field(description="技术要素ID")
    element_code: str = Field(description="技术要素代码")
    element_name: str = Field(description="技术要素名称")
    talent_count: int = Field(description="相关人才数", default=0)


class TopCountryItem(BaseModel):
    """主要国家项"""

    country_code: str = Field(description="国家代码")
    country_name: str | None = Field(default=None, description="国家名称")
    talent_count: int = Field(description="人才数", default=0)


class TopSchoolItem(BaseModel):
    """Top院校项"""

    school_id: int = Field(description="院校ID")
    school_name: str = Field(description="院校名称")
    country_name: str | None = Field(default=None, description="所在国家")
    country_code: str | None = Field(default=None, description="国家代码")
    talent_count: int = Field(description="人才数", default=0)


class HomepageHighlightsResponse(BaseModel):
    """首页聚合数据响应"""

    hot_tech_elements: list[HotTechElementItem] = Field(
        default_factory=list,
        description="热门技术要素列表"
    )
    top_countries: list[TopCountryItem] = Field(
        default_factory=list,
        description="主要国家列表"
    )
    top_schools: list[TopSchoolItem] = Field(
        default_factory=list,
        description="Top院校列表"
    )
    version: str = Field(description="数据版本")
    generated_at: str = Field(description="生成时间")
