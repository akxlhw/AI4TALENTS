"""
JD Match models.
岗位匹配模型 - v1.4
"""

from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class JDMatchSession(Base, TimestampMixin):
    """岗位匹配会话表

    存储每次岗位匹配的会话信息。
    """

    __tablename__ = "jd_match_session"

    session_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("iam_user_account.user_id"),
        nullable=False,
        index=True,
        comment="用户ID"
    )
    jd_text = Column(Text, nullable=False, comment="原始 JD 文本")
    jd_features = Column(JSON, nullable=True, comment="LLM 解析出的 JD 特征")
    status = Column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
        comment="状态: pending/completed/failed"
    )
    created_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True, comment="完成时间")

    # Relationships
    results = relationship(
        "JDMatchResult",
        back_populates="session",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<JDMatchSession(session_id={self.session_id}, status={self.status})>"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "jd_text": self.jd_text[:100] + "..." if len(self.jd_text or "") > 100 else self.jd_text,
            "jd_features": self.jd_features,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class JDMatchResult(Base, TimestampMixin):
    """岗位匹配结果表

    存储匹配会话的结果列表。
    """

    __tablename__ = "jd_match_result"

    result_id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(
        Integer,
        ForeignKey("jd_match_session.session_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="会话ID"
    )
    talent_id = Column(
        Integer,
        ForeignKey("core_talent.talent_id"),
        nullable=False,
        index=True,
        comment="人才ID"
    )

    # Scores
    overall_score = Column(Float, comment="综合匹配分数 0-100")
    skill_score = Column(Float, comment="技能匹配分数")
    research_score = Column(Float, comment="研究方向匹配分数")
    experience_score = Column(Float, comment="经验匹配分数")

    # Match details
    match_reasons = Column(JSON, comment="匹配原因列表")
    highlight_skills = Column(JSON, comment="匹配的技能列表")

    created_at = Column(DateTime, nullable=False)

    # Relationships
    session = relationship("JDMatchSession", back_populates="results")

    def __repr__(self):
        return f"<JDMatchResult(result_id={self.result_id}, score={self.overall_score})>"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "result_id": self.result_id,
            "session_id": self.session_id,
            "talent_id": self.talent_id,
            "overall_score": self.overall_score,
            "skill_score": self.skill_score,
            "research_score": self.research_score,
            "experience_score": self.experience_score,
            "match_reasons": self.match_reasons,
            "highlight_skills": self.highlight_skills,
        }
