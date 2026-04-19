"""Common OCR backend interface."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class RawOcrResult:
    """Untyped OCR engine output (before serial validation)."""

    backend: str
    texts: list[str] = field(default_factory=list)
    best_text: str | None = None
    confidence: float = 0.0  # 0..100
    raw_response: str | None = None  # for debugging / "Claude javobi" UI


class OcrBackend(Protocol):
    """Protocol implemented by all OCR backends."""

    name: str

    async def detect(self, image_bytes: bytes, mime_type: str) -> RawOcrResult:
        """Run OCR over the given image bytes."""
        ...
