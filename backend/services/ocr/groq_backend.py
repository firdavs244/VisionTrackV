"""Groq Vision OCR backend (free tier, fast inference)."""

import base64
import json
import logging
import re

import httpx

from backend.config import settings
from backend.services.ocr.base import RawOcrResult

logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

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


class GroqBackend:
    """OCR via Groq's Vision API (OpenAI-compatible)."""

    name = "groq"

    def __init__(self) -> None:
        if not settings.GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY o'rnatilmagan")
        self._headers = {
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            "Content-Type": "application/json",
        }

    async def detect(self, image_bytes: bytes, mime_type: str) -> RawOcrResult:
        """Send the image to Groq Vision and parse the JSON response."""
        b64 = base64.standard_b64encode(image_bytes).decode("ascii")
        data_url = f"data:{mime_type};base64,{b64}"

        body = {
            "model": settings.GROQ_MODEL,
            "max_completion_tokens": 1024,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": data_url},
                        },
                        {"type": "text", "text": PROMPT},
                    ],
                }
            ],
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(GROQ_API_URL, headers=self._headers, json=body)

        if resp.status_code != 200:
            body_text = resp.text
            logger.error("Groq API %s: %s", resp.status_code, body_text[:500])
            raise RuntimeError(f"Groq API error {resp.status_code}: {body_text[:200]}")

        data = resp.json()

        # Extract text from OpenAI-compatible response
        raw_text = ""
        choices = data.get("choices", [])
        if choices:
            raw_text = choices[0].get("message", {}).get("content", "").strip()

        # Try parse JSON object embedded in the response
        parsed: dict = {}
        match = re.search(r"\{[\s\S]*\}", raw_text)
        if match:
            try:
                parsed = json.loads(match.group(0))
            except json.JSONDecodeError:
                logger.warning("Groq returned non-JSON: %s", raw_text[:200])

        all_text = parsed.get("all_text_found") or ""
        candidate = parsed.get("serial_candidate")
        confidence = float(parsed.get("confidence", 0) or 0)
        description = parsed.get("description") or raw_text

        texts: list[str] = []
        if candidate:
            texts.append(str(candidate))
        if all_text:
            texts.extend([t.strip() for t in re.split(r"[,;\n]", str(all_text)) if t.strip()])

        return RawOcrResult(
            backend=self.name,
            texts=texts,
            best_text=str(candidate) if candidate else (all_text or None),
            confidence=max(0.0, min(100.0, confidence)),
            raw_response=description,
        )
