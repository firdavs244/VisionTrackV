"""Auth dependency: extract + verify the bearer token."""
from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.exceptions import AuthError, ForbiddenError
from backend.models.user import User, UserRole
from backend.services.auth_service import ACCESS_TYPE, decode_token, get_user_by_id

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Resolve the request's bearer token to an active ``User``.

    Raises:
        AuthError: missing/invalid token, or inactive user.
    """
    if not token:
        raise AuthError("Avtorizatsiya talab qilinadi", status_code=status.HTTP_401_UNAUTHORIZED)
    payload = decode_token(token, expected_type=ACCESS_TYPE)
    try:
        user_id = int(payload.get("sub", ""))
    except (TypeError, ValueError) as exc:
        raise AuthError("Yaroqsiz token") from exc
    user = await get_user_by_id(session, user_id)
    if user is None or not user.is_active:
        raise AuthError("Foydalanuvchi topilmadi yoki nofaol")
    return user


def require_role(*roles: UserRole) -> Callable:
    """Dependency factory enforcing the user has one of ``roles``."""

    async def _checker(
        user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if user.role not in roles:
            raise ForbiddenError("Sizda yetarli huquq yo'q")
        return user

    return _checker
