"""Activity log ORM model."""
from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from backend.models.user import User


class ActivityType(str, enum.Enum):
    """Activity log entry type."""

    OK = "ok"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"


class ActivityLog(Base, TimestampMixin):
    """A timeline event displayed on the dashboard feed."""

    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[ActivityType] = mapped_column(
        Enum(ActivityType, name="activity_type", values_callable=lambda x: [e.value for e in x]),
        default=ActivityType.INFO,
        nullable=False,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[str | None] = mapped_column(String(100), nullable=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    user: Mapped["User | None"] = relationship(back_populates="activities", lazy="joined")
