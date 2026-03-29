"""
Talent Pool Schemas.
人才池相关DTO
"""
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime


class CreatePoolRequest(BaseModel):
    """创建人才池请求"""
    pool_name: str
    pool_type: str = "custom"
    scope_desc: Optional[str] = None


class UpdatePoolRequest(BaseModel):
    """更新人才池请求"""
    pool_name: Optional[str] = None
    scope_desc: Optional[str] = None
    pool_status: Optional[str] = None


class AddMemberRequest(BaseModel):
    """添加成员请求"""
    talent_id: int
    notes: Optional[str] = None


class TalentPoolResponse(BaseModel):
    """人才池响应"""
    pool_id: int
    pool_name: str
    pool_type: str
    owner_user_id: int
    scope_desc: Optional[str] = None
    pool_status: str
    member_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class PoolMemberResponse(BaseModel):
    """人才池成员响应"""
    member_id: int
    pool_id: int
    talent_id: int
    name: str
    name_en: Optional[str] = None
    role_type: str
    school_id: Optional[int] = None
    school_name: Optional[str] = None
    current_title: Optional[str] = None
    works_count: int = 0
    cited_by_count: int = 0
    h_index: int = 0
    notes: Optional[str] = None
    added_at: Optional[str] = None


class PoolListResponse(BaseModel):
    """人才池列表响应"""
    items: List[TalentPoolResponse]
    total: int


class UpdateFollowupRequest(BaseModel):
    """更新跟进状态请求"""
    followup_status: str


# 跟进状态选项
FOLLOWUP_STATUS_OPTIONS = [
    {"value": "new_found", "label": "新发现"},
    {"value": "reviewed", "label": "已审阅"},
    {"value": "followed", "label": "已跟进"},
    {"value": "pending_evaluation", "label": "待评估"},
    {"value": "recommend_contact", "label": "推荐联系"},
    {"value": "no_followup", "label": "暂不跟进"},
]
