# app/services/pack_service.py

from datetime import datetime, timedelta, date
from typing import Optional, List

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Wallet, UserPack, DailyTask, UserDailyTask, User
from app.services.wallet_service import credit_wallet


# =========================================================
# DOMAIN LOGIC (AUCUNE DB ICI)
# =========================================================

def compute_pack_state(
    *,
    total_tasks: int,
    completed_today: int,
    last_claim_date: Optional[datetime],
) -> tuple[str, bool, bool]:
    """
    Retourne: (status, is_unlocked, all_tasks_completed)
    """

    today = date.today()

    if total_tasks == 0:
        return "payé", False, False

    if completed_today < total_tasks:
        return "en_cours", False, False

    # Toutes les tâches du jour complétées
    if last_claim_date and last_claim_date.date() == today:
        return "en_attente", False, False

    return "à_reclamer", True, True


# =========================================================
# QUERIES
# =========================================================

async def get_user_pack(db: AsyncSession, user_id: int, user_pack_id: int) -> UserPack:
    result = await db.execute(
        select(UserPack)
        .options(selectinload(UserPack.user))
        .where(UserPack.id == user_pack_id, UserPack.user_id == user_id)
    )
    pack = result.scalars().first()

    if not pack:
        raise HTTPException(404, "Pack introuvable")

    return pack


async def count_tasks(db: AsyncSession, pack_id: int) -> int:
    return (
        await db.scalar(
            select(func.count()).select_from(UserDailyTask)
            .where(UserDailyTask.user_pack_id == pack_id)
        )
    ) or 0


async def count_completed_today(db: AsyncSession, pack_id: int) -> int:
    today = date.today()

    return (
        await db.scalar(
            select(func.count()).select_from(UserDailyTask)
            .where(
                UserDailyTask.user_pack_id == pack_id,
                UserDailyTask.completed == True,
                func.date(UserDailyTask.completed_at) == today,
            )
        )
    ) or 0


# =========================================================
# CORE SERVICE
# =========================================================

async def refresh_pack_state(user_pack: UserPack, db: AsyncSession):
    total_tasks = await count_tasks(db, user_pack.id)
    completed_today = await count_completed_today(db, user_pack.id)

    status, unlocked, done = compute_pack_state(
        total_tasks=total_tasks,
        completed_today=completed_today,
        last_claim_date=user_pack.last_claim_date,
    )

    user_pack.pack_status = status
    user_pack.is_unlocked = unlocked
    user_pack.all_tasks_completed = done


# =========================================================
# START PACK
# =========================================================

async def start_pack(user_id: int, user_pack_id: int, db: AsyncSession):

    pack = await get_user_pack(db, user_id, user_pack_id)

    if pack.pack_status not in (None, "payé", "en_cours"):
        raise HTTPException(400, f"Impossible de démarrer depuis '{pack.pack_status}'")

    # récupérer tâches du pack
    tasks = (
        await db.execute(select(DailyTask).where(DailyTask.pack_id == pack.pack_id))
    ).scalars().all()

    if not tasks:
        raise HTTPException(404, "Aucune tâche définie")

    # créer user tasks si pas existantes
    existing = (
        await db.execute(select(UserDailyTask).where(UserDailyTask.user_pack_id == pack.id))
    ).scalars().all()

    if not existing:
        for t in tasks:
            db.add(UserDailyTask(
                user_id=user_id,
                task_id=t.id,
                user_pack_id=pack.id,
                completed=False,
                completed_at=None
            ))

    pack.start_date = datetime.utcnow()
    pack.current_day = date.today()

    await refresh_pack_state(pack, db)
    await db.commit()

    return pack


# =========================================================
# COMPLETE TASK
# =========================================================

async def complete_user_daily_task(user_id: int, task_id: int, db: AsyncSession):

    task = (
        await db.execute(
            select(UserDailyTask).where(
                UserDailyTask.id == task_id,
                UserDailyTask.user_id == user_id,
            )
        )
    ).scalars().first()

    if not task:
        raise HTTPException(404, "Tâche introuvable")

    now = datetime.utcnow()

    if task.completed and task.completed_at.date() == now.date():
        raise HTTPException(400, "Déjà complétée aujourd'hui")

    task.completed = True
    task.completed_at = now

    pack = await db.get(UserPack, task.user_pack_id)
    await refresh_pack_state(pack, db)

    await db.commit()

    return {
        "status": pack.pack_status,
        "unlocked": pack.is_unlocked,
        "completed": pack.all_tasks_completed,
    }


# =========================================================
# CLAIM REWARD
# =========================================================

async def claim_pack_reward(user_id: int, user_pack_id: int, db: AsyncSession):

    pack = await get_user_pack(db, user_id, user_pack_id)

    await refresh_pack_state(pack, db)

    if not pack.is_unlocked:
        raise HTTPException(400, "Complète d'abord les tâches")

    now = datetime.utcnow()

    if pack.last_claim_date and (now - pack.last_claim_date) < timedelta(hours=24):
        raise HTTPException(400, "Réclamation trop tôt")

    user = pack.user or await db.get(User, pack.user_id)

    await credit_wallet(user, float(pack.daily_earnings), db)

    pack.total_earned = (pack.total_earned or 0) + float(pack.daily_earnings)
    pack.last_claim_date = now

    await refresh_pack_state(pack, db)
    await db.commit()

    wallet = (
        await db.execute(select(Wallet).where(Wallet.user_id == user.id))
    ).scalars().first()


    return {
        "message": "Réclamation effectuée ✅",
        "claimed_amount": float(pack.daily_earnings),
        "wallet_balance": float(wallet.amount) if wallet else 0.0,
        "next_claim_available": (now + timedelta(hours=24)).isoformat(),
    }
