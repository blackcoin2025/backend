# app/routes/wallet.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.database import get_async_session
from app.models import RealCash, User
from app.dependencies.dependency import require_completed_welcome

# 🔥 cache
from app.core.cache import cache_get, cache_set

router = APIRouter(
    prefix="/wallet",
    tags=["CashMoney"]
)

logger = logging.getLogger(__name__)


# ============================================================
# 🔹 GET REAL CASH (PROTÉGÉ + CACHE)
# ============================================================
@router.get("/realcash")
async def get_real_cash(
    current_user: User = Depends(require_completed_welcome),
    db: AsyncSession = Depends(get_async_session)
):
    user_id = current_user.id
    cache_key = f"realcash:{user_id}"

    try:
        # ----------------------------------------------------
        # 🔥 1. CACHE
        # ----------------------------------------------------
        cached = await cache_get(cache_key)
        if cached:
            return {
                "success": True,
                "source": "cache",
                **cached
            }

        # ----------------------------------------------------
        # 🔥 2. DB QUERY
        # ----------------------------------------------------
        result = await db.execute(
            select(RealCash).where(RealCash.user_id == user_id)
        )
        real_cash = result.scalars().first()

        # ----------------------------------------------------
        # 🔥 3. FALLBACK SAFE (NO AUTO COMMIT HERE)
        # ----------------------------------------------------
        if not real_cash:
            # ⚠️ On ne crée pas automatiquement dans un GET
            # (bonne pratique REST)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portefeuille introuvable"
            )

        data = {
            "cash_balance": float(real_cash.cash_balance)
        }

        # ----------------------------------------------------
        # 🔥 4. CACHE SET
        # ----------------------------------------------------
        await cache_set(cache_key, data, ttl=30)

        return {
            "success": True,
            "source": "database",
            **data
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"[WALLET ERROR] {e}", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération du portefeuille"
        )