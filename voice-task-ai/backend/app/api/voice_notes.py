"""
Voice notes API.

Phase 3: upload, list, get-by-id, delete.
Phase 4: /process/{id} transcribes via Gemini.
Phase 6: /extract/{id} runs LLM structured extraction.
Phase 7+8: /confirm/{id} creates the actual Task/Order/Payment record,
following the confidence-based routing recommendation from /extract.
"""
from datetime import datetime, timezone
from typing import Union

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.voice_note import VoiceNote
from app.schemas.voice_note import VoiceNoteResponse
from app.schemas.transcript import TranscriptResponse
from app.schemas.extraction import ExtractionResult, ExtractionReviewResponse
from app.schemas.task import TaskResponse
from app.schemas.order import OrderResponse
from app.schemas.payment import PaymentResponse
from app.services.voice_note_service import save_audio_file
from app.services.user_service import get_or_create_demo_user
from app.services.transcription_service import process_voice_note
from app.services.confidence_service import determine_action
from app.services.confirmation_service import create_record_from_extraction
from app.ai.prompts import build_extraction_prompt
from app.ai.extraction_service import extract_structured_data, ExtractionError
from app.ai.gemini_service import translate_text, GeminiError

router = APIRouter(prefix="/api/voice-notes", tags=["voice-notes"])


@router.post("/upload", response_model=VoiceNoteResponse, status_code=status.HTTP_201_CREATED)
def upload_voice_note(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Accepts an audio file (mp3/wav/m4a/webm), stores it, and creates a VoiceNote record."""
    user = get_or_create_demo_user(db)

    audio_path, _size_bytes = save_audio_file(file)

    voice_note = VoiceNote(user_id=user.id, audio_path=audio_path)
    db.add(voice_note)
    db.commit()
    db.refresh(voice_note)

    return voice_note


@router.post("/process/{voice_note_id}", response_model=TranscriptResponse)
def process_voice_note_endpoint(
    voice_note_id: int,
    language: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Transcribes a previously uploaded voice note via Gemini.

    Optional query param `language` (e.g. ?language=Urdu, ?language=Sindhi,
    ?language=English) tells the model what to expect instead of relying
    purely on audio-based detection.
    """
    return process_voice_note(voice_note_id, db, language_hint=language)


@router.post("/extract/{voice_note_id}", response_model=ExtractionReviewResponse)
def extract_voice_note_endpoint(voice_note_id: int, db: Session = Depends(get_db)):
    """
    Runs LLM structured extraction on a voice note's transcript, and
    returns Phase 7's recommendation for what to do with it:
    auto_create, confirm_review, or manual_review.
    """
    voice_note = db.get(VoiceNote, voice_note_id)
    if not voice_note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voice note not found.")
    if not voice_note.transcript:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This voice note hasn't been transcribed yet. Call /process/{id} first.",
        )

    text = voice_note.transcript.cleaned_transcript or voice_note.transcript.raw_transcript
    prompt = build_extraction_prompt(
        cleaned_transcript=text,
        detected_language=voice_note.transcript.language or "Unknown",
        reference=datetime.now(timezone.utc),
    )

    try:
        result = extract_structured_data(prompt)
    except ExtractionError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM extraction failed: {exc}",
        )

    # Our own script/marker-based language detection (Phase 5) is more
    # reliable than the LLM's self-reported guess in the JSON schema —
    # use it instead of trusting the LLM's language field.
    result.language = voice_note.transcript.language or result.language

    return ExtractionReviewResponse(
        extraction=result,
        recommended_action=determine_action(result),
    )


@router.post("/translate/{voice_note_id}", response_model=TranscriptResponse)
def translate_voice_note_endpoint(voice_note_id: int, db: Session = Depends(get_db)):
    """
    Translates a voice note's transcript into both English and Urdu,
    regardless of the original language, and saves the result onto the
    Transcript row so it doesn't need to be re-translated on every view.
    """
    voice_note = db.get(VoiceNote, voice_note_id)
    if not voice_note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voice note not found.")
    if not voice_note.transcript:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This voice note hasn't been transcribed yet. Call /process/{id} first.",
        )

    text = voice_note.transcript.cleaned_transcript or voice_note.transcript.raw_transcript

    try:
        translations = translate_text(text)
    except GeminiError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Translation failed: {exc}",
        )

    voice_note.transcript.translation_english = translations["english"]
    voice_note.transcript.translation_urdu = translations["urdu"]
    db.commit()
    db.refresh(voice_note.transcript)

    return voice_note.transcript


@router.post(
    "/confirm/{voice_note_id}",
    response_model=Union[TaskResponse, OrderResponse, PaymentResponse],
)
def confirm_voice_note_endpoint(
    voice_note_id: int, extraction: ExtractionResult, db: Session = Depends(get_db)
):
    """
    Takes a (possibly user-edited) extraction result and creates the real
    Task/Order/Payment record from it. Used both for auto-create (high
    confidence, called immediately after /extract with no edits) and for
    human-reviewed confirmations (after the user corrects fields in the UI).
    """
    _record_type, record = create_record_from_extraction(voice_note_id, extraction, db)
    return record


@router.get("", response_model=list[VoiceNoteResponse])
def list_voice_notes(db: Session = Depends(get_db)):
    return db.query(VoiceNote).order_by(VoiceNote.created_at.desc()).all()


@router.get("/{voice_note_id}", response_model=VoiceNoteResponse)
def get_voice_note(voice_note_id: int, db: Session = Depends(get_db)):
    voice_note = db.get(VoiceNote, voice_note_id)
    if not voice_note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voice note not found.")
    return voice_note


@router.delete("/{voice_note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_voice_note(voice_note_id: int, db: Session = Depends(get_db)):
    voice_note = db.get(VoiceNote, voice_note_id)
    if not voice_note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voice note not found.")
    db.delete(voice_note)
    db.commit()
