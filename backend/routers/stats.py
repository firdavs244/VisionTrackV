"""Statistics endpoints."""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.middleware.auth_middleware import get_current_user
from backend.models.user import User
from backend.schemas.activity import ActivityRead
from backend.schemas.stats import (
    CameraStatsResponse,
    HourlyStats,
    OverviewStats,
    WeeklyStats,
)
from backend.services import activity_service, stats_service

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/overview", response_model=OverviewStats)
async def overview(
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> OverviewStats:
    """Top dashboard KPIs."""
    return await stats_service.overview(session)


@router.get("/weekly", response_model=WeeklyStats)
async def weekly(
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> WeeklyStats:
    """Last 7 days activity for the chart."""
    return WeeklyStats(days=await stats_service.weekly(session))


@router.get("/cameras", response_model=CameraStatsResponse)
async def cameras(
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> CameraStatsResponse:
    """Per-camera totals."""
    return CameraStatsResponse(cameras=await stats_service.cameras(session))


@router.get("/hourly", response_model=HourlyStats)
async def hourly(
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> HourlyStats:
    """Today's hourly activity."""
    return HourlyStats(buckets=await stats_service.hourly(session))


@router.get("/activity", response_model=list[ActivityRead])
async def activity(
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    limit: int = 12,
) -> list[ActivityRead]:
    """Recent activity feed."""
    rows = await activity_service.recent(session, limit=limit)
    return [ActivityRead.model_validate(r) for r in rows]
