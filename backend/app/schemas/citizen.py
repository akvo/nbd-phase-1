from typing import Optional, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class CitizenBase(BaseModel):
    phone_number: str = Field(..., max_length=50)
    site_id: UUID
    role: Literal["WATCHER", "SCIENTIST"]


class CitizenCreate(CitizenBase):
    pass


class CitizenUpdate(BaseModel):
    phone_number: Optional[str] = Field(None, max_length=50)
    site_id: Optional[UUID] = None
    role: Optional[Literal["WATCHER", "SCIENTIST"]] = None


class CitizenResponse(CitizenBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)
