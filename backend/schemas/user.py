"""User-related Pydantic schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.models.user import UserRole


class LoginRequest(BaseModel):
    """Login credentials."""

    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=1, max_length=128)


class TokenPair(BaseModel):
    """JWT access + refresh tokens."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until access token expires


class RefreshRequest(BaseModel):
    """Refresh token payload."""

    refresh_token: str


class UserRead(BaseModel):
    """Public user data."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    last_login: datetime | None = None


class LoginResponse(BaseModel):
    """Response for /auth/login."""

    user: UserRead
    tokens: TokenPair


class UserCreate(BaseModel):
    """Create user (admin / seed)."""

    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=4, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=100)
    role: UserRole = UserRole.OPERATOR


class UserUpdate(BaseModel):
    """Partial user update (admin)."""

    full_name: str | None = Field(None, min_length=1, max_length=100)
    role: UserRole | None = None
    is_active: bool | None = None
    password: str | None = Field(None, min_length=4, max_length=128)
