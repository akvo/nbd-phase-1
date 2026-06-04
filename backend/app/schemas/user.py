from typing import Optional, Literal
from uuid import UUID
from pydantic import BaseModel, EmailStr, ConfigDict, field_validator


class UserBase(BaseModel):
    email: EmailStr
    role: Literal["Admin", "Reviewer", "Partner"]
    organization: Optional[str] = None
    is_active: bool = True


class UserCreate(UserBase):
    password: Optional[str] = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ("Admin", "Reviewer", "Partner"):
            raise ValueError("Role must be 'Admin', 'Reviewer', or 'Partner'")
        return v


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    role: Optional[Literal["Admin", "Reviewer", "Partner"]] = None
    organization: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)
