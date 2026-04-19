"""OCR pipeline orchestrator: backend selection + serial validation."""
from __future__ import annotations

import logging
import time

from backend.config import settings
from backend.schemas.scan import ScanResult
from backend.services.ocr.base import OcrBackend, RawOcrResult
from backend.utils.serial_validator import (
    extract_from_text,
    reject_reason,
    validate_serial,
)

logger = logging.getLogger(__name__)

_backend_cache: OcrBackend | None = None


def _build_backend() -> OcrBackend:
    """Choose an OCR backend based on configuration."""
    mode = settings.OCR_BACKEND
    has_groq_key = bool(settings.GROQ_API_KEY)

    if mode == "groq" or (mode == "auto" and has_groq_key):
        from backend.services.ocr.groq_backend import GroqBackend

        logger.info("OCR backend: groq")
        return GroqBackend()

    from backend.services.ocr.easyocr_backend import EasyOcrBackend

    logger.info("OCR backend: easyocr")
    return EasyOcrBackend()


def get_backend() -> OcrBackend:
    """Return the cached OCR backend (built on first call)."""
    global _backend_cache
    if _backend_cache is None:
        _backend_cache = _build_backend()
    return _backend_cache


def current_backend_name() -> str:
    """Return the active backend name without forcing initialisation."""
    if _backend_cache is not None:
        return _backend_cache.name
    if settings.OCR_BACKEND == "groq":
        return "groq"
    if settings.OCR_BACKEND == "easyocr":
        return "easyocr"
    return "groq" if settings.GROQ_API_KEY else "easyocr"


def _validate_raw(raw: RawOcrResult) -> tuple[str | None, str | None]:
    """Run validator over raw OCR texts.

    Returns:
        Tuple ``(serial, candidate_for_reject_reason)``.
    """
    # Try the best_text first
    candidate = None
    if raw.best_text:
        candidate = raw.best_text
        serial = validate_serial(raw.best_text) or extract_from_text(raw.best_text)
        if serial:
            return serial, candidate

    # Fallback: scan every text block
    for t in raw.texts:
        serial = validate_serial(t) or extract_from_text(t)
        if serial:
            return serial, t
        if candidate is None:
            candidate = t

    # Last resort: search the joined response
    if raw.raw_response:
        serial = extract_from_text(raw.raw_response)
        if serial:
            return serial, raw.raw_response

    return None, candidate


async def process_image(image_bytes: bytes, mime_type: str) -> ScanResult:
    """Run OCR end-to-end and return a structured ``ScanResult``.

    Args:
        image_bytes: raw image bytes.
        mime_type: MIME type (e.g. ``image/jpeg``).

    Returns:
        ``ScanResult`` (no DB write — caller persists the part).
    """
    backend = get_backend()
    start = time.perf_counter()

    try:
        raw = await backend.detect(image_bytes, mime_type)
    except Exception as exc:
        # Auto-fallback: if Claude fails and we are in auto mode, try EasyOCR
        if settings.OCR_BACKEND == "auto" and backend.name == "claude":
            logger.warning("Claude OCR failed (%s); falling back to EasyOCR", exc)
            from backend.services.ocr.easyocr_backend import EasyOcrBackend

            backup = EasyOcrBackend()
            raw = await backup.detect(image_bytes, mime_type)
        else:
            raise

    elapsed_ms = int((time.perf_counter() - start) * 1000)

    serial, candidate = _validate_raw(raw)

    if serial:
        confidence = raw.confidence if raw.confidence > 0 else 85.0
        return ScanResult(
            found=True,
            serial_number=serial,
            confidence=round(confidence, 2),
            backend=raw.backend,
            processing_time_ms=elapsed_ms,
            all_texts=raw.texts,
            analysis_text=raw.raw_response,
        )

    return ScanResult(
        found=False,
        serial_number=None,
        confidence=0.0,
        backend=raw.backend,
        processing_time_ms=elapsed_ms,
        all_texts=raw.texts,
        analysis_text=raw.raw_response,
        reject_reason=reject_reason(candidate),
    )
