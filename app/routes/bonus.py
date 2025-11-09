# app/routes/bonus.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from typing import List, Optional, Dict

from app.database import get_async_session
from app.models import Bonus, User, Wallet, Friend, UserPack, Action, ActionCategory, UserAction
from app.schemas import BonusOut

router = APIRouter(prefix="/bonus", tags=["Bonus"])


# ------------------------------------------------------------
# 🧩 Liste de tous les bonus d’un utilisateur
# ------------------------------------------------------------
@router.get("/{user_id}", response_model=List[BonusOut])
async def get_user_bonus(user_id: int, db: AsyncSession = Depends(get_async_session)):
    stmt = select(Bonus).where(Bonus.user_id == user_id)
    res = await db.execute(stmt)
    bonuses = res.scalars().all()
    return bonuses or []


# ------------------------------------------------------------
# 🧩 Dernier bonus actif ou créé récemment
# ------------------------------------------------------------
@router.get("/{user_id}/latest", response_model=Optional[BonusOut])
async def get_latest_bonus(user_id: int, db: AsyncSession = Depends(get_async_session)):
    stmt = (
        select(Bonus)
        .where(Bonus.user_id == user_id)
        .order_by(Bonus.cree_le.desc())
        .limit(1)
    )
    res = await db.execute(stmt)
    bonus = res.scalars().first()
    return bonus


# ------------------------------------------------------------
# 🧩 Créer un nouveau bonus (optionnel)
# ------------------------------------------------------------
@router.post("/", response_model=BonusOut)
async def create_bonus(
    user_id: int,
    total_points: int,
    raison: str = "bonus_inscription",
    db: AsyncSession = Depends(get_async_session),
):
    user_check = await db.execute(select(User).where(User.id == user_id))
    user = user_check.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    bonus = Bonus(
        user_id=user_id,
        total_points=total_points,
        points_restants=total_points,
        raison=raison,
    )

    db.add(bonus)
    await db.commit()
    await db.refresh(bonus)
    return bonus


# ------------------------------------------------------------
# 🧩 Dernier bonus + état des conditions pour frontend
# ------------------------------------------------------------
@router.get("/{user_id}/status", response_model=Dict)
async def get_bonus_status(user_id: int, db: AsyncSession = Depends(get_async_session)):
    # 1️⃣ Récupérer le dernier bonus
    stmt = (
        select(Bonus)
        .where(Bonus.user_id == user_id)
        .order_by(Bonus.cree_le.desc())
        .limit(1)
    )
    res = await db.execute(stmt)
    bonus = res.scalars().first()

    if not bonus:
        return {
            "bonus": None,
            "conditions": {"pack": "non", "friends": "0/3", "deposit": "non"},
        }

    # 2️⃣ Vérifier si l'utilisateur possède un PACK (source principale : UserPack)
    pack_stmt = select(UserPack).where(UserPack.user_id == user_id)
    pack_res = await db.execute(pack_stmt)
    has_pack = pack_res.scalars().first() is not None

    # 3️⃣ Vérification de secours : via UserAction (ActionCategory.finance)
    if not has_pack:
        alt_pack_stmt = (
            select(UserAction)
            .join(Action)
            .where(
                UserAction.user_id == user_id,
                Action.category == ActionCategory.finance
            )
        )
        alt_pack_res = await db.execute(alt_pack_stmt)
        has_pack = alt_pack_res.scalars().first() is not None

    # 4️⃣ Vérifier si l'utilisateur a un dépôt positif
    wallet_stmt = select(Wallet).where(Wallet.user_id == user_id)
    wallet_res = await db.execute(wallet_stmt)
    wallet = wallet_res.scalars().first()
    has_deposit = bool(wallet and wallet.amount > 0)

    # 5️⃣ Vérifier le nombre d'amis acceptés
    friends_stmt = select(func.count()).select_from(Friend).where(
        Friend.user_id == user_id,
        Friend.status == "accepted"
    )
    friends_count = (await db.execute(friends_stmt)).scalar() or 0

    # 6️⃣ Retourner les données formatées
    return {
        "bonus": {
            "total_points": bonus.total_points,
            "points_restants": bonus.points_restants,
            "status": bonus.status.value if hasattr(bonus.status, "value") else bonus.status,
        },
        "conditions": {
            "pack": "oui" if has_pack else "non",
            "friends": f"{friends_count}/3",
            "deposit": "oui" if has_deposit else "non",
        },
    }
