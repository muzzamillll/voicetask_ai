"""Contacts API — manual CRUD, plus auto-save from confirmed voice notes (see confirmation_service.py)."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.contact import Contact
from app.schemas.contact import ContactResponse, ContactCreate, ContactUpdate
from app.services.user_service import get_or_create_demo_user

router = APIRouter(prefix="/api/contacts", tags=["contacts"])


@router.get("", response_model=list[ContactResponse])
def list_contacts(db: Session = Depends(get_db)):
    return db.query(Contact).order_by(Contact.name.asc()).all()


@router.post("", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
def create_contact(body: ContactCreate, db: Session = Depends(get_db)):
    user = get_or_create_demo_user(db)
    contact = Contact(user_id=user.id, name=body.name, phone=body.phone, notes=body.notes)
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


@router.get("/{contact_id}", response_model=ContactResponse)
def get_contact(contact_id: int, db: Session = Depends(get_db)):
    contact = db.get(Contact, contact_id)
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found.")
    return contact


@router.put("/{contact_id}", response_model=ContactResponse)
def update_contact(contact_id: int, body: ContactUpdate, db: Session = Depends(get_db)):
    contact = db.get(Contact, contact_id)
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found.")
    if body.name is not None:
        contact.name = body.name
    if body.phone is not None:
        contact.phone = body.phone
    if body.notes is not None:
        contact.notes = body.notes
    db.commit()
    db.refresh(contact)
    return contact


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contact(contact_id: int, db: Session = Depends(get_db)):
    contact = db.get(Contact, contact_id)
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found.")
    db.delete(contact)
    db.commit()
