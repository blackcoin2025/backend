# app/routes/minhistory.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from datetime import datetime

from app.database import get_async_session
from app.models import MiningHistory, Balance
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
    Retourne le total des points minés par l'utilisateur et son niveau.
    """
    result = await session.execute(
        select(func.coalesce(func.sum(MiningHistory.points), 0))
        .where(MiningHistory.user_id == user_id)
    )
    total_points = int(result.scalar() or 0)
    level = compute_level(total_points)

    return {
        "user_id": user_id,
        "total_points": total_points,
        "level": level
    }


@router.post("/add", response_model=AddMiningResponse)
async def add_mining_entry(payload: AddMiningPayload, session: AsyncSession = Depends(get_async_session)):
    """
    Ajoute une entrée dans MiningHistory, met à jour la balance,
    et renvoie le nouveau solde + niveau calculé.
    """
    user_id = payload.user_id
    points = int(payload.amount)

    if points <= 0:
        raise HTTPException(status_code=400, detail="Le montant doit être positif.")

    # 1️⃣ Créer l'entrée MiningHistory
    history = MiningHistory(
        user_id=user_id,
        points=points,
        created_at=datetime.utcnow()
    )
    session.add(history)

    # 2️⃣ Mettre à jour la table balance
    q = select(Balance).where(Balance.user_id == user_id)
    result = await session.execute(q)
    balance_row = result.scalar_one_or_none()

    if balance_row is None:
        balance_row = Balance(user_id=user_id, points=points)
        session.add(balance_row)
    else:
        balance_row.points = (balance_row.points or 0) + points

    await session.commit()
    await session.refresh(balance_row)
    await session.refresh(history)

    # 3️⃣ Recalculer total_points (depuis MiningHistory pour cohérence)
    total_res = await session.execute(
        select(func.coalesce(func.sum(MiningHistory.points), 0))
        .where(MiningHistory.user_id == user_id)
    )
    total_points = int(total_res.scalar() or 0)
    level = compute_level(total_points)

    return {
        "user_id": user_id,
        "added": points,
        "new_balance": int(balance_row.points),
        "level": level,
        "history_id": int(history.id)
    }


@router.post("/reset/{user_id}")
async def reset_user_mining(user_id: int, session: AsyncSession = Depends(get_async_session)):
    """
    Supprime l'historique de minage d'un utilisateur et remet sa balance à 0.
    (Réservé aux tests/administration)
    """
    # Supprimer l'historique
    await session.execute(delete(MiningHistory).where(MiningHistory.user_id == user_id))

    # Réinitialiser la balance si elle existe
    q = select(Balance).where(Balance.user_id == user_id)
    result = await session.execute(q)
    balance_row = result.scalar_one_or_none()
    if balance_row:
        balance_row.points = 0
        session.add(balance_row)

    await session.commit()
    return {"status": "reset", "user_id": user_id}
