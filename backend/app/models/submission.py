from enum import Enum
from typing import Optional
import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
    Float,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base


class SubmissionStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class Datapoint(Base):
    __tablename__ = "datapoint"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(
        UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False
    )
    form_id = Column(
        Integer, ForeignKey("form.id", ondelete="RESTRICT"), nullable=False
    )
    published_version_id = Column(
        Integer,
        ForeignKey("form_published_version.id", ondelete="SET NULL"),
        nullable=True,
    )
    name = Column(Text, nullable=True)

    basin_id = Column(
        UUID(as_uuid=True),
        ForeignKey("basins.id", ondelete="SET NULL"),
        nullable=True,
    )
    wetland_id = Column(
        UUID(as_uuid=True),
        ForeignKey("wetlands.id", ondelete="SET NULL"),
        nullable=True,
    )
    site_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="SET NULL"),
        nullable=True,
    )

    geo = Column(JSONB, nullable=True)
    created_by_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, nullable=True)
    duration = Column(Integer, default=0, nullable=False)
    submitter = Column(String(255), nullable=True)
    status = Column(
        String(20), default=SubmissionStatus.PENDING, nullable=False
    )

    # Relationships
    form = relationship("Form", foreign_keys=[form_id])
    published_version = relationship(
        "FormPublishedVersion", foreign_keys=[published_version_id]
    )
    basin = relationship("Basin")
    wetland = relationship("Wetland")
    site = relationship("Site")
    created_by = relationship("User")
    answers = relationship(
        "Answer", back_populates="datapoint", cascade="all, delete-orphan"
    )

    @property
    def form_name(self) -> str:
        return self.form.name if self.form else "Unknown Form"

    @property
    def basin_name(self) -> Optional[str]:
        return self.basin.name if self.basin else None

    @property
    def wetland_name(self) -> Optional[str]:
        return self.wetland.name if self.wetland else None

    @property
    def site_name(self) -> Optional[str]:
        return self.site.name if self.site else None

    @property
    def creator_name(self) -> Optional[str]:
        if self.created_by:
            return self.created_by.display_name or self.created_by.email
        return self.submitter

    @property
    def creator_email(self) -> Optional[str]:
        if self.created_by:
            return self.created_by.email
        return None

    __table_args__ = (
        CheckConstraint(
            "(basin_id IS NOT NULL)::int + "
            "(wetland_id IS NOT NULL)::int + "
            "(site_id IS NOT NULL)::int = 1",
            name="chk_polymorphic_anchor",
        ),
    )


class Answer(Base):
    __tablename__ = "answer"

    id = Column(Integer, primary_key=True, index=True)
    datapoint_id = Column(
        Integer, ForeignKey("datapoint.id", ondelete="CASCADE"), nullable=False
    )
    question_id = Column(
        Integer, ForeignKey("question.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(Text, nullable=True)  # holds qualitative/text answers
    value = Column(Float, nullable=True)  # holds numeric/float answers
    options = Column(
        JSONB, nullable=True
    )  # holds array of selected option values
    created_by_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, nullable=True)
    index = Column(Integer, default=0, nullable=False)

    # Relationships
    datapoint = relationship("Datapoint", back_populates="answers")
    question = relationship("Question")
    created_by = relationship("User")

    @property
    def read_url(self) -> Optional[str]:
        return getattr(self, "_read_url", None)

    @read_url.setter
    def read_url(self, value: str):
        self._read_url = value

    __table_args__ = (
        UniqueConstraint(
            "datapoint_id",
            "question_id",
            "index",
            name="unique_datapoint_question_index",
        ),
    )
