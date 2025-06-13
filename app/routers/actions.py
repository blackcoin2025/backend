# app/routers/actions.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import MyAction
from app.schemas import ActionBase

router = APIRouter()

@router.get("/{telegram_id}")
def get_actions(telegram_id: str, db: Session = Depends(get_db)):
    return db.query(MyAction).filter(MyAction.telegram_id == telegram_id).all()

@router.post("/")
def create_action(action_data: ActionBase, db: Session = Depends(get_db)):
    new_action = MyAction(**action_data.dict())
    db.add(new_action)
    db.commit()
    db.refresh(new_action)
    return new_action