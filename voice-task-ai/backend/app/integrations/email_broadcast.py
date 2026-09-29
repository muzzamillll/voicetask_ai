"""
Group email broadcast.

Whenever a voice note is transcribed, sends an email — with the audio
file attached and the transcript in the body — to every address in
GROUP_MEMBER_EMAILS, so members don't have to listen to the original
voice note themselves to know what it says.

Uses Python's built-in smtplib/email modules — no new dependency needed.
Works with Gmail (requires a 2FA-enabled account + an "App Password",
not your normal password), Outlook, or any other SMTP provider.
"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path

from app.config import settings


def is_configured() -> bool:
    return bool(
        settings.GROUP_BROADCAST_ENABLED
        and settings.SMTP_USERNAME
        and settings.SMTP_PASSWORD
        and settings.GROUP_MEMBER_EMAILS
    )


def _recipient_list() -> list[str]:
    return [e.strip() for e in settings.GROUP_MEMBER_EMAILS.split(",") if e.strip()]


def send_transcript_broadcast(
    voice_note_id: int,
    audio_path: str,
    transcript_text: str,
    language: str,
    translation_english: str = "",
    translation_urdu: str = "",
) -> None:
    """
    Emails the voice note (as an attachment) plus its transcript — and,
    when available, English and Urdu translations — to the whole group
    member list. Never raises — a broadcast failure should never break
    the transcription pipeline that already succeeded.
    """
    if not is_configured():
        print("[group_broadcast] Skipped — not configured (set GROUP_BROADCAST_ENABLED, SMTP_*, GROUP_MEMBER_EMAILS).")
        return

    recipients = _recipient_list()
    if not recipients:
        print("[group_broadcast] Skipped — GROUP_MEMBER_EMAILS is empty.")
        return

    msg = MIMEMultipart()
    msg["From"] = settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = f"New voice note transcribed (#{voice_note_id}) - {language}"

    body_parts = [
        "A new voice note was sent and has been automatically transcribed.",
        "",
        f"Language: {language}",
        "",
        f"Transcript (original):\n{transcript_text}",
    ]
    if translation_english:
        body_parts += ["", f"English translation:\n{translation_english}"]
    if translation_urdu:
        body_parts += ["", f"Urdu translation:\n{translation_urdu}"]
    body_parts += [
        "",
        "The original audio is attached - you don't need to listen to it "
        "to know what was said, but it's there if you want to.",
    ]
    body = "\n".join(body_parts)
    msg.attach(MIMEText(body, "plain", "utf-8"))

    audio_file = Path(audio_path)
    if audio_file.exists():
        with open(audio_file, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f'attachment; filename="{audio_file.name}"')
        msg.attach(part)

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.sendmail(msg["From"], recipients, msg.as_string())
        print(f"[group_broadcast] Sent to {len(recipients)} recipient(s): {recipients}")
    except Exception as exc:
        print(f"[group_broadcast] Failed to send: {exc}")
