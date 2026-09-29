"""Transcript model — raw and cleaned text produced from a voice note."""
from datetime import datetime, timezone

from sqlalchemy import Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base


class Transcript(Base):
    __tablename__ = "transcripts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    voice_note_id: Mapped[int] = mapped_column(
        ForeignKey("voice_notes.id"), unique=True, nullable=False
    )
    raw_transcript: Mapped[str] = mapped_column(Text, nullable=False)
    cleaned_transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str | None] = mapped_column(String(30), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    translation_english: Mapped[str | None] = mapped_column(Text, nullable=True)
    translation_urdu: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    voice_note = relationship("VoiceNote", back_populates="transcript")
