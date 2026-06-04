import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base


class DeadLetter(Base):
    __tablename__ = "dead_letters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_system = Column(String(50), nullable=False)
    raw_payload = Column(JSONB, nullable=False)
    error_reason = Column(Text, nullable=False)
    status = Column(String(20), default="Pending Triage", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_dead_letters_status_source", "status", "source_system"),
    )
