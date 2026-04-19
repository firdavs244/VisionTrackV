"""Part CRUD + filtering + CSV export."""
from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.exceptions import NotFoundError, ValidationError
from backend.models.camera import Camera
from backend.models.part import Part, PartStatus
from backend.utils.serial_validator import validate_serial

logger = logging.getLogger(__name__)


async def _ensure_camera(session: AsyncSession, camera_id: str) -> Camera:
    """Return the camera or raise ``ValidationError``."""
    cam = await session.get(Camera, camera_id)
    if cam is None:
        raise ValidationError(f"Kamera topilmadi: {camera_id}")
    return cam


async def list_parts(
    session: AsyncSession,
    *,
    page: int = 1,
    limit: int = 15,
    search: str | None = None,
    status: PartStatus | None = None,
    camera_id: str | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
) -> tuple[list[Part], int]:
    """Return a paginated, filtered list of parts.

    Returns:
        Tuple ``(items, total)``.
    """
    page = max(1, page)
    limit = max(1, min(100, limit))

    conditions = [Part.is_deleted.is_(False)]
    if search:
        conditions.append(Part.serial_number.ilike(f"%{search.upper()}%"))
    if status is not None:
        conditions.append(Part.status == status)
    if camera_id:
        conditions.append(Part.camera_id == camera_id)
    if from_date:
        conditions.append(Part.created_at >= from_date)
    if to_date:
        conditions.append(Part.created_at <= to_date)

    where = and_(*conditions)

    total = (await session.execute(select(func.count(Part.id)).where(where))).scalar_one()

    stmt = (
        select(Part)
        .where(where)
        .order_by(Part.created_at.desc(), Part.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    items = list((await session.execute(stmt)).scalars().unique().all())
    return items, int(total)


async def get_part(session: AsyncSession, part_id: int) -> Part:
    """Return part or raise NotFoundError."""
    part = await session.get(Part, part_id)
    if part is None or part.is_deleted:
        raise NotFoundError(f"Detal topilmadi: #{part_id}")
    return part


async def create_part(
    session: AsyncSession,
    *,
    serial_number: str,
    camera_id: str,
    confidence: float = 100.0,
    status: PartStatus = PartStatus.VERIFIED,
    image_path: str | None = None,
    notes: str | None = None,
    analysis_text: str | None = None,
    ocr_backend: str | None = None,
    scanned_by: int | None = None,
) -> Part:
    """Persist a new ``Part``."""
    normalised = validate_serial(serial_number)
    if normalised is None:
        raise ValidationError(
            "Seriya raqam formati noto'g'ri (2 harf + 4-6 raqam)",
            details={"raw": serial_number},
        )
    cam = await _ensure_camera(session, camera_id)
    cam.last_seen_at = datetime.now(timezone.utc)

    part = Part(
        serial_number=normalised,
        camera_id=camera_id,
        confidence=float(confidence),
        status=status,
        image_path=image_path,
        notes=notes,
        analysis_text=analysis_text,
        ocr_backend=ocr_backend,
        scanned_by=scanned_by,
    )
    session.add(part)
    await session.commit()
    await session.refresh(part)
    return part


async def update_part(
    session: AsyncSession,
    part_id: int,
    *,
    serial_number: str | None = None,
    status: PartStatus | None = None,
    notes: str | None = None,
) -> Part:
    """Patch a part's mutable fields."""
    part = await get_part(session, part_id)
    if serial_number is not None:
        normalised = validate_serial(serial_number)
        if normalised is None:
            raise ValidationError("Seriya raqam formati noto'g'ri")
        part.serial_number = normalised
    if status is not None:
        part.status = status
    if notes is not None:
        part.notes = notes
    await session.commit()
    await session.refresh(part)
    return part


async def set_status(session: AsyncSession, part_id: int, status: PartStatus) -> Part:
    """Shortcut for verify/reject."""
    return await update_part(session, part_id, status=status)


async def delete_part(session: AsyncSession, part_id: int) -> None:
    """Soft-delete a part."""
    part = await get_part(session, part_id)
    part.is_deleted = True
    await session.commit()


async def export_csv(session: AsyncSession) -> bytes:
    """Render every non-deleted part as a UTF-8 CSV blob."""
    stmt = select(Part).where(Part.is_deleted.is_(False)).order_by(Part.created_at.desc())
    rows = (await session.execute(stmt)).scalars().unique().all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "id",
            "serial_number",
            "camera_id",
            "confidence",
            "status",
            "ocr_backend",
            "notes",
            "created_at",
        ]
    )
    for p in rows:
        writer.writerow(
            [
                p.id,
                p.serial_number,
                p.camera_id,
                f"{p.confidence:.2f}",
                p.status.value,
                p.ocr_backend or "",
                (p.notes or "").replace("\n", " "),
                p.created_at.isoformat(),
            ]
        )
    return buf.getvalue().encode("utf-8-sig")  # BOM for Excel
