from datetime import datetime
from typing import Optional, Literal
from uuid import UUID
from pydantic import BaseModel, EmailStr, ConfigDict, field_validator


# Valid roles for admin users (SSO-only, invite model)
AdminRole = Literal["Admin", "Reviewer"]


class UserBase(BaseModel):
    email: EmailStr
    role: AdminRole
    organization: Optional[str] = None
    is_active: bool = True


class UserCreate(UserBase):
    password: Optional[str] = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ("Admin", "Reviewer"):
            raise ValueError("Role must be 'Admin' or 'Reviewer'")
        return v


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    role: Optional[AdminRole] = None
    organization: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: UUID
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    invited_at: Optional[datetime] = None
    first_login_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class GoogleAuthRequest(BaseModel):
    """Request body for Google ID token verification."""

    token: str


class CurrentUserResponse(BaseModel):
    """Response for /auth/me endpoint."""

    id: UUID
    email: EmailStr
    role: AdminRole
    organization: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class UserInviteRequest(BaseModel):
    """Request body for inviting a new user."""

    email: EmailStr
    role: AdminRole
    organization: Optional[str] = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ("Admin", "Reviewer"):
            raise ValueError("Role must be 'Admin' or 'Reviewer'")
        return v
