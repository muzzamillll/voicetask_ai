"""
Phase 7+8 tests: confidence-based routing and creating Task/Order/Payment
records from a confirmed extraction.

Run with:
    pytest tests/test_confirmation.py -v
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.database.database import Base
from app.models.user import User
from app.models.voice_note import VoiceNote
from app.schemas.extraction import ExtractionResult, ContactInfo, DeadlineInfo, AmountInfo
from app.services.confidence_service import determine_action
from app.services.confirmation_service import create_record_from_extraction
from app.models.task import Task
from app.models.order import Order
from app.models.payment import Payment


# --- confidence_service ---

def _extraction(confidence=0.9, needs_clarification=False, **overrides):
    return ExtractionResult(confidence=confidence, needs_clarification=needs_clarification, **overrides)


def test_high_confidence_auto_creates():
    assert determine_action(_extraction(confidence=0.9)) == "auto_create"


def test_boundary_085_is_auto_create():
    assert determine_action(_extraction(confidence=0.85)) == "auto_create"


def test_mid_confidence_needs_review():
    assert determine_action(_extraction(confidence=0.75)) == "confirm_review"


def test_boundary_060_is_confirm_review():
    assert determine_action(_extraction(confidence=0.60)) == "confirm_review"


def test_low_confidence_needs_manual_review():
    assert determine_action(_extraction(confidence=0.3)) == "manual_review"


def test_needs_clarification_forces_manual_review_even_at_high_confidence():
    assert determine_action(_extraction(confidence=0.99, needs_clarification=True)) == "manual_review"


# --- confirmation_service ---

@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    user = User(name="Demo", email="demo@test.local")
    session.add(user)
    session.commit()

    voice_note = VoiceNote(user_id=user.id, audio_path="data/audio/fake.mp3")
    session.add(voice_note)
    session.commit()

    yield session, voice_note.id
    session.close()


def test_task_intent_creates_task(db_session):
    session, voice_note_id = db_session
    extraction = ExtractionResult(
        intent="task",
        title="Call Ali",
        contact=ContactInfo(name="Ali", phone="0300-1111111"),
        deadline=DeadlineInfo(date="2026-09-11", time="17:00", datetime="2026-09-11T17:00:00", is_specific=True),
        priority="high",
        confidence=0.9,
    )
    record_type, record = create_record_from_extraction(voice_note_id, extraction, session)
    assert record_type == "task"
    assert isinstance(record, Task)
    assert record.meeting_link is None
    assert record.title == "Call Ali"
    assert record.contact_name == "Ali"
    assert record.priority.value == "high"
    assert record.intent == "task"


def test_order_intent_creates_order(db_session):
    session, voice_note_id = db_session
    extraction = ExtractionResult(
        intent="order",
        contact=ContactInfo(name="Waseem"),
        amount=AmountInfo(value=200000, currency="PKR"),
        quantity=2,
        confidence=0.9,
    )
    record_type, record = create_record_from_extraction(voice_note_id, extraction, session)
    assert record_type == "order"
    assert isinstance(record, Order)
    assert record.customer_name == "Waseem"
    assert record.amount == 200000
    assert record.quantity == 2


def test_payment_intent_creates_payment(db_session):
    session, voice_note_id = db_session
    extraction = ExtractionResult(
        intent="payment",
        contact=ContactInfo(name="Faizan"),
        amount=AmountInfo(value=25000, currency="PKR"),
        confidence=0.9,
    )
    record_type, record = create_record_from_extraction(voice_note_id, extraction, session)
    assert record_type == "payment"
    assert isinstance(record, Payment)
    assert record.contact_name == "Faizan"
    assert record.amount == 25000


def test_unknown_intent_defaults_to_task(db_session):
    session, voice_note_id = db_session
    extraction = ExtractionResult(intent="unknown", title="Something unclear", confidence=0.4)
    record_type, record = create_record_from_extraction(voice_note_id, extraction, session)
    assert record_type == "task"
    assert record.title == "Something unclear"


def test_meeting_intent_triggers_calendar_event(db_session, monkeypatch):
    session, voice_note_id = db_session
    from app.services import confirmation_service

    calls = []
    monkeypatch.setattr(
        confirmation_service.google_calendar, "create_meeting_event", lambda task: calls.append(task)
    )

    extraction = ExtractionResult(
        intent="meeting",
        title="Meet Ali",
        deadline=DeadlineInfo(date="2026-09-15", time="10:00", datetime="2026-09-15T10:00:00", is_specific=True),
        confidence=0.9,
    )
    record_type, record = create_record_from_extraction(voice_note_id, extraction, session)
    assert record_type == "task"
    assert len(calls) == 1
    assert calls[0].id == record.id
    assert record.meeting_link is not None
    assert record.meeting_link.startswith("https://meet.jit.si/")


def test_task_intent_does_not_trigger_calendar_event(db_session, monkeypatch):
    session, voice_note_id = db_session
    from app.services import confirmation_service

    calls = []
    monkeypatch.setattr(
        confirmation_service.google_calendar, "create_meeting_event", lambda task: calls.append(task)
    )

    extraction = ExtractionResult(intent="task", title="Call Ali", confidence=0.9)
    create_record_from_extraction(voice_note_id, extraction, session)
    assert len(calls) == 0


def test_missing_voice_note_raises_404(db_session):
    session, _voice_note_id = db_session
    extraction = ExtractionResult(intent="task", title="X", confidence=0.9)
    with pytest.raises(Exception):
        create_record_from_extraction(9999, extraction, session)


def test_empty_title_falls_back_to_untitled(db_session):
    session, voice_note_id = db_session
    extraction = ExtractionResult(intent="task", confidence=0.5)  # no title, no task
    _record_type, record = create_record_from_extraction(voice_note_id, extraction, session)
    assert record.title == "Untitled task"
