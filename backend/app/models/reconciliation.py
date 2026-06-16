import uuid
from sqlalchemy import (
    Column,
    String,
    ForeignKey,
    Numeric,
    DateTime,
    UniqueConstraint,
    Index,
    Integer,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class ReconciliationLog(Base):
    __tablename__ = "reconciliation_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    citizen_id = Column(
        UUID(as_uuid=True),
        ForeignKey("citizens.id", ondelete="CASCADE"),
        nullable=False,
    )
    citizen_datapoint_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sampling_records.id", ondelete="CASCADE"),
        nullable=False,
    )
    lab_datapoint_id = Column(
        Integer,
        ForeignKey("datapoint.id", ondelete="CASCADE"),
        nullable=False,
    )
    parameter_name = Column(String(50), nullable=False)
    citizen_value = Column(Numeric(6, 2), nullable=False)
    lab_value = Column(Numeric(6, 2), nullable=False)
    calculated_variance = Column(Numeric(6, 2), nullable=False)
    # status can be 'DISCREPANT' or 'RECONCILIATION_OK'
    status = Column(String(20), nullable=False)
    reconciled_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    citizen = relationship("Citizen", back_populates="reconciliation_logs")
    citizen_datapoint = relationship("SamplingRecord")
    lab_datapoint = relationship("Datapoint")

    __table_args__ = (
        UniqueConstraint(
            "citizen_id",
            "citizen_datapoint_id",
            "lab_datapoint_id",
            "parameter_name",
            name="uq_reconciliation_log_pair",
        ),
        Index("idx_reconciliation_log_citizen_id", "citizen_id"),
        Index("idx_reconciliation_log_status", "status"),
    )
