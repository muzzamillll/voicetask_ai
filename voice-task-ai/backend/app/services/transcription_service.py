"""
Transcription orchestration for Phase 4.

Given a voice_note_id: loads the VoiceNote, runs Whisper on its audio file,
saves the result as a Transcript row, and updates the VoiceNote's
processing_status. Phase 5 will extend this with cleaning + refined
language detection; Phase 6 will chain LLM extraction after this step.
"""
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.voice_note import VoiceNote, ProcessingStatus
from app.models.transcript import Transcript
from app.ai.gemini_service import transcribe_audio, translate_text, GeminiError
from app.utils.transcript_cleaner import clean_transcript
from app.utils.language_detector import detect_language
from app.integrations import email_broadcast


def process_voice_note(voice_note_id: int, db: Session, language_hint: str | None = None) -> Transcript:
    voice_note = db.get(VoiceNote, voice_note_id)
    if not voice_note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voice note not found.")

    if voice_note.transcript is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This voice note has already been transcribed.",
        )

    voice_note.processing_status = ProcessingStatus.TRANSCRIBING
    db.commit()

    try:
        result = transcribe_audio(voice_note.audio_path, language_hint=language_hint)
    except Exception as exc:
        voice_note.processing_status = ProcessingStatus.FAILED
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transcription failed: {exc}",
        )

    language_code = result["language"]
    cleaned_text = clean_transcript(result["text"])
    language_display = detect_language(cleaned_text, language_code)

    transcript = Transcript(
        voice_note_id=voice_note.id,
        raw_transcript=result["text"],
        cleaned_transcript=cleaned_text,
        language=language_display,
    )
    db.add(transcript)

    # Next stop in the pipeline is LLM extraction (Phase 6) — for now,
    # land in REVIEW so the user can see the raw transcript.
    voice_note.processing_status = ProcessingStatus.REVIEW
    db.commit()
    db.refresh(transcript)

    # Also translate into English + Urdu up front so the broadcast email
    # is useful regardless of the reader's own language — and save it
    # onto the transcript so the dashboard's translate button doesn't
    # need to redo this work later.
    try:
        translations = translate_text(cleaned_text or result["text"])
        transcript.translation_english = translations["english"]
        transcript.translation_urdu = translations["urdu"]
        db.commit()
    except GeminiError as exc:
        print(f"[transcription_service] Translation failed (broadcast will skip it): {exc}")
        translations = {"english": "", "urdu": ""}

    email_broadcast.send_transcript_broadcast(
        voice_note_id=voice_note.id,
        audio_path=voice_note.audio_path,
        transcript_text=cleaned_text or result["text"],
        language=language_display,
        translation_english=translations["english"],
        translation_urdu=translations["urdu"],
    )

    return transcript
