"""
Jitsi Meet integration.

Jitsi's public server (meet.jit.si) needs no API key or account —
any unique room name in the URL creates a real, working video meeting
room on demand. This is the entire integration: generate a unique,
hard-to-guess room name and build the URL.
"""
import re
import uuid


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-")
    return slug or "meeting"


def generate_meeting_link(title: str) -> str:
    """
    Builds a Jitsi Meet URL with a unique room name derived from the
    meeting title, so links are both readable and collision-free.
    """
    room_name = f"VoiceTaskAI-{_slugify(title)}-{uuid.uuid4().hex[:8]}"
    return f"https://meet.jit.si/{room_name}"
