"""Pydantic schemas for tasks."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.task import TaskStatus, TaskPriority


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    voice_note_id: int | None
    title: str
    description: str | None
    contact_name: str | None
    contact_phone: str | None
    deadline: datetime | None
    priority: TaskPriority
    status: TaskStatus
    confidence: float | None
    intent: str | None
    meeting_link: str | None
    created_at: datetime
    completed_at: datetime | None
