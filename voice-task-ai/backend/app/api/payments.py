"""Payments API. Phase 8: list, get, status updates."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.payment import Payment, PaymentStatus
from app.schemas.payment import PaymentResponse

router = APIRouter(prefix="/api/payments", tags=["payments"])


class PaymentStatusUpdate(BaseModel):
    status: PaymentStatus


@router.get("", response_model=list[PaymentResponse])
def list_payments(db: Session = Depends(get_db)):
    return db.query(Payment).order_by(Payment.created_at.desc()).all()


@router.get("/{payment_id}", response_model=PaymentResponse)
def get_payment(payment_id: int, db: Session = Depends(get_db)):
    payment = db.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found.")
    return payment


@router.put("/{payment_id}/status", response_model=PaymentResponse)
def update_payment_status(payment_id: int, body: PaymentStatusUpdate, db: Session = Depends(get_db)):
    payment = db.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found.")
    payment.status = body.status
    db.commit()
    db.refresh(payment)
    return payment
