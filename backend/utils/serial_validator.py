"""Serial number validation and extraction.

Format rule: EXACTLY 2 latin letters + 4 to 6 digits.
Allowed separators (stripped): space, dash, underscore, dot, slash, backslash.

Valid:    AD0072, AD 0072, AD-0072, XK1234, MF-9876, AB999999
Invalid:  ASD32 (3 letters), A1234 (1 letter), AB123 (too few digits),
          AB1234567 (too many digits)
"""
from __future__ import annotations

import re

SERIAL_PATTERN = re.compile(r"^[A-Z]{2}\d{4,6}$")
_SEPARATORS = re.compile(r"[\s\-_./\\]")

# Search patterns ordered longest-to-shortest so we always grab the most digits.
_SEARCH_PATTERNS = [
    re.compile(r"\b([A-Z]{2})[\s\-_]?(\d{6})\b"),
    re.compile(r"\b([A-Z]{2})[\s\-_]?(\d{5})\b"),
    re.compile(r"\b([A-Z]{2})[\s\-_]?(\d{4})\b"),
]


def validate_serial(raw: str | None) -> str | None:
    """Normalise and validate a candidate serial number.

    Args:
        raw: candidate string (may contain separators / lowercase).

    Returns:
        Normalised uppercase serial (e.g. ``"AD0072"``) or ``None`` if invalid.
    """
    if not raw:
        return None
    clean = _SEPARATORS.sub("", raw.upper())
    return clean if SERIAL_PATTERN.match(clean) else None


def extract_from_text(text: str | None) -> str | None:
    """Extract the first matching serial number from a free-form text block.

    Args:
        text: arbitrary OCR output.

    Returns:
        Normalised serial or ``None``.
    """
    if not text:
        return None
    upper = text.upper()
    for pattern in _SEARCH_PATTERNS:
        match = pattern.search(upper)
        if match:
            return match.group(1) + match.group(2)
    return None


def reject_reason(raw: str | None) -> str:
    """Return a human-readable explanation of why ``raw`` was rejected."""
    if not raw:
        return "Bo'sh matn"
    clean = _SEPARATORS.sub("", raw.upper())
    letters = sum(1 for c in clean if c.isalpha())
    digits = sum(1 for c in clean if c.isdigit())
    parts = [f'"{raw.strip()}" — {letters} ta harf + {digits} ta raqam']
    if letters != 2:
        parts.append(f"harf soni noto'g'ri ({letters} ta, aynan 2 ta kerak)")
    if digits < 4:
        parts.append(f"raqam soni kam ({digits} ta, kamida 4 ta kerak)")
    if digits > 6:
        parts.append(f"raqam soni ko'p ({digits} ta, ko'pi bilan 6 ta)")
    return ". ".join(parts)
