"""Activity log writes + recent feed."""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.activity_log import ActivityLog, ActivityType

logger = logging.getLogger(__name__)


async def log(
    session: AsyncSession,
    *,
    type_: ActivityType,
    message: str,
    context: str | None = None,
    user_id: int | None = None,
    commit: bool = True,
) -> ActivityLog:
    """Insert one activity log row.

    Args:
        commit: if False, leaves the row pending in the session (caller commits).
    """
    entry = ActivityLog(type=type_, message=message, context=context, user_id=user_id)
    session.add(entry)
    if commit:
        await session.commit()
        await session.refresh(entry)
    return entry


async def recent(session: AsyncSession, limit: int = 12) -> list[ActivityLog]:
    """Return the most recent ``limit`` activity entries."""
    stmt = select(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(limit)
    return list((await session.execute(stmt)).scalars().unique().all())
