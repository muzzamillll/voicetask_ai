"""Orders API. Phase 8: list, get, status updates."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.order import Order, OrderStatus
from app.schemas.order import OrderResponse

router = APIRouter(prefix="/api/orders", tags=["orders"])


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


@router.get("", response_model=list[OrderResponse])
def list_orders(db: Session = Depends(get_db)):
    return db.query(Order).order_by(Order.created_at.desc()).all()


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
    return order


@router.put("/{order_id}/status", response_model=OrderResponse)
def update_order_status(order_id: int, body: OrderStatusUpdate, db: Session = Depends(get_db)):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
    order.status = body.status
    db.commit()
    db.refresh(order)
    return order
