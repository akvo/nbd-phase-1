from typing import Optional, Literal
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class FgdRecordBase(BaseModel):
    wetland_id: UUID
    fish_abundance: Literal["Same", "Slight", "Moderate", "Severe"]
    water_clarity: Literal["Same", "Somewhat Worse", "Much Worse"]
    vegetation_cover: Literal["Same", "Partial Loss", "Severe Loss"]
    conducted_at: datetime


class FgdRecordCreate(FgdRecordBase):
    id: Optional[UUID] = None


class FgdRecordUpdate(BaseModel):
    wetland_id: Optional[UUID] = None
    fish_abundance: Optional[
        Literal["Same", "Slight", "Moderate", "Severe"]
    ] = None
    water_clarity: Optional[
        Literal["Same", "Somewhat Worse", "Much Worse"]
    ] = None
    vegetation_cover: Optional[
        Literal["Same", "Partial Loss", "Severe Loss"]
    ] = None
    conducted_at: Optional[datetime] = None


class FgdRecordResponse(FgdRecordBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)
