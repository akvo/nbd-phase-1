from typing import List, Optional, Any, Dict
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, model_validator

from app.models.submission import SubmissionStatus


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
    question_name: str
    question_label: str
    datapoint_id: int
    read_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def resolve_fields(cls, data: Any) -> Any:
        is_dict = isinstance(data, dict)

        # Get question
        question = (
            data.get("question")
            if is_dict
            else getattr(data, "question", None)
        )

        # Extract variables dynamically
        name = data.get("name") if is_dict else getattr(data, "name", None)
        value = data.get("value") if is_dict else getattr(data, "value", None)
        options = (
            data.get("options") if is_dict else getattr(data, "options", None)
        )
        read_url = (
            data.get("read_url")
            if is_dict
            else getattr(data, "read_url", None)
        )
        if not read_url:
            read_url = (
                data.get("_read_url")
                if is_dict
                else getattr(data, "_read_url", None)
            )

        index = data.get("index", 0) if is_dict else getattr(data, "index", 0)
        id_val = data.get("id") if is_dict else getattr(data, "id", None)
        datapoint_id = (
            data.get("datapoint_id")
            if is_dict
            else getattr(data, "datapoint_id", None)
        )
        question_id = (
            data.get("question_id")
            if is_dict
            else getattr(data, "question_id", None)
        )

        from app.models.form import QuestionType

        # Get q_type
        q_type = None
        if question:
            if isinstance(question, dict):
                q_type = question.get("type")
            else:
                q_type = getattr(question, "type", None)

        resolved_value = None

        if q_type in (
            QuestionType.option.value,
            QuestionType.multiple_option.value,
            QuestionType.cascade.value,
        ):
            resolved_value = (
                data.get("_resolved_value")
                if is_dict
                else getattr(data, "_resolved_value", None)
            )
            if resolved_value is None:
                if options is not None:
                    resolved_value = (
                        ", ".join(str(x) for x in options)
                        if isinstance(options, list)
                        else str(options)
                    )
                elif name is not None:
                    resolved_value = name
                else:
                    resolved_value = value
        elif q_type in (
            QuestionType.image.value,
            QuestionType.attachment.value,
            QuestionType.signature.value,
        ):
            if name is not None:
                resolved_value = name
            elif value is not None:
                resolved_value = str(value)
            elif options and isinstance(options, list) and len(options) > 0:
                resolved_value = str(options[0])
        else:
            if name is not None:
                resolved_value = name
            elif value is not None:
                resolved_value = value
            elif options is not None:
                resolved_value = (
                    ", ".join(str(x) for x in options)
                    if isinstance(options, list)
                    else str(options)
                )

        if not read_url:
            is_media = False
            blob_name = None

            # Standard forms with image/attachment/signature types
            is_type_match = False
            if q_type:
                if q_type in (
                    QuestionType.image,
                    QuestionType.attachment,
                    QuestionType.signature,
                ):
                    is_type_match = True
                elif hasattr(q_type, "value") and q_type.value in (
                    "image",
                    "attachment",
                    "signature",
                ):
                    is_type_match = True
                elif str(q_type) in ("image", "attachment", "signature"):
                    is_type_match = True
                elif isinstance(q_type, str) and (
                    "image" in q_type
                    or "attachment" in q_type
                    or "signature" in q_type
                ):
                    is_type_match = True

            if is_type_match:
                is_media = True
                if name and (
                    name.startswith("media/") or name.startswith("webforms/")
                ):
                    blob_name = name
                elif (
                    options
                    and isinstance(options, list)
                    and len(options) > 0
                    and isinstance(options[0], str)
                ):
                    blob_name = options[0]
                elif isinstance(value, str) and (
                    value.startswith("media/") or value.startswith("webforms/")
                ):
                    blob_name = value

            # WhatsApp / generic media_attachment fallback
            elif (
                name == "media_attachment"
                and options
                and isinstance(options, list)
                and len(options) > 0
                and isinstance(options[0], str)
            ):
                is_media = True
                blob_name = options[0]

            # Direct media path in value fallback
            elif isinstance(value, str) and (
                value.startswith("media/") or value.startswith("webforms/")
            ):
                is_media = True
                blob_name = value

            # Direct media path in name fallback
            elif isinstance(name, str) and (
                name.startswith("media/") or name.startswith("webforms/")
            ):
                is_media = True
                blob_name = name

            if (
                is_media
                and blob_name
                and not blob_name.startswith("data:")
                and not blob_name.startswith("http")
            ):
                from app.services.storage import StorageService

                try:
                    read_url = StorageService().generate_read_signed_url(
                        blob_name
                    )
                except Exception as sig_err:
                    try:
                        with open("/app/debug_resolve_fields.log", "a") as f:
                            f.write(f"ERROR generating signature: {sig_err}\n")
                    except Exception:
                        pass

        # Return dict representation
        question_label = None
        if question:
            question_label = (
                question.get("label")
                if isinstance(question, dict)
                else getattr(question, "label", None)
            )

        question_name = None
        if question:
            question_name = (
                question.get("name")
                if isinstance(question, dict)
                else getattr(question, "name", None)
            )

        res_dict = {
            "id": id_val,
            "datapoint_id": datapoint_id,
            "question_id": question_id,
            "question_label": question_label,
            "question_name": question_name,
            "name": name,
            "value": resolved_value,
            "options": options,
            "index": index,
            "read_url": read_url,
        }

        return res_dict


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
    status: str = SubmissionStatus.PENDING


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
    basin_name: Optional[str] = None
    wetland_name: Optional[str] = None
    site_name: Optional[str] = None
    creator_name: Optional[str] = None
    creator_email: Optional[str] = None
    image_url: Optional[str] = None
    incident_type_name: Optional[str] = None
    incident_type_id: Optional[int] = None
    reported_location: Optional[str] = None
    answers: List[AnswerResponse] = []

    model_config = ConfigDict(from_attributes=True)


class SubmissionStatusUpdate(BaseModel):
    status: str

    @model_validator(mode="after")
    def validate_status(self) -> "SubmissionStatusUpdate":
        if self.status not in (
            SubmissionStatus.APPROVED,
            SubmissionStatus.REJECTED,
        ):
            raise ValueError(
                f"Status must be either {SubmissionStatus.APPROVED.value} or {SubmissionStatus.REJECTED.value}"  # noqa
            )
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

        if self.submitter:
            if self.submitter.startswith("wa-"):
                parts = self.submitter.split("-")
                if len(parts) > 1:
                    phone = parts[1]
                    if len(phone) > 6:
                        masked_phone = (
                            phone[:4] + "*" * (len(phone) - 7) + phone[-3:]
                        )
                        self.submitter = f"wa-{masked_phone}"
                    else:
                        self.submitter = "wa-***"
            elif self.submitter.startswith("ussd-"):
                parts = self.submitter.split("-")
                if len(parts) > 1:
                    phone = parts[1]
                    if len(phone) > 6:
                        masked_phone = (
                            phone[:4] + "*" * (len(phone) - 7) + phone[-3:]
                        )
                        self.submitter = f"ussd-{masked_phone}"
                    else:
                        self.submitter = "ussd-***"
        return self


class SubmissionEditPayload(BaseModel):
    answers: List[AnswerCreate]
