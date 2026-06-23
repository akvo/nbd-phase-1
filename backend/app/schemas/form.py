from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, model_validator
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


class BlueprintOptionSchema(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    label: Optional[str] = None
    value: Optional[str] = None
    order: Optional[int] = None
    other: bool = False
    color: Optional[str] = None
    translations: List[Dict[str, Any]] = []

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_model(cls, opt):
        if not opt:
            return None
        return cls(
            id=opt.id,
            name=opt.label,
            label=opt.label,
            value=opt.value,
            order=opt.order,
            other=opt.other,
            color=opt.color,
            translations=opt.translations or [],
        )


class BlueprintQuestionSchema(BaseModel):
    id: int
    name: Optional[str] = None
    label: str
    short_label: Optional[str] = None
    shortLabel: Optional[str] = None
    type: str
    required: bool = True
    rule: Optional[Dict[str, Any]] = None
    dependency: Optional[List[Dict[str, Any]]] = None
    dependency_rule: Optional[str] = None
    dependencyRule: Optional[str] = None
    api: Optional[Dict[str, Any]] = None
    extra: Optional[Dict[str, Any]] = None
    tooltip: Optional[Dict[str, Any]] = None
    fn: Optional[Dict[str, Any]] = None
    pre: Optional[Dict[str, Any]] = None
    displayOnly: bool = False
    display_only: bool = False
    hiddenString: bool = False
    hidden_string: bool = False
    requiredDoubleEntry: bool = False
    required_double_entry: bool = False
    requiredSign: Optional[str] = None
    required_sign: Optional[str] = None
    meta: bool = False
    translations: List[Dict[str, Any]] = []
    option: Optional[Any] = None
    options: Optional[List[BlueprintOptionSchema]] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode='before')
    @classmethod
    def normalize_options(cls, data: Any) -> Any:
        if isinstance(data, dict):
            opt = data.get("option")
            opts = data.get("options")
            if opt is None and opts is not None:
                data["option"] = opts
            elif opt is not None and opts is None:
                if isinstance(opt, list):
                    data["options"] = opt
        return data

    @classmethod
    def from_orm_model(cls, q):
        opts = (
            [BlueprintOptionSchema.from_orm_model(o) for o in q.options]
            if q.options
            else []
        )
        extra = q.extra or {}

        opt_val = opts if opts else None
        if extra and "option" in extra and isinstance(extra["option"], str):
            opt_val = extra["option"]

        q_type_str = q.type.value if hasattr(q.type, "value") else str(q.type)

        return cls(
            id=q.id,
            name=q.name,
            label=q.label,
            short_label=q.short_label,
            shortLabel=q.short_label,
            type=q_type_str,
            required=q.required,
            rule=q.rule,
            dependency=q.dependency,
            dependency_rule=q.dependency_rule,
            dependencyRule=q.dependency_rule,
            api=q.api,
            extra=q.extra,
            tooltip=q.tooltip,
            fn=q.fn,
            pre=q.pre,
            displayOnly=q.display_only or False,
            display_only=q.display_only or False,
            hiddenString=extra.get("hiddenString", False),
            hidden_string=extra.get("hiddenString", False),
            requiredDoubleEntry=extra.get("requiredDoubleEntry", False),
            required_double_entry=extra.get("requiredDoubleEntry", False),
            requiredSign=extra.get("requiredSign"),
            required_sign=extra.get("requiredSign"),
            meta=q.meta,
            translations=q.translations or [],
            option=opt_val,
            options=opts if opts else None,
        )


class BlueprintQuestionGroupSchema(BaseModel):
    id: int
    name: str
    label: Optional[str] = None
    description: Optional[str] = None
    order: Optional[int] = None
    repeatable: bool = False
    repeatText: Optional[str] = None
    repeat_text: Optional[str] = None
    repeatButtonPlacement: Optional[str] = None
    translations: List[Dict[str, Any]] = []
    question: List[BlueprintQuestionSchema] = []
    questions: List[BlueprintQuestionSchema] = []

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode='before')
    @classmethod
    def normalize_questions(cls, data: Any) -> Any:
        if isinstance(data, dict):
            q = data.get("question")
            qs = data.get("questions")
            if not q and qs:
                data["question"] = qs
            elif q and not qs:
                data["questions"] = q
        return data

    @classmethod
    def from_orm_model(cls, g):
        qs = (
            [
                BlueprintQuestionSchema.from_orm_model(q)
                for q in g.questions
                if q.deleted_at is None
            ]
            if g.questions
            else []
        )
        return cls(
            id=g.id,
            name=g.name,
            label=g.label,
            description=g.label,
            order=g.order,
            repeatable=g.repeatable,
            repeatText=g.repeat_text,
            repeat_text=g.repeat_text,
            repeatButtonPlacement=None,
            translations=g.translations or [],
            question=qs,
            questions=qs,
        )


class FormBlueprintResponse(BaseModel):
    form_id: Optional[int] = None
    name: str
    type: int = 1
    version: int = 1
    languages: List[str] = ["en"]
    defaultLanguage: str = "en"
    translations: List[Dict[str, Any]] = []
    question_group: List[BlueprintQuestionGroupSchema] = []
    question_groups: List[BlueprintQuestionGroupSchema] = []

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode='before')
    @classmethod
    def normalize_groups(cls, data: Any) -> Any:
        if isinstance(data, dict):
            q_group = data.get("question_group")
            q_groups = data.get("question_groups")
            if not q_group and q_groups:
                data["question_group"] = q_groups
            elif q_group and not q_groups:
                data["question_groups"] = q_group
        return data

    @classmethod
    def from_orm_model(cls, db_form, active_groups):
        groups = [
            BlueprintQuestionGroupSchema.from_orm_model(g)
            for g in active_groups
        ]
        return cls(
            form_id=db_form.id,
            name=db_form.name,
            type=db_form.type,
            version=db_form.version,
            languages=db_form.languages or ["en"],
            defaultLanguage="en",
            translations=db_form.translations or [],
            question_group=groups,
            question_groups=groups,
        )


# --- Update schemas for PUT /forms/{form_id} ---


class OptionUpdate(BaseModel):
    id: Optional[int] = None  # None = new option
    name: Optional[str] = None
    label: Optional[str] = None
    value: Optional[str] = None
    order: Optional[int] = None
    other: bool = False
    color: Optional[str] = None
    translations: List[Dict[str, Any]] = []


class QuestionUpdate(BaseModel):
    id: Optional[int] = None  # None = new question
    name: Optional[str] = None
    label: str
    short_label: Optional[str] = None
    shortLabel: Optional[str] = None
    type: str
    required: bool = True
    order: Optional[int] = None
    meta: bool = False
    rule: Optional[Dict[str, Any]] = None
    dependency: Optional[List[Dict[str, Any]]] = None
    dependency_rule: Optional[str] = None
    dependencyRule: Optional[str] = None
    api: Optional[Dict[str, Any]] = None
    extra: Optional[Dict[str, Any]] = None
    tooltip: Optional[Dict[str, Any]] = None
    fn: Optional[Dict[str, Any]] = None
    pre: Optional[Dict[str, Any]] = None
    displayOnly: bool = False
    display_only: bool = False
    hiddenString: bool = False
    hidden_string: bool = False
    requiredDoubleEntry: bool = False
    required_double_entry: bool = False
    requiredSign: Optional[str] = None
    required_sign: Optional[str] = None
    translations: List[Dict[str, Any]] = []
    option: Optional[Any] = None
    options: Optional[List[OptionUpdate]] = None

    @model_validator(mode='before')
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Normalize options
            opt = data.get("option")
            opts = data.get("options")
            if opt is None and opts is not None:
                data["option"] = opts
            elif opt is not None and opts is None:
                if isinstance(opt, list):
                    data["options"] = opt
            # Normalize shortLabel to short_label
            if data.get("shortLabel") and not data.get("short_label"):
                data["short_label"] = data["shortLabel"]
            # Normalize dependencyRule to dependency_rule
            if data.get("dependencyRule") and not data.get("dependency_rule"):
                data["dependency_rule"] = data["dependencyRule"]
            # Normalize displayOnly to display_only
            if data.get("displayOnly") and not data.get("display_only"):
                data["display_only"] = data["displayOnly"]
        return data


class QuestionGroupUpdate(BaseModel):
    id: Optional[int] = None  # None = new group
    name: str
    label: Optional[str] = None
    description: Optional[str] = None
    order: Optional[int] = None
    repeatable: bool = False
    repeatText: Optional[str] = None
    repeat_text: Optional[str] = None
    repeatButtonPlacement: Optional[str] = None
    translations: List[Dict[str, Any]] = []
    question: List[QuestionUpdate] = []
    questions: List[QuestionUpdate] = []

    @model_validator(mode='before')
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Normalize questions
            q = data.get("question")
            qs = data.get("questions")
            if not q and qs:
                data["question"] = qs
            elif q and not qs:
                data["questions"] = q
            # Normalize repeatText to repeat_text
            if data.get("repeatText") and not data.get("repeat_text"):
                data["repeat_text"] = data["repeatText"]
        return data


class FormBlueprintUpdate(BaseModel):
    name: str
    type: int = 1
    languages: List[str] = ["en"]
    defaultLanguage: str = "en"
    translations: List[Dict[str, Any]] = []
    question_group: List[QuestionGroupUpdate] = []
    question_groups: List[QuestionGroupUpdate] = []

    @model_validator(mode='before')
    @classmethod
    def normalize_groups(cls, data: Any) -> Any:
        if isinstance(data, dict):
            q_group = data.get("question_group")
            q_groups = data.get("question_groups")
            if not q_group and q_groups:
                data["question_group"] = q_groups
            elif q_group and not q_groups:
                data["question_groups"] = q_group
        return data
