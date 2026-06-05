from typing import Optional, Literal
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


class SamplingRecordBase(BaseModel):
    site_id: UUID
    ph_value: Decimal = Field(..., ge=2.0, le=10.0)
    temp_value: Decimal = Field(..., ge=5.0, le=50.0)
    do_value: Decimal = Field(..., ge=0.5, le=35.0)
    invasive_macrophytes: Decimal = Field(..., ge=0.0, le=100.0)
    cpue_value: Optional[Decimal] = Field(None, ge=0.0)
    water_level: Literal["HIGH", "MEDIUM", "LOW"]
    sampled_at: datetime


class SamplingRecordCreate(SamplingRecordBase):
    id: Optional[UUID] = None


class SamplingRecordUpdate(BaseModel):
    site_id: Optional[UUID] = None
    ph_value: Optional[Decimal] = Field(None, ge=2.0, le=10.0)
    temp_value: Optional[Decimal] = Field(None, ge=5.0, le=50.0)
    do_value: Optional[Decimal] = Field(None, ge=0.5, le=35.0)
    invasive_macrophytes: Optional[Decimal] = Field(None, ge=0.0, le=100.0)
    cpue_value: Optional[Decimal] = Field(None, ge=0.0)
    water_level: Optional[Literal["HIGH", "MEDIUM", "LOW"]] = None
    sampled_at: Optional[datetime] = None


class SamplingRecordResponse(SamplingRecordBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)
