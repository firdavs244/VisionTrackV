"""Health check endpoint."""
import shutil
from typing import Any

from fastapi import APIRouter

from backend import __version__
from backend.config import settings
from backend.database import ping_db
from backend.services.ocr.pipeline import current_backend_name

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, Any]:
    """Liveness + dependency status."""
    db_ok = await ping_db()
    disk = shutil.disk_usage(settings.upload_path)
    return {
        "status": "ok" if db_ok else "degraded",
        "version": __version__,
        "db": db_ok,
        "ocr_backend": current_backend_name(),
        "disk_free_mb": disk.free // (1024 * 1024),
        "upload_dir": str(settings.upload_path),
    }
