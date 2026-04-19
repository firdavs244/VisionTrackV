"""Camera ORM model."""
from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.models.part import Part


class CameraStatus(str, enum.Enum):
    """Camera operational status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


class Camera(Base, TimestampMixin):
    """Production camera (e.g. CAM-001)."""

    __tablename__ = "cameras"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    location: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    status: Mapped[CameraStatus] = mapped_column(
        Enum(CameraStatus, name="camera_status", values_callable=lambda x: [e.value for e in x]),
        default=CameraStatus.ACTIVE,
        nullable=False,
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    parts: Mapped[list["Part"]] = relationship(back_populates="camera")

    def __repr__(self) -> str:
        return f"<Camera id={self.id!r} name={self.name!r} status={self.status.value}>"
