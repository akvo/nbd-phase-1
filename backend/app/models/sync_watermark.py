import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class SyncWatermark(Base):
    __tablename__ = "sync_watermarks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_system = Column(String(50), nullable=False)
    form_id = Column(String(100), nullable=True)
    last_sync_time = Column(DateTime, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "source_system", "form_id", name="uq_sync_watermarks_source_form"
        ),
    )
