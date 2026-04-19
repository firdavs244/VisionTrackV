"""EasyOCR offline backend (lazy-loaded singleton)."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from backend.config import settings
from backend.services.ocr.base import RawOcrResult
from backend.utils.image_processor import preprocess_for_ocr

logger = logging.getLogger(__name__)

_reader_lock = asyncio.Lock()
_reader: Any | None = None  # easyocr.Reader, lazy-initialised


async def _get_reader():
    """Lazily build the global EasyOCR reader (heavy)."""
    global _reader
    if _reader is not None:
        return _reader
    async with _reader_lock:
        if _reader is None:
            import easyocr

            logger.info(
                "Initialising EasyOCR (langs=%s gpu=%s)…",
                settings.ocr_languages_list,
                settings.OCR_GPU,
            )
            _reader = await asyncio.to_thread(
                easyocr.Reader,
                settings.ocr_languages_list,
                gpu=settings.OCR_GPU,
                verbose=False,
            )
            logger.info("EasyOCR ready.")
    return _reader


class EasyOcrBackend:
    """Offline OCR using EasyOCR + OpenCV preprocessing."""

    name = "easyocr"

    async def detect(self, image_bytes: bytes, mime_type: str) -> RawOcrResult:  # noqa: ARG002
        """Run EasyOCR on a preprocessed image."""
        # Preprocess in a thread (CPU-bound)
        processed = await asyncio.to_thread(preprocess_for_ocr, image_bytes)

        reader = await _get_reader()

        # readtext is blocking – run in threadpool
        results = await asyncio.to_thread(
            reader.readtext,
            processed,
            detail=1,
            paragraph=False,
        )

        # results: list of (bbox, text, confidence in 0..1)
        texts: list[str] = []
        best_text: str | None = None
        best_conf = 0.0
        for _bbox, text, conf in results:
            t = str(text).strip()
            if not t:
                continue
            texts.append(t)
            if conf > best_conf:
                best_conf = float(conf)
                best_text = t

        return RawOcrResult(
            backend=self.name,
            texts=texts,
            best_text=best_text,
            confidence=round(best_conf * 100.0, 2),
            raw_response=" | ".join(texts) if texts else None,
        )


async def warmup() -> None:
    """Initialise EasyOCR ahead of the first request (called from lifespan)."""
    try:
        await _get_reader()
    except Exception as exc:  # pragma: no cover
        logger.warning("EasyOCR warmup failed: %s", exc)
