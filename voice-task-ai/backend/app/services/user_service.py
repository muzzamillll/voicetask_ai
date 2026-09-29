"""
No authentication system exists yet (out of scope for the MVP phases so far).
Until Phase 12+ or a dedicated auth phase, every request operates as a single
demo user so the rest of the app has a concrete user_id to attach records to.
"""
from sqlalchemy.orm import Session

from app.models.user import User

DEMO_USER_EMAIL = "demo@voicetask.local"


def get_or_create_demo_user(db: Session) -> User:
    user = db.query(User).filter(User.email == DEMO_USER_EMAIL).first()
    if user:
        return user
    user = User(name="Demo User", email=DEMO_USER_EMAIL)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
