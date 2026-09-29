"""Pydantic schemas for orders."""
from datetime import datetime, date

from pydantic import BaseModel, ConfigDict

from app.models.order import OrderStatus


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    voice_note_id: int | None
    customer_name: str | None
    description: str | None
    quantity: int | None
    amount: float | None
    currency: str
    delivery_date: date | None
    status: OrderStatus
    created_at: datetime
