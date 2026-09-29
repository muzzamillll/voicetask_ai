"""
Telegram bot automation — automatic voice note ingestion.

Long-polls Telegram's getUpdates API for incoming voice messages, downloads
each one, ingests it as a VoiceNote, and transcribes it automatically —
no manual upload step, no public webhook/ngrok needed (long polling works
fine from a plain local machine).

Runs as a background asyncio task alongside the FastAPI app (started in
main.py's lifespan, only when TELEGRAM_POLL_ENABLED=true). Each voice
message is downloaded and processed in a worker thread (via
asyncio.to_thread) so a slow transcription call never blocks the app
from handling normal HTTP requests at the same time.
"""
import asyncio
import uuid
from pathlib import Path

import httpx

from app.config import settings
from app.database.database import SessionLocal
from app.models.voice_note import VoiceNote
from app.services.voice_note_service import ingest_local_file, InvalidAudioFile
from app.services.user_service import get_or_create_demo_user
from app.services.transcription_service import process_voice_note

_API_BASE = "https://api.telegram.org"
_POLL_TIMEOUT_SECONDS = 30  # long-polling timeout Telegram holds the connection open for


def _download_voice_file(file_id: str, tmp_dir: Path) -> Path:
    """Downloads a Telegram voice message to a temp file, preserving its extension."""
    with httpx.Client(timeout=30.0) as client:
        file_info = client.get(
            f"{_API_BASE}/bot{settings.TELEGRAM_BOT_TOKEN}/getFile",
            params={"file_id": file_id},
        ).json()
        telegram_path = file_info["result"]["file_path"]  # e.g. "voice/file_0.oga"
        ext = Path(telegram_path).suffix or ".oga"

        dest = tmp_dir / f"{uuid.uuid4().hex}{ext}"
        download_url = f"{_API_BASE}/file/bot{settings.TELEGRAM_BOT_TOKEN}/{telegram_path}"
        response = client.get(download_url)
        dest.write_bytes(response.content)
        return dest


def _process_voice_message(file_id: str) -> None:
    """Runs in a worker thread — safe to make blocking calls here."""
    tmp_dir = Path(settings.UPLOAD_DIR).parent / "_telegram_tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    downloaded_path = _download_voice_file(file_id, tmp_dir)
    db = SessionLocal()
    try:
        try:
            audio_path, _size = ingest_local_file(downloaded_path)
        except InvalidAudioFile as exc:
            print(f"[telegram_watcher] Skipping voice message: {exc}")
            return
        finally:
            downloaded_path.unlink(missing_ok=True)  # clean up the temp download

        user = get_or_create_demo_user(db)
        voice_note = VoiceNote(user_id=user.id, audio_path=audio_path)
        db.add(voice_note)
        db.commit()
        db.refresh(voice_note)
        print(f"[telegram_watcher] Ingested Telegram voice message as voice note #{voice_note.id}")

        try:
            process_voice_note(voice_note.id, db)
            print(f"[telegram_watcher] Transcribed voice note #{voice_note.id}")
        except Exception as exc:
            print(f"[telegram_watcher] Auto-transcription failed for #{voice_note.id}: {exc}")
    finally:
        db.close()


async def watch_telegram() -> None:
    if not settings.TELEGRAM_BOT_TOKEN:
        print("[telegram_watcher] TELEGRAM_BOT_TOKEN not set — watcher not started.")
        return

    print("[telegram_watcher] Polling Telegram for incoming voice messages...")
    offset = None

    async with httpx.AsyncClient(timeout=_POLL_TIMEOUT_SECONDS + 10) as client:
        while True:
            try:
                params = {"timeout": _POLL_TIMEOUT_SECONDS}
                if offset is not None:
                    params["offset"] = offset

                response = await client.get(
                    f"{_API_BASE}/bot{settings.TELEGRAM_BOT_TOKEN}/getUpdates",
                    params=params,
                )
                data = response.json()

                if not data.get("ok"):
                    print(f"[telegram_watcher] Telegram API error: {data}")
                    await asyncio.sleep(5)
                    continue

                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    message = update.get("message", {})
                    voice = message.get("voice") or message.get("audio")
                    if voice:
                        await asyncio.to_thread(_process_voice_message, voice["file_id"])

            except asyncio.CancelledError:
                raise
            except Exception as exc:
                import traceback
                print(f"[telegram_watcher] Polling error: {type(exc).__name__}: {exc!r}")
                print(traceback.format_exc())
                await asyncio.sleep(5)
