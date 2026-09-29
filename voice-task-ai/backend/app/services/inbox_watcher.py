"""
Inbox watcher — automatic voice note ingestion.

Watches a folder for new audio files and automatically ingests +
transcribes them, with zero manual upload step. Point INBOX_DIR at
WhatsApp Desktop's own auto-saved voice notes folder to turn incoming
WhatsApp voice notes into fully automatic ingestion — no Meta Business
API, no webhook, no external accounts needed.

Runs as a background asyncio task alongside the FastAPI app (started in
main.py's lifespan, only when INBOX_POLL_ENABLED=true). Each detected
file is processed in a worker thread (via asyncio.to_thread) so a slow
transcription call never blocks the app from handling normal HTTP
requests at the same time.
"""
import asyncio
from pathlib import Path

from watchfiles import awatch, Change

from app.config import settings
from app.database.database import SessionLocal
from app.models.voice_note import VoiceNote
from app.services.voice_note_service import ingest_local_file, InvalidAudioFile
from app.services.user_service import get_or_create_demo_user
from app.services.transcription_service import process_voice_note

# Give a newly-appearing file a moment to finish being written/copied
# before we try to read it — otherwise a large file mid-copy could be
# ingested as truncated/corrupt. WhatsApp Desktop writes voice notes
# quickly (they're small), so this is a generous safety margin.
_SETTLE_SECONDS = 2.0


def _process_file(path: Path) -> None:
    """Runs in a worker thread — safe to make blocking calls here."""
    db = SessionLocal()
    try:
        try:
            audio_path, _size = ingest_local_file(path)
        except InvalidAudioFile as exc:
            print(f"[inbox_watcher] Skipping {path.name}: {exc}")
            return

        user = get_or_create_demo_user(db)
        voice_note = VoiceNote(user_id=user.id, audio_path=audio_path)
        db.add(voice_note)
        db.commit()
        db.refresh(voice_note)
        print(f"[inbox_watcher] Ingested {path.name} as voice note #{voice_note.id}")

        try:
            process_voice_note(voice_note.id, db)
            print(f"[inbox_watcher] Transcribed voice note #{voice_note.id}")
        except Exception as exc:
            # Ingestion already succeeded and is visible in the dashboard
            # even if auto-transcription fails — the user can retry it
            # manually from there, so we don't let this crash the watcher.
            print(f"[inbox_watcher] Auto-transcription failed for #{voice_note.id}: {exc}")
    finally:
        db.close()


async def watch_inbox() -> None:
    inbox_dir = Path(settings.INBOX_DIR)
    inbox_dir.mkdir(parents=True, exist_ok=True)
    print(f"[inbox_watcher] Watching {inbox_dir.resolve()} for new voice notes...")

    async for changes in awatch(inbox_dir):
        for change_type, changed_path in changes:
            if change_type not in (Change.added, Change.modified):
                continue
            path = Path(changed_path)
            if not path.is_file():
                continue
            if path.suffix.lower() not in settings.ALLOWED_AUDIO_EXTENSIONS:
                continue

            await asyncio.sleep(_SETTLE_SECONDS)
            await asyncio.to_thread(_process_file, path)
