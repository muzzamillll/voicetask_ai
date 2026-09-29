"""
Microsoft Teams webhook — receives Bot Framework "Activity" payloads
whenever someone messages the bot, pulls out any voice message
attachment, and runs it through the same automatic pipeline as a
manual upload: ingest -> transcribe.

NOTE: the exact shape of a voice-message Activity from Teams can vary
a little by client (mobile vs desktop) and Teams version. If a real
test message doesn't produce a voice note, the fix is almost always in
_extract_audio_attachments() below — log the raw payload (there's a
commented-out line for this) and adjust the content-type/extension
matching to what your tenant actually sends.
"""
import asyncio
import mimetypes
import uuid
from pathlib import Path

from fastapi import APIRouter, Request, HTTPException, status

from app.config import settings
from app.database.database import SessionLocal
from app.models.voice_note import VoiceNote
from app.services.voice_note_service import ingest_local_file, InvalidAudioFile
from app.services.user_service import get_or_create_demo_user
from app.services.transcription_service import process_voice_note
from app.services.teams_service import validate_incoming_request, download_attachment, TeamsAuthError

router = APIRouter(prefix="/api/webhooks", tags=["teams"])

_AUDIO_EXTENSION_BY_CONTENT_TYPE = {
    "audio/mp4": ".m4a",
    "audio/mpeg": ".mp3",
    "audio/wav": ".wav",
    "audio/ogg": ".ogg",
    "audio/webm": ".webm",
}


def _extract_audio_attachments(activity: dict) -> list[dict]:
    """Returns [{"content_url": ..., "extension": ...}, ...] for any audio attachments on this activity."""
    results = []
    for attachment in activity.get("attachments", []):
        content_type = attachment.get("contentType", "")
        content_url = attachment.get("contentUrl")
        if not content_url or not content_type.startswith("audio/"):
            continue
        ext = _AUDIO_EXTENSION_BY_CONTENT_TYPE.get(
            content_type, mimetypes.guess_extension(content_type) or ".m4a"
        )
        results.append({"content_url": content_url, "extension": ext})
    return results


def _process_teams_voice_message(content_url: str, extension: str) -> None:
    """Runs in a worker thread — safe to make blocking calls here."""
    tmp_dir = Path(settings.UPLOAD_DIR).parent / "_teams_tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    downloaded_path = tmp_dir / f"{uuid.uuid4().hex}{extension}"

    try:
        audio_bytes = download_attachment(content_url)
        downloaded_path.write_bytes(audio_bytes)
    except Exception as exc:
        print(f"[teams_webhook] Failed to download attachment: {exc}")
        return

    db = SessionLocal()
    try:
        try:
            audio_path, _size = ingest_local_file(downloaded_path)
        except InvalidAudioFile as exc:
            print(f"[teams_webhook] Skipping attachment: {exc}")
            return
        finally:
            downloaded_path.unlink(missing_ok=True)

        user = get_or_create_demo_user(db)
        voice_note = VoiceNote(user_id=user.id, audio_path=audio_path)
        db.add(voice_note)
        db.commit()
        db.refresh(voice_note)
        print(f"[teams_webhook] Ingested Teams voice message as voice note #{voice_note.id}")

        try:
            process_voice_note(voice_note.id, db)
            print(f"[teams_webhook] Transcribed voice note #{voice_note.id}")
        except Exception as exc:
            print(f"[teams_webhook] Auto-transcription failed for #{voice_note.id}: {exc}")
    finally:
        db.close()


@router.post("/teams")
async def teams_webhook(request: Request):
    if not settings.MICROSOFT_APP_ID:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Teams bot not configured.")

    try:
        validate_incoming_request(request.headers.get("Authorization", ""))
    except TeamsAuthError as exc:
        print(f"[teams_webhook] Auth validation failed: {exc}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))

    activity = await request.json()
    # Uncomment while debugging a real Teams message to see its exact shape:
    # print(f"[teams_webhook] Raw activity: {activity}")

    if activity.get("type") == "message":
        for attachment in _extract_audio_attachments(activity):
            asyncio.create_task(
                asyncio.to_thread(
                    _process_teams_voice_message, attachment["content_url"], attachment["extension"]
                )
            )

    # Bot Framework just needs a fast 200 acknowledgment — the actual
    # work happens in the background task(s) kicked off above.
    return {"status": "accepted"}
