# app/routers/wallet.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Wallet
from app.schemas import WalletBase

router = APIRouter()

@router.get("/{telegram_id}")
def get_wallet(telegram_id: str, db: Session = Depends(get_db)):
    wallet = db.query(Wallet).filter(Wallet.telegram_id == telegram_id).first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    return wallet

@router.post("/")
def create_wallet(wallet_data: WalletBase, db: Session = Depends(get_db)):
    wallet = Wallet(**wallet_data.dict())
    db.add(wallet)
    db.commit()
    db.refresh(wallet)
    return wallet

@router.put("/{telegram_id}")
def update_wallet(telegram_id: str, wallet_data: WalletBase, db: Session = Depends(get_db)):
    wallet = db.query(Wallet).filter(Wallet.telegram_id == telegram_id).first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    wallet.ton_wallet_address = wallet_data.ton_wallet_address
    db.commit()
    db.refresh(wallet)
    return wallet

