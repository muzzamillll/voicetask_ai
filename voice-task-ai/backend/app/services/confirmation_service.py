"""
Phase 8 — converts a confirmed (possibly user-edited) ExtractionResult
into a real Task, Order, or Payment row.

This is the ONLY place extraction JSON turns into persisted business
data — nothing gets saved as a Task/Order/Payment without going through
here, whether that's an automatic high-confidence save (Phase 7's
"auto_create") or a human manually confirming/editing first.
"""
from datetime import datetime, date

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.voice_note import VoiceNote, ProcessingStatus
from app.models.task import Task, TaskPriority
from app.models.order import Order
from app.models.payment import Payment
from app.models.contact import Contact
from app.schemas.extraction import ExtractionResult, Intent
from app.integrations import google_sheets, google_calendar, jitsi

# Meeting-like intents that get a calendar event created automatically
# when confirmed with a specific date+time.
_MEETING_INTENTS = {Intent.MEETING, Intent.APPOINTMENT}

# Which model an intent becomes. Anything not explicitly an order/payment
# becomes a Task — tasks, reminders, meetings, appointments, follow-ups,
# notes, and even "unknown" all fit the generic title/description/deadline
# shape a Task already has, and the spec's Task table is intentionally
# general-purpose for exactly this reason.
_ORDER_INTENTS = {Intent.ORDER}
_PAYMENT_INTENTS = {Intent.PAYMENT}


def _parse_iso_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _parse_iso_date(value: str) -> date | None:
    parsed = _parse_iso_datetime(value)
    return parsed.date() if parsed else None


def _upsert_contact(user_id: int, name: str, phone: str, db: Session) -> None:
    """
    Auto-saves a contact whenever an extraction names one — matches by
    name (case-insensitive) for this user. If the contact already exists
    and a phone number wasn't on file yet, fills it in; never overwrites
    an existing phone number with an empty one.
    """
    if not name:
        return

    existing = (
        db.query(Contact)
        .filter(Contact.user_id == user_id, Contact.name.ilike(name))
        .first()
    )
    if existing:
        if phone and not existing.phone:
            existing.phone = phone
            db.commit()
        return

    contact = Contact(user_id=user_id, name=name, phone=phone or None)
    db.add(contact)
    db.commit()


def create_record_from_extraction(
    voice_note_id: int, extraction: ExtractionResult, db: Session
) -> tuple[str, Task | Order | Payment]:
    """
    Returns (record_type, record) where record_type is "task", "order",
    or "payment" — the caller uses this to pick the right response schema.
    """
    voice_note = db.get(VoiceNote, voice_note_id)
    if not voice_note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voice note not found.")

    user_id = voice_note.user_id

    if extraction.intent in _ORDER_INTENTS:
        record = Order(
            user_id=user_id,
            voice_note_id=voice_note_id,
            customer_name=extraction.contact.name or None,
            description=extraction.description or extraction.task or None,
            quantity=extraction.quantity,
            amount=extraction.amount.value,
            currency=extraction.amount.currency or "PKR",
            delivery_date=_parse_iso_date(extraction.deadline.datetime),
        )
        record_type = "order"

    elif extraction.intent in _PAYMENT_INTENTS:
        record = Payment(
            user_id=user_id,
            voice_note_id=voice_note_id,
            contact_name=extraction.contact.name or None,
            amount=extraction.amount.value,
            currency=extraction.amount.currency or "PKR",
            due_date=_parse_iso_date(extraction.deadline.datetime),
        )
        record_type = "payment"

    else:
        title = extraction.title or extraction.task or "Untitled task"
        meeting_link = (
            jitsi.generate_meeting_link(title) if extraction.intent in _MEETING_INTENTS else None
        )
        record = Task(
            user_id=user_id,
            voice_note_id=voice_note_id,
            title=title,
            description=extraction.description or None,
            contact_name=extraction.contact.name or None,
            contact_phone=extraction.contact.phone or None,
            deadline=_parse_iso_datetime(extraction.deadline.datetime),
            priority=TaskPriority(extraction.priority.value),
            confidence=extraction.confidence,
            intent=extraction.intent.value,
            meeting_link=meeting_link,
        )
        record_type = "task"

    db.add(record)
    voice_note.processing_status = ProcessingStatus.COMPLETED
    db.commit()
    db.refresh(record)

    _upsert_contact(user_id, extraction.contact.name, extraction.contact.phone, db)

    if record_type == "order":
        google_sheets.append_order_row(record)

    if record_type == "task" and extraction.intent in _MEETING_INTENTS:
        google_calendar.create_meeting_event(record)

    return record_type, record
