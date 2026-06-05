from typing import Optional, Literal
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


class HealthScoreBase(BaseModel):
    site_id: UUID
    wqi_score: Decimal = Field(..., ge=0.0, le=1.0)
    composite_score: Decimal = Field(..., ge=0.0, le=1.0)
    ik_signal_value: Decimal = Field(..., ge=0.0, le=1.0)
    adjusted_score: Decimal = Field(..., ge=0.0, le=1.0)
    health_class: Literal["A", "B", "C", "D", "E"]
    calculated_at: Optional[datetime] = None


class HealthScoreCreate(HealthScoreBase):
    pass


class HealthScoreUpdate(BaseModel):
    site_id: Optional[UUID] = None
    wqi_score: Optional[Decimal] = Field(None, ge=0.0, le=1.0)
    composite_score: Optional[Decimal] = Field(None, ge=0.0, le=1.0)
    ik_signal_value: Optional[Decimal] = Field(None, ge=0.0, le=1.0)
    adjusted_score: Optional[Decimal] = Field(None, ge=0.0, le=1.0)
    health_class: Optional[Literal["A", "B", "C", "D", "E"]] = None
    calculated_at: Optional[datetime] = None


class HealthScoreResponse(HealthScoreBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)
