"""Payment model — a payment owed or received, extracted from a voice note."""
import enum
from datetime import datetime, timezone

from sqlalchemy import Integer, String, Float, DateTime, Date, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    voice_note_id: Mapped[int | None] = mapped_column(ForeignKey("voice_notes.id"), nullable=True)

    contact_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="PKR")
    due_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), default=PaymentStatus.PENDING)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user = relationship("User", back_populates="payments")
    voice_note = relationship("VoiceNote", back_populates="payments")
