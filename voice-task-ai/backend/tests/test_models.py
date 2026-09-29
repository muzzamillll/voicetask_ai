"""
Phase 2 sanity test: creates all tables in an in-memory SQLite DB
and exercises basic CRUD across the model relationships.

This does NOT touch your real Postgres database — it's a fast check
that the model definitions and relationships are structurally correct
before you run real Alembic migrations against Postgres.

Run with:
    pytest tests/test_models.py -v
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.database import Base
from app.models.user import User
from app.models.voice_note import VoiceNote, ProcessingStatus
from app.models.transcript import Transcript
from app.models.task import Task, TaskStatus, TaskPriority
from app.models.order import Order
from app.models.payment import Payment
from app.models.contact import Contact


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_create_user():
    db = make_session()
    user = User(name="Ali Raza", email="ali@example.com")
    db.add(user)
    db.commit()
    assert user.id is not None
    assert user.created_at is not None


def test_voice_note_and_transcript_relationship():
    db = make_session()
    user = User(name="Sara Khan", email="sara@example.com")
    db.add(user)
    db.commit()

    note = VoiceNote(user_id=user.id, audio_path="data/audio/note1.m4a", duration=12.5)
    db.add(note)
    db.commit()
    assert note.processing_status == ProcessingStatus.UPLOADED

    transcript = Transcript(
        voice_note_id=note.id,
        raw_transcript="Ali ko kal 5 baje call karna hai",
        language="Roman Urdu",
        confidence=0.91,
    )
    db.add(transcript)
    db.commit()

    assert note.transcript.raw_transcript.startswith("Ali ko kal")


def test_task_lifecycle():
    db = make_session()
    user = User(name="Bilal", email="bilal@example.com")
    db.add(user)
    db.commit()

    task = Task(
        user_id=user.id,
        title="Call Ali",
        contact_name="Ali",
        priority=TaskPriority.HIGH,
        confidence=0.94,
    )
    db.add(task)
    db.commit()
    assert task.status == TaskStatus.PENDING

    task.status = TaskStatus.COMPLETED
    db.commit()
    assert task.status == TaskStatus.COMPLETED


def test_order_and_payment_creation():
    db = make_session()
    user = User(name="Nida", email="nida@example.com")
    db.add(user)
    db.commit()

    order = Order(user_id=user.id, customer_name="Waseem", amount=25000, quantity=2)
    payment = Payment(user_id=user.id, contact_name="Waseem", amount=25000)
    db.add_all([order, payment])
    db.commit()

    assert order.currency == "PKR"
    assert payment.status.value == "pending"


def test_contact_creation():
    db = make_session()
    user = User(name="Hina", email="hina@example.com")
    db.add(user)
    db.commit()

    contact = Contact(user_id=user.id, name="Ali", phone="0300-1234567")
    db.add(contact)
    db.commit()

    assert user.contacts[0].name == "Ali"
