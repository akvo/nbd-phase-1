import uuid
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import (
    Column,
    String,
    ForeignKey,
    CheckConstraint,
    exists,
    and_,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Citizen(Base):
    __tablename__ = "citizens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone_number = Column(String(50), nullable=True)
    site_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="RESTRICT"),
        nullable=False,
    )
    role = Column(String(20), nullable=False)

    site = relationship("Site")
    reconciliation_logs = relationship(
        "ReconciliationLog",
        back_populates="citizen",
        cascade="all, delete-orphan",
    )

    @hybrid_property
    def needs_retraining(self) -> bool:
        """
        Dynamically checks if there is any discrepant reconciliation log.
        """
        return any(
            log.status == "DISCREPANT" for log in self.reconciliation_logs
        )

    @needs_retraining.expression
    def needs_retraining(cls):
        """
        SQL expression for filtering query by needs_retraining.
        """
        from app.models.reconciliation import ReconciliationLog

        return exists().where(
            and_(
                ReconciliationLog.citizen_id == cls.id,
                ReconciliationLog.status == "DISCREPANT",
            )
        )

    __table_args__ = (
        CheckConstraint(
            "role IN ('WATCHER', 'SCIENTIST')",
            name="check_citizens_role",
        ),
    )
