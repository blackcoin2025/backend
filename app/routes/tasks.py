# app/routes/tasks.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from decimal import Decimal
import logging

from app.database import get_async_session
from app.models import Task, UserTask, User
from app.schemas import TaskSchema
from app.dependencies.dependency import require_completed_welcome
from app.services.balance_service import credit_balance
from app.services.bonus_service import add_bonus_points

# 🔥 cache
from app.core.cache import cache_get, cache_set, cache_delete

router = APIRouter(tags=["Tasks"])
logger = logging.getLogger(__name__)

TASK_MIN_DURATION = 120


# ============================================================
# 🔹 SCHEMA
# ============================================================
class ValidateTaskRequest(BaseModel):
    code: str = Field(..., min_length=4, max_length=20)


# ============================================================
# 🔹 ALL TASKS (PROTÉGÉ)
# ============================================================
@router.get("/", response_model=List[TaskSchema])
async def get_all_tasks(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_completed_welcome)
):
    result = await db.execute(select(Task))
    return result.scalars().all()


# ============================================================
# 🔹 START TASK
# ============================================================
@router.post("/{task_id}/start")
async def start_task(
    task_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_completed_welcome)
):
    user_id = current_user.id

    task = (await db.execute(select(Task).where(Task.id == task_id))).scalars().first()
    if not task:
        raise HTTPException(404, "Tâche non trouvée")

    user_task = (
        await db.execute(
            select(UserTask).where(
                UserTask.user_id == user_id,
                UserTask.task_id == task_id
            )
        )
    ).scalars().first()

    now = datetime.now(timezone.utc)

    if not user_task:
        user_task = UserTask(
            user_id=user_id,
            task_id=task_id,
            started_at=now
        )
        db.add(user_task)
    else:
        user_task.started_at = now

    await db.commit()

    await cache_delete(f"tasks_pending:{user_id}")

    return {
        "success": True,
        "task_id": task_id,
        "started_at": now
    }


# ============================================================
# 🔹 VALIDATE TASK
# ============================================================
@router.post("/{task_id}/validate")
async def validate_task(
    task_id: int,
    payload: ValidateTaskRequest,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_completed_welcome)
):
    user_id = current_user.id

    task = (await db.execute(select(Task).where(Task.id == task_id))).scalars().first()
    if not task:
        raise HTTPException(404, "Tâche non trouvée")

    # 🔥 sécurité code
    if payload.code.strip() != task.validation_code:
        raise HTTPException(400, "Code invalide")

    user_task = (
        await db.execute(
            select(UserTask).where(
                UserTask.user_id == user_id,
                UserTask.task_id == task_id
            )
        )
    ).scalars().first()

    if not user_task or not user_task.started_at:
        raise HTTPException(400, "Tâche non démarrée")

    if user_task.completed:
        raise HTTPException(409, "Déjà complétée")

    elapsed = (datetime.now(timezone.utc) - user_task.started_at).total_seconds()

    if elapsed < TASK_MIN_DURATION:
        raise HTTPException(
            400,
            f"Attends {TASK_MIN_DURATION - int(elapsed)} sec"
        )

    # 🔥 reward
    total = Decimal(task.reward_points)

    bonus = Decimal("0.05") if total >= Decimal("0.05") else total
    balance = total - bonus

    try:
        user_task.completed = True
        user_task.completed_at = datetime.now(timezone.utc)

        await credit_balance(db, user_id, balance)
        await add_bonus_points(db, user_id, bonus)

        await db.commit()

    except Exception as e:
        await db.rollback()
        logger.error(f"[TASK ERROR] {e}", exc_info=True)
        raise HTTPException(500, "Erreur récompense")

    # 🔥 cache clear
    await cache_delete(f"tasks_pending:{user_id}")
    await cache_delete(f"tasks_count:{user_id}")

    return {
        "success": True,
        "task_id": task_id,
        "reward": {
            "balance": float(balance),
            "bonus": float(bonus),
            "total": float(total)
        }
    }


# ============================================================
# 🔹 COMPLETED COUNT
# ============================================================
@router.get("/me/completed-count")
async def get_completed_tasks_count(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_completed_welcome)
):
    user_id = current_user.id
    cache_key = f"tasks_count:{user_id}"

    cached = await cache_get(cache_key)
    if cached:
        return cached

    result = await db.execute(
        select(UserTask).where(
            UserTask.user_id == user_id,
            UserTask.completed == True
        )
    )

    count = len(result.scalars().all())

    data = {"completed_tasks": count}

    await cache_set(cache_key, data, ttl=30)

    return data


# ============================================================
# 🔹 PENDING TASKS
# ============================================================
@router.get("/me/pending")
async def get_my_pending_tasks(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_completed_welcome)
):
    user_id = current_user.id
    cache_key = f"tasks_pending:{user_id}"

    cached = await cache_get(cache_key)
    if cached:
        return cached

    tasks = (await db.execute(select(Task))).scalars().all()

    user_tasks = (
        await db.execute(
            select(UserTask).where(UserTask.user_id == user_id)
        )
    ).scalars().all()

    user_map = {ut.task_id: ut for ut in user_tasks}

    now = datetime.now(timezone.utc)
    pending = []

    for task in tasks:
        ut = user_map.get(task.id)

        if ut and ut.completed:
            continue

        time_left = 0

        if ut and ut.started_at:
            elapsed = (now - ut.started_at).total_seconds()
            time_left = max(0, TASK_MIN_DURATION - int(elapsed))

        pending.append({
            "id": task.id,
            "title": task.title,
            "reward_points": task.reward_points,
            "time_left": time_left
        })

    await cache_set(cache_key, pending, ttl=30)

    return pending