"""Uploaded file validation: size, magic bytes, safe filename."""
from __future__ import annotations

import io
import logging
import uuid
from pathlib import Path

import aiofiles
from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

from backend.config import settings
from backend.exceptions import ValidationError

logger = logging.getLogger(__name__)

# Magic byte signatures for allowed formats
_MAGIC_SIGNATURES: dict[str, list[bytes]] = {
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "image/webp": [b"RIFF"],  # secondary check below
}

_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def _detect_mime(head: bytes) -> str | None:
    """Return MIME type from leading bytes, or None if unknown."""
    if head[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    return None


async def validate_and_save_image(file: UploadFile) -> tuple[Path, bytes, str]:
    """Validate an uploaded image and persist it under ``UPLOAD_DIR``.

    Args:
        file: FastAPI ``UploadFile``.

    Returns:
        Tuple of (saved file path, raw bytes, detected mime type).

    Raises:
        ValidationError: If the file is missing, too large, wrong type,
            or fails Pillow's integrity check.
    """
    if not file or not file.filename:
        raise ValidationError("Fayl yuborilmadi")

    # Read bytes (size cap enforced in routers via Content-Length, but double-check)
    raw = await file.read()
    if not raw:
        raise ValidationError("Fayl bo'sh")
    if len(raw) > settings.max_file_size_bytes:
        raise ValidationError(
            f"Fayl hajmi {settings.MAX_FILE_SIZE_MB}MB dan oshmasligi kerak",
        )

    # Magic byte check
    mime = _detect_mime(raw[:16])
    if mime is None:
        raise ValidationError(
            "Faqat JPEG, PNG yoki WebP tasvirlar qabul qilinadi",
            details={"detected": "unknown"},
        )

    # Pillow integrity check
    try:
        with Image.open(io.BytesIO(raw)) as img:
            img.verify()
    except (UnidentifiedImageError, Exception) as exc:
        raise ValidationError(
            "Tasvir fayli buzilgan yoki o'qib bo'lmaydi",
            details={"error": str(exc)},
        ) from exc

    # Generate safe filename
    suffix = Path(file.filename).suffix.lower()
    if suffix not in _ALLOWED_EXTENSIONS:
        # derive from mime
        suffix = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}[mime]
    safe_name = f"{uuid.uuid4().hex}{suffix}"
    dest = settings.upload_path / safe_name

    async with aiofiles.open(dest, "wb") as f:
        await f.write(raw)

    logger.info("Saved upload: %s (%d bytes, %s)", safe_name, len(raw), mime)
    return dest, raw, mime
