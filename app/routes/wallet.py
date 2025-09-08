# app/routes/wallet.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.services.wallet_service import add_wallet_points, get_wallet_balance
from app.routers.auth import get_current_user

router = APIRouter(
    prefix="/wallet",
    tags=["Wallet"]
)

@router.post("/add")
async def add_wallet(user = Depends(get_current_user), amount: int = 0, db: AsyncSession = Depends(get_async_session)):
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Montant invalide")
    wallet = await add_wallet_points(user, amount, db)
    return {"user_id": user.id, "new_amount": wallet.amount}

@router.get("/")
async def wallet_info(user = Depends(get_current_user), db: AsyncSession = Depends(get_async_session)):
    amount = await get_wallet_balance(user, db)
    return {"user_id": user.id, "amount": amount}
