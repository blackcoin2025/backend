# app/routers/myactions.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import MyAction
from app.schemas import MyActionBase

router = APIRouter()

@router.get("/{telegram_id}")
def get_user_actions(telegram_id: str, db: Session = Depends(get_db)):
    actions = db.query(MyAction).filter(MyAction.telegram_id == telegram_id).all()
    if not actions:
        raise HTTPException(status_code=404, detail="No actions found for this user.")
    return actions

@router.post("/")
def add_user_action(action_data: MyActionBase, db: Session = Depends(get_db)):
    new_action = MyAction(**action_data.dict())
    db.add(new_action)
    db.commit()
    db.refresh(new_action)
    return new_action

@router.delete("/{action_id}")
def delete_user_action(action_id: int, db: Session = Depends(get_db)):
    action = db.query(MyAction).filter(MyAction.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found.")
    db.delete(action)
    db.commit()
    return {"detail": "Action deleted successfully"}