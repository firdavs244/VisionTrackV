"""Authentication service: bcrypt hashing + PyJWT tokens."""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.exceptions import AuthError
from backend.models.user import User

logger = logging.getLogger(__name__)

ACCESS_TYPE = "access"
REFRESH_TYPE = "refresh"


# ─── Password hashing ─────────────────────────────────────


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt (cost 12)."""
    if not password:
        raise ValueError("Password must not be empty")
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Verify a plaintext password against a stored hash."""
    if not password or not hashed:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# ─── JWT ──────────────────────────────────────────────────


def _create_token(subject: str, token_type: str, expires_delta: timedelta) -> str:
    """Create a signed JWT."""
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "jti": secrets.token_urlsafe(16),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: int) -> str:
    """Issue a short-lived access token for ``user_id``."""
    return _create_token(
        str(user_id),
        ACCESS_TYPE,
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(user_id: int) -> str:
    """Issue a long-lived refresh token for ``user_id``."""
    return _create_token(
        str(user_id),
        REFRESH_TYPE,
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str, expected_type: str | None = None) -> dict[str, Any]:
    """Decode and validate a JWT.

    Args:
        token: encoded JWT string.
        expected_type: enforce ``type`` claim if provided.

    Returns:
        Decoded payload dict.

    Raises:
        AuthError: on invalid signature, expired token, or wrong type.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("Token muddati tugagan") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthError("Yaroqsiz token") from exc

    if expected_type and payload.get("type") != expected_type:
        raise AuthError(f"Kutilgan token turi: {expected_type}")
    return payload


# ─── DB-backed authentication ────────────────────────────


async def authenticate(session: AsyncSession, username: str, password: str) -> User:
    """Verify credentials and return the active ``User``.

    Raises:
        AuthError: if user not found, inactive, or password mismatched.
    """
    stmt = select(User).where(User.username == username)
    user = (await session.execute(stmt)).scalar_one_or_none()
    if not user or not user.is_active:
        raise AuthError("Login yoki parol noto'g'ri")
    if not verify_password(password, user.password_hash):
        raise AuthError("Login yoki parol noto'g'ri")

    user.last_login = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(user)
    return user


async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    """Return user by primary key, or None."""
    return await session.get(User, user_id)


def access_token_seconds() -> int:
    """Lifetime of an access token in seconds."""
    return settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
