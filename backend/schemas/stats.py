"""Stats schemas."""
from __future__ import annotations

from pydantic import BaseModel


class OverviewStats(BaseModel):
    """Top-level numbers."""

    total: int
    today: int
    verified: int
    review: int
    rejected: int
    avg_confidence: float
    verified_pct: float


class WeeklyDay(BaseModel):
    """One day in weekly chart."""

    date: str  # YYYY-MM-DD
    label: str  # localized weekday short
    total: int
    verified: int


class WeeklyStats(BaseModel):
    """Last 7 days activity."""

    days: list[WeeklyDay]


class CameraStat(BaseModel):
    """Per-camera aggregated counts."""

    camera_id: str
    name: str
    total: int
    today: int
    verified: int


class CameraStatsResponse(BaseModel):
    """Per-camera distribution."""

    cameras: list[CameraStat]


class HourlyBucket(BaseModel):
    """One hour bucket."""

    hour: int  # 0..23
    count: int


class HourlyStats(BaseModel):
    """Today's hourly activity."""

    buckets: list[HourlyBucket]
