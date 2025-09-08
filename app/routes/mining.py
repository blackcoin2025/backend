# app/routes/mining.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta

from app.database import get_async_session
from app.models import User, MiningHistory, MineTimer
from app.services.balance_service import credit_balance  # ✅ ajout

router = APIRouter(tags=["Mining"])

# ⚡ Config : 1 cycle de minage dure 24 heures
COOLDOWN_HOURS = 24
POINTS_PER_CYCLE = 200


# -----------------------------
# Démarrer un minage
# -----------------------------
@router.post("/start/{user_id}")
async def start_mining(user_id: int, session: AsyncSession = Depends(get_async_session)):
    # Vérifier que l'utilisateur existe
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    now = datetime.utcnow()

    # Vérifier si un minage est déjà en cours
    result_timer = await session.execute(
        select(MineTimer).where(MineTimer.user_id == user_id, MineTimer.claimed == False)
    )
    active_timer = result_timer.scalar_one_or_none()

    if active_timer and active_timer.end_time > now:
        remaining = active_timer.end_time - now
        minutes, seconds = divmod(remaining.total_seconds(), 60)
        raise HTTPException(
            status_code=400,
            detail=f"Mining already in progress. Remaining time: {int(minutes):02d}:{int(seconds):02d}"
        )

    # Créer un nouveau timer de minage (24h)
    end_time = now + timedelta(hours=COOLDOWN_HOURS)
    new_timer = MineTimer(
        user_id=user_id,
        start_time=now,
        end_time=end_time,
        claimed=False
    )
    session.add(new_timer)
    await session.commit()
    await session.refresh(new_timer)

    return {
        "status": "authorized",
        "user_id": user_id,
        "mining_timer_id": new_timer.id,
        "expires_at": new_timer.end_time.isoformat(),
        "total_cycle_ms": int(COOLDOWN_HOURS * 3600 * 1000)  # ✅ durée totale
    }


# -----------------------------
# Vérifier l'état du minage
# -----------------------------
@router.get("/status/{user_id}")
async def mining_status(user_id: int, session: AsyncSession = Depends(get_async_session)):
    now = datetime.utcnow()
    result_timer = await session.execute(
        select(MineTimer).where(MineTimer.user_id == user_id, MineTimer.claimed == False)
    )
    active_timer = result_timer.scalar_one_or_none()

    if not active_timer:
        return {"status": "idle", "message": "No mining in progress"}

    if active_timer.end_time > now:
        remaining = active_timer.end_time - now
        minutes, seconds = divmod(remaining.total_seconds(), 60)
        return {
            "status": "running",
            "remaining_time": f"{int(minutes):02d}:{int(seconds):02d}",
            "remaining_time_ms": int(remaining.total_seconds() * 1000),  # ✅ ms restantes
            "total_cycle_ms": int(COOLDOWN_HOURS * 3600 * 1000)          # ✅ durée totale
        }

    return {"status": "ready_to_claim", "message": "Mining completed, ready to claim rewards"}


# -----------------------------
# Réclamer les récompenses
# -----------------------------
@router.post("/claim/{user_id}")
async def claim_mining(user_id: int, session: AsyncSession = Depends(get_async_session)):
    now = datetime.utcnow()
    result_timer = await session.execute(
        select(MineTimer).where(MineTimer.user_id == user_id, MineTimer.claimed == False)
    )
    active_timer = result_timer.scalar_one_or_none()

    if not active_timer:
        raise HTTPException(status_code=400, detail="No mining session to claim")

    if active_timer.end_time > now:
        remaining = active_timer.end_time - now
        minutes, seconds = divmod(remaining.total_seconds(), 60)
        raise HTTPException(
            status_code=400,
            detail=f"Mining still in progress. Remaining time: {int(minutes):02d}:{int(seconds):02d}"
        )

    # ✅ Points gagnés : 200
    points_earned = POINTS_PER_CYCLE

    # Créer l'entrée MiningHistory
    new_entry = MiningHistory(
        user_id=user_id,
        points=points_earned,
        source="mining_claim",
        created_at=now
    )
    session.add(new_entry)

    # ✅ Créditer la balance avec les points
    new_total = await credit_balance(session, user_id, points_earned)

    # Marquer le timer comme "claimed"
    active_timer.claimed = True

    await session.commit()
    await session.refresh(new_entry)

    return {
        "status": "success",
        "user_id": user_id,
        "mining_entry_id": new_entry.id,
        "points_earned": new_entry.points,
        "new_balance": new_total
    }


# -----------------------------
# Historique du minage
# -----------------------------
@router.get("/history/{user_id}")
async def get_mining_history(user_id: int, session: AsyncSession = Depends(get_async_session)):
    # Vérifier que l'utilisateur existe
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Récupérer l'historique
    result_hist = await session.execute(
        select(MiningHistory)
        .where(MiningHistory.user_id == user_id)
        .order_by(MiningHistory.created_at.desc())
    )
    history = result_hist.scalars().all()

    return {
        "user_id": user_id,
        "history": [
            {
                "id": entry.id,
                "points": entry.points,
                "source": getattr(entry, "source", None),
                "created_at": entry.created_at.isoformat() if entry.created_at else None
            }
            for entry in history
        ]
    }
