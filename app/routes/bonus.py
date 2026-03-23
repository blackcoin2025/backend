# app/routes/bonus.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
from typing import List, Dict
from decimal import Decimal

from app.database import get_async_session
from app.models import (
    Bonus,
    RealCash,
    Friend,
    UserPack,
    Action,
    ActionCategory,
    UserAction,
    User,
)
from app.schemas import BonusOut
from app.services.wallet_service import credit_wallet

router = APIRouter(prefix="/bonus", tags=["Bonus"])

CLAIM_AMOUNT = Decimal("0.3")
COOLDOWN_HOURS = 24


# ============================================================
# 🔹 VERIFICATION CONDITIONS
# ============================================================
async def check_bonus_conditions(user_id: int, db: AsyncSession):

    # 1️⃣ PACK
    has_pack = (
        await db.execute(
            select(UserPack).where(UserPack.user_id == user_id)
        )
    ).scalars().first() is not None

    if not has_pack:
        has_pack = (
            await db.execute(
                select(UserAction)
                .join(Action)
                .where(
                    UserAction.user_id == user_id,
                    Action.category == ActionCategory.finance,
                )
            )
        ).scalars().first() is not None

    # 2️⃣ DEPOT
    real_cash = (
        await db.execute(
            select(RealCash).where(RealCash.user_id == user_id)
        )
    ).scalars().first()

    has_deposit = bool(real_cash and real_cash.cash_balance > 0)

    # 3️⃣ FRIENDS
    friends_count = (
        await db.execute(
            select(func.count())
            .select_from(Friend)
            .where(
                Friend.user_id == user_id,
                Friend.status == "accepted",
            )
        )
    ).scalar() or 0

    return {
        "has_pack": has_pack,
        "has_deposit": has_deposit,
        "friends_count": friends_count,
        "all_conditions_met": has_pack and has_deposit and friends_count >= 3,
    }


# ============================================================
# 🔹 LISTE BONUS USER
# ============================================================
@router.get("/{user_id}", response_model=List[BonusOut])
async def get_user_bonus(user_id: int, db: AsyncSession = Depends(get_async_session)):

    result = await db.execute(
        select(Bonus).where(Bonus.user_id == user_id)
    )
    return result.scalars().all()


# ============================================================
# 🔹 STATUS BONUS (FRONTEND)
# ============================================================
@router.get("/{user_id}/status", response_model=Dict)
async def get_bonus_status(user_id: int, db: AsyncSession = Depends(get_async_session)):

    bonus = (
        await db.execute(
            select(Bonus)
            .where(Bonus.user_id == user_id)
            .order_by(Bonus.cree_le.desc())
            .limit(1)
        )
    ).scalars().first()

    if not bonus:
        return {"status": "not_found"}

    conditions = await check_bonus_conditions(user_id, db)

    status = "conditions_not_met"
    next_claim_at = None

    if conditions["all_conditions_met"]:

        if bonus.points_restants < CLAIM_AMOUNT:
            status = "insufficient_points"

        else:
            if not bonus.last_claim_at:
                status = "eligible"
            else:
                next_allowed = bonus.last_claim_at + timedelta(hours=COOLDOWN_HOURS)

                if datetime.utcnow() >= next_allowed:
                    status = "eligible"
                else:
                    status = "cooldown"
                    next_claim_at = next_allowed

    return {
        "status": status,
        "total_points": float(bonus.total_points),
        "points_restants": float(bonus.points_restants),
        "last_claim_at": bonus.last_claim_at,
        "next_claim_at": next_claim_at,
        "conditions": conditions,
        "claim_amount": float(CLAIM_AMOUNT),
    }


# ============================================================
# 🔹 CLAIM BONUS (PRODUCTION SAFE)
# ============================================================
@router.post("/{user_id}/claim")
async def claim_bonus(user_id: int, db: AsyncSession = Depends(get_async_session)):

    bonus = (
        await db.execute(
            select(Bonus)
            .where(Bonus.user_id == user_id)
            .order_by(Bonus.cree_le.desc())
            .limit(1)
        )
    ).scalars().first()

    if not bonus:
        raise HTTPException(status_code=404, detail="Bonus introuvable")

    conditions = await check_bonus_conditions(user_id, db)

    if not conditions["all_conditions_met"]:
        raise HTTPException(status_code=400, detail="Conditions non remplies")

    if bonus.points_restants < CLAIM_AMOUNT:
        raise HTTPException(status_code=400, detail="Points bonus insuffisants")

    # 🔹 COOLDOWN
    if bonus.last_claim_at:
        next_allowed = bonus.last_claim_at + timedelta(hours=COOLDOWN_HOURS)
        if datetime.utcnow() < next_allowed:
            raise HTTPException(status_code=400, detail="Cooldown actif")

    # 🔹 CREDIT WALLET VIA SERVICE
    # On récupère l'utilisateur pour le service
    user = (
        await db.execute(
            select(User).where(User.id == user_id)
        )
    ).scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    await credit_wallet(user, Decimal(str(CLAIM_AMOUNT)), db)

    # 🔹 UPDATE BONUS
    bonus.points_restants -= CLAIM_AMOUNT
    bonus.last_claim_at = datetime.utcnow()

    if bonus.points_restants <= Decimal("0"):
        bonus.status = "converti"
        bonus.converti_le = datetime.utcnow()

    await db.commit()

    return {
        "message": "Bonus réclamé avec succès",
        "amount": float(CLAIM_AMOUNT),
        "points_restants": float(bonus.points_restants),
        "next_claim_at": bonus.last_claim_at + timedelta(hours=COOLDOWN_HOURS),
    }
