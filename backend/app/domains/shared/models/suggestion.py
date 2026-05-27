"""
Suggestion / Feedback model.
"""

from sqlalchemy import JSON, Column, ForeignKey, Integer, String, Text

from app.core.database import Base
from app.domains.shared.models.base import TimestampMixin


class Suggestion(Base, TimestampMixin):
    """User suggestion/feedback model."""

    __tablename__ = "shared_suggestion"

    suggestion_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("iam_user_account.user_id"),
        nullable=False,
        index=True,
    )
    category = Column(String(50), nullable=False)
    subject = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="open")
    admin_reply = Column(Text, nullable=True)
    attachments = Column(JSON, nullable=True, default=list)
