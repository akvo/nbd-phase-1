import uuid
from sqlalchemy import Column, String, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Citizen(Base):
    __tablename__ = "citizens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone_number = Column(String(50), nullable=False)
    site_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="RESTRICT"),
        nullable=False,
    )
    role = Column(String(20), nullable=False)

    site = relationship("Site")

    __table_args__ = (
        CheckConstraint(
            "role IN ('WATCHER', 'SCIENTIST')",
            name="check_citizens_role",
        ),
    )
