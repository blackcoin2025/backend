# app/routers/status.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import UserStatus
from app.schemas import StatusBase

router = APIRouter()

@router.get("/{telegram_id}")
def get_status(telegram_id: str, db: Session = Depends(get_db)):
    status = db.query(Status).filter(Status.telegram_id == telegram_id).first()
    if not status:
        raise HTTPException(status_code=404, detail="Status not found")
    return status

@router.put("/{telegram_id}")
def update_status(telegram_id: str, status_data: StatusBase, db: Session = Depends(get_db)):
    status = db.query(Status).filter(Status.telegram_id == telegram_id).first()
    if not status:
        raise HTTPException(status_code=404, detail="Status not found")
    status.status_text = status_data.status_text
    db.commit()
    db.refresh(status)
    return status
