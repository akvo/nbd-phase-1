import uuid
from sqlalchemy import (
    Column,
    String,
    ForeignKey,
    Numeric,
    DateTime,
    CheckConstraint,
    Index,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class SamplingRecord(Base):
    __tablename__ = "sampling_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="RESTRICT"),
        nullable=False,
    )
    ph_value = Column(Numeric(4, 2), nullable=False)
    temp_value = Column(Numeric(4, 1), nullable=False)
    do_value = Column(Numeric(4, 1), nullable=False)
    invasive_macrophytes = Column(Numeric(5, 2), nullable=False)
    cpue_value = Column(Numeric(6, 2), nullable=True)
    water_level = Column(String(10), nullable=False)
    sampled_at = Column(DateTime, nullable=False)

    site = relationship("Site")

    __table_args__ = (
        CheckConstraint(
            "ph_value BETWEEN 2.0 AND 10.0",
            name="check_sampling_records_ph_value",
        ),
        CheckConstraint(
            "temp_value BETWEEN 5.0 AND 50.0",
            name="check_sampling_records_temp_value",
        ),
        CheckConstraint(
            "do_value BETWEEN 0.5 AND 35.0",
            name="check_sampling_records_do_value",
        ),
        CheckConstraint(
            "invasive_macrophytes BETWEEN 0.0 AND 100.0",
            name="check_sampling_records_invasive_macrophytes",
        ),
        CheckConstraint(
            "water_level IN ('HIGH', 'MEDIUM', 'LOW')",
            name="check_sampling_records_water_level",
        ),
        Index(
            "idx_sampling_records_site_date",
            "site_id",
            text("sampled_at DESC"),
        ),
    )
