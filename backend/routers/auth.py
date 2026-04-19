"""Authentication endpoints."""
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.exceptions import AuthError
from backend.middleware.auth_middleware import get_current_user
from backend.models.activity_log import ActivityType
from backend.models.user import User
from backend.schemas.common import MessageResponse
from backend.schemas.user import (
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    TokenPair,
    UserRead,
)
from backend.services import activity_service
from backend.services.auth_service import (
    REFRESH_TYPE,
    access_token_seconds,
    authenticate,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_user_by_id,
)

router = APIRouter(prefix="/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def login(
    request: Request,  # noqa: ARG001 (required by slowapi)
    payload: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> LoginResponse:
    """Exchange username/password for a JWT pair."""
    user = await authenticate(session, payload.username, payload.password)
    tokens = TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        expires_in=access_token_seconds(),
    )
    await activity_service.log(
        session,
        type_=ActivityType.OK,
        message=f"Tizimga kirdi: {user.username}",
        user_id=user.id,
    )
    return LoginResponse(user=UserRead.model_validate(user), tokens=tokens)


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    payload: RefreshRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TokenPair:
    """Rotate an access token using a valid refresh token."""
    decoded = decode_token(payload.refresh_token, expected_type=REFRESH_TYPE)
    try:
        user_id = int(decoded["sub"])
    except (KeyError, ValueError) as exc:
        raise AuthError("Yaroqsiz refresh token") from exc
    user = await get_user_by_id(session, user_id)
    if user is None or not user.is_active:
        raise AuthError("Foydalanuvchi topilmadi yoki nofaol")
    return TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        expires_in=access_token_seconds(),
    )


@router.get("/me", response_model=UserRead)
async def me(user: Annotated[User, Depends(get_current_user)]) -> UserRead:
    """Return the current user."""
    return UserRead.model_validate(user)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    """Stateless logout (client must drop the tokens)."""
    await activity_service.log(
        session,
        type_=ActivityType.INFO,
        message=f"Tizimdan chiqdi: {user.username}",
        user_id=user.id,
    )
    return MessageResponse(message="Tizimdan chiqildi")
