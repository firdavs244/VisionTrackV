"""Seed default users + cameras."""
from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select

from backend.config import settings
from backend.database import AsyncSessionLocal
from backend.logging_config import setup_logging
from backend.models.camera import Camera, CameraStatus
from backend.models.user import User, UserRole
from backend.services.auth_service import hash_password

setup_logging()
logger = logging.getLogger("seed")


DEFAULT_CAMERAS = [
    ("CAM-001", "Konveyer 1 — Kirish", "Seksiya A", CameraStatus.ACTIVE),
    ("CAM-002", "Konveyer 2 — Chiqish", "Seksiya B", CameraStatus.ACTIVE),
    ("CAM-003", "Kontrol nuqtasi", "Seksiya C", CameraStatus.INACTIVE),
    ("CAM-004", "Tayyor mahsulot", "Seksiya D", CameraStatus.ACTIVE),
]


async def _ensure_user(session, *, username: str, password: str, full_name: str, role: UserRole) -> None:
    existing = (
        await session.execute(select(User).where(User.username == username))
    ).scalar_one_or_none()
    if existing:
        logger.info("User exists: %s", username)
        return
    session.add(
        User(
            username=username,
            password_hash=hash_password(password),
            full_name=full_name,
            role=role,
        )
    )
    logger.info("Created user: %s (%s)", username, role.value)


async def _ensure_camera(session, *, id_: str, name: str, location: str, status: CameraStatus) -> None:
    existing = await session.get(Camera, id_)
    if existing:
        logger.info("Camera exists: %s", id_)
        return
    session.add(Camera(id=id_, name=name, location=location, status=status))
    logger.info("Created camera: %s", id_)


async def main() -> None:
    async with AsyncSessionLocal() as session:
        await _ensure_user(
            session,
            username=settings.SEED_ADMIN_USERNAME,
            password=settings.SEED_ADMIN_PASSWORD,
            full_name="Administrator",
            role=UserRole.ADMIN,
        )
        await _ensure_user(
            session,
            username=settings.SEED_OPERATOR_USERNAME,
            password=settings.SEED_OPERATOR_PASSWORD,
            full_name="Operator Aliyev",
            role=UserRole.OPERATOR,
        )
        for cam in DEFAULT_CAMERAS:
            await _ensure_camera(
                session, id_=cam[0], name=cam[1], location=cam[2], status=cam[3]
            )
        await session.commit()
    logger.info("Seed complete.")


if __name__ == "__main__":
    asyncio.run(main())
