from typing import Optional, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class ManagementActionBase(BaseModel):
    site_id: UUID
    status_color: Literal["GREEN", "YELLOW", "RED"]
    short_label: str = Field(..., max_length=50)
    description_text: str


class ManagementActionCreate(ManagementActionBase):
    pass


class ManagementActionUpdate(BaseModel):
    site_id: Optional[UUID] = None
    status_color: Optional[Literal["GREEN", "YELLOW", "RED"]] = None
    short_label: Optional[str] = Field(None, max_length=50)
    description_text: Optional[str] = None


class ManagementActionResponse(ManagementActionBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)
