"""
Discord bot integration.

Unlike Slack/LINE/WhatsApp, this needs no public webhook or ngrok: the bot
connects OUT to Discord over a websocket (same shape as the Telegram
poller), so it works from any machine with outbound internet access.

Discord voice messages (recorded with the mic button in the mobile/desktop
app) arrive as a message attachment whose content type is "audio/ogg" and
which Discord flags as a voice message. A user can also just attach a
regular audio file - we accept both.
"""

import asyncio
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import uuid

import discord

from app.config import settings
from app.database.database import SessionLocal
from app.models.slack_event import SlackEvent
from app.models.voice_note import VoiceNote, ProcessingStatus
from app.models.transcript import Transcript

from app.services.voice_note_service import ingest_local_file, InvalidAudioFile
from app.services.user_service import get_or_create_demo_user
from app.services.transcription_service import process_voice_note

from app.ai.prompts import build_extraction_prompt
from app.ai.extraction_service import extract_structured_data, ExtractionError
from app.services.confidence_service import determine_action
from app.services.confirmation_service import create_record_from_extraction

from sqlalchemy.exc import IntegrityError


# Discord's own audio container for voice messages is Ogg/Opus, which
# ingest_local_file() already allows. A few other common audio types are
# mapped too, in case someone attaches a regular audio file instead.
_EXTENSION_BY_CONTENT_TYPE = {
    "audio/ogg": ".ogg",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/mp4": ".m4a",
    "audio/x-m4a": ".m4a",
    "audio/aac": ".aac",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/webm": ".webm",
}


def _claim_message(message_id: int) -> bool:
    """De-dupe using the same table Slack/WhatsApp use, prefixed "discord:"."""
    db = SessionLocal()
    try:
        db.add(SlackEvent(event_id=f"discord:{message_id}"))
        db.commit()
        return True
    except IntegrityError:
        db.rollback()
        return False
    except Exception as exc:
        db.rollback()
        print(
            "[discord_bot] Could not record message for de-duplication "
            "(have you run `alembic upgrade head`?):",
            repr(exc),
        )
        return True
    finally:
        db.close()


def _extension_for(attachment: "discord.Attachment") -> Optional[str]:
    content_type = (attachment.content_type or "").split(";")[0].strip().lower()

    if content_type in _EXTENSION_BY_CONTENT_TYPE:
        ext = _EXTENSION_BY_CONTENT_TYPE[content_type]
        if ext in settings.ALLOWED_AUDIO_EXTENSIONS:
            return ext

    name_ext = Path(attachment.filename or "").suffix.lower()
    if name_ext in settings.ALLOWED_AUDIO_EXTENSIONS:
        return name_ext

    return None


def _is_audio_attachment(attachment: "discord.Attachment") -> bool:
    is_voice = bool(getattr(attachment, "is_voice_message", lambda: False)())
    content_type = (attachment.content_type or "").lower()
    return is_voice or content_type.startswith("audio/") or _extension_for(attachment) is not None


def _process_discord_audio(audio_bytes: bytes, extension: str, reply_to) -> None:
    """
    Runs in a worker thread. `reply_to` is a plain callable(text) -> None
    (see on_message below) so this function has no asyncio/discord.py
    dependency and can be exercised without the library at all.
    """

    print(f"[discord_bot] START AUDIO PROCESSING bytes={len(audio_bytes)} ext={extension}")

    tmp_dir = Path(settings.UPLOAD_DIR).parent / "_discord_tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    downloaded_path = tmp_dir / f"{uuid.uuid4().hex}{extension}"

    try:
        downloaded_path.write_bytes(audio_bytes)

        db = SessionLocal()
        try:
            audio_path, _size = ingest_local_file(downloaded_path)

            user = get_or_create_demo_user(db)
            voice_note = VoiceNote(user_id=user.id, audio_path=audio_path)
            db.add(voice_note)
            db.commit()
            db.refresh(voice_note)
            print(f"[discord_bot] VoiceNote created: {voice_note.id}")

            process_voice_note(voice_note.id, db)
            db.refresh(voice_note)

            if not voice_note.transcript:
                raise RuntimeError("Transcription completed but no transcript was created.")

            text = (
                voice_note.transcript.cleaned_transcript
                or voice_note.transcript.raw_transcript
                or ""
            )
            language = voice_note.transcript.language or "Unknown"
            print("[discord_bot] Transcript:", repr(text), "| Language:", language)

            prompt = build_extraction_prompt(
                cleaned_transcript=text,
                detected_language=language,
                reference=datetime.now(timezone.utc),
            )
            extraction = extract_structured_data(prompt)
            extraction.language = language if language != "Unknown" else extraction.language

            action = determine_action(extraction)
            print("[discord_bot] Determined action:", action)

            if action == "auto_create":
                record_type, record = create_record_from_extraction(
                    voice_note.id, extraction, db
                )
                reply_to(
                    f"Voice task processed. Created {record_type} #{record.id}.\n\n"
                    f"Transcript: {text}"
                )
            else:
                reply_to(
                    "Voice message transcribed. "
                    f"It needs {str(action).replace('_', ' ')} in VoiceTask AI "
                    f"before a record is created.\n\nTranscript: {text}"
                )

            print("[discord_bot] PROCESSING COMPLETE")

        finally:
            db.close()

    except InvalidAudioFile as exc:
        print("[discord_bot] Invalid audio:", repr(exc))
        reply_to(f"Your voice message was received but could not be processed: {exc}")

    except ExtractionError as exc:
        print("[discord_bot] Extraction failed:", repr(exc))
        reply_to(f"Your audio was transcribed, but task extraction failed: {exc}")

    except Exception as exc:
        print(
            "\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n"
            "[discord_bot] PROCESSING FAILED\n"
            f"[discord_bot] error={type(exc).__name__}: {exc}\n"
            "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n"
        )
        reply_to(
            "Your voice message was received, but automatic processing failed. "
            f"Error: {type(exc).__name__}"
        )

    finally:
        try:
            downloaded_path.unlink(missing_ok=True)
        except Exception as exc:
            print("[discord_bot] Could not delete temp file:", repr(exc))


def _process_discord_text(text: str, reply_to) -> None:
    """
    Same pipeline as _process_discord_audio, but for a typed message: skips
    ingest + transcription entirely and treats `text` as the transcript.
    Runs in a worker thread, same as the audio path.
    """

    print(f"[discord_bot] START TEXT PROCESSING text={text!r}")

    db = SessionLocal()
    try:
        user = get_or_create_demo_user(db)

        # A VoiceNote row is required (Task/Order/Payment link to one), so a
        # sentinel value is used instead of a real audio file. A matching
        # Transcript row is also created so this looks normal on the
        # dashboard, and process_voice_note() is never called for it.
        voice_note = VoiceNote(
            user_id=user.id,
            audio_path="discord-text-message",
            processing_status=ProcessingStatus.REVIEW,
        )
        db.add(voice_note)
        db.commit()
        db.refresh(voice_note)
        print(f"[discord_bot] VoiceNote created (text): {voice_note.id}")

        transcript = Transcript(
            voice_note_id=voice_note.id,
            raw_transcript=text,
            cleaned_transcript=text,
            language="Text (Discord)",
        )
        db.add(transcript)
        db.commit()

        prompt = build_extraction_prompt(
            cleaned_transcript=text,
            detected_language="Text (Discord)",
            reference=datetime.now(timezone.utc),
        )
        extraction = extract_structured_data(prompt)

        action = determine_action(extraction)
        print("[discord_bot] Determined action:", action)

        if action == "auto_create":
            record_type, record = create_record_from_extraction(
                voice_note.id, extraction, db
            )
            reply_to(f"Got it. Created {record_type} #{record.id}.")
        else:
            reply_to(
                "Received. "
                f"It needs {str(action).replace('_', ' ')} in VoiceTask AI "
                "before a record is created."
            )

        print("[discord_bot] PROCESSING COMPLETE (text)")

    except ExtractionError as exc:
        print("[discord_bot] Extraction failed (text):", repr(exc))
        reply_to(f"Sorry, I couldn't understand that as a task: {exc}")

    except Exception as exc:
        print(
            "\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n"
            "[discord_bot] TEXT PROCESSING FAILED\n"
            f"[discord_bot] error={type(exc).__name__}: {exc}\n"
            "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n"
        )
        reply_to(f"Something went wrong processing that. Error: {type(exc).__name__}")

    finally:
        db.close()


def build_client() -> "discord.Client":
    intents = discord.Intents.default()
    intents.message_content = True  # required to see attachments' context / any caption

    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f"[discord_bot] Logged in as {client.user} (id={client.user.id})")

    @client.event
    async def on_message(message: "discord.Message"):
        if message.author == client.user or message.author.bot:
            return

        audio_attachments = [a for a in message.attachments if _is_audio_attachment(a)]

        for attachment in audio_attachments:
            if not _is_audio_attachment(attachment):
                continue

            if not await asyncio.to_thread(_claim_message, message.id):
                print("[discord_bot] Duplicate message ignored:", message.id)
                continue

            extension = _extension_for(attachment) or ".ogg"
            print(
                f"[discord_bot] Audio attachment from {message.author}: "
                f"{attachment.filename} ({attachment.content_type}) -> {extension}"
            )

            try:
                audio_bytes = await attachment.read()
            except Exception as exc:
                print("[discord_bot] Failed to download attachment:", repr(exc))
                await message.channel.send(
                    "Sorry, I couldn't download that voice message. Please try again."
                )
                continue

            loop = asyncio.get_running_loop()

            def reply_to(text: str, _channel=message.channel, _loop=loop):
                asyncio.run_coroutine_threadsafe(_channel.send(text[:2000]), _loop)

            asyncio.create_task(
                asyncio.to_thread(_process_discord_audio, audio_bytes, extension, reply_to)
            )

        # Plain text: only handled when the bot is @mentioned or the message
        # is a DM, so ordinary channel chatter isn't turned into tasks. To
        # process EVERY text message instead, drop the `is_dm or mentioned`
        # condition below (not recommended in a shared/busy channel).
        if audio_attachments:
            return

        is_dm = isinstance(message.channel, discord.DMChannel)
        mentioned = client.user in message.mentions

        if not (is_dm or mentioned):
            return

        text = re.sub(rf"<@!?{client.user.id}>", "", message.content).strip()

        if not text:
            return

        if not await asyncio.to_thread(_claim_message, message.id):
            print("[discord_bot] Duplicate text message ignored:", message.id)
            return

        print(f"[discord_bot] Text message from {message.author}: {text!r}")

        loop = asyncio.get_running_loop()

        def reply_to(reply_text: str, _channel=message.channel, _loop=loop):
            asyncio.run_coroutine_threadsafe(_channel.send(reply_text[:2000]), _loop)

        asyncio.create_task(asyncio.to_thread(_process_discord_text, text, reply_to))

    return client


async def run_discord_bot() -> None:
    """Entry point scheduled from app.main's lifespan."""

    if not settings.DISCORD_BOT_TOKEN:
        print("[discord_bot] DISCORD_BOT_TOKEN not set; Discord bot not started.")
        return

    client = build_client()

    try:
        await client.start(settings.DISCORD_BOT_TOKEN)
    except discord.LoginFailure:
        print(
            "[discord_bot] Login failed: DISCORD_BOT_TOKEN is invalid. "
            "Copy a fresh token from the Discord Developer Portal -> Bot -> Reset Token."
        )
    except Exception as exc:
        print("[discord_bot] Stopped:", repr(exc))
