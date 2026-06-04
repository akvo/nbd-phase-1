from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


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


class QuestionBase(BaseModel):
    name: Optional[str] = None
    label: str
    short_label: Optional[str] = None
    type: int
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


class FormDetailResponse(FormResponse):
    question_groups: List[QuestionGroupResponse] = []


class FormPublishedVersionResponse(BaseModel):
    id: int
    form_id: int
    version: int
    schema_snapshot: Dict[str, Any] = Field(..., alias="schema")
    published_at: datetime
    published_by_id: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
