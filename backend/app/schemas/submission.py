from typing import List, Optional, Any, Dict
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, model_validator


class AnswerBase(BaseModel):
    question_id: int
    name: Optional[str] = None
    value: Optional[Any] = None
    options: Optional[List[Any]] = None
    index: int = 0


class AnswerCreate(AnswerBase):
    pass


class AnswerResponse(AnswerBase):
    id: int
    datapoint_id: int
    read_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def resolve_fields(cls, data: Any) -> Any:
        if hasattr(data, "question"):
            q_type = data.question.type if data.question else None
            resolved_value = None

            if q_type in ("option", "multiple_option", "cascade"):
                if hasattr(data, "_resolved_value"):
                    resolved_value = data._resolved_value
            elif q_type in ("image", "attachment"):
                resolved_value = data.name
            else:
                resolved_value = (
                    data.name if data.name is not None else data.value
                )

            return {
                "id": data.id,
                "datapoint_id": data.datapoint_id,
                "question_id": data.question_id,
                "name": data.question.name if data.question else None,
                "value": resolved_value,
                "options": data.options,
                "index": data.index,
                "read_url": getattr(data, "_read_url", None),
            }
        return data


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
    form_name: Optional[str] = None
    answers: List[AnswerResponse] = []

    model_config = ConfigDict(from_attributes=True)


class SubmissionStatusUpdate(BaseModel):
    status: str

    @model_validator(mode="after")
    def validate_status(self) -> "SubmissionStatusUpdate":
        if self.status not in ("APPROVED", "REJECTED"):
            raise ValueError("Status must be either APPROVED or REJECTED")
        return self


class PublicDatapointResponse(DatapointResponse):
    @model_validator(mode="after")
    def mask_pii_name(self) -> "PublicDatapointResponse":
        if self.name:
            if self.name.startswith("wa-"):
                parts = self.name.split("-")
                if len(parts) > 1:
                    phone = parts[1]
                    if len(phone) > 6:
                        masked_phone = (
                            phone[:4] + "*" * (len(phone) - 7) + phone[-3:]
                        )
                        self.name = f"wa-{masked_phone}"
                    else:
                        self.name = "wa-***"
            elif self.name.startswith("+") and self.name[1:].isdigit():
                phone = self.name
                if len(phone) > 6:
                    self.name = phone[:4] + "*" * (len(phone) - 7) + phone[-3:]
                else:
                    self.name = "***"
        return self
