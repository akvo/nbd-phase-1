import uuid
from sqlalchemy import (
    Column,
    String,
    ForeignKey,
    Numeric,
    DateTime,
    text,
    CheckConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class HealthScore(Base):
    __tablename__ = "health_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
    )
    wqi_score = Column(Numeric(3, 2), nullable=False)
    composite_score = Column(Numeric(3, 2), nullable=False)
    ik_signal_value = Column(Numeric(3, 2), nullable=False)
    adjusted_score = Column(Numeric(3, 2), nullable=False)
    health_class = Column(String(1), nullable=False)
    calculated_at = Column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )

    site = relationship("Site")

    __table_args__ = (
        CheckConstraint(
            "wqi_score BETWEEN 0.00 AND 1.00",
            name="check_health_scores_wqi_score",
        ),
        CheckConstraint(
            "composite_score BETWEEN 0.00 AND 1.00",
            name="check_health_scores_composite_score",
        ),
        CheckConstraint(
            "ik_signal_value BETWEEN 0.00 AND 1.00",
            name="check_health_scores_ik_signal_value",
        ),
        CheckConstraint(
            "adjusted_score BETWEEN 0.00 AND 1.00",
            name="check_health_scores_adjusted_score",
        ),
        CheckConstraint(
            "health_class IN ('A', 'B', 'C', 'D', 'E')",
            name="check_health_scores_health_class",
        ),
        Index("idx_health_scores_site", "site_id", text("calculated_at DESC")),
    )
