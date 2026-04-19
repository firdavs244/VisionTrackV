"""Camera Pydantic schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.models.camera import CameraStatus


class CameraRead(BaseModel):
    """Camera data + statistics."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    location: str
    status: CameraStatus
    last_seen_at: datetime | None = None
    created_at: datetime


class CameraReadWithStats(CameraRead):
    """Camera with aggregated counts."""

    total_parts: int = 0
    today_parts: int = 0


class CameraUpdate(BaseModel):
    """Partial camera update."""

    name: str | None = Field(None, min_length=1, max_length=100)
    location: str | None = Field(None, max_length=100)
    status: CameraStatus | None = None
