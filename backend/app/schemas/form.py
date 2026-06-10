from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.models.form import QuestionType
from app.services.translation import get_translation


class OptionBase(BaseModel):
    label: Optional[str] = None
    value: Optional[str] = None
    order: Optional[int] = None
    other: bool = False
    color: Optional[str] = None


class OptionCreate(OptionBase):
    question_id: int


class OptionResponse(OptionBase):
    id: int
    question_id: int

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_localized(cls, db_obj, lang: str):
        label = get_translation(db_obj.translations, lang, db_obj.label)
        return cls(
            id=db_obj.id,
            question_id=db_obj.question_id,
            label=label,
            value=db_obj.value,
            order=db_obj.order,
            other=db_obj.other,
            color=db_obj.color,
        )


class QuestionBase(BaseModel):
    name: Optional[str] = None
    label: str
    short_label: Optional[str] = None
    type: QuestionType
    required: bool = True
    order: Optional[int] = None
    meta: bool = False
    validation_min: Optional[float] = None
    validation_max: Optional[float] = None
    rule: Optional[Dict[str, Any]] = None
    dependency: Optional[Dict[str, Any]] = None
    dependency_rule: Optional[str] = None
    api: Optional[Dict[str, Any]] = None
    extra: Optional[Dict[str, Any]] = None
    tooltip: Optional[Dict[str, Any]] = None
    fn: Optional[Dict[str, Any]] = None
    pre: Optional[Dict[str, Any]] = None
    display_only: bool = False


class QuestionCreate(QuestionBase):
    form_id: int
    question_group_id: int


class QuestionResponse(QuestionBase):
    id: int
    form_id: int
    question_group_id: int
    options: List[OptionResponse] = []

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_localized(cls, db_obj, lang: str):
        label = get_translation(db_obj.translations, lang, db_obj.label)
        short_label = (
            get_translation(db_obj.translations, lang, db_obj.short_label)
            if db_obj.short_label
            else db_obj.short_label
        )
        options = [
            OptionResponse.from_orm_localized(opt, lang)
            for opt in db_obj.options
        ]
        return cls(
            id=db_obj.id,
            form_id=db_obj.form_id,
            question_group_id=db_obj.question_group_id,
            name=db_obj.name,
            label=label,
            short_label=short_label,
            type=db_obj.type,
            required=db_obj.required,
            order=db_obj.order,
            meta=db_obj.meta,
            rule=db_obj.rule,
            dependency=db_obj.dependency,
            dependency_rule=db_obj.dependency_rule,
            api=db_obj.api,
            extra=db_obj.extra,
            tooltip=db_obj.tooltip,
            fn=db_obj.fn,
            pre=db_obj.pre,
            display_only=db_obj.display_only,
            options=options,
        )


class QuestionGroupBase(BaseModel):
    name: str
    label: Optional[str] = None
    order: Optional[int] = None
    repeatable: bool = False
    repeat_text: Optional[str] = None


class QuestionGroupCreate(QuestionGroupBase):
    form_id: int


class QuestionGroupResponse(QuestionGroupBase):
    id: int
    form_id: int
    questions: List[QuestionResponse] = []

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_localized(cls, db_obj, lang: str):
        label = (
            get_translation(db_obj.translations, lang, db_obj.label)
            if db_obj.label
            else db_obj.label
        )
        questions = [
            QuestionResponse.from_orm_localized(q, lang)
            for q in db_obj.questions
        ]
        return cls(
            id=db_obj.id,
            form_id=db_obj.form_id,
            name=db_obj.name,
            label=label,
            order=db_obj.order,
            repeatable=db_obj.repeatable,
            repeat_text=db_obj.repeat_text,
            questions=questions,
        )


class FormBase(BaseModel):
    name: str
    type: int = 1
    status: int = 1


class FormCreate(FormBase):
    pass


class FormResponse(FormBase):
    id: int
    uuid: UUID
    version: int
    published_at: Optional[datetime] = None
    parent_id: Optional[int] = None
    previous_version_id: Optional[int] = None
    active_version_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_localized(cls, db_obj, lang: str):
        name = get_translation(db_obj.translations, lang, db_obj.name)
        return cls(
            id=db_obj.id,
            uuid=db_obj.uuid,
            name=name,
            type=db_obj.type,
            status=db_obj.status,
            version=db_obj.version,
            published_at=db_obj.published_at,
            parent_id=db_obj.parent_id,
            previous_version_id=db_obj.previous_version_id,
            active_version_id=db_obj.active_version_id,
        )


class FormDetailResponse(FormResponse):
    question_groups: List[QuestionGroupResponse] = []

    @classmethod
    def from_orm_localized(cls, db_obj, lang: str):
        name = get_translation(db_obj.translations, lang, db_obj.name)
        # Filter active (non-deleted) groups
        active_groups = [
            g for g in db_obj.question_groups if g.deleted_at is None
        ]
        question_groups = []
        for g in active_groups:
            # Filter active questions dynamically
            active_qs = [q for q in g.questions if q.deleted_at is None]
            g_label = (
                get_translation(g.translations, lang, g.label)
                if g.label
                else g.label
            )
            questions_list = [
                QuestionResponse.from_orm_localized(q, lang) for q in active_qs
            ]
            question_groups.append(
                QuestionGroupResponse(
                    id=g.id,
                    form_id=g.form_id,
                    name=g.name,
                    label=g_label,
                    order=g.order,
                    repeatable=g.repeatable,
                    repeat_text=g.repeat_text,
                    questions=questions_list,
                )
            )

        return cls(
            id=db_obj.id,
            uuid=db_obj.uuid,
            name=name,
            type=db_obj.type,
            status=db_obj.status,
            version=db_obj.version,
            published_at=db_obj.published_at,
            parent_id=db_obj.parent_id,
            previous_version_id=db_obj.previous_version_id,
            active_version_id=db_obj.active_version_id,
            question_groups=question_groups,
        )


class FormPublishedVersionResponse(BaseModel):
    id: int
    form_id: int
    version: int
    schema_snapshot: Dict[str, Any] = Field(..., alias="schema")
    published_at: datetime
    published_by_id: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
