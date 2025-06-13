# app/routers/friends.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Friend
from app.schemas import FriendBase

router = APIRouter()

@router.post("/")
def add_friend(friend_data: FriendBase, db: Session = Depends(get_db)):
    new_friend = Friend(**friend_data.dict())
    db.add(new_friend)
    db.commit()
    db.refresh(new_friend)
    return new_friend

@router.get("/{telegram_id}")
def get_friends(telegram_id: str, db: Session = Depends(get_db)):
    return db.query(Friend).filter(Friend.inviter_id == telegram_id).all()