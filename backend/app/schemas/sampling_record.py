from typing import Optional, Literal
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


class SamplingRecordBase(BaseModel):
    site_id: UUID = Field(
        ..., description="Unique identifier of the associated monitoring site"
    )
    ph_value: Decimal = Field(
        ...,
        ge=2.0,
        le=10.0,
        description="Water pH level (dimensionless scale, 2.0 to 10.0)",
    )
    temp_value: Decimal = Field(
        ...,
        ge=5.0,
        le=50.0,
        description="Water temperature in degrees Celsius (°C)",
    )
    do_value: Decimal = Field(
        ...,
        ge=0.5,
        le=35.0,
        description="Dissolved oxygen concentration in mg/L",
    )
    invasive_macrophytes: Decimal = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Invasive macrophyte cover percentage (%)",
    )
    cpue_value: Optional[Decimal] = Field(
        None, ge=0.0, description="Catch Per Unit Effort in kg/net-night"
    )
    water_level: Literal["HIGH", "MEDIUM", "LOW"] = Field(
        ...,
        description="Qualitative water level rating (HIGH, MEDIUM, or LOW)",
    )
    sampled_at: datetime = Field(
        ..., description="Timestamp when the sampling was conducted"
    )


class SamplingRecordCreate(SamplingRecordBase):
    id: Optional[UUID] = None


class SamplingRecordUpdate(BaseModel):
    site_id: Optional[UUID] = Field(
        None, description="Unique identifier of the associated monitoring site"
    )
    ph_value: Optional[Decimal] = Field(
        None,
        ge=2.0,
        le=10.0,
        description="Water pH level (dimensionless scale, 2.0 to 10.0)",
    )
    temp_value: Optional[Decimal] = Field(
        None,
        ge=5.0,
        le=50.0,
        description="Water temperature in degrees Celsius (°C)",
    )
    do_value: Optional[Decimal] = Field(
        None,
        ge=0.5,
        le=35.0,
        description="Dissolved oxygen concentration in mg/L",
    )
    invasive_macrophytes: Optional[Decimal] = Field(
        None,
        ge=0.0,
        le=100.0,
        description="Invasive macrophyte cover percentage (%)",
    )
    cpue_value: Optional[Decimal] = Field(
        None, ge=0.0, description="Catch Per Unit Effort in kg/net-night"
    )
    water_level: Optional[Literal["HIGH", "MEDIUM", "LOW"]] = Field(
        None,
        description="Qualitative water level rating (HIGH, MEDIUM, or LOW)",
    )
    sampled_at: Optional[datetime] = Field(
        None, description="Timestamp when the sampling was conducted"
    )


class SamplingRecordResponse(SamplingRecordBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)
