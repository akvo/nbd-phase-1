import uuid
from typing import Optional
from pydantic import BaseModel, Field


class CitizenBase(BaseModel):
    phone_number: str = Field(
        ..., description="E.164 phone number of reporter"
    )
    site_id: uuid.UUID = Field(..., description="Home site UUID")
    role: str = Field(..., description="WATCHER or SCIENTIST")


class CitizenCreate(CitizenBase):
    pass


class CitizenUpdate(BaseModel):
    phone_number: Optional[str] = None
    site_id: Optional[uuid.UUID] = None
    role: Optional[str] = None


class CitizenResponse(CitizenBase):
    id: uuid.UUID

    class Config:
        from_attributes = True
