"""
Tests for the contacts API and auto-save-on-confirm behavior.

Run with:
    pytest tests/test_contacts.py -v
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database.database import Base, get_db
from app.models.user import User
from app.models.voice_note import VoiceNote
from app.models.contact import Contact
from app.schemas.extraction import ExtractionResult, ContactInfo
from app.services.confirmation_service import create_record_from_extraction


@pytest.fixture()
def db_and_client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    db = TestingSession()
    yield db, TestClient(app)
    app.dependency_overrides.clear()
    db.close()


def test_create_and_list_contact(db_and_client):
    _db, client = db_and_client
    response = client.post("/api/contacts", json={"name": "Ali", "phone": "0300-1111111"})
    assert response.status_code == 201

    list_response = client.get("/api/contacts")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["name"] == "Ali"


def test_update_contact(db_and_client):
    _db, client = db_and_client
    created = client.post("/api/contacts", json={"name": "Sara"}).json()

    response = client.put(f"/api/contacts/{created['id']}", json={"phone": "0333-9999999"})
    assert response.status_code == 200
    assert response.json()["phone"] == "0333-9999999"
    assert response.json()["name"] == "Sara"  # unchanged


def test_delete_contact(db_and_client):
    _db, client = db_and_client
    created = client.post("/api/contacts", json={"name": "Bilal"}).json()

    delete_response = client.delete(f"/api/contacts/{created['id']}")
    assert delete_response.status_code == 204

    get_response = client.get(f"/api/contacts/{created['id']}")
    assert get_response.status_code == 404


def test_get_nonexistent_contact_404(db_and_client):
    _db, client = db_and_client
    response = client.get("/api/contacts/9999")
    assert response.status_code == 404


def test_confirming_extraction_auto_creates_contact(db_and_client):
    db, _client = db_and_client
    user = User(name="Demo", email="demo@test.local")
    db.add(user)
    db.commit()
    voice_note = VoiceNote(user_id=user.id, audio_path="data/audio/fake.mp3")
    db.add(voice_note)
    db.commit()

    extraction = ExtractionResult(
        intent="task",
        title="Call Waseem",
        contact=ContactInfo(name="Waseem", phone="0321-5555555"),
        confidence=0.9,
    )
    create_record_from_extraction(voice_note.id, extraction, db)

    contacts = db.query(Contact).all()
    assert len(contacts) == 1
    assert contacts[0].name == "Waseem"
    assert contacts[0].phone == "0321-5555555"


def test_confirming_extraction_fills_in_missing_phone_for_existing_contact(db_and_client):
    db, _client = db_and_client
    user = User(name="Demo", email="demo@test.local")
    db.add(user)
    db.commit()
    voice_note = VoiceNote(user_id=user.id, audio_path="data/audio/fake.mp3")
    db.add(voice_note)
    db.commit()

    # Pre-existing contact with no phone on file
    db.add(Contact(user_id=user.id, name="Ahmed"))
    db.commit()

    extraction = ExtractionResult(
        intent="task",
        title="Call Ahmed",
        contact=ContactInfo(name="ahmed", phone="0300-7777777"),  # case-insensitive match
        confidence=0.9,
    )
    create_record_from_extraction(voice_note.id, extraction, db)

    contacts = db.query(Contact).all()
    assert len(contacts) == 1  # no duplicate created
    assert contacts[0].phone == "0300-7777777"


def test_confirming_extraction_with_no_contact_name_creates_nothing(db_and_client):
    db, _client = db_and_client
    user = User(name="Demo", email="demo@test.local")
    db.add(user)
    db.commit()
    voice_note = VoiceNote(user_id=user.id, audio_path="data/audio/fake.mp3")
    db.add(voice_note)
    db.commit()

    extraction = ExtractionResult(intent="note", title="Buy groceries", confidence=0.8)
    create_record_from_extraction(voice_note.id, extraction, db)

    assert db.query(Contact).count() == 0
