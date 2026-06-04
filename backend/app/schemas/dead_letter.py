from typing import Any, Dict, Literal
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class DeadLetterBase(BaseModel):
    source_system: str
    raw_payload: Dict[str, Any]
    error_reason: str
    status: Literal["Pending Triage", "Resolved", "Discarded"] = (
        "Pending Triage"
    )


class DeadLetterCreate(DeadLetterBase):
    pass


class DeadLetterUpdate(BaseModel):
    status: Literal["Pending Triage", "Resolved", "Discarded"]


class DeadLetterResponse(DeadLetterBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
