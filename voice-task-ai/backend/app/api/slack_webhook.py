"""
Slack Events API webhook.

Flow:

Slack audio file_shared
    -> verify signature
    -> acknowledge immediately
    -> fetch Slack file
    -> download audio
    -> create VoiceNote
    -> transcribe
    -> extract intent
    -> create Task/Order/Payment when confidence permits
    -> reply to Slack
"""

import asyncio
import mimetypes
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.database.database import SessionLocal
from app.models.voice_note import VoiceNote
from app.models.slack_event import SlackEvent

from app.services.voice_note_service import (
    ingest_local_file,
    InvalidAudioFile,
)

from app.services.user_service import (
    get_or_create_demo_user,
)

from app.services.transcription_service import (
    process_voice_note,
)

from app.services.slack_service import (
    validate_request,
    get_file_info,
    download_file,
    post_message,
    check_setup,
    SlackAuthError,
)

from app.ai.prompts import build_extraction_prompt
from app.ai.extraction_service import (
    extract_structured_data,
    ExtractionError,
)

from app.services.confidence_service import (
    determine_action,
)

from app.services.confirmation_service import (
    create_record_from_extraction,
)


router = APIRouter(
    prefix="/api/webhooks",
    tags=["slack"],
)


_AUDIO_MIME_PREFIX = "audio/"

# asyncio only keeps a weak reference to tasks, so a fire-and-forget task can
# be garbage-collected mid-run. Hold strong references until each finishes.
_background_tasks: set[asyncio.Task] = set()


_AUDIO_EXTENSIONS = {
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/mp4": ".m4a",
    "audio/m4a": ".m4a",
    "audio/x-m4a": ".m4a",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/ogg": ".ogg",
    "audio/webm": ".webm",
    "audio/opus": ".opus",
    "audio/aac": ".aac",
    # Slack audio clips can be labelled as video/* even though they are
    # audio-only; same containers, so map them to allowed audio extensions.
    "video/mp4": ".m4a",
    "video/webm": ".webm",
}


_AUDIO_FILE_EXTENSIONS = {
    ".mp3",
    ".mp4",
    ".m4a",
    ".wav",
    ".ogg",
    ".webm",
    ".opus",
    ".oga",
    ".aac",
}


def _is_audio_file(file_info: dict) -> bool:
    """Determine whether the Slack file is an audio file."""

    mimetype = (
        file_info.get("mimetype") or ""
    ).lower()

    filetype = (
        file_info.get("filetype") or ""
    ).lower()

    name = (
        file_info.get("name") or ""
    ).lower()

    extension = Path(name).suffix.lower()

    subtype = (
        file_info.get("subtype") or ""
    ).lower()

    result = (
        subtype == "slack_audio"
        or mimetype.startswith(_AUDIO_MIME_PREFIX)
        or filetype in {
            "mp3",
            "mp4",
            "m4a",
            "wav",
            "ogg",
            "webm",
            "opus",
            "oga",
            "aac",
        }
        or extension in _AUDIO_FILE_EXTENSIONS
    )

    print(
        "[slack_webhook] Audio detection:",
        {
            "mimetype": mimetype,
            "filetype": filetype,
            "name": name,
            "extension": extension,
            "is_audio": result,
        },
    )

    return result


def _extension_for(file_info: dict) -> str:
    """Determine a safe extension for the downloaded file."""

    mimetype = (
        file_info.get("mimetype") or ""
    ).lower()

    name = file_info.get("name") or ""

    name_extension = Path(name).suffix.lower()

    if mimetype in _AUDIO_EXTENSIONS:
        extension = _AUDIO_EXTENSIONS[mimetype]
    elif name_extension in _AUDIO_FILE_EXTENSIONS:
        extension = name_extension
    else:
        extension = mimetypes.guess_extension(mimetype) or ".m4a"

    # ".mp4" is the same AAC-in-MP4 container as ".m4a", but it is NOT in
    # settings.ALLOWED_AUDIO_EXTENSIONS, so ingest_local_file() would reject
    # it with "Unsupported file type '.mp4'".
    if extension == ".mp4":
        extension = ".m4a"

    if extension not in settings.ALLOWED_AUDIO_EXTENSIONS:
        extension = ".m4a"

    return extension


def _claim_event(event_id: str) -> bool:
    """
    Record a Slack event_id so redeliveries are processed only once.

    Slack redelivers an event whenever it doesn't get a fast 2xx (e.g. a slow
    first request over a tunnel). Returns True if this is the first time we
    see the event, False if it is a duplicate.

    If the table is missing (migration not applied) we log a hint and let the
    event through instead of breaking the whole integration.
    """
    db = SessionLocal()

    try:
        db.add(SlackEvent(event_id=event_id))
        db.commit()
        return True

    except IntegrityError:
        db.rollback()
        return False

    except Exception as exc:
        db.rollback()
        print(
            "[slack_webhook] Could not record event for de-duplication "
            "(have you run `alembic upgrade head`?):",
            repr(exc),
        )
        return True

    finally:
        db.close()


def _process_slack_audio(
    file_id: str,
    channel_id: str | None,
) -> None:
    """
    Process a Slack audio file outside the HTTP request.
    """

    print(
        "\n"
        "========================================\n"
        "[slack_webhook] START AUDIO PROCESSING\n"
        f"[slack_webhook] file_id={file_id}\n"
        f"[slack_webhook] channel_id={channel_id}\n"
        "========================================"
    )

    tmp_dir = (
        Path(settings.UPLOAD_DIR).parent
        / "_slack_tmp"
    )

    tmp_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    downloaded_path = None

    try:
        # -------------------------------------------------
        # 1. GET FILE INFORMATION
        # -------------------------------------------------

        print(
            f"[slack_webhook] Step 1: "
            f"Fetching file info for {file_id}"
        )

        file_info = get_file_info(file_id)

        print(
            "[slack_webhook] Slack file:",
            {
                "id": file_info.get("id"),
                "name": file_info.get("name"),
                "title": file_info.get("title"),
                "mimetype": file_info.get("mimetype"),
                "filetype": file_info.get("filetype"),
                "size": file_info.get("size"),
                "mode": file_info.get("mode"),
                "is_external": file_info.get(
                    "is_external"
                ),
            },
        )

        # -------------------------------------------------
        # 2. CHECK AUDIO
        # -------------------------------------------------

        print(
            "[slack_webhook] Step 2: "
            "Checking whether file is audio"
        )

        if not _is_audio_file(file_info):
            print(
                "[slack_webhook] File is NOT audio. "
                "Ignoring."
            )
            return

        extension = _extension_for(file_info)

        downloaded_path = (
            tmp_dir
            / f"{uuid.uuid4().hex}{extension}"
        )

        # -------------------------------------------------
        # 3. DOWNLOAD FILE
        # -------------------------------------------------

        print(
            "[slack_webhook] Step 3: "
            "Downloading Slack audio..."
        )

        audio_bytes = download_file(file_info)

        print(
            "[slack_webhook] Download complete:",
            {
                "bytes": len(audio_bytes),
                "path": str(downloaded_path),
                "extension": extension,
            },
        )

        if not audio_bytes:
            raise RuntimeError(
                "Downloaded Slack audio is empty."
            )

        downloaded_path.write_bytes(
            audio_bytes
        )

        # -------------------------------------------------
        # 4. DATABASE
        # -------------------------------------------------

        print(
            "[slack_webhook] Step 4: "
            "Ingesting local audio..."
        )

        db = SessionLocal()

        try:
            audio_path, size = ingest_local_file(
                downloaded_path
            )

            print(
                "[slack_webhook] Audio ingested:",
                {
                    "audio_path": audio_path,
                    "size": size,
                },
            )

            user = get_or_create_demo_user(db)

            voice_note = VoiceNote(
                user_id=user.id,
                audio_path=audio_path,
            )

            db.add(voice_note)
            db.commit()
            db.refresh(voice_note)

            print(
                "[slack_webhook] VoiceNote created:",
                voice_note.id,
            )

            # -------------------------------------------------
            # 5. TRANSCRIPTION
            # -------------------------------------------------

            print(
                "[slack_webhook] Step 5: "
                f"Transcribing VoiceNote #{voice_note.id}"
            )

            process_voice_note(
                voice_note.id,
                db,
            )

            db.refresh(voice_note)

            print(
                "[slack_webhook] Transcription finished."
            )

            if not voice_note.transcript:
                raise RuntimeError(
                    "Transcription completed but "
                    "no transcript was created."
                )

            text = (
                voice_note.transcript.cleaned_transcript
                or voice_note.transcript.raw_transcript
                or ""
            )

            language = (
                voice_note.transcript.language
                or "Unknown"
            )

            print(
                "[slack_webhook] Transcript:",
                repr(text),
            )

            print(
                "[slack_webhook] Language:",
                language,
            )

            # -------------------------------------------------
            # 6. EXTRACTION
            # -------------------------------------------------

            print(
                "[slack_webhook] Step 6: "
                "Extracting structured task data..."
            )

            prompt = build_extraction_prompt(
                cleaned_transcript=text,
                detected_language=language,
                reference=datetime.now(
                    timezone.utc
                ),
            )

            extraction = extract_structured_data(
                prompt
            )

            extraction.language = (
                language
                if language != "Unknown"
                else extraction.language
            )

            print(
                "[slack_webhook] Extraction complete."
            )

            # -------------------------------------------------
            # 7. CONFIDENCE / ACTION
            # -------------------------------------------------

            action = determine_action(
                extraction
            )

            print(
                "[slack_webhook] Determined action:",
                action,
            )

            if action == "auto_create":

                print(
                    "[slack_webhook] Creating record..."
                )

                record_type, record = (
                    create_record_from_extraction(
                        voice_note.id,
                        extraction,
                        db,
                    )
                )

                result_text = (
                    "Voice task processed successfully. "
                    f"Created {record_type} #{record.id}.\n\n"
                    f"Transcript: {text}"
                )

            else:

                result_text = (
                    "Voice message transcribed.\n\n"
                    f"It needs {str(action).replace('_', ' ')} "
                    "in VoiceTask AI before a record is created.\n\n"
                    f"Transcript: {text}"
                )

            # -------------------------------------------------
            # 8. SLACK RESPONSE
            # -------------------------------------------------

            if channel_id:

                print(
                    "[slack_webhook] Step 8: "
                    "Sending result back to Slack..."
                )

                try:
                    post_message(
                        channel_id,
                        result_text,
                    )

                except Exception as exc:
                    print(
                        "[slack_webhook] "
                        "Failed to post result:",
                        repr(exc),
                    )

            print(
                "========================================\n"
                "[slack_webhook] PROCESSING COMPLETE\n"
                "========================================"
            )

        finally:
            db.close()

    except InvalidAudioFile as exc:

        print(
            "[slack_webhook] Invalid audio:",
            repr(exc),
        )

        if channel_id:
            try:
                post_message(
                    channel_id,
                    f"Slack audio was received but "
                    f"could not be processed: {exc}",
                )
            except Exception as post_exc:
                print(
                    "[slack_webhook] "
                    "Failed to send error:",
                    repr(post_exc),
                )

    except ExtractionError as exc:

        print(
            "[slack_webhook] Extraction failed:",
            repr(exc),
        )

        if channel_id:
            try:
                post_message(
                    channel_id,
                    f"Audio was transcribed, but "
                    f"task extraction failed: {exc}",
                )
            except Exception as post_exc:
                print(
                    "[slack_webhook] "
                    "Failed to send error:",
                    repr(post_exc),
                )

    except Exception as exc:

        print(
            "\n"
            "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n"
            "[slack_webhook] PROCESSING FAILED\n"
            f"[slack_webhook] file_id={file_id}\n"
            f"[slack_webhook] error={type(exc).__name__}: {exc}\n"
            "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n"
        )

        if channel_id:
            try:
                post_message(
                    channel_id,
                    "Voice message was received, "
                    "but automatic processing failed.\n\n"
                    f"Error: {type(exc).__name__}: {exc}",
                )
            except Exception as post_exc:
                print(
                    "[slack_webhook] "
                    "Failed to send error message:",
                    repr(post_exc),
                )

    finally:

        if downloaded_path:
            try:
                downloaded_path.unlink(
                    missing_ok=True
                )
            except Exception as exc:
                print(
                    "[slack_webhook] "
                    "Could not delete temporary file:",
                    repr(exc),
                )


@router.post("/slack")
async def slack_webhook(
    request: Request,
):
    """
    Receive Slack Events API events.
    """

    if not settings.SLACK_ENABLED:

        raise HTTPException(
            status_code=(
                status.HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail=(
                "Slack integration is not enabled."
            ),
        )

    # -----------------------------------------------------
    # 1. READ REQUEST
    # -----------------------------------------------------

    raw_body = await request.body()

    # -----------------------------------------------------
    # 2. VERIFY SLACK SIGNATURE
    # -----------------------------------------------------

    try:

        validate_request(
            raw_body,
            request.headers.get(
                "X-Slack-Request-Timestamp",
                "",
            ),
            request.headers.get(
                "X-Slack-Signature",
                "",
            ),
        )

    except SlackAuthError as exc:

        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=str(exc),
        )

    # -----------------------------------------------------
    # 3. PARSE PAYLOAD
    # -----------------------------------------------------

    payload = await request.json()

    print(
        "[slack_webhook] Incoming Slack event:",
        payload.get("type"),
    )

    # -----------------------------------------------------
    # 4. URL VERIFICATION
    # -----------------------------------------------------

    if payload.get("type") == "url_verification":

        print(
            "[slack_webhook] URL verification request"
        )

        return {
            "challenge": payload.get(
                "challenge"
            )
        }

    # -----------------------------------------------------
    # 5. ONLY EVENT CALLBACKS
    # -----------------------------------------------------

    if payload.get("type") != "event_callback":

        return {
            "status": "ignored"
        }

    event_id = payload.get(
        "event_id"
    )

    event = payload.get(
        "event"
    ) or {}

    print(
        "[slack_webhook] Event:",
        {
            "event_id": event_id,
            "event_type": event.get("type"),
            "file_id": event.get("file_id"),
            "channel_id": event.get("channel_id"),
        },
    )

    if not event_id:

        return {
            "status": "accepted"
        }

    if not await asyncio.to_thread(_claim_event, event_id):

        print(
            "[slack_webhook] Duplicate event ignored:",
            event_id,
        )

        return {
            "status": "duplicate"
        }

    # -----------------------------------------------------
    # 6. HANDLE FILE_SHARED
    # -----------------------------------------------------

    if event.get("type") == "file_shared":

        file_id = (
            event.get("file_id")
            or (
                event.get("file") or {}
            ).get("id")
        )

        channel_id = event.get(
            "channel_id"
        )

        if not file_id:

            print(
                "[slack_webhook] "
                "file_shared event has no file_id."
            )

            return {
                "status": "accepted"
            }

        print(
            "[slack_webhook] "
            f"Scheduling processing for file={file_id}"
        )

        task = asyncio.create_task(
            asyncio.to_thread(
                _process_slack_audio,
                file_id,
                channel_id,
            )
        )

        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)

    else:

        print(
            "[slack_webhook] Ignoring event type:",
            event.get("type"),
        )

    # -----------------------------------------------------
    # 7. ACKNOWLEDGE SLACK IMMEDIATELY
    # -----------------------------------------------------

    return {
        "status": "accepted"
    }


@router.get("/slack/health")
def slack_health():
    """
    Diagnose the Slack setup. Returns only booleans / scope names — never
    secrets. Run: curl http://localhost:8000/api/webhooks/slack/health
    """

    token = settings.SLACK_BOT_TOKEN or ""
    secret = settings.SLACK_SIGNING_SECRET or ""

    events_table_ready = True
    db = SessionLocal()
    try:
        db.query(SlackEvent).limit(1).first()
    except Exception:
        events_table_ready = False
    finally:
        db.close()

    return {
        "slack_enabled": settings.SLACK_ENABLED,
        "bot_token_configured": bool(token),
        "bot_token_looks_valid": bool(
            re.fullmatch(r"xoxb-\d+-\d+-[A-Za-z0-9]+", token)
        ),
        "signing_secret_configured": bool(secret),
        "signing_secret_looks_valid": bool(
            re.fullmatch(r"[0-9a-f]{32}", secret)
        ),
        "slack_api": check_setup() if token else None,
        "slack_events_table_ready": events_table_ready,
    }
