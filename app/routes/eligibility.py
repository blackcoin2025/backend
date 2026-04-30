from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, distinct
from datetime import datetime, timezone

from app.database import get_async_session
from app.models import (
    User,
    Friend,
    UserPack,
    UserTask,
    Balance,
    UserMiningStats,
)
from app.dependencies.auth import get_current_user

from app.core.cache import cache_get, cache_set

router = APIRouter(prefix="/eligibility", tags=["Airdrop"])


# =========================
# 🧠 UTILS
# =========================
def ensure_utc(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@router.get("/check")
async def check_eligibility(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    user_id = current_user.id
    cache_key = f"eligibility:{user_id}"

    # -------------------------
    # 🔥 CACHE
    # -------------------------
    cached = await cache_get(cache_key)
    if cached:
        return cached

    # =========================
    # FRIENDS
    # =========================
    friends_count = (
        await db.execute(
            select(func.count()).select_from(Friend).where(
                Friend.user_id == user_id,
                Friend.status == "accepted",
            )
        )
    ).scalar() or 0

    # =========================
    # PACK
    # =========================
    has_pack = (
        await db.execute(
            select(UserPack.id).where(
                UserPack.user_id == user_id,
                UserPack.pack_status == "payé",
            )
        )
    ).first() is not None

    # =========================
    # TASKS
    # =========================
    tasks_completed = (
        await db.execute(
            select(func.count(distinct(UserTask.task_id))).where(
                UserTask.user_id == user_id,
                UserTask.completed == True,
            )
        )
    ).scalar() or 0

    # =========================
    # POINTS
    # =========================
    balance = (
        await db.execute(
            select(Balance).where(Balance.user_id == user_id)
        )
    ).scalars().first()

    points = int(balance.points) if balance and balance.points else 0

    # =========================
    # DAYS (FIX TIMEZONE 🔥)
    # =========================
    created_at = ensure_utc(current_user.created_at)
    now = datetime.now(timezone.utc)

    days_active = (now - created_at).days if created_at else 0

    # =========================
    # LEVEL
    # =========================
    stats = (
        await db.execute(
            select(UserMiningStats).where(
                UserMiningStats.user_id == user_id
            )
        )
    ).scalars().first()

    level = stats.level if stats and stats.level else 1

    # =========================
    # RESULT
    # =========================
    result = {
        "friends": friends_count >= 5,
        "pack": has_pack,
        "tasks": tasks_completed >= 50,
        "points": points >= 50_000_000,
        "days": days_active >= 21,
        "level": level >= 5,

        "details": {
            "friends_count": friends_count,
            "tasks_completed": tasks_completed,
            "points": points,
            "days_active": days_active,
            "level": level,
        }
    }

    result["eligible"] = all(result.values())

    # -------------------------
    # 🔥 CACHE SET
    # -------------------------
    await cache_set(cache_key, result, ttl=400)

    return result