"""
LINE webhook — receives LINE's "events" payload whenever someone
messages the bot, pulls out any audio message, and runs it through the
same automatic pipeline as a manual upload: ingest -> transcribe.
"""
import asyncio
import uuid
from pathlib import Path

from fastapi import APIRouter, Request, HTTPException, status

from app.config import settings
from app.database.database import SessionLocal
from app.models.voice_note import VoiceNote
from app.services.voice_note_service import ingest_local_file, InvalidAudioFile
from app.services.user_service import get_or_create_demo_user
from app.services.transcription_service import process_voice_note
from app.services.line_service import validate_signature, download_audio_content, LineAuthError

router = APIRouter(prefix="/api/webhooks", tags=["line"])


def _process_line_audio_message(message_id: str) -> None:
    """Runs in a worker thread - safe to make blocking calls here."""
    tmp_dir = Path(settings.UPLOAD_DIR).parent / "_line_tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    # LINE voice messages are m4a (AAC-in-MP4).
    downloaded_path = tmp_dir / f"{uuid.uuid4().hex}.m4a"

    try:
        audio_bytes = download_audio_content(message_id)
        downloaded_path.write_bytes(audio_bytes)
    except Exception as exc:
        print(f"[line_webhook] Failed to download audio content: {exc}")
        return

    db = SessionLocal()
    try:
        try:
            audio_path, _size = ingest_local_file(downloaded_path)
        except InvalidAudioFile as exc:
            print(f"[line_webhook] Skipping message: {exc}")
            return
        finally:
            downloaded_path.unlink(missing_ok=True)

        user = get_or_create_demo_user(db)
        voice_note = VoiceNote(user_id=user.id, audio_path=audio_path)
        db.add(voice_note)
        db.commit()
        db.refresh(voice_note)
        print(f"[line_webhook] Ingested LINE voice message as voice note #{voice_note.id}")

        try:
            process_voice_note(voice_note.id, db)
            print(f"[line_webhook] Transcribed voice note #{voice_note.id}")
        except Exception as exc:
            print(f"[line_webhook] Auto-transcription failed for #{voice_note.id}: {exc}")
    finally:
        db.close()


@router.post("/line")
async def line_webhook(request: Request):
    if not settings.LINE_CHANNEL_SECRET:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="LINE bot not configured.")

    raw_body = await request.body()

    try:
        validate_signature(raw_body, request.headers.get("X-Line-Signature", ""))
    except LineAuthError as exc:
        print(f"[line_webhook] Signature validation failed: {exc}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))

    payload = await request.json()

    for event in payload.get("events", []):
        message = event.get("message", {})
        if event.get("type") == "message" and message.get("type") == "audio":
            asyncio.create_task(asyncio.to_thread(_process_line_audio_message, message["id"]))

    # LINE just needs a fast 200 acknowledgment - the actual work happens
    # in the background task(s) kicked off above.
    return {"status": "accepted"}
