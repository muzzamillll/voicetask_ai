"""Pydantic schemas for transcripts."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TranscriptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    voice_note_id: int
    raw_transcript: str
    cleaned_transcript: str | None
    language: str | None
    confidence: float | None
    translation_english: str | None = None
    translation_urdu: str | None = None
    created_at: datetime
