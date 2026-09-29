"""
Tests for order/payment status update endpoints.

Run with:
    pytest tests/test_status_updates.py -v
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
from app.models.order import Order
from app.models.payment import Payment


@pytest.fixture()
def client_and_ids():
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
    user = User(name="Demo", email="demo@test.local")
    db.add(user)
    db.commit()

    voice_note = VoiceNote(user_id=user.id, audio_path="data/audio/fake.mp3")
    db.add(voice_note)
    db.commit()

    order = Order(user_id=user.id, voice_note_id=voice_note.id, customer_name="Ali", amount=1000)
    payment = Payment(user_id=user.id, voice_note_id=voice_note.id, contact_name="Ali", amount=500)
    db.add_all([order, payment])
    db.commit()
    ids = {"order_id": order.id, "payment_id": payment.id}
    db.close()

    yield TestClient(app), ids
    app.dependency_overrides.clear()


def test_update_order_status_to_confirmed(client_and_ids):
    client, ids = client_and_ids
    response = client.put(f"/api/orders/{ids['order_id']}/status", json={"status": "confirmed"})
    assert response.status_code == 200
    assert response.json()["status"] == "confirmed"


def test_update_order_status_to_delivered(client_and_ids):
    client, ids = client_and_ids
    response = client.put(f"/api/orders/{ids['order_id']}/status", json={"status": "delivered"})
    assert response.status_code == 200
    assert response.json()["status"] == "delivered"


def test_update_order_status_invalid_value_rejected(client_and_ids):
    client, ids = client_and_ids
    response = client.put(f"/api/orders/{ids['order_id']}/status", json={"status": "not_a_real_status"})
    assert response.status_code == 422


def test_update_order_status_nonexistent_order_404(client_and_ids):
    client, _ids = client_and_ids
    response = client.put("/api/orders/9999/status", json={"status": "confirmed"})
    assert response.status_code == 404


def test_update_payment_status_to_paid(client_and_ids):
    client, ids = client_and_ids
    response = client.put(f"/api/payments/{ids['payment_id']}/status", json={"status": "paid"})
    assert response.status_code == 200
    assert response.json()["status"] == "paid"


def test_update_payment_status_to_overdue(client_and_ids):
    client, ids = client_and_ids
    response = client.put(f"/api/payments/{ids['payment_id']}/status", json={"status": "overdue"})
    assert response.status_code == 200
    assert response.json()["status"] == "overdue"


def test_update_payment_status_nonexistent_payment_404(client_and_ids):
    client, _ids = client_and_ids
    response = client.put("/api/payments/9999/status", json={"status": "paid"})
    assert response.status_code == 404
