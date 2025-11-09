# app/services/pack_service.py

import asyncio
from datetime import datetime, timedelta, date
from typing import Optional, List

from fastapi import HTTPException
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import func

from app.models import Wallet
from app.database import AsyncSessionLocal
from app.models import Action, UserPack, DailyTask, UserDailyTask, User
from app.services.wallet_service import credit_wallet


# -----------------------------------------------------------------
# 🔍 Mise à jour du statut d'un UserPack
# -----------------------------------------------------------------
async def update_pack_status(user_pack: UserPack, db: AsyncSession) -> UserPack:
    """
    Met à jour le statut d’un pack utilisateur en fonction des tâches journalières.
    """
    now = datetime.utcnow()
    today = now.date()

    if not user_pack.start_date:
        user_pack.pack_status = "payé"
        user_pack.is_unlocked = False
        user_pack.all_tasks_completed = False
        await db.commit()
        await db.refresh(user_pack)
        return user_pack

    total_tasks = await db.scalar(
        select(func.count()).select_from(UserDailyTask).where(
            UserDailyTask.user_pack_id == user_pack.id
        )
    ) or 0

    if total_tasks == 0:
        user_pack.pack_status = "payé"
        user_pack.is_unlocked = False
        user_pack.all_tasks_completed = False
        await db.commit()
        await db.refresh(user_pack)
        return user_pack

    completed_today = await db.scalar(
        select(func.count()).select_from(UserDailyTask).where(
            UserDailyTask.user_pack_id == user_pack.id,
            UserDailyTask.completed == True,
            func.date(UserDailyTask.completed_at) == today
        )
    ) or 0

    if completed_today >= total_tasks:
        if user_pack.last_claim_date and user_pack.last_claim_date.date() == today:
            user_pack.pack_status = "en_attente"
            user_pack.is_unlocked = False
            user_pack.all_tasks_completed = False
        else:
            user_pack.pack_status = "à_reclamer"
            user_pack.is_unlocked = True
            user_pack.all_tasks_completed = True
    else:
        user_pack.pack_status = "en_cours"
        user_pack.is_unlocked = False
        user_pack.all_tasks_completed = False

    await db.commit()
    await db.refresh(user_pack)
    return user_pack


# -----------------------------------------------------------------
# 🚀 Démarrer un pack
# -----------------------------------------------------------------
async def start_pack(user_id: int, user_pack_id: int, db: AsyncSession) -> UserPack:
    result = await db.execute(
        select(UserPack).where(UserPack.id == user_pack_id, UserPack.user_id == user_id)
    )
    user_pack: Optional[UserPack] = result.scalars().first()

    if not user_pack:
        raise HTTPException(status_code=404, detail="Pack introuvable ou non associé à cet utilisateur")

    if user_pack.pack_status not in (None, "payé", "en_cours"):
        raise HTTPException(status_code=400, detail=f"Ce pack ne peut pas être démarré depuis l'état '{user_pack.pack_status}'")

    task_result = await db.execute(select(DailyTask).where(DailyTask.pack_id == user_pack.pack_id))
    daily_tasks: List[DailyTask] = task_result.scalars().all()

    if not daily_tasks:
        raise HTTPException(status_code=404, detail="Aucune tâche journalière définie pour ce pack")

    existing_q = await db.execute(
        select(UserDailyTask).where(UserDailyTask.user_pack_id == user_pack.id)
    )
    existing_tasks = existing_q.scalars().all()

    if not existing_tasks:
        for t in daily_tasks:
            db.add(UserDailyTask(
                user_id=user_id,
                task_id=t.id,
                user_pack_id=user_pack.id,
                completed=False,
                completed_at=None
            ))

    user_pack.start_date = datetime.utcnow()
    user_pack.pack_status = "en_cours"
    user_pack.is_unlocked = False
    user_pack.all_tasks_completed = False
    user_pack.current_day = datetime.utcnow().date()

    await db.commit()
    await update_pack_status(user_pack, db)
    return user_pack


# -----------------------------------------------------------------
# ✅ Compléter une tâche utilisateur
# -----------------------------------------------------------------
async def complete_user_daily_task(user_id: int, user_daily_task_id: int, db: AsyncSession):
    result = await db.execute(
        select(UserDailyTask).where(
            UserDailyTask.id == user_daily_task_id,
            UserDailyTask.user_id == user_id
        )
    )
    user_task = result.scalars().first()
    if not user_task:
        raise HTTPException(status_code=404, detail="Tâche introuvable")

    now = datetime.utcnow()
    if user_task.completed and user_task.completed_at and user_task.completed_at.date() == now.date():
        raise HTTPException(status_code=400, detail="Tâche déjà complétée aujourd'hui")

    user_task.completed = True
    user_task.completed_at = now
    db.add(user_task)
    await db.commit()
    await db.refresh(user_task)

    user_pack = await db.get(UserPack, user_task.user_pack_id)
    if not user_pack:
        raise HTTPException(status_code=404, detail="Pack utilisateur introuvable")

    await update_pack_status(user_pack, db)

    return {
        "message": "Tâche complétée avec succès",
        "pack_status": user_pack.pack_status,
        "is_unlocked": user_pack.is_unlocked,
        "all_tasks_completed": user_pack.all_tasks_completed
    }


# -----------------------------------------------------------------
# 💰 Réclamer la récompense quotidienne
# -----------------------------------------------------------------
async def claim_pack_reward(user_id: int, user_pack_id: int, db: AsyncSession):
    result = await db.execute(
        select(UserPack).options(selectinload(UserPack.user)).where(
            UserPack.id == user_pack_id, UserPack.user_id == user_id
        )
    )
    user_pack = result.scalars().first()
    if not user_pack:
        raise HTTPException(status_code=404, detail="Pack introuvable")

    await update_pack_status(user_pack, db)

    if not user_pack.is_unlocked:
        raise HTTPException(status_code=400, detail="Pack verrouillé : complète d'abord toutes les tâches du jour.")

    incomplete = await db.scalar(
        select(func.count()).select_from(UserDailyTask).where(
            UserDailyTask.user_pack_id == user_pack.id,
            (UserDailyTask.completed == False)
            | (func.date(UserDailyTask.completed_at) != date.today())
        )
    ) or 0

    if incomplete > 0:
        raise HTTPException(status_code=400, detail="Toutes les tâches ne sont pas encore terminées")

    now = datetime.utcnow()
    if user_pack.last_claim_date and (now - user_pack.last_claim_date) < timedelta(hours=24):
        remaining = timedelta(hours=24) - (now - user_pack.last_claim_date)
        h, m = divmod(int(remaining.total_seconds()) // 60, 60)
        raise HTTPException(status_code=400, detail=f"⏳ Attends encore {h}h{m:02d} avant la prochaine réclamation.")

    user_obj = user_pack.user or (await db.get(User, user_pack.user_id))
    if not user_obj:
        raise HTTPException(status_code=500, detail="Impossible de charger l’utilisateur")

    await credit_wallet(user_obj, float(user_pack.daily_earnings), db)

    wallet_result = await db.execute(select(Wallet).where(Wallet.user_id == user_obj.id))
    wallet = wallet_result.scalars().first()
    wallet_balance = float(wallet.amount) if wallet else 0.0

    user_pack.total_earned = (user_pack.total_earned or 0) + float(user_pack.daily_earnings)
    user_pack.last_claim_date = now
    user_pack.all_tasks_completed = False
    user_pack.is_unlocked = False
    user_pack.pack_status = "en_attente"

    await db.commit()
    await update_pack_status(user_pack, db)

    return {
        "status": "success",
        "message": f"✅ Vous avez réclamé {user_pack.daily_earnings:.5f} BKC avec succès !",
        "claimed_amount": float(user_pack.daily_earnings),
        "wallet_balance": wallet_balance,
        "next_claim_available": (now + timedelta(hours=24)).isoformat(),
        "timestamp": datetime.utcnow().isoformat()
    }
