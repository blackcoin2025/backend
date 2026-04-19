from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta

from app.database import get_async_session
from app.models import MiningHistory, MineTimer, UserMiningStats
from app.services.balance_service import credit_balance

# 🔒 cache + redis health + lock
from app.core.cache import (
    cache_get,
    cache_set,
    cache_delete,
    cache_lock,
    is_redis_available
)

router = APIRouter(tags=["Mining"])

# ⚡ Config
COOLDOWN_HOURS = 24
POINTS_PER_CYCLE = 200

LEVEL_THRESHOLDS = [
    0, 1000, 3000, 6000, 10000, 15000, 25000, 40000, 60000
]


# =========================
# 🔒 HARD CHECK REDIS
# =========================
async def require_redis():
    ok = await is_redis_available()
    if not ok:
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable (Redis required)"
        )


# -----------------------------
# LEVEL CALC
# -----------------------------
def calculate_level(total_mined: int) -> int:
    level = 1
    for i, threshold in enumerate(LEVEL_THRESHOLDS, start=1):
        if total_mined >= threshold:
            level = i
        else:
            break
    return level


# -----------------------------
# START MINING
# -----------------------------
@router.post("/start/{user_id}")
async def start_mining(
    user_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    await require_redis()  # 🔒 HARD BLOCK

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
            detail=f"Mining already in progress: {int(minutes):02d}:{int(seconds):02d}"
        )

    new_timer = MineTimer(
        user_id=user_id,
        start_time=now,
        end_time=now + timedelta(hours=COOLDOWN_HOURS),
        claimed=False
    )

    session.add(new_timer)
    await session.commit()
    await session.refresh(new_timer)

    await cache_delete(f"mining_status:{user_id}")

    return {
        "status": "authorized",
        "mining_timer_id": new_timer.id,
        "expires_at": new_timer.end_time.isoformat(),
        "total_cycle_ms": COOLDOWN_HOURS * 3600 * 1000
    }


# -----------------------------
# STATUS
# -----------------------------
@router.get("/status/{user_id}")
async def mining_status(
    user_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    await require_redis()  # 🔒 HARD BLOCK

    cache_key = f"mining_status:{user_id}"

    cached = await cache_get(cache_key)
    if cached:
        return cached

    now = datetime.utcnow()

    result_timer = await session.execute(
        select(MineTimer).where(
            MineTimer.user_id == user_id,
            MineTimer.claimed == False
        )
    )
    active_timer = result_timer.scalar_one_or_none()

    result_stats = await session.execute(
        select(UserMiningStats).where(UserMiningStats.user_id == user_id)
    )
    stats = result_stats.scalar_one_or_none()

    level = stats.level if stats else 1
    total_mined = stats.total_mined if stats else 0

    if not active_timer:
        data = {
            "status": "idle",
            "level": level,
            "total_mined": total_mined
        }

    elif active_timer.end_time > now:
        remaining = active_timer.end_time - now
        data = {
            "status": "running",
            "remaining_time_ms": int(remaining.total_seconds() * 1000),
            "total_cycle_ms": COOLDOWN_HOURS * 3600 * 1000,
            "level": level,
            "total_mined": total_mined
        }

    else:
        data = {
            "status": "ready_to_claim",
            "level": level,
            "total_mined": total_mined
        }

    await cache_set(cache_key, data, ttl=10)

    return data


# -----------------------------
# CLAIM (ULTRA SAFE)
# -----------------------------
@router.post("/claim/{user_id}")
async def claim_mining(
    user_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    await require_redis()  # 🔒 HARD BLOCK

    lock_key = f"lock:claim:{user_id}"

    # 🔒 Redis lock obligatoire
    locked = await cache_lock(lock_key, ttl=10)

    if not locked:
        raise HTTPException(
            status_code=429,
            detail="Action already in progress"
        )

    try:
        now = datetime.utcnow()

        result_timer = await session.execute(
            select(MineTimer)
            .where(
                MineTimer.user_id == user_id,
                MineTimer.claimed == False
            )
            .with_for_update()
        )
        active_timer = result_timer.scalar_one_or_none()

        if not active_timer:
            raise HTTPException(status_code=400, detail="No mining session")

        if active_timer.end_time > now:
            raise HTTPException(status_code=400, detail="Mining not finished")

        if active_timer.claimed:
            raise HTTPException(status_code=400, detail="Already claimed")

        points_earned = POINTS_PER_CYCLE

        result_stats = await session.execute(
            select(UserMiningStats)
            .where(UserMiningStats.user_id == user_id)
            .with_for_update()
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
        stats.level = calculate_level(stats.total_mined)

        new_entry = MiningHistory(
            user_id=user_id,
            points=points_earned,
            source="mining_claim",
            created_at=now
        )
        session.add(new_entry)

        new_balance = await credit_balance(session, user_id, points_earned)

        active_timer.claimed = True

        await session.commit()

        await cache_delete(f"mining_status:{user_id}")

        return {
            "status": "success",
            "points_earned": points_earned,
            "new_balance": new_balance,
            "total_mined": stats.total_mined,
            "level": stats.level
        }

    finally:
        await cache_delete(lock_key)


# -----------------------------
# HISTORY
# -----------------------------
@router.get("/history/{user_id}")
async def get_mining_history(
    user_id: int,
    limit: int = 20,
    session: AsyncSession = Depends(get_async_session)
):
    await require_redis()  # 🔒 HARD BLOCK

    result_hist = await session.execute(
        select(MiningHistory)
        .where(MiningHistory.user_id == user_id)
        .order_by(MiningHistory.created_at.desc())
        .limit(limit)
    )

    history = result_hist.scalars().all()

    return {
        "user_id": user_id,
        "count": len(history),
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