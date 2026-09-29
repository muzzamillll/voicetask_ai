"""Pydantic schemas for contacts."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ContactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    phone: str | None
    notes: str | None
    created_at: datetime


class ContactCreate(BaseModel):
    name: str
    phone: str | None = None
    notes: str | None = None


class ContactUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    notes: str | None = None
