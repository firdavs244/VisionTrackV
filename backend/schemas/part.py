"""Part Pydantic schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.models.part import PartStatus


class PartBase(BaseModel):
    """Common part fields."""

    serial_number: str = Field(..., min_length=6, max_length=32)
    camera_id: str = Field(..., min_length=1, max_length=20)
    notes: str | None = None


class PartCreate(PartBase):
    """Manual part creation payload."""

    confidence: float = Field(default=100.0, ge=0.0, le=100.0)
    status: PartStatus = PartStatus.VERIFIED
    image_path: str | None = None
    analysis_text: str | None = None


class PartUpdate(BaseModel):
    """Partial update."""

    serial_number: str | None = Field(default=None, min_length=6, max_length=32)
    status: PartStatus | None = None
    notes: str | None = None


class PartRead(BaseModel):
    """Part response model."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    serial_number: str
    camera_id: str
    confidence: float
    status: PartStatus
    image_path: str | None = None
    notes: str | None = None
    analysis_text: str | None = None
    ocr_backend: str | None = None
    scanned_by: int | None = None
    created_at: datetime
    updated_at: datetime
