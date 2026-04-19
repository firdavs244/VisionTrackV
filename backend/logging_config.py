"""Logging configuration."""
from __future__ import annotations

import logging
import sys
from logging.config import dictConfig

from backend.config import settings


def setup_logging() -> None:
    """Configure root logger with console handler."""
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s [%(levelname)-7s] %(name)s: %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "stream": sys.stdout,
                },
            },
            "loggers": {
                "uvicorn.access": {"level": "WARNING"},
                "sqlalchemy.engine": {"level": "WARNING"},
                "easyocr": {"level": "WARNING"},
            },
            "root": {
                "level": settings.LOG_LEVEL,
                "handlers": ["console"],
            },
        }
    )
    logging.getLogger(__name__).debug("Logging configured (level=%s)", settings.LOG_LEVEL)
