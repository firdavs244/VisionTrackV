"""Parts CRUD endpoints."""
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.middleware.auth_middleware import get_current_user
from backend.models.activity_log import ActivityType
from backend.models.part import PartStatus
from backend.models.user import User
from backend.schemas.common import MessageResponse, Page, PageMeta
from backend.schemas.part import PartCreate, PartRead, PartUpdate
from backend.services import activity_service, part_service

router = APIRouter(prefix="/parts", tags=["parts"])


@router.get("/", response_model=Page[PartRead])
async def list_parts(
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    limit: int = Query(15, ge=1, le=100),
    search: str | None = None,
    status_: PartStatus | None = Query(None, alias="status"),
    camera: str | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
) -> Page[PartRead]:
    """Paginated parts list."""
    items, total = await part_service.list_parts(
        session,
        page=page,
        limit=limit,
        search=search,
        status=status_,
        camera_id=camera,
        from_date=from_date,
        to_date=to_date,
    )
    pages = (total + limit - 1) // limit if total else 0
    return Page[PartRead](
        items=[PartRead.model_validate(p) for p in items],
        meta=PageMeta(total=total, page=page, limit=limit, pages=pages),
    )


@router.get("/export/csv")
async def export_csv(
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> Response:
    """Download all parts as CSV."""
    data = await part_service.export_csv(session)
    return Response(
        content=data,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="visiontrack-parts.csv"'},
    )


@router.get("/{part_id}", response_model=PartRead)
async def get_part(
    part_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> PartRead:
    """Single part details."""
    part = await part_service.get_part(session, part_id)
    return PartRead.model_validate(part)


@router.post("/", response_model=PartRead, status_code=status.HTTP_201_CREATED)
async def create_part(
    payload: PartCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> PartRead:
    """Create a part manually."""
    part = await part_service.create_part(
        session,
        serial_number=payload.serial_number,
        camera_id=payload.camera_id,
        confidence=payload.confidence,
        status=payload.status,
        image_path=payload.image_path,
        notes=payload.notes,
        analysis_text=payload.analysis_text,
        scanned_by=user.id,
    )
    await activity_service.log(
        session,
        type_=ActivityType.OK,
        message=f"Yangi detal qo'shildi: {part.serial_number}",
        user_id=user.id,
    )
    return PartRead.model_validate(part)


@router.put("/{part_id}", response_model=PartRead)
async def update_part(
    part_id: int,
    payload: PartUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> PartRead:
    """Patch a part."""
    part = await part_service.update_part(
        session,
        part_id,
        serial_number=payload.serial_number,
        status=payload.status,
        notes=payload.notes,
    )
    await activity_service.log(
        session,
        type_=ActivityType.INFO,
        message=f"Detal yangilandi: {part.serial_number}",
        user_id=user.id,
    )
    return PartRead.model_validate(part)


@router.delete("/{part_id}", response_model=MessageResponse)
async def delete_part(
    part_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> MessageResponse:
    """Soft-delete a part."""
    part = await part_service.get_part(session, part_id)
    serial = part.serial_number
    await part_service.delete_part(session, part_id)
    await activity_service.log(
        session,
        type_=ActivityType.WARN,
        message=f"O'chirildi: {serial}",
        user_id=user.id,
    )
    return MessageResponse(message=f"O'chirildi: {serial}")


@router.post("/{part_id}/verify", response_model=PartRead)
async def verify_part(
    part_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> PartRead:
    """Mark part as verified."""
    part = await part_service.set_status(session, part_id, PartStatus.VERIFIED)
    await activity_service.log(
        session,
        type_=ActivityType.OK,
        message=f"Tasdiqlandi: {part.serial_number}",
        user_id=user.id,
    )
    return PartRead.model_validate(part)


@router.post("/{part_id}/reject", response_model=PartRead)
async def reject_part(
    part_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> PartRead:
    """Mark part as rejected."""
    part = await part_service.set_status(session, part_id, PartStatus.REJECTED)
    await activity_service.log(
        session,
        type_=ActivityType.WARN,
        message=f"Rad etildi: {part.serial_number}",
        user_id=user.id,
    )
    return PartRead.model_validate(part)
