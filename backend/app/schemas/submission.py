from typing import List, Optional, Any, Dict
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, model_validator


class AnswerBase(BaseModel):
    question_id: int
    name: Optional[str] = None
    value: Optional[float] = None
    options: Optional[List[Any]] = None
    index: int = 0


class AnswerCreate(AnswerBase):
    pass


class AnswerResponse(AnswerBase):
    id: int
    datapoint_id: int

    model_config = ConfigDict(from_attributes=True)


class DatapointBase(BaseModel):
    form_id: int
    published_version_id: Optional[int] = None
    name: Optional[str] = None
    basin_id: Optional[UUID] = None
    wetland_id: Optional[UUID] = None
    site_id: Optional[UUID] = None
    geo: Optional[Dict[str, Any]] = None
    duration: int = 0
    submitter: Optional[str] = None
    status: str = "PENDING"


class DatapointCreate(DatapointBase):
    answers: List[AnswerCreate] = []

    @model_validator(mode="after")
    def validate_polymorphic_anchor(self) -> "DatapointCreate":
        anchors = [self.basin_id, self.wetland_id, self.site_id]
        provided = sum(1 for a in anchors if a is not None)
        if provided != 1:
            raise ValueError(
                "Exactly one geographic anchor (basin_id, wetland_id, "
                "or site_id) must be specified."
            )
        return self


class DatapointResponse(DatapointBase):
    id: int
    uuid: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    answers: List[AnswerResponse] = []

    model_config = ConfigDict(from_attributes=True)
