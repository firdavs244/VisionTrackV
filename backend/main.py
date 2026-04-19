"""FastAPI application entry point."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from backend import __version__
from backend.config import ROOT_DIR, settings
from backend.database import ping_db
from backend.exceptions import register_exception_handlers
from backend.logging_config import setup_logging
from backend.middleware.security_headers import SecurityHeadersMiddleware
from backend.routers import auth, cameras, health, parts, scan, stats

setup_logging()
logger = logging.getLogger(__name__)

FRONTEND_DIR = ROOT_DIR / "frontend"
UPLOADS_DIR = settings.upload_path


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    """Startup / shutdown hooks."""
    logger.info("VisionTrack starting (version=%s)", __version__)
    if not await ping_db():
        logger.warning("Database is not reachable on startup — check DATABASE_URL")
    else:
        logger.info("Database OK (%s)", settings.DATABASE_URL.split("@")[-1])
    logger.info("Uploads dir: %s", UPLOADS_DIR)
    yield
    logger.info("VisionTrack shutting down")


app = FastAPI(
    title="VisionTrack API",
    description="Sanoat OCR va detal monitoring tizimi",
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ─── Middleware (order matters: outermost first) ──────────
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

# ─── Rate limiting (slowapi) ──────────────────────────────
app.state.limiter = auth.limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ─── Global exception handlers ────────────────────────────
register_exception_handlers(app)

# ─── API routers ──────────────────────────────────────────
API_PREFIX = "/api/v1"
app.include_router(health.router)  # /health (no prefix)
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(parts.router, prefix=API_PREFIX)
app.include_router(scan.router, prefix=API_PREFIX)
app.include_router(stats.router, prefix=API_PREFIX)
app.include_router(cameras.router, prefix=API_PREFIX)

# ─── Static: uploaded images (read-only) ─────────────────
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

# ─── Static: frontend SPA ─────────────────────────────────
if FRONTEND_DIR.is_dir():
    app.mount(
        "/assets",
        StaticFiles(directory=str(FRONTEND_DIR / "assets")) if (FRONTEND_DIR / "assets").is_dir() else StaticFiles(directory=str(FRONTEND_DIR)),
        name="assets",
    )

    @app.get("/", include_in_schema=False, response_model=None)
    async def _index():
        """Serve the frontend SPA."""
        index = FRONTEND_DIR / "index.html"
        if not index.exists():
            return JSONResponse(
                {"error": {"code": "NOT_FOUND", "message": "frontend/index.html not found"}},
                status_code=404,
            )
        return FileResponse(index)

    @app.get("/{full_path:path}", include_in_schema=False, response_model=None)
    async def _spa_fallback(full_path: str, request: Request):
        """SPA fallback: serve static file if exists else index.html."""
        # Don't intercept API routes
        if full_path.startswith(("api/", "docs", "redoc", "openapi", "uploads/", "health")):
            return JSONResponse(
                {"error": {"code": "NOT_FOUND", "message": "Not found"}},
                status_code=404,
            )
        candidate = FRONTEND_DIR / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIR / "index.html")
else:
    logger.warning("frontend/ directory missing — UI will not be served")
