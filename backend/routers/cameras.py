"""Cameras endpoints."""
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.exceptions import NotFoundError
from backend.middleware.auth_middleware import get_current_user, require_role
from backend.models.camera import Camera
from backend.models.part import Part
from backend.models.user import User, UserRole
from backend.schemas.camera import CameraReadWithStats, CameraUpdate

router = APIRouter(prefix="/cameras", tags=["cameras"])


def _today_start_utc() -> datetime:
    return datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)


async def _attach_stats(session: AsyncSession, cams: list[Camera]) -> list[CameraReadWithStats]:
    today_start = _today_start_utc()

    totals = dict(
        (
            await session.execute(
                select(Part.camera_id, func.count(Part.id))
                .where(Part.is_deleted.is_(False))
                .group_by(Part.camera_id)
            )
        ).all()
    )
    today = dict(
        (
            await session.execute(
                select(Part.camera_id, func.count(Part.id))
                .where(Part.is_deleted.is_(False), Part.created_at >= today_start)
                .group_by(Part.camera_id)
            )
        ).all()
    )
    out: list[CameraReadWithStats] = []
    for c in cams:
        item = CameraReadWithStats.model_validate(c)
        item.total_parts = int(totals.get(c.id, 0))
        item.today_parts = int(today.get(c.id, 0))
        out.append(item)
    return out


@router.get("/", response_model=list[CameraReadWithStats])
async def list_cameras(
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> list[CameraReadWithStats]:
    """All cameras with aggregated counts."""
    cams = (await session.execute(select(Camera).order_by(Camera.id))).scalars().all()
    return await _attach_stats(session, list(cams))


@router.get("/{camera_id}", response_model=CameraReadWithStats)
async def get_camera(
    camera_id: str,
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> CameraReadWithStats:
    """Single camera details + counts."""
    cam = await session.get(Camera, camera_id)
    if cam is None:
        raise NotFoundError(f"Kamera topilmadi: {camera_id}")
    out = await _attach_stats(session, [cam])
    return out[0]


@router.patch("/{camera_id}", response_model=CameraReadWithStats)
async def update_camera(
    camera_id: str,
    payload: CameraUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_role(UserRole.ADMIN))],
) -> CameraReadWithStats:
    """Update camera fields (admin only)."""
    cam = await session.get(Camera, camera_id)
    if cam is None:
        raise NotFoundError(f"Kamera topilmadi: {camera_id}")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(cam, field, value)
    await session.commit()
    await session.refresh(cam)
    out = await _attach_stats(session, [cam])
    return out[0]
