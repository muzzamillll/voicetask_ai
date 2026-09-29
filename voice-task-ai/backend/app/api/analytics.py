"""Analytics API — aggregated stats for the dashboard's Analytics page."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.voice_note import VoiceNote
from app.models.transcript import Transcript
from app.models.task import Task, TaskStatus
from app.models.order import Order
from app.models.payment import Payment

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/summary")
def get_summary(db: Session = Depends(get_db)):
    total_voice_notes = db.query(VoiceNote).count()
    total_tasks = db.query(Task).count()
    completed_tasks = db.query(Task).filter(Task.status == TaskStatus.COMPLETED).count()
    total_orders = db.query(Order).count()
    total_payments = db.query(Payment).count()

    avg_confidence = db.query(func.avg(Transcript.confidence)).scalar()
    avg_extraction_confidence = db.query(func.avg(Task.confidence)).scalar()

    pending_payments_total = (
        db.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(Payment.status == "pending")
        .scalar()
    )

    return {
        "total_voice_notes": total_voice_notes,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "total_orders": total_orders,
        "total_payments": total_payments,
        "pending_payments_total": float(pending_payments_total or 0),
        "average_confidence": round(avg_extraction_confidence, 3) if avg_extraction_confidence else None,
    }


@router.get("/intents")
def get_intent_distribution(db: Session = Depends(get_db)):
    """
    Combines Task's stored `intent` field with Order/Payment counts
    (which are always "order"/"payment" respectively, by definition of
    how they were created) into one distribution.
    """
    counts: dict[str, int] = {}

    task_rows = (
        db.query(Task.intent, func.count(Task.id)).group_by(Task.intent).all()
    )
    for intent, count in task_rows:
        key = intent or "unknown"
        counts[key] = counts.get(key, 0) + count

    order_count = db.query(Order).count()
    if order_count:
        counts["order"] = counts.get("order", 0) + order_count

    payment_count = db.query(Payment).count()
    if payment_count:
        counts["payment"] = counts.get("payment", 0) + payment_count

    return [{"intent": k, "count": v} for k, v in sorted(counts.items(), key=lambda x: -x[1])]


@router.get("/languages")
def get_language_distribution(db: Session = Depends(get_db)):
    rows = (
        db.query(Transcript.language, func.count(Transcript.id))
        .group_by(Transcript.language)
        .all()
    )
    return [
        {"language": lang or "Unknown", "count": count}
        for lang, count in sorted(rows, key=lambda x: -x[1])
    ]


@router.get("/voice-notes-per-day")
def get_voice_notes_per_day(days: int = 14, db: Session = Depends(get_db)):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        db.query(func.date(VoiceNote.created_at), func.count(VoiceNote.id))
        .filter(VoiceNote.created_at >= since)
        .group_by(func.date(VoiceNote.created_at))
        .order_by(func.date(VoiceNote.created_at))
        .all()
    )
    return [{"date": str(date), "count": count} for date, count in rows]
