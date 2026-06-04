import uuid
from sqlalchemy import (
    Column,
    String,
    ForeignKey,
    DateTime,
    CheckConstraint,
    Index,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class FgdRecord(Base):
    __tablename__ = "fgd_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wetland_id = Column(
        UUID(as_uuid=True),
        ForeignKey("wetlands.id", ondelete="RESTRICT"),
        nullable=False,
    )
    fish_abundance = Column(String(15), nullable=False)
    water_clarity = Column(String(15), nullable=False)
    vegetation_cover = Column(String(15), nullable=False)
    conducted_at = Column(DateTime, nullable=False)

    wetland = relationship("Wetland")

    __table_args__ = (
        CheckConstraint(
            "fish_abundance IN ('Same', 'Slight', 'Moderate', 'Severe')",
            name="check_fgd_records_fish_abundance",
        ),
        CheckConstraint(
            "water_clarity IN ('Same', 'Somewhat Worse', 'Much Worse')",
            name="check_fgd_records_water_clarity",
        ),
        CheckConstraint(
            "vegetation_cover IN ('Same', 'Partial Loss', 'Severe Loss')",
            name="check_fgd_records_vegetation_cover",
        ),
        Index(
            "idx_fgd_records_wetland", "wetland_id", text("conducted_at DESC")
        ),
    )
