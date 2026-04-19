"""Part (scanned serial number) ORM model."""
from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.models.camera import Camera
    from backend.models.user import User


class PartStatus(str, enum.Enum):
    """Verification status of a scanned part."""

    VERIFIED = "verified"
    REVIEW = "review"
    REJECTED = "rejected"


class Part(Base, TimestampMixin):
    """A serial number scanned from a camera image."""

    __tablename__ = "parts"
    __table_args__ = (
        Index("ix_parts_serial_number", "serial_number"),
        Index("ix_parts_camera_created", "camera_id", "created_at"),
        Index("ix_parts_status", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    serial_number: Mapped[str] = mapped_column(String(32), nullable=False)
    camera_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("cameras.id", ondelete="RESTRICT"),
        nullable=False,
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[PartStatus] = mapped_column(
        Enum(PartStatus, name="part_status", values_callable=lambda x: [e.value for e in x]),
        default=PartStatus.REVIEW,
        nullable=False,
    )
    image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    analysis_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_backend: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    scanned_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    camera: Mapped["Camera"] = relationship(back_populates="parts", lazy="joined")
    scanned_by_user: Mapped["User | None"] = relationship(back_populates="parts", lazy="joined")

    def __repr__(self) -> str:
        return f"<Part id={self.id} serial={self.serial_number!r} status={self.status.value}>"
