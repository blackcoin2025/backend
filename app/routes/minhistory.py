# app/routes/minhistory.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from datetime import datetime

from app.database import get_async_session
from app.models import MiningHistory, Balance, UserMiningStats
from app.schemas import AddMiningPayload, MiningStatusResponse, AddMiningResponse

router = APIRouter(prefix="/minhistory", tags=["MiningHistory"])

# ⚡ Paliers de niveau (doivent rester cohérents frontend/backend)
LEVEL_THRESHOLDS = [0, 5000, 14000, 32000, 65000, 100000, 160000, 230000, 310000]


# ---------- Helpers ----------
def compute_level(total_points: int) -> int:
    level = 1
    for i, threshold in enumerate(LEVEL_THRESHOLDS, start=1):
        if total_points >= threshold:
            level = i
    return level


# ---------- Endpoints ----------
@router.get("/user/{user_id}", response_model=MiningStatusResponse)
async def get_user_mining_status(user_id: int, session: AsyncSession = Depends(get_async_session)):
    """
    Retourne le total des points minés et le niveau de l'utilisateur.
    """
    result = await session.execute(
        select(UserMiningStats).where(UserMiningStats.user_id == user_id)
    )
    stats = result.scalar_one_or_none()

    if not stats:
        return {
            "user_id": user_id,
            "total_points": 0,
            "level": 1
        }

    return {
        "user_id": user_id,
        "total_points": int(stats.total_mined),
        "level": stats.level
    }


@router.post("/add", response_model=AddMiningResponse)
async def add_mining_entry(payload: AddMiningPayload, session: AsyncSession = Depends(get_async_session)):
    """
    Ajoute une entrée MiningHistory,
    met à jour Balance et UserMiningStats.
    """
    user_id = payload.user_id
    points = int(payload.amount)

    if points <= 0:
        raise HTTPException(status_code=400, detail="Le montant doit être positif.")

    now = datetime.utcnow()

    # -------------------------
    # 1️⃣ Ajouter dans MiningHistory
    # -------------------------
    history = MiningHistory(
        user_id=user_id,
        points=points,
        source="mining_claim",
        created_at=now
    )
    session.add(history)

    # -------------------------
    # 2️⃣ Mettre à jour Balance
    # -------------------------
    result = await session.execute(
        select(Balance).where(Balance.user_id == user_id)
    )
    balance_row = result.scalar_one_or_none()

    if balance_row is None:
        balance_row = Balance(user_id=user_id, points=points)
        session.add(balance_row)
    else:
        balance_row.points = (balance_row.points or 0) + points

    # -------------------------
    # 3️⃣ Mettre à jour UserMiningStats
    # -------------------------
    result_stats = await session.execute(
        select(UserMiningStats).where(UserMiningStats.user_id == user_id)
    )
    stats = result_stats.scalar_one_or_none()

    if stats is None:
        total_mined = points
        level = compute_level(total_mined)

        stats = UserMiningStats(
            user_id=user_id,
            total_mined=total_mined,
            level=level
        )
        session.add(stats)

    else:
        stats.total_mined += points
        stats.level = compute_level(stats.total_mined)

    # -------------------------
    # Commit
    # -------------------------
    await session.commit()
    await session.refresh(history)
    await session.refresh(balance_row)
    await session.refresh(stats)

    return {
        "user_id": user_id,
        "added": points,
        "new_balance": int(balance_row.points),
        "total_mined": int(stats.total_mined),
        "level": stats.level,
        "history_id": int(history.id)
    }


@router.post("/reset/{user_id}")
async def reset_user_mining(user_id: int, session: AsyncSession = Depends(get_async_session)):
    """
    Supprime l'historique de mining et réinitialise les stats.
    (Admin / tests uniquement)
    """

    # Supprimer MiningHistory
    await session.execute(
        delete(MiningHistory).where(MiningHistory.user_id == user_id)
    )

    # Réinitialiser Balance
    result = await session.execute(
        select(Balance).where(Balance.user_id == user_id)
    )
    balance_row = result.scalar_one_or_none()

    if balance_row:
        balance_row.points = 0
        session.add(balance_row)

    # Réinitialiser UserMiningStats
    result_stats = await session.execute(
        select(UserMiningStats).where(UserMiningStats.user_id == user_id)
    )
    stats = result_stats.scalar_one_or_none()

    if stats:
        stats.total_mined = 0
        stats.level = 1
        session.add(stats)

    await session.commit()

    return {
        "status": "reset",
        "user_id": user_id
    }