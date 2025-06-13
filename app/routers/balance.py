# app/routers/balance.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Balance
from app.schemas import BalanceBase, BalanceOut

router = APIRouter()

@router.get("/{telegram_id}", response_model=BalanceOut)
def get_balance(telegram_id: str, db: Session = Depends(get_db)):
    balance = db.query(Balance).filter(Balance.telegram_id == telegram_id).first()
    if not balance:
        raise HTTPException(status_code=404, detail="Balance not found")
    return balance

@router.put("/{telegram_id}", response_model=BalanceOut)
def update_balance(telegram_id: str, balance_data: BalanceBase, db: Session = Depends(get_db)):
    balance = db.query(Balance).filter(Balance.telegram_id == telegram_id).first()
    if not balance:
        raise HTTPException(status_code=404, detail="Balance not found")
    balance.points = balance_data.points
    db.commit()
    db.refresh(balance)
    return balance
