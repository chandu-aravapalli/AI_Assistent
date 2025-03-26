from sqlalchemy.orm import Session
from . import models

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, email: str):
    user = models.User(email=email)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def update_user_credentials(db: Session, user_id: int, credentials: dict):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user:
        user.google_credentials = credentials
        db.commit()
        db.refresh(user)
    return user 