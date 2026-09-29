"""
Phase 3 API tests for /api/voice-notes.

Uses FastAPI's dependency override to swap the real Postgres session for
a temporary in-memory SQLite one, and a temp directory for uploads —
so this test never touches your real database or disk uploads folder.

Run with:
    pytest tests/test_voice_notes_api.py -v
"""
import io
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database.database import Base, get_db
from app.config import settings


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))

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
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_upload_valid_audio(client):
    fake_audio = io.BytesIO(b"fake-mp3-bytes")
    response = client.post(
        "/api/voice-notes/upload",
        files={"file": ("note.mp3", fake_audio, "audio/mpeg")},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["processing_status"] == "uploaded"
    assert body["audio_path"].endswith(".mp3")


def test_upload_rejects_bad_extension(client):
    fake_file = io.BytesIO(b"not audio")
    response = client.post(
        "/api/voice-notes/upload",
        files={"file": ("note.txt", fake_file, "text/plain")},
    )
    assert response.status_code == 400


def test_upload_rejects_empty_file(client):
    response = client.post(
        "/api/voice-notes/upload",
        files={"file": ("note.wav", io.BytesIO(b""), "audio/wav")},
    )
    assert response.status_code == 400


def test_list_and_get_voice_note(client):
    fake_audio = io.BytesIO(b"fake-wav-bytes")
    upload_response = client.post(
        "/api/voice-notes/upload",
        files={"file": ("note.wav", fake_audio, "audio/wav")},
    )
    note_id = upload_response.json()["id"]

    list_response = client.get("/api/voice-notes")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    get_response = client.get(f"/api/voice-notes/{note_id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == note_id


def test_get_nonexistent_voice_note_returns_404(client):
    response = client.get("/api/voice-notes/9999")
    assert response.status_code == 404


# --- ingest_local_file (used by the inbox watcher) ---

def test_ingest_local_file_valid_audio(tmp_path, monkeypatch):
    from app.services.voice_note_service import ingest_local_file
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "audio"))

    source = tmp_path / "incoming.ogg"
    source.write_bytes(b"fake-ogg-bytes")

    dest_path, size = ingest_local_file(source)
    assert dest_path.endswith(".ogg")
    assert size == len(b"fake-ogg-bytes")
    assert Path(dest_path).exists()
    # Source file must NOT be deleted — the watcher never owns folders
    # like WhatsApp Desktop's media folder, only copies from them.
    assert source.exists()


def test_ingest_local_file_rejects_bad_extension(tmp_path, monkeypatch):
    from app.services.voice_note_service import ingest_local_file, InvalidAudioFile
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "audio"))

    source = tmp_path / "incoming.txt"
    source.write_bytes(b"not audio")

    with pytest.raises(InvalidAudioFile):
        ingest_local_file(source)


def test_ingest_local_file_rejects_empty_file(tmp_path, monkeypatch):
    from app.services.voice_note_service import ingest_local_file, InvalidAudioFile
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "audio"))

    source = tmp_path / "incoming.mp3"
    source.write_bytes(b"")

    with pytest.raises(InvalidAudioFile):
        ingest_local_file(source)
