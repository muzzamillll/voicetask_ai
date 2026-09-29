"""VoiceNote model — an uploaded audio file and its processing status."""
import enum
from datetime import datetime, timezone

from sqlalchemy import Integer, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base


class ProcessingStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    TRANSCRIBING = "transcribing"
    EXTRACTING = "extracting"
    REVIEW = "review"
    COMPLETED = "completed"
    FAILED = "failed"


class VoiceNote(Base):
    __tablename__ = "voice_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    audio_path: Mapped[str] = mapped_column(String(500), nullable=False)
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    processing_status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus), default=ProcessingStatus.UPLOADED, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user = relationship("User", back_populates="voice_notes")
    transcript = relationship(
        "Transcript", back_populates="voice_note", uselist=False, cascade="all, delete-orphan"
    )
    tasks = relationship("Task", back_populates="voice_note")
    orders = relationship("Order", back_populates="voice_note")
    payments = relationship("Payment", back_populates="voice_note")
