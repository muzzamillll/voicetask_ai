"""Pydantic schemas for payments."""
from datetime import datetime, date

from pydantic import BaseModel, ConfigDict

from app.models.payment import PaymentStatus


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    voice_note_id: int | None
    contact_name: str | None
    amount: float | None
    currency: str
    due_date: date | None
    status: PaymentStatus
    created_at: datetime
