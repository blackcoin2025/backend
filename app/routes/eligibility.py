# app/routes/eligibility.py

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, distinct
from datetime import datetime

from app.database import get_async_session
from app.models import (
    User,
    Friend,
    UserPack,
    UserTask,
    Balance,
    UserMiningStats,  # ✅ AJOUT
)
from app.dependencies.auth import get_current_user

router = APIRouter(prefix="/eligibility", tags=["Airdrop"])


@router.get("/check")
async def check_eligibility(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    user_id = current_user.id

    # =========================
    # 1️⃣ FRIENDS (>=5)
    # =========================
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

    # =========================
    # 2️⃣ PACK PAYÉ
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
    # 3️⃣ 50 TASKS DISTINCT
    # =========================
    tasks_completed = (
        await db.execute(
            select(func.count(distinct(UserTask.task_id)))
            .where(
                UserTask.user_id == user_id,
                UserTask.completed == True,
            )
        )
    ).scalar() or 0

    # =========================
    # 4️⃣ POINTS
    # =========================
    balance = (
        await db.execute(
            select(Balance).where(Balance.user_id == user_id)
        )
    ).scalars().first()

    points = balance.points if balance else 0

    # =========================
    # 5️⃣ DAYS ACTIVE
    # =========================
    days_active = (datetime.utcnow() - current_user.created_at).days

    # =========================
    # 6️⃣ LEVEL (Mining)
    # =========================
    stats = (
        await db.execute(
            select(UserMiningStats).where(
                UserMiningStats.user_id == user_id
            )
        )
    ).scalars().first()

    level = stats.level if stats else 1

    # =========================
    # RESULT
    # =========================
    result = {
        "friends": friends_count >= 5,
        "pack": has_pack,
        "tasks": tasks_completed >= 50,
        "points": points >= 50_000_000,
        "days": days_active >= 21,
        "level": level >= 5,  # ✅ NOUVEAU CRITÈRE

        "details": {
            "friends_count": friends_count,
            "tasks_completed": tasks_completed,
            "points": int(points),
            "days_active": days_active,
            "level": level,
        }
    }

    # =========================
    # ELIGIBILITY FINAL
    # =========================
    result["eligible"] = all([
        result["friends"],
        result["pack"],
        result["tasks"],
        result["points"],
        result["days"],
        result["level"],  # ✅ AJOUT
    ])

    return result