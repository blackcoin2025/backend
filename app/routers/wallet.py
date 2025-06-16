from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models import Wallet
from app.schemas import WalletBase, WalletOut

router = APIRouter(prefix="/wallet", tags=["Wallet"])

@router.get("/{telegram_id}", response_model=WalletOut)
async def get_wallet(telegram_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Wallet).where(Wallet.telegram_id == telegram_id))
    wallet = result.scalar_one_or_none()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    return wallet

@router.post("/", response_model=WalletOut)
async def create_wallet(wallet_data: WalletBase, db: AsyncSession = Depends(get_db)):
    new_wallet = Wallet(**wallet_data.dict())
    db.add(new_wallet)
    await db.commit()
    await db.refresh(new_wallet)
    return new_wallet

@router.put("/{telegram_id}", response_model=WalletOut)
async def update_wallet(telegram_id: str, wallet_data: WalletBase, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Wallet).where(Wallet.telegram_id == telegram_id))
    wallet = result.scalar_one_or_none()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    
    wallet.ton_wallet_address = wallet_data.ton_wallet_address
    wallet.is_verified = wallet_data.is_verified
    await db.commit()
    await db.refresh(wallet)
    return wallet

@router.get("/{telegram_id}/balance")
async def get_wallet_balance(telegram_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Wallet).where(Wallet.telegram_id == telegram_id))
    wallet = result.scalar_one_or_none()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    return {
        "ton_wallet_address": wallet.ton_wallet_address,
        "is_verified": wallet.is_verified
    }
