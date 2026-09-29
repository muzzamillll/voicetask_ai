"""Pydantic schemas for the voice_notes API."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.voice_note import ProcessingStatus
from app.schemas.transcript import TranscriptResponse


class VoiceNoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    audio_path: str
    duration: float | None
    processing_status: ProcessingStatus
    created_at: datetime
    transcript: TranscriptResponse | None = None
