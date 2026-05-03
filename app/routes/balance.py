# app/routes/balance.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
import logging

from app.database import get_async_session
from app.services.balance_service import credit_balance, get_user_balance
from app.dependencies.dependency import require_completed_welcome
from app.models import User

# 🔥 cache
from app.core.cache import cache_get, cache_set, cache_delete

router = APIRouter(
    prefix="/balance",
    tags=["Balance"]
)

logger = logging.getLogger(__name__)


# ============================================================
# 🔹 SCHEMA
# ============================================================
class AddBalanceRequest(BaseModel):
    points: int = Field(..., gt=0)


# ============================================================
# 🔹 ADD BALANCE (PROTÉGÉ + CACHE INVALIDATION)
# ============================================================
@router.post("/add")
async def add_balance_points(
    payload: AddBalanceRequest,
    current_user: User = Depends(require_completed_welcome),
    db: AsyncSession = Depends(get_async_session)
):
    try:
        # 🔥 crédit
        new_total = await credit_balance(
            db=db,
            user_id=current_user.id,
            points=payload.points
        )

        # 🔥 invalider cache
        cache_key = f"balance:{current_user.id}"
        await cache_delete(cache_key)

        return {
            "success": True,
            "message": "Points ajoutés",
            "balance": new_total
        }

    except Exception as e:
        logger.error(f"[BALANCE ERROR] {e}", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de l'ajout de balance"
        )


# ============================================================
# 🔹 GET BALANCE (CACHE + PROTÉGÉ)
# ============================================================
@router.get("/")
async def get_balance(
    current_user: User = Depends(require_completed_welcome),
    db: AsyncSession = Depends(get_async_session)
):
    user_id = current_user.id
    cache_key = f"balance:{user_id}"

    # 🔥 1. CACHE
    cached = await cache_get(cache_key)
    if cached:
        return {
            "success": True,
            "source": "cache",
            **cached
        }

    # 🔥 2. DB
    points = await get_user_balance(db, user_id)

    data = {
        "user_id": user_id,
        "points": points
    }

    # 🔥 3. SET CACHE
    await cache_set(cache_key, data, ttl=30)

    return {
        "success": True,
        "source": "database",
        **data
    }