"""
Talent Embedding model.
人才向量嵌入模型 - v1.4
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class TalentEmbedding(Base, TimestampMixin):
    """人才向量嵌入表

    存储人才的向量嵌入，用于语义搜索和相似度计算。
    支持多种向量类型：research（研究方向）、papers（论文标题）
    """

    __tablename__ = "core_talent_embedding"

    embedding_id = Column(Integer, primary_key=True, autoincrement=True)
    talent_id = Column(
        Integer,
        ForeignKey("core_talent.talent_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="关联人才ID"
    )
    vector_type = Column(
        String(20),
        nullable=False,
        default='research',
        index=True,
        comment="向量类型: research(研究方向) / papers(论文标题)"
    )
    # Note: embedding column is vector(1536) in PostgreSQL
    # For SQLAlchemy, we use a placeholder that gets handled by migration
    embedding = Column(String, nullable=False, comment="向量嵌入 (JSON或pgvector)")
    model_name = Column(
        String(100),
        nullable=False,
        comment="嵌入模型名称"
    )
    source_text_hash = Column(
        String(64),
        nullable=False,
        comment="源文本哈希，用于判断是否需要更新"
    )

    # Relationships
    talent = relationship("Talent", back_populates="embedding")

    # Table constraints
    __table_args__ = (
        UniqueConstraint('talent_id', 'vector_type', name='uq_talent_vector_type'),
    )

    def __repr__(self) -> str:
        return f"<TalentEmbedding(talent_id={self.talent_id}, type={self.vector_type}, model={self.model_name})>"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "embedding_id": self.embedding_id,
            "talent_id": self.talent_id,
            "vector_type": self.vector_type,
            "model_name": self.model_name,
            "source_text_hash": self.source_text_hash,
        }
