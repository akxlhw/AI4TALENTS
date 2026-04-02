"""
Audit log model.
"""
from sqlalchemy import JSON, Column, DateTime, Integer, String, Text

from app.core.database import Base


class AuditOperationLog(Base):
    """Audit log for tracking user operations."""

    __tablename__ = "audit_operation_log"

    log_id = Column(Integer, primary_key=True, index=True)

    # Timing
    event_time = Column(DateTime, nullable=False, index=True)

    # User info
    user_id = Column(Integer, nullable=True, index=True)
    user_ip = Column(String(50), nullable=True)

    # Event info
    event_type = Column(String(50), nullable=False, index=True)  # 'authentication', 'authorization', 'data_operation', etc.
    event_subtype = Column(String(50), nullable=True)

    # Resource info
    resource_type = Column(String(50), nullable=True, index=True)  # 'user', 'talent', 'school', etc.
    resource_id = Column(String(100), nullable=True)

    # Operation
    operation = Column(String(50), nullable=False)  # 'create', 'read', 'update', 'delete', 'export'
    operation_detail = Column(JSON, nullable=True)

    # Result
    status = Column(String(20), nullable=False)  # 'success', 'failure', 'partial'
    error_message = Column(Text, nullable=True)

    # Request tracking
    request_id = Column(String(100), nullable=True, index=True)
    user_agent = Column(Text, nullable=True)

    def __repr__(self):
        return f"<AuditOperationLog(log_id={self.log_id}, type={self.event_type}, operation={self.operation})>"
