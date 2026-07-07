from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.models.form import QuestionType
from app.services.translation import get_translation

# ─── Language normalisation helpers ─────────────────────────────────────────
# akvo-react-form-editor builds its locale dropdown from `locale-codes`, which
# joins windows-locale entries with iso639-codes by exact language name.
# "Kiswahili" (windows-locale sw/sw-KE) ≠ "Swahili" (iso639-codes), so "sw"
# has no iso639-1 mapping and is absent from the editor's 121-code locale list.
# Sending "sw" (or "sw-KE") in the `languages` array crashes the editor's
# ExistingTranslation component with "findLang is undefined".
#
# Rule: normalise to plain 2-letter ISO 639-1 codes; drop unsupported ones.

# Verbose English names → 2-letter ISO 639-1
_VERBOSE_TO_ISO = {
    "english": "en",
    "swahili": "sw",
    "kiswahili": "sw",
    "french": "fr",
    "spanish": "es",
    "indonesian": "id",
    "portuguese": "pt",
    "arabic": "ar",
    "german": "de",
}

# Codes confirmed absent from akvo-react-form-editor's localeDropdownValue
# (121 codes derived from locale-codes 1.x with lodash uniqBy on iso639-1).
# "sw" fails because windows-locale calls it "Kiswahili" while iso639-codes
# calls it "Swahili" — the name join produces no iso639-1 entry.
_EDITOR_UNSUPPORTED = {"sw", "swc"}


def _to_editor_lang_code(raw: str) -> Optional[str]:
    """Return the 2-letter ISO 639-1 code the editor expects, or None."""
    cleaned = raw.strip().lower()
    # Map verbose names first
    if cleaned in _VERBOSE_TO_ISO:
        cleaned = _VERBOSE_TO_ISO[cleaned]
    # Strip regional suffix: "en-US" → "en", "sw-KE" → "sw"
    base = cleaned.split("-")[0]
    if base in _EDITOR_UNSUPPORTED:
        return None
    return base if len(base) >= 2 else None


def _normalize_blueprint_languages(langs: List[str]) -> List[str]:
    """Filter and normalise a language list for editor compatibility."""
    seen: List[str] = []
    for lang in langs or []:
        code = _to_editor_lang_code(str(lang))
        if code and code not in seen:
            seen.append(code)
    return seen or ["en"]


# ────────────────────────────────────────────────────────────────────────────


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
    shortLabel: Optional[str] = None
    type: str
    order: Optional[int] = None
    required: bool = True
    rule: Optional[Dict[str, Any]] = None
    dependency: Optional[List[Dict[str, Any]]] = None
    dependencyRule: Optional[str] = None
    api: Optional[Dict[str, Any]] = None
    extra: Optional[Dict[str, Any]] = None
    tooltip: Optional[Dict[str, Any]] = None
    fn: Optional[Dict[str, Any]] = None
    pre: Optional[Dict[str, Any]] = None
    displayOnly: bool = False
    hiddenString: bool = False
    requiredDoubleEntry: bool = False
    requiredSign: Optional[str] = None
    allowOther: bool = False
    allowOtherText: Optional[str] = None
    meta: bool = False
    isRepeatIdentifier: bool = False
    translations: List[Dict[str, Any]] = []
    option: Optional[Any] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Normalize snake_case to camelCase for output consistency
            if "short_label" in data and "shortLabel" not in data:
                data["shortLabel"] = data.pop("short_label")
            if "dependency_rule" in data and "dependencyRule" not in data:
                data["dependencyRule"] = data.pop("dependency_rule")
            if "display_only" in data and "displayOnly" not in data:
                data["displayOnly"] = data.pop("display_only")
            if "hidden_string" in data and "hiddenString" not in data:
                data["hiddenString"] = data.pop("hidden_string")
            if "required_double_entry" in data:
                if "requiredDoubleEntry" not in data:
                    val = data.pop("required_double_entry")
                    data["requiredDoubleEntry"] = val
            if "required_sign" in data and "requiredSign" not in data:
                data["requiredSign"] = data.pop("required_sign")
            if "allow_other" in data and "allowOther" not in data:
                data["allowOther"] = data.pop("allow_other")
            if "allow_other_text" in data and "allowOtherText" not in data:
                data["allowOtherText"] = data.pop("allow_other_text")
            if (
                "is_repeat_identifier" in data
                and "isRepeatIdentifier" not in data
            ):
                data["isRepeatIdentifier"] = data.pop("is_repeat_identifier")
            # Normalize options to option
            if "options" in data and "option" not in data:
                data["option"] = data.pop("options")
        return data

    @classmethod
    def from_orm_model(cls, q):
        sorted_options = (
            sorted(
                q.options,
                key=lambda x: x.order if x.order is not None else float("inf"),
            )
            if q.options
            else []
        )
        opts = (
            [BlueprintOptionSchema.from_orm_model(o) for o in sorted_options]
            if sorted_options
            else []
        )
        extra = dict(q.extra) if q.extra else {}

        opt_val = opts if opts else None
        if extra and "option" in extra and isinstance(extra["option"], str):
            opt_val = extra.pop("option")

        hidden_string = extra.pop("hiddenString", False)
        required_double_entry = extra.pop("requiredDoubleEntry", False)
        required_sign = extra.pop("requiredSign", None)
        allow_other = extra.pop("allowOther", False)
        allow_other_text = extra.pop("allowOtherText", None)

        q_type_str = q.type.value if hasattr(q.type, "value") else str(q.type)

        return cls(
            id=q.id,
            name=q.name,
            label=q.label,
            shortLabel=q.short_label,
            order=q.order,
            type=q_type_str,
            required=q.required,
            rule=q.rule,
            dependency=q.dependency,
            dependencyRule=q.dependency_rule,
            api=q.api,
            extra=extra if extra else None,
            tooltip=q.tooltip,
            fn=q.fn,
            pre=q.pre or {},
            displayOnly=q.display_only or False,
            hiddenString=hidden_string,
            requiredDoubleEntry=required_double_entry,
            requiredSign=required_sign,
            allowOther=allow_other,
            allowOtherText=allow_other_text,
            meta=q.meta,
            isRepeatIdentifier=q.is_repeat_identifier or False,
            translations=q.translations or [],
            option=opt_val,
        )


class BlueprintQuestionGroupSchema(BaseModel):
    id: int
    name: str
    label: Optional[str] = None
    description: Optional[str] = None
    order: Optional[int] = None
    repeatable: bool = False
    repeatText: Optional[str] = None
    repeatButtonPlacement: Optional[str] = None
    leadingQuestion: bool = False
    showRepeatInQuestionLevel: bool = False
    translations: List[Dict[str, Any]] = []
    question: List[BlueprintQuestionSchema] = []

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Normalize questions to question
            if "questions" in data and "question" not in data:
                data["question"] = data.pop("questions")
            # Normalize repeat_text to repeatText
            if "repeat_text" in data and "repeatText" not in data:
                data["repeatText"] = data.pop("repeat_text")
            if (
                "repeat_button_placement" in data
                and "repeatButtonPlacement" not in data
            ):
                data["repeatButtonPlacement"] = data.pop(
                    "repeat_button_placement"
                )
            if "leading_question" in data and "leadingQuestion" not in data:
                data["leadingQuestion"] = data.pop("leading_question")
            if (
                "show_repeat_in_question_level" in data
                and "showRepeatInQuestionLevel" not in data
            ):
                data["showRepeatInQuestionLevel"] = data.pop(
                    "show_repeat_in_question_level"
                )
        return data

    @classmethod
    def from_orm_model(cls, g):
        sorted_questions = (
            sorted(
                [q for q in g.questions if q.deleted_at is None],
                key=lambda x: x.order if x.order is not None else float("inf"),
            )
            if g.questions
            else []
        )
        qs = (
            [
                BlueprintQuestionSchema.from_orm_model(q)
                for q in sorted_questions
            ]
            if sorted_questions
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
            repeatButtonPlacement=g.repeat_button_placement,
            leadingQuestion=g.leading_question or False,
            showRepeatInQuestionLevel=g.show_repeat_in_question_level or False,
            translations=g.translations or [],
            question=qs,
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

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def normalize_groups(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Normalize question_groups to question_group
            if "question_groups" in data and "question_group" not in data:
                data["question_group"] = data.pop("question_groups")

            # Normalize languages to 2-letter ISO 639-1 codes compatible with
            # akvo-react-form-editor's localeDropdownValue (which uses iso639-1
            # codes from locale-codes). Regional codes ("en-US") are stripped
            # to their base ("en"). Codes with no matching entry in the
            # editor's 121-code locale list (e.g. "sw" — Kiswahili name
            # mismatch) are dropped to prevent ExistingTranslation crashes.
            if "languages" in data and data["languages"]:
                data["languages"] = _normalize_blueprint_languages(
                    data["languages"]
                )
                if "defaultLanguage" in data and data["defaultLanguage"]:
                    base = _to_editor_lang_code(str(data["defaultLanguage"]))
                    # Fall back to first valid language
                    # if default is unsupported
                    data["defaultLanguage"] = (
                        base
                        if base in data["languages"]
                        else (
                            data["languages"][0] if data["languages"] else "en"
                        )
                    )
        return data

    @classmethod
    def from_orm_model(cls, db_form, active_groups):
        langs = db_form.languages or ["en"]
        normalized_langs = _normalize_blueprint_languages(langs)
        default_lang = normalized_langs[0] if normalized_langs else "en"
        groups = [
            BlueprintQuestionGroupSchema.from_orm_model(g)
            for g in active_groups
        ]
        return cls(
            form_id=db_form.id,
            name=db_form.name,
            type=db_form.type,
            version=db_form.version,
            languages=normalized_langs,
            defaultLanguage=default_lang,
            translations=db_form.translations or [],
            question_group=groups,
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
    type: str
    required: bool = True
    order: Optional[int] = None
    meta: bool = False
    rule: Optional[Dict[str, Any]] = None
    dependency: Optional[List[Dict[str, Any]]] = None
    dependency_rule: Optional[str] = None
    api: Optional[Dict[str, Any]] = None
    extra: Optional[Dict[str, Any]] = None
    tooltip: Optional[Dict[str, Any]] = None
    fn: Optional[Dict[str, Any]] = None
    pre: Optional[Dict[str, Any]] = None
    display_only: bool = False
    hidden_string: bool = False
    required_double_entry: bool = False
    required_sign: Optional[str] = None
    allow_other: bool = False
    allow_other_text: Optional[str] = None
    translations: List[Dict[str, Any]] = []
    option: Optional[List[OptionUpdate]] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Normalize camelCase to snake_case
            if "shortLabel" in data and "short_label" not in data:
                data["short_label"] = data.pop("shortLabel")
            if "dependencyRule" in data and "dependency_rule" not in data:
                data["dependency_rule"] = data.pop("dependencyRule")
            if "displayOnly" in data and "display_only" not in data:
                data["display_only"] = data.pop("displayOnly")
            if "hiddenString" in data and "hidden_string" not in data:
                data["hidden_string"] = data.pop("hiddenString")
            if "requiredDoubleEntry" in data:
                if "required_double_entry" not in data:
                    val = data.pop("requiredDoubleEntry")
                    data["required_double_entry"] = val
            if "requiredSign" in data and "required_sign" not in data:
                data["required_sign"] = data.pop("requiredSign")
            if "allowOther" in data and "allow_other" not in data:
                data["allow_other"] = data.pop("allowOther")
            if "allowOtherText" in data and "allow_other_text" not in data:
                data["allow_other_text"] = data.pop("allowOtherText")
            # Normalize options to option
            if "options" in data and "option" not in data:
                data["option"] = data.pop("options")
        return data


class QuestionGroupUpdate(BaseModel):
    id: Optional[int] = None  # None = new group
    name: str
    label: Optional[str] = None
    description: Optional[str] = None
    order: Optional[int] = None
    repeatable: bool = False
    repeat_text: Optional[str] = None
    translations: List[Dict[str, Any]] = []
    question: List[QuestionUpdate] = []

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Normalize questions to question
            if "questions" in data and "question" not in data:
                data["question"] = data.pop("questions")
            # Normalize repeatText to repeat_text
            if "repeatText" in data and "repeat_text" not in data:
                data["repeat_text"] = data.pop("repeatText")
        return data


class FormBlueprintUpdate(BaseModel):
    name: str
    type: int = 1
    languages: List[str] = ["en"]
    defaultLanguage: str = "en"
    translations: List[Dict[str, Any]] = []
    question_group: List[QuestionGroupUpdate] = []

    @model_validator(mode="before")
    @classmethod
    def normalize_groups(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Normalize question_groups to question_group
            if "question_groups" in data and "question_group" not in data:
                data["question_group"] = data.pop("question_groups")
        return data


class FormSettingsUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[int] = None
    status: Optional[int] = None
