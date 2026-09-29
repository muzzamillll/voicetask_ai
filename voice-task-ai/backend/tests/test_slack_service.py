import hashlib
import hmac
import time

from app.config import settings
from app.services.slack_service import validate_request, SlackAuthError


def test_slack_signature_is_accepted(monkeypatch):
    secret = "test-secret"
    body = b'{"type":"event_callback"}'
    timestamp = str(int(time.time()))
    monkeypatch.setattr(settings, "SLACK_SIGNING_SECRET", secret)
    base = f"v0:{timestamp}:{body.decode()}"
    signature = "v0=" + hmac.new(
        secret.encode(), base.encode(), hashlib.sha256
    ).hexdigest()

    validate_request(body, timestamp, signature)


def test_slack_signature_rejects_bad_signature(monkeypatch):
    monkeypatch.setattr(settings, "SLACK_SIGNING_SECRET", "test-secret")
    timestamp = str(int(time.time()))

    try:
        validate_request(b"{}", timestamp, "v0=bad")
    except SlackAuthError:
        return
    assert False, "Expected SlackAuthError"
