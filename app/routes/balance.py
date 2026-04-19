from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.services.balance_service import credit_balance, get_user_balance
from app.routers.auth import get_current_user
from app.models import User

# 🔥 cache
from app.core.cache import cache_get, cache_set, cache_delete

router = APIRouter(
    prefix="/balance",
    tags=["Balance"]
)


# -----------------------------
# ADD BALANCE (NO CACHE + INVALIDATE)
# -----------------------------
@router.post("/add")
async def add_balance_points(
    points: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    if points <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Points invalides"
        )

    try:
        new_total = await credit_balance(db, current_user.id, points)

        # 🔥 invalider cache
        await cache_delete(f"balance:{current_user.id}")

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

    return {
        "message": "Points ajoutés à la balance",
        "points": new_total
    }


# -----------------------------
# GET BALANCE (CACHE)
# -----------------------------
@router.get("/")
async def get_balance(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    user_id = current_user.id
    cache_key = f"balance:{user_id}"

    # 🔥 1. try cache
    cached = await cache_get(cache_key)
    if cached:
        return cached

    # 🔥 2. fallback DB
    points = await get_user_balance(db, user_id)

    data = {
        "user_id": user_id,
        "points": points
    }

    # 🔥 3. set cache (TTL court = cohérence)
    await cache_set(cache_key, data, ttl=30)

    return data