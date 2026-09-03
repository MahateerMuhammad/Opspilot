import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB

from .base import Base

class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    key = Column(String(255), nullable=False, index=True)
    tool_name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False) # e.g., "completed", "in_progress"
    result_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
