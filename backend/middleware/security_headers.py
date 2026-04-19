"""Security headers middleware (CSP, X-Frame-Options, etc.)."""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Append common security headers to every response.

    NOTE: CSP allows ``'unsafe-inline'`` for scripts and styles because the
    legacy ``visiontrack_v2.html`` design embeds inline CSS/JS — a hard
    requirement of the project. This trades stricter XSS isolation for
    preserving the existing UI as-is.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # Skip for Swagger / Redoc to keep them functional
        path = request.url.path
        is_docs = path.startswith(("/docs", "/redoc", "/openapi"))

        if not is_docs:
            response.headers.setdefault(
                "Content-Security-Policy",
                (
                    "default-src 'self'; "
                    "script-src 'self' 'unsafe-inline' blob:; "
                    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                    "font-src 'self' https://fonts.gstatic.com data:; "
                    "img-src 'self' data: blob:; "
                    "connect-src 'self'; "
                    "frame-ancestors 'none';"
                ),
            )
            response.headers.setdefault("X-Frame-Options", "DENY")

        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        return response
