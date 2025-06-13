from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import UserProfile
from app.schemas import UserCreate, UserOut  # <-- noms corrects

router = APIRouter()

@router.post("/", response_model=UserOut)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(UserProfile).filter(UserProfile.telegram_id == user.telegram_id).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")
    new_user = UserProfile(**user.dict())
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.get("/{telegram_id}", response_model=UserOut)
def get_user(telegram_id: str, db: Session = Depends(get_db)):
    user = db.query(UserProfile).filter(UserProfile.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
