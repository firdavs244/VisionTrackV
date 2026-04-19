"""OCR scan schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field

from backend.schemas.part import PartRead


class ScanResult(BaseModel):
    """Result of an OCR scan attempt."""

    found: bool
    serial_number: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=100.0)
    backend: str  # "claude" | "easyocr"
    processing_time_ms: int
    all_texts: list[str] = []
    analysis_text: str | None = None
    reject_reason: str | None = None
    image_path: str | None = None
    part: PartRead | None = None


class ManualScanRequest(BaseModel):
    """Manual entry payload."""

    serial_number: str = Field(..., min_length=6, max_length=32)
    camera_id: str = Field(..., min_length=1, max_length=20)
    notes: str | None = None
    image_path: str | None = None
