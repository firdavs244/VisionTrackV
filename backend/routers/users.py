"""User management endpoints (admin only)."""
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.exceptions import ConflictError, NotFoundError
from backend.middleware.auth_middleware import get_current_user, require_role
from backend.models.user import User, UserRole
from backend.schemas.user import UserCreate, UserRead, UserUpdate
from backend.services.auth_service import hash_password

router = APIRouter(prefix="/users", tags=["users"])

_admin = require_role(UserRole.ADMIN)


@router.get("/", response_model=list[UserRead])
async def list_users(
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> list[UserRead]:
    """All users (any authenticated user can list)."""
    users = (await session.execute(select(User).order_by(User.id))).scalars().all()
    return [UserRead.model_validate(u) for u in users]


@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(_admin)],
) -> UserRead:
    """Create a new user (admin only)."""
    existing = (
        await session.execute(select(User).where(User.username == payload.username))
    ).scalar_one_or_none()
    if existing:
        raise ConflictError(f"'{payload.username}' foydalanuvchi nomi band")
    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return UserRead.model_validate(user)


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(_admin)],
) -> UserRead:
    """Update user fields (admin only)."""
    user = await session.get(User, user_id)
    if user is None:
        raise NotFoundError("Foydalanuvchi topilmadi")
    data = payload.model_dump(exclude_unset=True)
    if "password" in data:
        user.password_hash = hash_password(data.pop("password"))
    for field, value in data.items():
        setattr(user, field, value)
    await session.commit()
    await session.refresh(user)
    return UserRead.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
    current: Annotated[User, Depends(_admin)],
) -> None:
    """Deactivate user (admin only, cannot delete self)."""
    if user_id == current.id:
        raise ConflictError("O'zingizni o'chira olmaysiz")
    user = await session.get(User, user_id)
    if user is None:
        raise NotFoundError("Foydalanuvchi topilmadi")
    user.is_active = False
    await session.commit()
