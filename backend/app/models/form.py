import uuid
import enum
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    ForeignKey,
    DateTime,
    BigInteger,
    Text,
    Index,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import relationship
from app.database import Base


class FormNames:
    POLLUTION_REPORTING = "Pollution Reporting Form"
    WETLAND_SAMPLING = "Monthly Wetland Sampling"
    INDIGENOUS_KNOWLEDGE = "Indigenous Knowledge Record"
    LAB_QA = "Lab QA Report"
    SATELLITE_CLIMATE = "External Satellite & Climate Data"


class QuestionType(str, enum.Enum):
    input = "input"
    number = "number"
    cascade = "cascade"
    text = "text"
    date = "date"
    option = "option"
    multiple_option = "multiple_option"
    tree = "tree"
    table = "table"
    autofield = "autofield"
    image = "image"
    geo = "geo"
    geotrace = "geotrace"
    geoshape = "geoshape"
    entity = "entity"
    signature = "signature"
    attachment = "attachment"


class Form(Base):
    __tablename__ = "form"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(Text, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    uuid = Column(
        PG_UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False
    )
    kobo_asset_id = Column(String(255), nullable=True, unique=True, index=True)
    parent_id = Column(
        Integer, ForeignKey("form.id", ondelete="CASCADE"), nullable=True
    )
    type = Column(Integer, default=1, nullable=False)
    status = Column(Integer, default=1, nullable=False)
    published_at = Column(DateTime, nullable=True)
    previous_version_id = Column(
        Integer, ForeignKey("form.id", ondelete="SET NULL"), nullable=True
    )
    active_version_id = Column(
        Integer,
        ForeignKey(
            "form_published_version.id",
            ondelete="SET NULL",
            use_alter=True,
            name="form_active_version_id_fkey",
        ),
        nullable=True,
    )

    parent = relationship(
        "Form",
        remote_side=[id],
        foreign_keys=[parent_id],
        back_populates="children",
    )
    children = relationship(
        "Form",
        remote_side=[parent_id],
        foreign_keys=[parent_id],
        back_populates="parent",
    )
    previous_version = relationship(
        "Form", remote_side=[id], foreign_keys=[previous_version_id]
    )
    active_version = relationship(
        "FormPublishedVersion",
        foreign_keys=[active_version_id],
        post_update=True,
    )

    question_groups = relationship(
        "QuestionGroup", back_populates="form", cascade="all, delete-orphan"
    )
    questions = relationship(
        "Question", back_populates="form", cascade="all, delete-orphan"
    )
    published_versions = relationship(
        "FormPublishedVersion",
        foreign_keys="[FormPublishedVersion.form_id]",
        cascade="all, delete-orphan",
        back_populates="form",
    )


class QuestionGroup(Base):
    __tablename__ = "question_group"

    id = Column(Integer, primary_key=True, index=True)
    form_id = Column(
        Integer, ForeignKey("form.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String(255), nullable=False)
    label = Column(Text, nullable=True)
    order = Column(BigInteger, nullable=True)
    repeatable = Column(Boolean, default=False, nullable=False)
    repeat_text = Column(String(255), nullable=True)
    deleted_at = Column(DateTime, nullable=True)

    form = relationship("Form", back_populates="question_groups")
    questions = relationship(
        "Question",
        back_populates="question_group",
        cascade="all, delete-orphan",
    )


# Conditional unique constraint: active groups must have unique name per form
Index(
    "unique_active_form_question_group",
    QuestionGroup.form_id,
    QuestionGroup.name,
    unique=True,
    postgresql_where=QuestionGroup.deleted_at.is_(None),
)


class Question(Base):
    __tablename__ = "question"

    id = Column(Integer, primary_key=True, index=True)
    form_id = Column(
        Integer, ForeignKey("form.id", ondelete="CASCADE"), nullable=False
    )
    question_group_id = Column(
        Integer,
        ForeignKey("question_group.id", ondelete="CASCADE"),
        nullable=False,
    )
    order = Column(BigInteger, nullable=True)
    label = Column(Text, nullable=False)
    short_label = Column(Text, nullable=True)
    name = Column(String(255), nullable=True)
    type = Column(SQLEnum(QuestionType, name="question_type"), nullable=False)
    meta = Column(Boolean, default=False, nullable=False)
    required = Column(Boolean, default=True, nullable=False)
    rule = Column(JSONB, nullable=True)
    dependency = Column(JSONB, nullable=True)
    dependency_rule = Column(String(3), nullable=True)
    api = Column(JSONB, nullable=True)
    extra = Column(JSONB, nullable=True)
    tooltip = Column(JSONB, nullable=True)
    fn = Column(JSONB, nullable=True)
    pre = Column(JSONB, nullable=True)
    display_only = Column(Boolean, default=False, nullable=True)
    deleted_at = Column(DateTime, nullable=True)

    form = relationship("Form", back_populates="questions")
    question_group = relationship("QuestionGroup", back_populates="questions")
    options = relationship(
        "Option", back_populates="question", cascade="all, delete-orphan"
    )

    @property
    def validation_min(self):
        return self.rule.get("min") if self.rule else None

    @property
    def validation_max(self):
        return self.rule.get("max") if self.rule else None


# Conditional unique constraint: active questions unique per form
Index(
    "unique_active_form_question",
    Question.form_id,
    Question.name,
    unique=True,
    postgresql_where=Question.deleted_at.is_(None),
)


class Option(Base):
    __tablename__ = "option"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(
        Integer, ForeignKey("question.id", ondelete="CASCADE"), nullable=False
    )
    order = Column(BigInteger, nullable=True)
    label = Column(Text, nullable=True)
    value = Column(String(255), nullable=True)
    other = Column(Boolean, default=False, nullable=False)
    color = Column(Text, nullable=True)

    question = relationship("Question", back_populates="options")


Index("unique_question_option", Option.question_id, Option.value, unique=True)


class FormPublishedVersion(Base):
    __tablename__ = "form_published_version"

    id = Column(Integer, primary_key=True, index=True)
    form_id = Column(
        Integer, ForeignKey("form.id", ondelete="CASCADE"), nullable=False
    )
    version = Column(Integer, nullable=False)
    schema = Column(JSONB, nullable=False)
    published_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    published_by_id = Column(PG_UUID(as_uuid=True), nullable=True)

    form = relationship(
        "Form", foreign_keys=[form_id], back_populates="published_versions"
    )


Index(
    "unique_form_published_version",
    FormPublishedVersion.form_id,
    FormPublishedVersion.version,
    unique=True,
)
