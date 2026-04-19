"""Activity log schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from backend.models.activity_log import ActivityType


class ActivityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: ActivityType
    message: str
    context: str | None = None
    user_id: int | None = None
    created_at: datetime
