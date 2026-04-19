"""Application configuration loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Global settings.

    Values are read from environment variables (or .env file).
    """

    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── Database ──────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./visiontrack.db"

    # ─── JWT ───────────────────────────────────────
    SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ─── Server ────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # ─── CORS ──────────────────────────────────────
    ALLOWED_ORIGINS: str = "http://localhost:8000,http://127.0.0.1:8000"

    # ─── Uploads ───────────────────────────────────
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE_MB: int = 15

    # ─── OCR ───────────────────────────────────────
    OCR_BACKEND: Literal["auto", "groq", "easyocr"] = "auto"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    OCR_LANGUAGES: str = "en"
    OCR_GPU: bool = False
    OCR_MIN_CONFIDENCE: float = 0.5

    # ─── Seed ──────────────────────────────────────
    SEED_ADMIN_USERNAME: str = "admin"
    SEED_ADMIN_PASSWORD: str = "admin123"
    SEED_OPERATOR_USERNAME: str = "operator1"
    SEED_OPERATOR_PASSWORD: str = "op123"

    # ─── Derived properties ───────────────────────
    @property
    def allowed_origins_list(self) -> list[str]:
        """Return CORS origins as a list."""
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def ocr_languages_list(self) -> list[str]:
        """Return OCR languages as a list."""
        return [lang.strip() for lang in self.OCR_LANGUAGES.split(",") if lang.strip()]

    @property
    def upload_path(self) -> Path:
        """Absolute path to upload directory (created if missing)."""
        path = ROOT_DIR / self.UPLOAD_DIR
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def max_file_size_bytes(self) -> int:
        """Max upload size in bytes."""
        return self.MAX_FILE_SIZE_MB * 1024 * 1024

    @property
    def is_sqlite(self) -> bool:
        """True if DATABASE_URL points to SQLite."""
        return self.DATABASE_URL.startswith("sqlite")

    @field_validator("SECRET_KEY")
    @classmethod
    def _check_secret(cls, v: str) -> str:
        if len(v) < 16:
            raise ValueError("SECRET_KEY must be at least 16 characters long")
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached Settings instance."""
    return Settings()


settings = get_settings()
