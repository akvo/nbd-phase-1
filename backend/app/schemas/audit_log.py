from typing import List, Literal
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict

AuditAction = Literal[
    "APPROVE",
    "REJECT",
    "EDIT",
    "DELETE",
    "INVITE_USER",
    "UPDATE_ROLE",
    "ALERT",
    "LOGIN",  # Legacy, kept for existing records
]


class AuditLogBase(BaseModel):
    actor_id: UUID
    action: AuditAction
    entity_type: str
    entity_id: str


class AuditLogCreate(AuditLogBase):
    pass


class AuditLogResponse(AuditLogBase):
    id: UUID
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditLogListResponse(BaseModel):
    items: List[AuditLogResponse]
    total: int
    page: int
    page_size: int
