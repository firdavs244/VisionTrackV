"""Aggregations powering the dashboard charts."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.camera import Camera
from backend.models.part import Part, PartStatus
from backend.schemas.stats import (
    CameraStat,
    HourlyBucket,
    OverviewStats,
    WeeklyDay,
)

_UZ_WEEKDAYS_SHORT = ["Du", "Se", "Cho", "Pa", "Ju", "Sha", "Ya"]


def _start_of_today_utc() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _not_deleted():
    return Part.is_deleted.is_(False)


async def overview(session: AsyncSession) -> OverviewStats:
    """Top-level dashboard KPIs."""
    today_start = _start_of_today_utc()

    base = select(
        func.count(Part.id),
        func.coalesce(func.avg(Part.confidence), 0.0),
        func.sum(case((Part.status == PartStatus.VERIFIED, 1), else_=0)),
        func.sum(case((Part.status == PartStatus.REVIEW, 1), else_=0)),
        func.sum(case((Part.status == PartStatus.REJECTED, 1), else_=0)),
    ).where(_not_deleted())
    total, avg_conf, verified, review, rejected = (await session.execute(base)).one()

    today_stmt = (
        select(func.count(Part.id))
        .where(_not_deleted())
        .where(Part.created_at >= today_start)
    )
    today = (await session.execute(today_stmt)).scalar_one()

    total_i = int(total or 0)
    verified_i = int(verified or 0)
    return OverviewStats(
        total=total_i,
        today=int(today or 0),
        verified=verified_i,
        review=int(review or 0),
        rejected=int(rejected or 0),
        avg_confidence=round(float(avg_conf or 0.0), 2),
        verified_pct=round(verified_i / total_i * 100, 2) if total_i else 0.0,
    )


async def weekly(session: AsyncSession) -> list[WeeklyDay]:
    """Last 7 days (oldest → newest) totals + verified counts."""
    today_start = _start_of_today_utc()
    start = today_start - timedelta(days=6)

    stmt = (
        select(Part.created_at, Part.status)
        .where(_not_deleted())
        .where(Part.created_at >= start)
    )
    rows = (await session.execute(stmt)).all()

    by_day: dict[str, dict[str, int]] = {}
    for created_at, status in rows:
        day = created_at.astimezone(timezone.utc).date().isoformat()
        bucket = by_day.setdefault(day, {"total": 0, "verified": 0})
        bucket["total"] += 1
        if status == PartStatus.VERIFIED:
            bucket["verified"] += 1

    out: list[WeeklyDay] = []
    for i in range(7):
        day = (start + timedelta(days=i)).date()
        key = day.isoformat()
        b = by_day.get(key, {"total": 0, "verified": 0})
        out.append(
            WeeklyDay(
                date=key,
                label=_UZ_WEEKDAYS_SHORT[day.weekday()],
                total=b["total"],
                verified=b["verified"],
            )
        )
    return out


async def cameras(session: AsyncSession) -> list[CameraStat]:
    """Per-camera totals."""
    today_start = _start_of_today_utc()

    cams = (await session.execute(select(Camera).order_by(Camera.id))).scalars().all()

    totals_stmt = (
        select(Part.camera_id, func.count(Part.id))
        .where(_not_deleted())
        .group_by(Part.camera_id)
    )
    totals = dict((await session.execute(totals_stmt)).all())

    today_stmt = (
        select(Part.camera_id, func.count(Part.id))
        .where(and_(_not_deleted(), Part.created_at >= today_start))
        .group_by(Part.camera_id)
    )
    today_map = dict((await session.execute(today_stmt)).all())

    verified_stmt = (
        select(Part.camera_id, func.count(Part.id))
        .where(and_(_not_deleted(), Part.status == PartStatus.VERIFIED))
        .group_by(Part.camera_id)
    )
    verified_map = dict((await session.execute(verified_stmt)).all())

    return [
        CameraStat(
            camera_id=c.id,
            name=c.name,
            total=int(totals.get(c.id, 0)),
            today=int(today_map.get(c.id, 0)),
            verified=int(verified_map.get(c.id, 0)),
        )
        for c in cams
    ]


async def hourly(session: AsyncSession) -> list[HourlyBucket]:
    """Today's per-hour bucketed counts (0..23)."""
    today_start = _start_of_today_utc()
    stmt = (
        select(Part.created_at)
        .where(_not_deleted())
        .where(Part.created_at >= today_start)
    )
    rows = (await session.execute(stmt)).all()
    counts = [0] * 24
    for (created_at,) in rows:
        h = created_at.astimezone(timezone.utc).hour
        counts[h] += 1
    return [HourlyBucket(hour=h, count=c) for h, c in enumerate(counts)]
