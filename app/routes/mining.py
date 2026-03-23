# app/routes/mining.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta

from app.database import get_async_session
from app.models import User, MiningHistory, MineTimer, UserMiningStats
from app.services.balance_service import credit_balance

router = APIRouter(tags=["Mining"])

# ⚡ Config
COOLDOWN_HOURS = 24
POINTS_PER_CYCLE = 200

# 🎯 Level thresholds (progressif)
LEVEL_THRESHOLDS = [
    0,
    1000,
    3000,
    6000,
    10000,
    15000,
    25000,
    40000,
    60000
]


def calculate_level(total_mined: int) -> int:
    level = 1
    for i, threshold in enumerate(LEVEL_THRESHOLDS, start=1):
        if total_mined >= threshold:
            level = i
        else:
            break
    return level


# -----------------------------
# Démarrer un minage
# -----------------------------
@router.post("/start/{user_id}")
async def start_mining(user_id: int, session: AsyncSession = Depends(get_async_session)):

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    now = datetime.utcnow()

    result_timer = await session.execute(
        select(MineTimer).where(
            MineTimer.user_id == user_id,
            MineTimer.claimed == False
        )
    )
    active_timer = result_timer.scalar_one_or_none()

    if active_timer and active_timer.end_time > now:
        remaining = active_timer.end_time - now
        minutes, seconds = divmod(remaining.total_seconds(), 60)

        raise HTTPException(
            status_code=400,
            detail=f"Mining already in progress. Remaining time: {int(minutes):02d}:{int(seconds):02d}"
        )

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
        "mining_timer_id": new_timer.id,
        "expires_at": new_timer.end_time.isoformat(),
        "total_cycle_ms": COOLDOWN_HOURS * 3600 * 1000
    }


# -----------------------------
# Statut du minage
# -----------------------------
@router.get("/status/{user_id}")
async def mining_status(user_id: int, session: AsyncSession = Depends(get_async_session)):

    now = datetime.utcnow()

    result_timer = await session.execute(
        select(MineTimer).where(
            MineTimer.user_id == user_id,
            MineTimer.claimed == False
        )
    )
    active_timer = result_timer.scalar_one_or_none()

    # 🔥 récupérer les stats
    result_stats = await session.execute(
        select(UserMiningStats).where(UserMiningStats.user_id == user_id)
    )
    stats = result_stats.scalar_one_or_none()

    level = stats.level if stats else 1
    total_mined = stats.total_mined if stats else 0

    if not active_timer:
        return {
            "status": "idle",
            "level": level,
            "total_mined": total_mined
        }

    if active_timer.end_time > now:
        remaining = active_timer.end_time - now

        return {
            "status": "running",
            "remaining_time_ms": int(remaining.total_seconds() * 1000),
            "total_cycle_ms": COOLDOWN_HOURS * 3600 * 1000,
            "level": level,
            "total_mined": total_mined
        }

    return {
        "status": "ready_to_claim",
        "level": level,
        "total_mined": total_mined
    }


# -----------------------------
# Claim minage
# -----------------------------
@router.post("/claim/{user_id}")
async def claim_mining(user_id: int, session: AsyncSession = Depends(get_async_session)):

    now = datetime.utcnow()

    result_timer = await session.execute(
        select(MineTimer).where(
            MineTimer.user_id == user_id,
            MineTimer.claimed == False
        )
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

    points_earned = POINTS_PER_CYCLE

    # -------------------------
    # Historique mining
    # -------------------------
    new_entry = MiningHistory(
        user_id=user_id,
        points=points_earned,
        source="mining_claim",
        created_at=now
    )
    session.add(new_entry)

    # -------------------------
    # Balance globale
    # -------------------------
    new_balance = await credit_balance(session, user_id, points_earned)

    # -------------------------
    # Mining stats
    # -------------------------
    result_stats = await session.execute(
        select(UserMiningStats).where(UserMiningStats.user_id == user_id)
    )
    stats = result_stats.scalar_one_or_none()

    if not stats:
        stats = UserMiningStats(
            user_id=user_id,
            total_mined=0,
            level=1
        )
        session.add(stats)
        await session.flush()

    stats.total_mined += points_earned

    # ✅ Nouveau calcul level (progressif)
    stats.level = calculate_level(stats.total_mined)

    # -------------------------
    # Finalisation
    # -------------------------
    active_timer.claimed = True

    await session.commit()
    await session.refresh(new_entry)

    return {
        "status": "success",
        "points_earned": points_earned,
        "new_balance": new_balance,
        "total_mined": stats.total_mined,
        "level": stats.level
    }


# -----------------------------
# Historique
# -----------------------------
@router.get("/history/{user_id}")
async def get_mining_history(user_id: int, session: AsyncSession = Depends(get_async_session)):

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

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
                "id": h.id,
                "points": h.points,
                "source": h.source,
                "created_at": h.created_at.isoformat() if h.created_at else None
            }
            for h in history
        ]
    }