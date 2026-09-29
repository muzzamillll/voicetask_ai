"""Task model — an actionable item extracted from a voice note."""
import enum
from datetime import datetime, timezone

from sqlalchemy import Integer, String, Float, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    voice_note_id: Mapped[int | None] = mapped_column(ForeignKey("voice_notes.id"), nullable=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    priority: Mapped[TaskPriority] = mapped_column(Enum(TaskPriority), default=TaskPriority.MEDIUM)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), default=TaskStatus.PENDING)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    # The specific AI-detected intent (task/reminder/meeting/appointment/
    # follow_up/note/unknown) — Order and Payment intents get their own
    # tables, but everything else lands here as a Task, so we preserve
    # which specific intent it was for analytics (Phase 11).
    intent: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # Auto-generated Jitsi Meet link for meeting/appointment intents.
    meeting_link: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="tasks")
    voice_note = relationship("VoiceNote", back_populates="tasks")
