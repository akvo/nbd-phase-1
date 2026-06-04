from typing import Literal
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class AuditLogBase(BaseModel):
    actor_id: UUID
    action: Literal["APPROVE", "REJECT", "EDIT", "DELETE", "INVITE_USER"]
    entity_type: str
    entity_id: str


class AuditLogCreate(AuditLogBase):
    pass


class AuditLogResponse(AuditLogBase):
    id: UUID
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
