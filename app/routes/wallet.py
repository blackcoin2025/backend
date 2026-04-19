from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.services.wallet_service import credit_wallet, debit_wallet, get_wallet_balance
from app.routers.auth import get_current_user

# 🔥 cache
from app.core.cache import cache_get, cache_set, cache_delete

router = APIRouter(
    prefix="/wallet",
    tags=["Wallet"]
)


# -----------------------------
# CREDIT (NO CACHE + INVALIDATE)
# -----------------------------
@router.post("/credit")
async def credit_user_wallet(
    amount: float = Body(..., embed=True, ge=0.01),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    try:
        wallet = await credit_wallet(user, amount, db)

        # 🔥 invalider cache
        await cache_delete(f"wallet:{user.id}")

        return {
            "message": f"✅ {amount:.2f} $BKC ajoutés au wallet.",
            "user_id": user.id,
            "balance": wallet.amount
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# -----------------------------
# DEBIT (NO CACHE + INVALIDATE)
# -----------------------------
@router.post("/debit")
async def debit_user_wallet(
    amount: float = Body(..., embed=True, ge=0.01),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    try:
        wallet = await debit_wallet(user, amount, db)

        # 🔥 invalider cache
        await cache_delete(f"wallet:{user.id}")

        return {
            "message": f"💸 {amount:.2f} $BKC retirés du wallet.",
            "user_id": user.id,
            "balance": wallet.amount
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# -----------------------------
# GET WALLET (CACHE)
# -----------------------------
@router.get("/")
async def wallet_info(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    user_id = user.id
    cache_key = f"wallet:{user_id}"

    # 🔥 1. CACHE
    cached = await cache_get(cache_key)
    if cached:
        return cached

    # 🔥 2. DB
    balance = await get_wallet_balance(user, db)

    data = {
        "user_id": user_id,
        "balance": balance
    }

    # 🔥 3. SET CACHE
    await cache_set(cache_key, data, ttl=30)

    return data