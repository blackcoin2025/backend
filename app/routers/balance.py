# app/routers/balance.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db
from app.models import Balance
from app.schemas import BalanceBase, BalanceOut

router = APIRouter(prefix="/wallet", tags=["Balance"])

@router.get("/{telegram_id}/balance", response_model=BalanceOut)
async def get_balance(telegram_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Balance).where(Balance.telegram_id == telegram_id))
    balance = result.scalar_one_or_none()
    if not balance:
        raise HTTPException(status_code=404, detail="Balance not found")
    return balance

@router.put("/{telegram_id}/balance", response_model=BalanceOut)
async def update_balance(telegram_id: str, balance_data: BalanceBase, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Balance).where(Balance.telegram_id == telegram_id))
    balance = result.scalar_one_or_none()
    if not balance:
        raise HTTPException(status_code=404, detail="Balance not found")

    balance.points = balance_data.points
    await db.commit()
    await db.refresh(balance)
    return balance
