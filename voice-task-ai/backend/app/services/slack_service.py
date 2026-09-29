"""
Slack Events API integration.

Handles:
- Slack request signature verification
- Fetching file information
- Downloading private Slack files
- Posting messages back to Slack
"""

import hashlib
import hmac
import time

import httpx

from app.config import settings


_SLACK_API = "https://slack.com/api"

# Scopes the bot needs: files:read (files.info + download) and chat:write
# (reply in the channel). Slack also needs the `file_shared` bot event
# subscribed and the bot invited to the channel.
REQUIRED_SCOPES = {"files:read", "chat:write"}

# Slack fires `file_shared` before a freshly uploaded clip is always ready,
# so files.info can briefly answer file_not_found / no download URL yet.
_FILE_INFO_ATTEMPTS = 5
_FILE_INFO_RETRY_DELAY_SECONDS = 2.0


class SlackAuthError(Exception):
    """Raised when a Slack request cannot be authenticated."""


def _headers() -> dict:
    """Common authenticated Slack headers."""
    if not settings.SLACK_BOT_TOKEN:
        raise RuntimeError("SLACK_BOT_TOKEN is not configured.")

    return {
        "Authorization": f"Bearer {settings.SLACK_BOT_TOKEN}",
        "User-Agent": "VoiceTaskAI/1.0",
    }


def validate_request(
    raw_body: bytes,
    timestamp: str,
    signature: str,
) -> None:
    """Validate Slack's v0 HMAC signature and reject replayed requests."""

    if not settings.SLACK_SIGNING_SECRET:
        raise SlackAuthError(
            "Slack signing secret is not configured."
        )

    if not timestamp or not signature:
        raise SlackAuthError(
            "Missing Slack signature headers."
        )

    try:
        request_ts = int(timestamp)
    except ValueError as exc:
        raise SlackAuthError(
            "Invalid Slack timestamp."
        ) from exc

    if abs(time.time() - request_ts) > settings.SLACK_MAX_EVENT_AGE_SECONDS:
        raise SlackAuthError(
            "Slack request timestamp is too old."
        )

    basestring = (
        f"v0:{timestamp}:{raw_body.decode('utf-8')}"
    )

    expected = "v0=" + hmac.new(
        settings.SLACK_SIGNING_SECRET.encode("utf-8"),
        basestring.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        raise SlackAuthError(
            "Slack signature does not match."
        )


def _fetch_file_info(file_id: str) -> dict:
    """Single files.info call (no retry)."""

    if not file_id:
        raise RuntimeError("Slack file_id is empty.")

    print(
        f"[slack_service] Fetching file information "
        f"for file_id={file_id}"
    )

    try:
        with httpx.Client(
            timeout=20.0,
            follow_redirects=True,
        ) as client:

            response = client.get(
                f"{_SLACK_API}/files.info",
                params={
                    "file": file_id,
                },
                headers=_headers(),
            )

        print(
            "[slack_service] files.info response:",
            response.status_code,
        )

        response.raise_for_status()

        data = response.json()

        if not data.get("ok"):
            error = data.get(
                "error",
                "unknown_error",
            )

            raise RuntimeError(
                f"Slack files.info failed: {error}"
            )

        file_info = data.get("file")

        if not file_info:
            raise RuntimeError(
                "Slack files.info returned no file object."
            )

        print(
            "[slack_service] File information:",
            {
                "id": file_info.get("id"),
                "name": file_info.get("name"),
                "title": file_info.get("title"),
                "mimetype": file_info.get("mimetype"),
                "filetype": file_info.get("filetype"),
                "size": file_info.get("size"),
                "mode": file_info.get("mode"),
                "is_external": file_info.get("is_external"),
                "has_url_private": bool(
                    file_info.get("url_private")
                ),
                "has_url_private_download": bool(
                    file_info.get("url_private_download")
                ),
            },
        )

        return file_info

    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            "Slack files.info HTTP error: "
            f"{exc.response.status_code} "
            f"{exc.response.text[:500]}"
        ) from exc

    except httpx.RequestError as exc:
        raise RuntimeError(
            "Slack files.info connection error: "
            f"{type(exc).__name__}: {exc}"
        ) from exc


def get_file_info(file_id: str) -> dict:
    """
    Fetch complete information about a Slack file, retrying briefly while
    Slack is still processing a just-uploaded clip.

    Auth/scope errors (invalid_auth, missing_scope, ...) are NOT retried —
    they will never fix themselves.
    """
    last_exc: Exception | None = None

    for attempt in range(1, _FILE_INFO_ATTEMPTS + 1):
        try:
            file_info = _fetch_file_info(file_id)

            if file_info.get("url_private_download") or file_info.get("url_private"):
                return file_info

            last_exc = RuntimeError(
                "Slack file has no download URL yet (still processing)."
            )

        except RuntimeError as exc:
            if "file_not_found" not in str(exc):
                raise
            last_exc = exc

        if attempt < _FILE_INFO_ATTEMPTS:
            print(
                f"[slack_service] File not ready "
                f"(attempt {attempt}/{_FILE_INFO_ATTEMPTS}); "
                f"retrying in {_FILE_INFO_RETRY_DELAY_SECONDS}s..."
            )
            time.sleep(_FILE_INFO_RETRY_DELAY_SECONDS)

    raise RuntimeError(
        f"Slack file {file_id} never became available: {last_exc}. "
        "If this keeps happening, make sure the bot is invited to the "
        "channel and the app has the files:read scope."
    )


def download_file(file_info: dict) -> bytes:
    """
    Download a private Slack file using the bot token.

    Slack private files require Authorization: Bearer <bot token>.
    Redirects are explicitly followed.
    """

    if not file_info:
        raise RuntimeError(
            "Slack file information is empty."
        )

    url = (
        file_info.get("url_private_download")
        or file_info.get("url_private")
    )

    if not url:
        raise RuntimeError(
            "Slack file has no url_private_download "
            "or url_private."
        )

    print(
        "[slack_service] Downloading Slack file:",
        {
            "name": file_info.get("name"),
            "mimetype": file_info.get("mimetype"),
            "filetype": file_info.get("filetype"),
            "size": file_info.get("size"),
            "url": url,
        },
    )

    try:
        with httpx.Client(
            timeout=httpx.Timeout(
                connect=20.0,
                read=60.0,
                write=60.0,
                pool=20.0,
            ),
            follow_redirects=True,
        ) as client:

            response = client.get(
                url,
                headers=_headers(),
            )

        print(
            "[slack_service] Download response:",
            {
                "status": response.status_code,
                "content_type": response.headers.get(
                    "content-type"
                ),
                "content_length": len(
                    response.content
                ),
            },
        )

        response.raise_for_status()

        if not response.content:
            raise RuntimeError(
                "Slack returned an empty file."
            )

        # When the token is wrong or lacks files:read, Slack answers 200 with
        # an HTML sign-in page instead of the file. Without this check that
        # HTML gets saved as ".m4a" and fails later with a confusing error.
        content_type = (
            response.headers.get("content-type") or ""
        ).lower()

        if content_type.startswith("text/html"):
            raise RuntimeError(
                "Slack returned an HTML page instead of the audio file. "
                "Check that SLACK_BOT_TOKEN is the real xoxb- Bot User "
                "OAuth token, the app has the files:read scope, and the "
                "app was reinstalled after adding scopes."
            )

        return response.content

    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            "Slack file download HTTP error: "
            f"{exc.response.status_code} "
            f"{exc.response.text[:500]}"
        ) from exc

    except httpx.RequestError as exc:
        raise RuntimeError(
            "Slack file download connection error: "
            f"{type(exc).__name__}: {exc}"
        ) from exc


def post_message(
    channel_id: str,
    text: str,
) -> None:
    """Send a message back to the Slack channel."""

    if not settings.SLACK_BOT_TOKEN:
        print(
            "[slack_service] Cannot post message: "
            "SLACK_BOT_TOKEN is not configured."
        )
        return

    if not channel_id:
        print(
            "[slack_service] Cannot post message: "
            "channel_id is empty."
        )
        return

    if not text:
        text = "Voice message processed."

    print(
        f"[slack_service] Posting response to "
        f"channel={channel_id}"
    )

    try:
        with httpx.Client(
            timeout=20.0,
            follow_redirects=True,
        ) as client:

            response = client.post(
                f"{_SLACK_API}/chat.postMessage",
                headers=_headers(),
                json={
                    "channel": channel_id,
                    "text": text,
                },
            )

        print(
            "[slack_service] chat.postMessage response:",
            response.status_code,
        )

        response.raise_for_status()

        data = response.json()

        if not data.get("ok"):
            raise RuntimeError(
                "Slack chat.postMessage failed: "
                f"{data.get('error', 'unknown_error')}"
            )

    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            "Slack chat.postMessage HTTP error: "
            f"{exc.response.status_code} "
            f"{exc.response.text[:500]}"
        ) from exc

    except httpx.RequestError as exc:
        raise RuntimeError(
            "Slack chat.postMessage connection error: "
            f"{type(exc).__name__}: {exc}"
        ) from exc


def check_setup() -> dict:
    """
    Ask Slack whether the configured bot token works and which scopes it has.
    Used by the /api/webhooks/slack/health diagnostic. Never returns secrets.
    """
    if not settings.SLACK_BOT_TOKEN:
        return {"token_ok": False, "error": "SLACK_BOT_TOKEN is not set"}

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(
                f"{_SLACK_API}/auth.test",
                headers=_headers(),
            )

        data = response.json()

        if not data.get("ok"):
            return {
                "token_ok": False,
                "error": data.get("error", "unknown_error"),
            }

        granted = {
            scope.strip()
            for scope in (
                response.headers.get("x-oauth-scopes") or ""
            ).split(",")
            if scope.strip()
        }

        return {
            "token_ok": True,
            "granted_scopes": sorted(granted),
            "missing_scopes": sorted(REQUIRED_SCOPES - granted),
        }

    except Exception as exc:
        return {
            "token_ok": False,
            "error": f"{type(exc).__name__}: {exc}",
        }
