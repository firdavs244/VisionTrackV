"""Anthropic Claude Vision OCR backend."""
from __future__ import annotations

import base64
import json
import logging
import re

import httpx

from backend.config import settings
from backend.services.ocr.base import RawOcrResult

logger = logging.getLogger(__name__)

CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"

PROMPT = """Siz sanoat OCR tizimisiz. Tasvirda ko'rinadigan BARCHA harflar va raqamlarni o'qing.

QOIDA — Faqat quyidagi formatga mos seriya raqamni qabul qiling:
- AYNAN 2 ta lotin harf (A-Z)
- Keyin bo'shliq, chiziqcha yoki hech narsa
- Keyin 4 dan 6 gacha raqam (0-9)

TO'G'RI: AD 00723, XK1234, MF-9876, ZP99999
NOTO'G'RI: ASD32 (3 harf), A1234 (1 harf), AB123 (3 raqam), AB1234567 (7 raqam)

FAQAT JSON formatida javob bering, boshqa hech narsa qo'shmang:
{
  "all_text_found": "tasvirda ko'rilgan barcha matn",
  "serial_candidate": "formatga mos matn yoki null",
  "found": true yoki false,
  "confidence": 0-100,
  "description": "qisqa o'zbekcha izoh"
}"""


class ClaudeBackend:
    """OCR via Anthropic's Vision API."""

    name = "claude"

    def __init__(self) -> None:
        if not settings.ANTHROPIC_API_KEY:
            raise RuntimeError("ANTHROPIC_API_KEY o'rnatilmagan")
        self._headers = {
            "x-api-key": settings.ANTHROPIC_API_KEY,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }

    async def detect(self, image_bytes: bytes, mime_type: str) -> RawOcrResult:
        """Send the image to Claude Vision and parse the JSON response."""
        b64 = base64.standard_b64encode(image_bytes).decode("ascii")
        body = {
            "model": settings.ANTHROPIC_MODEL,
            "max_tokens": 1000,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mime_type,
                                "data": b64,
                            },
                        },
                        {"type": "text", "text": PROMPT},
                    ],
                }
            ],
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(CLAUDE_API_URL, headers=self._headers, json=body)
        resp.raise_for_status()
        data = resp.json()

        # Extract text content
        text_blocks = [
            b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"
        ]
        raw_text = "\n".join(text_blocks).strip()

        # Try parse JSON object embedded in the response
        parsed: dict = {}
        match = re.search(r"\{[\s\S]*\}", raw_text)
        if match:
            try:
                parsed = json.loads(match.group(0))
            except json.JSONDecodeError:
                logger.warning("Claude returned non-JSON: %s", raw_text[:200])

        all_text = parsed.get("all_text_found") or ""
        candidate = parsed.get("serial_candidate")
        confidence = float(parsed.get("confidence", 0) or 0)
        description = parsed.get("description") or raw_text

        texts: list[str] = []
        if candidate:
            texts.append(str(candidate))
        if all_text:
            # Split on common separators so the validator can scan each token.
            texts.extend([t.strip() for t in re.split(r"[,;\n]", str(all_text)) if t.strip()])

        return RawOcrResult(
            backend=self.name,
            texts=texts,
            best_text=str(candidate) if candidate else (all_text or None),
            confidence=max(0.0, min(100.0, confidence)),
            raw_response=description,
        )
