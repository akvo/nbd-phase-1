import uuid
from sqlalchemy import Column, String, ForeignKey, Text, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class ManagementAction(Base):
    __tablename__ = "management_actions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
    )
    status_color = Column(String(10), nullable=False)
    short_label = Column(String(50), nullable=False)
    description_text = Column(Text, nullable=False)

    site = relationship("Site")

    __table_args__ = (
        CheckConstraint(
            "status_color IN ('GREEN', 'YELLOW', 'RED')",
            name="check_management_actions_status_color",
        ),
        Index("idx_management_actions_site_color", "site_id", "status_color"),
    )
