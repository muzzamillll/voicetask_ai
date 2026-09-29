"""
Pydantic schema for LLM structured extraction output.

Mirrors the exact schema from the project spec. The LLM must never invent
information — missing fields come back as null/empty, never guessed.
"""
from enum import Enum

from pydantic import BaseModel, Field


class Intent(str, Enum):
    TASK = "task"
    REMINDER = "reminder"
    ORDER = "order"
    PAYMENT = "payment"
    MEETING = "meeting"
    APPOINTMENT = "appointment"
    FOLLOW_UP = "follow_up"
    NOTE = "note"
    UNKNOWN = "unknown"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ContactInfo(BaseModel):
    name: str = ""
    phone: str = ""


class DeadlineInfo(BaseModel):
    date: str = ""
    time: str = ""
    datetime: str = ""
    is_specific: bool = False


class AmountInfo(BaseModel):
    value: float | None = None
    currency: str = "PKR"


class ExtractionResult(BaseModel):
    intent: Intent = Intent.UNKNOWN
    title: str = ""
    description: str = ""
    task: str = ""
    contact: ContactInfo = Field(default_factory=ContactInfo)
    deadline: DeadlineInfo = Field(default_factory=DeadlineInfo)
    amount: AmountInfo = Field(default_factory=AmountInfo)
    quantity: int | None = None
    location: str = ""
    priority: Priority = Priority.MEDIUM
    status: str = "pending"
    language: str = "English"
    confidence: float = 0.0
    needs_clarification: bool = False
    clarification_question: str = ""


class ExtractionReviewResponse(BaseModel):
    """What /extract/{id} actually returns: the raw extraction plus
    Phase 7's recommendation for what should happen with it."""

    extraction: ExtractionResult
    recommended_action: str  # "auto_create" | "confirm_review" | "manual_review"
