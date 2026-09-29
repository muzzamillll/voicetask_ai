"""
LINE Messaging API integration.

Unlike Telegram (polling) and like Teams, LINE pushes messages to us via
a webhook — LINE's servers call our /api/webhooks/line endpoint whenever
someone sends the bot a message. Two things this module handles:

1. Verifying incoming requests are genuinely from LINE, by checking the
   `X-Line-Signature` header — an HMAC-SHA256 of the raw request body,
   signed with the channel secret.
2. Downloading a voice message's actual audio content, which needs the
   channel access token as a bearer credential.

No SDK needed — LINE's webhook and content APIs are both plain REST/HMAC,
so this only needs `httpx` and Python's built-in `hmac`/`hashlib`.
"""
import base64
import hashlib
import hmac

import httpx

from app.config import settings

_CONTENT_URL_TEMPLATE = "https://api-data.line.me/v2/bot/message/{message_id}/content"


class LineAuthError(Exception):
    """Raised when an incoming request's signature doesn't match — not genuinely from LINE."""


def validate_signature(raw_body: bytes, signature_header: str) -> None:
    """
    Recomputes the expected HMAC-SHA256 signature over the raw request
    body using the channel secret, and compares it (constant-time) to
    what LINE sent in the X-Line-Signature header.
    """
    if not signature_header:
        raise LineAuthError("Missing X-Line-Signature header.")

    expected = base64.b64encode(
        hmac.new(settings.LINE_CHANNEL_SECRET.encode("utf-8"), raw_body, hashlib.sha256).digest()
    ).decode("utf-8")

    if not hmac.compare_digest(expected, signature_header):
        raise LineAuthError("Signature does not match — request may not be genuinely from LINE.")


def download_audio_content(message_id: str) -> bytes:
    """Downloads a voice message's audio bytes using the channel access token."""
    url = _CONTENT_URL_TEMPLATE.format(message_id=message_id)
    response = httpx.get(
        url,
        headers={"Authorization": f"Bearer {settings.LINE_CHANNEL_ACCESS_TOKEN}"},
        timeout=30.0,
    )
    response.raise_for_status()
    return response.content
