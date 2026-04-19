"""OpenCV image preprocessing pipeline for OCR."""
from __future__ import annotations

import logging

import cv2
import numpy as np

logger = logging.getLogger(__name__)

_MIN_HEIGHT = 600


def preprocess_for_ocr(image_bytes: bytes) -> np.ndarray:
    """Decode + preprocess an image for OCR.

    Pipeline:
        1. Decode (color)
        2. Upscale if too small (bicubic, target height >= 600px)
        3. Convert to grayscale
        4. CLAHE (contrast enhancement)
        5. Bilateral filter (edge-preserving denoise)
        6. Adaptive threshold
        7. Morphological close (connect characters)

    Args:
        image_bytes: raw image bytes (JPEG / PNG / WebP).

    Returns:
        Single-channel ``uint8`` numpy array suitable for OCR engines.

    Raises:
        ValueError: If the image cannot be decoded.
    """
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Tasvirni dekodlash imkonsiz (noto'g'ri format yoki buzilgan fayl)")

    # Upscale small images
    h, w = img.shape[:2]
    if h < _MIN_HEIGHT:
        scale = _MIN_HEIGHT / h
        new_w, new_h = int(w * scale), int(h * scale)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        logger.debug("Image upscaled %dx%d -> %dx%d", w, h, new_w, new_h)

    # Grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # CLAHE
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    # Bilateral filter (preserve edges, denoise)
    denoised = cv2.bilateralFilter(enhanced, d=9, sigmaColor=75, sigmaSpace=75)

    # Adaptive threshold (binarize)
    binary = cv2.adaptiveThreshold(
        denoised,
        maxValue=255,
        adaptiveMethod=cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        thresholdType=cv2.THRESH_BINARY,
        blockSize=31,
        C=10,
    )

    # Morphological close to connect broken characters
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)

    return closed
