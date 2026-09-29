"""
Microsoft Teams bot integration.

Unlike Telegram (which we poll), Teams/Bot Framework pushes messages to
US via a webhook — Azure calls our /api/webhooks/teams endpoint whenever
someone sends the bot a message. Two things this module handles:

1. Verifying incoming requests are genuinely from Microsoft's Bot
   Framework (not a forged request) by validating the JWT bearer token
   Azure attaches to every call, using Bot Framework's published signing
   keys.
2. Getting our OWN bearer token (via OAuth2 client credentials) to
   download voice message attachments, since Teams attachment URLs
   require authentication.

Uses PyJWT directly rather than the full botframework-connector SDK, to
avoid a much heavier dependency for what is, at its core, two REST calls
and a signature check.
"""
import time

import httpx
import jwt
from jwt import PyJWKClient

from app.config import settings

_TOKEN_URL = "https://login.microsoftonline.com/botframework.com/oauth2/v2.0/token"
_OPENID_CONFIG_URL = "https://login.botframework.com/v1/.well-known/openidconfiguration"
_EXPECTED_ISSUER = "https://api.botframework.com"

_cached_token: str | None = None
_cached_token_expiry: float = 0.0
_jwks_client: PyJWKClient | None = None


class TeamsAuthError(Exception):
    """Raised when an incoming request can't be verified as genuinely from Bot Framework."""


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        config = httpx.get(_OPENID_CONFIG_URL, timeout=10.0).json()
        _jwks_client = PyJWKClient(config["jwks_uri"])
    return _jwks_client


def validate_incoming_request(authorization_header: str) -> None:
    """
    Verifies the Authorization header on an incoming webhook call is a
    validly signed token from Microsoft's Bot Framework, addressed to
    OUR bot specifically. Raises TeamsAuthError if anything's wrong.
    """
    if not authorization_header or not authorization_header.startswith("Bearer "):
        raise TeamsAuthError("Missing or malformed Authorization header.")

    token = authorization_header.removeprefix("Bearer ").strip()

    try:
        signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
        jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.MICROSOFT_APP_ID,
            issuer=_EXPECTED_ISSUER,
        )
    except jwt.PyJWTError as exc:
        raise TeamsAuthError(f"Token validation failed: {exc}") from exc


def get_bot_access_token() -> str:
    """
    Returns a cached bearer token for calling back into Bot Framework
    APIs (e.g. downloading attachments), refreshing it via OAuth2 client
    credentials when expired.
    """
    global _cached_token, _cached_token_expiry

    if _cached_token and time.time() < _cached_token_expiry - 60:
        return _cached_token

    response = httpx.post(
        _TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": settings.MICROSOFT_APP_ID,
            "client_secret": settings.MICROSOFT_APP_PASSWORD,
            "scope": "https://api.botframework.com/.default",
        },
        timeout=10.0,
    )
    response.raise_for_status()
    data = response.json()
    _cached_token = data["access_token"]
    _cached_token_expiry = time.time() + data["expires_in"]
    return _cached_token


def download_attachment(content_url: str) -> bytes:
    """Downloads a Teams message attachment (e.g. a voice message) using our bot's own token."""
    token = get_bot_access_token()
    response = httpx.get(content_url, headers={"Authorization": f"Bearer {token}"}, timeout=30.0)
    response.raise_for_status()
    return response.content
