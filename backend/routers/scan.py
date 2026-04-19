"""OCR scan endpoints."""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_db
from backend.middleware.auth_middleware import get_current_user
from backend.models.activity_log import ActivityType
from backend.models.part import PartStatus
from backend.models.user import User
from backend.schemas.part import PartRead
from backend.schemas.scan import ManualScanRequest, ScanResult
from backend.services import activity_service, part_service
from backend.services.ocr.pipeline import process_image
from backend.utils.file_validation import validate_and_save_image

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scan", tags=["scan"])


@router.post("/upload", response_model=ScanResult, status_code=status.HTTP_200_OK)
async def upload_scan(
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    image: Annotated[UploadFile, File(...)],
    camera_id: Annotated[str, Form(...)],
    min_confidence: Annotated[float, Form()] = 85.0,
) -> ScanResult:
    """Upload a part image, run OCR, persist on success.

    The OCR backend is selected by ``OCR_BACKEND`` settings (auto / claude /
    easyocr). On success a ``Part`` row is created.
    """
    saved_path, raw, mime = await validate_and_save_image(image)

    try:
        result = await process_image(raw, mime)
    except Exception as exc:
        logger.exception("OCR pipeline failed")
        await activity_service.log(
            session,
            type_=ActivityType.ERROR,
            message=f"OCR xatosi: {exc}",
            user_id=user.id,
        )
        raise

    rel_path = saved_path.relative_to(settings.upload_path.parent).as_posix()
    result.image_path = rel_path

    if result.found and result.serial_number:
        part_status = (
            PartStatus.VERIFIED if result.confidence >= min_confidence else PartStatus.REVIEW
        )
        part = await part_service.create_part(
            session,
            serial_number=result.serial_number,
            camera_id=camera_id,
            confidence=result.confidence,
            status=part_status,
            image_path=rel_path,
            analysis_text=result.analysis_text,
            ocr_backend=result.backend,
            scanned_by=user.id,
        )
        result.part = PartRead.model_validate(part)
        await activity_service.log(
            session,
            type_=ActivityType.OK,
            message=f"Skan qabul qilindi: {result.serial_number} ({result.confidence:.1f}%)",
            context=camera_id,
            user_id=user.id,
        )
    else:
        await activity_service.log(
            session,
            type_=ActivityType.WARN,
            message=f"Skan rad etildi: {(result.reject_reason or 'format topilmadi')[:80]}",
            context=camera_id,
            user_id=user.id,
        )
    return result


@router.post("/manual", response_model=PartRead, status_code=status.HTTP_201_CREATED)
async def manual_scan(
    payload: ManualScanRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> PartRead:
    """Insert a part with a manually-entered serial number."""
    part = await part_service.create_part(
        session,
        serial_number=payload.serial_number,
        camera_id=payload.camera_id,
        confidence=100.0,
        status=PartStatus.VERIFIED,
        image_path=payload.image_path,
        notes=payload.notes,
        analysis_text="Qo'lda kiritilgan",
        ocr_backend="manual",
        scanned_by=user.id,
    )
    await activity_service.log(
        session,
        type_=ActivityType.INFO,
        message=f"Qo'lda kiritildi: {part.serial_number}",
        user_id=user.id,
    )
    return PartRead.model_validate(part)
