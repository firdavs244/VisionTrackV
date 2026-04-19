"""Common reusable Pydantic schemas."""
from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PageMeta(BaseModel):
    """Pagination metadata."""

    total: int = Field(..., ge=0)
    page: int = Field(..., ge=1)
    limit: int = Field(..., ge=1)
    pages: int = Field(..., ge=0)


class Page(BaseModel, Generic[T]):
    """Generic paginated response."""

    items: list[T]
    meta: PageMeta


class ErrorBody(BaseModel):
    """Inner error body."""

    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """Standard error envelope."""

    error: ErrorBody


class MessageResponse(BaseModel):
    """Generic success message."""

    message: str
