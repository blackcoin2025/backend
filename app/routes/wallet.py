# app/routes/wallet.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from decimal import Decimal
import logging

from app.database import get_async_session
from app.services.wallet_service import (
    credit_wallet,
    debit_wallet,
    get_wallet_balance
)
from app.dependencies.dependency import require_completed_welcome
from app.models import User

# 🔥 cache
from app.core.cache import cache_get, cache_set, cache_delete

router = APIRouter(
    prefix="/wallet",
    tags=["Wallet"]
)

logger = logging.getLogger(__name__)


# ============================================================
# 🔹 SCHEMA
# ============================================================
class WalletOperationRequest(BaseModel):
    amount: Decimal = Field(..., gt=0)


# ============================================================
# 🔹 CREDIT WALLET (PROTÉGÉ)
# ============================================================
@router.post("/credit")
async def credit_user_wallet(
    payload: WalletOperationRequest,
    current_user: User = Depends(require_completed_welcome),
    db: AsyncSession = Depends(get_async_session)
):
    try:
        # ⚠️ PROTECTION : empêcher appel externe abusif
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Opération interdite"
        )

        # 👉 à utiliser uniquement en interne (services)
        wallet = await credit_wallet(
            user=current_user,
            amount=payload.amount,
            db=db
        )

        await cache_delete(f"wallet:{current_user.id}")

        return {
            "success": True,
            "balance": float(wallet.amount)
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"[WALLET CREDIT ERROR] {e}", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors du crédit"
        )


# ============================================================
# 🔹 DEBIT WALLET (PROTÉGÉ)
# ============================================================
@router.post("/debit")
async def debit_user_wallet(
    payload: WalletOperationRequest,
    current_user: User = Depends(require_completed_welcome),
    db: AsyncSession = Depends(get_async_session)
):
    try:
        wallet = await debit_wallet(
            user=current_user,
            amount=payload.amount,
            db=db
        )

        await cache_delete(f"wallet:{current_user.id}")

        return {
            "success": True,
            "message": f"{payload.amount} retiré",
            "balance": float(wallet.amount)
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    except Exception as e:
        logger.error(f"[WALLET DEBIT ERROR] {e}", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors du débit"
        )


# ============================================================
# 🔹 GET WALLET (CACHE + PROTÉGÉ)
# ============================================================
@router.get("/")
async def wallet_info(
    current_user: User = Depends(require_completed_welcome),
    db: AsyncSession = Depends(get_async_session)
):
    user_id = current_user.id
    cache_key = f"wallet:{user_id}"

    try:
        # 🔥 1. CACHE
        cached = await cache_get(cache_key)
        if cached:
            return {
                "success": True,
                "source": "cache",
                **cached
            }

        # 🔥 2. DB
        balance = await get_wallet_balance(current_user, db)

        data = {
            "user_id": user_id,
            "balance": float(balance)
        }

        # 🔥 3. SET CACHE
        await cache_set(cache_key, data, ttl=30)

        return {
            "success": True,
            "source": "database",
            **data
        }

    except Exception as e:
        logger.error(f"[WALLET FETCH ERROR] {e}", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération du wallet"
        )