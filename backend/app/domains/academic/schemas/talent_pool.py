"""
Talent Pool Schemas.
人才池相关DTO
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CreatePoolRequest(BaseModel):
    """创建人才池请求"""

    pool_name: str = Field(..., min_length=1, max_length=100, description="人才池名称")
    pool_type: str = Field(default="custom", description="人才池类型: custom/system")
    scope_desc: str | None = Field(default=None, description="范围描述")


class UpdatePoolRequest(BaseModel):
    """更新人才池请求"""

    pool_name: str | None = Field(
        default=None, min_length=1, max_length=100, description="人才池名称"
    )
    scope_desc: str | None = Field(default=None, description="范围描述")
    pool_status: str | None = Field(default=None, description="状态: active/archived")


class AddMemberRequest(BaseModel):
    """添加成员请求"""

    talent_id: int = Field(..., description="人才ID")
    notes: str | None = Field(default=None, description="备注")


class TalentPoolResponse(BaseModel):
    """人才池响应"""

    pool_id: int = Field(description="人才池ID")
    pool_name: str = Field(description="人才池名称")
    pool_type: str = Field(description="人才池类型")
    owner_user_id: int = Field(description="创建者用户ID")
    scope_desc: str | None = Field(default=None, description="范围描述")
    pool_status: str = Field(description="状态")
    member_count: int = Field(default=0, description="成员数量")
    created_at: datetime = Field(description="创建时间")

    model_config = ConfigDict(from_attributes=True)


class PoolMemberResponse(BaseModel):
    """人才池成员响应"""

    member_id: int = Field(description="成员记录ID")
    pool_id: int = Field(description="所属人才池ID")
    talent_id: int = Field(description="人才ID")
    name: str = Field(description="姓名")
    name_en: str | None = Field(default=None, description="英文名")
    role_type: str = Field(description="角色类型: professor/student")
    school_id: int | None = Field(default=None, description="院校ID")
    school_name: str | None = Field(default=None, description="院校名称")
    current_title: str | None = Field(default=None, description="当前职称")
    works_count: int = Field(default=0, description="论文数量")
    cited_by_count: int = Field(default=0, description="被引次数")
    h_index: int = Field(default=0, description="H指数")
    notes: str | None = Field(default=None, description="备注")
    added_at: str | None = Field(default=None, description="加入时间")


class PoolListResponse(BaseModel):
    """人才池列表响应"""

    items: list[TalentPoolResponse] = Field(description="人才池列表")
    total: int = Field(description="总数")


class UpdateFollowupRequest(BaseModel):
    """更新跟进状态请求"""

    followup_status: str = Field(..., description="跟进状态")


# 跟进状态选项
FOLLOWUP_STATUS_OPTIONS = [
    {"value": "new_found", "label": "新发现"},
    {"value": "reviewed", "label": "已审阅"},
    {"value": "followed", "label": "已跟进"},
    {"value": "pending_evaluation", "label": "待评估"},
    {"value": "recommend_contact", "label": "推荐联系"},
    {"value": "no_followup", "label": "暂不跟进"},
]
