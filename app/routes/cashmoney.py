from fastapi import APIRouter, Depends
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.models import RealCash, User
from app.routers.auth import get_current_user

# 🔥 cache
from app.core.cache import cache_get, cache_set

router = APIRouter(
    prefix="/wallet",
    tags=["CashMoney"]
)


@router.get("/realcash")
async def get_real_cash(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    user_id = current_user.id
    cache_key = f"realcash:{user_id}"

    # -----------------------------
    # 🔥 1. CACHE
    # -----------------------------
    cached = await cache_get(cache_key)
    if cached:
        return cached

    # -----------------------------
    # 🔥 2. DB QUERY
    # -----------------------------
    result = await db.execute(
        select(RealCash).where(RealCash.user_id == user_id)
    )
    real_cash = result.scalars().first()

    # -----------------------------
    # 🔥 3. AUTO CREATE SAFE
    # -----------------------------
    if not real_cash:
        real_cash = RealCash(
            user_id=user_id,
            cash_balance=0
        )

        db.add(real_cash)
        await db.commit()
        await db.refresh(real_cash)

    data = {
        "cash_balance": float(real_cash.cash_balance)
    }

    # -----------------------------
    # 🔥 4. CACHE SET
    # -----------------------------
    await cache_set(cache_key, data, ttl=30)

    return data