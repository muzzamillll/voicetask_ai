"""
Google Calendar integration.

Same approach as google_sheets.py: a simple Apps Script Web App as a
webhook, instead of the full Calendar API — no OAuth consent flow,
no service account, no new heavy Python dependencies.

If GOOGLE_CALENDAR_WEBHOOK_URL isn't configured, this integration is
silently skipped — it's optional, not required for the app to function.
"""
import httpx

from app.config import settings


def is_configured() -> bool:
    return bool(settings.GOOGLE_CALENDAR_WEBHOOK_URL)


def create_meeting_event(task) -> None:
    """
    Sends one Task (with intent meeting/appointment and a concrete
    deadline) to the configured Google Calendar webhook to create a
    real calendar event.

    Never raises — a Calendar failure should never break saving the
    task to the real database, which already succeeded by the time
    this runs.
    """
    if not is_configured():
        print("[google_calendar] Skipped — GOOGLE_CALENDAR_WEBHOOK_URL is not set.")
        return

    if not task.deadline:
        print(f"[google_calendar] Skipped task #{task.id} — no specific date/time to schedule.")
        return

    description_parts = []
    if task.description:
        description_parts.append(task.description)
    if task.contact_name:
        description_parts.append(f"Contact: {task.contact_name}")
    if task.contact_phone:
        description_parts.append(f"Phone: {task.contact_phone}")
    if task.meeting_link:
        description_parts.append(f"Join video call: {task.meeting_link}")

    payload = {
        "title": task.title,
        "description": "\n".join(description_parts),
        "start_datetime": task.deadline.isoformat(),
        "duration_minutes": settings.MEETING_DEFAULT_DURATION_MINUTES,
    }

    try:
        response = httpx.post(settings.GOOGLE_CALENDAR_WEBHOOK_URL, json=payload, timeout=10.0)
        print(f"[google_calendar] POST to webhook -> status {response.status_code}")
        print(f"[google_calendar] Response body: {response.text[:300]}")
    except httpx.HTTPError as exc:
        print(f"[google_calendar] Request failed: {exc}")
