from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal

from app.database import get_async_session
from app.models import Task, UserTask, User
from app.schemas import TaskSchema
from app.dependencies.auth import get_current_user
from app.services.balance_service import credit_balance
from app.services.bonus_service import add_bonus_points

# 🔥 cache
from app.core.cache import cache_get, cache_set, cache_delete

router = APIRouter(tags=["Tasks"])

TASK_MIN_DURATION = 120


# ------------------------
# SCHEMA
# ------------------------
class ValidateTaskRequest(BaseModel):
    code: str


# ------------------------
# 1. ALL TASKS
# ------------------------
@router.get("/", response_model=List[TaskSchema])
async def get_all_tasks(db: AsyncSession = Depends(get_async_session)):
    result = await db.execute(select(Task))
    return result.scalars().all()


# ------------------------
# 2. START TASK
# ------------------------
@router.post("/{task_id}/start")
async def start_task(
    task_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    user_id = current_user.id

    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalars().first()
    if not task:
        raise HTTPException(404, "Tâche non trouvée")

    result = await db.execute(
        select(UserTask).where(
            UserTask.user_id == user_id,
            UserTask.task_id == task_id
        )
    )
    user_task = result.scalars().first()

    if not user_task:
        user_task = UserTask(
            user_id=user_id,
            task_id=task_id,
            started_at=datetime.utcnow()
        )
        db.add(user_task)
    else:
        user_task.started_at = datetime.utcnow()

    await db.commit()
    await db.refresh(user_task)

    # 🔥 INVALIDATION CACHE
    await cache_delete(f"tasks_pending:{user_id}")

    return {
        "message": "⏳ Tâche démarrée",
        "task_id": task_id,
        "started_at": user_task.started_at
    }


# ------------------------
# 3. VALIDATE TASK
# ------------------------
@router.post("/{task_id}/validate")
async def validate_task(
    task_id: int,
    payload: ValidateTaskRequest,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    user_id = current_user.id

    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalars().first()
    if not task:
        raise HTTPException(404, "Tâche non trouvée")

    if task.validation_code != payload.code:
        raise HTTPException(400, "Code invalide")

    result = await db.execute(
        select(UserTask).where(
            UserTask.user_id == user_id,
            UserTask.task_id == task_id
        )
    )
    user_task = result.scalars().first()

    if not user_task or not user_task.started_at:
        raise HTTPException(400, "Tâche non démarrée")

    if user_task.completed:
        raise HTTPException(400, "Tâche déjà complétée")

    elapsed = (datetime.utcnow() - user_task.started_at).total_seconds()

    if elapsed < TASK_MIN_DURATION:
        raise HTTPException(
            400,
            f"⏱ Attends encore {TASK_MIN_DURATION - int(elapsed)} secondes"
        )

    # 🔥 VALIDATION
    user_task.completed = True
    user_task.completed_at = datetime.utcnow()

    total_points = Decimal(task.reward_points)

    BONUS_FIXED = Decimal("0.05")
    bonus_points = BONUS_FIXED if total_points >= BONUS_FIXED else total_points
    balance_points = total_points - bonus_points

    try:
        await credit_balance(db, user_id, balance_points)
        await add_bonus_points(db, user_id, bonus_points)
    except Exception as e:
        await db.rollback()
        raise HTTPException(500, f"Erreur crédit points: {str(e)}")

    await db.commit()
    await db.refresh(user_task)

    # 🔥 INVALIDATION CACHE
    await cache_delete(f"tasks_pending:{user_id}")
    await cache_delete(f"tasks_count:{user_id}")

    return {
        "message": "✅ Tâche validée",
        "task_id": task_id,
        "reward": {
            "balance": balance_points,
            "bonus": bonus_points,
            "total": total_points
        }
    }


# ------------------------
# 4. COMPLETED COUNT (CACHE)
# ------------------------
@router.get("/me/completed-count")
async def get_completed_tasks_count(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
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

    data = {
        "user_id": user_id,
        "completed_tasks": count
    }

    await cache_set(cache_key, data, ttl=30)

    return data


# ------------------------
# 5. PENDING TASKS (CACHE + OPTIMISÉ)
# ------------------------
@router.get("/me/pending")
async def get_my_pending_tasks(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    user_id = current_user.id
    cache_key = f"tasks_pending:{user_id}"

    cached = await cache_get(cache_key)
    if cached:
        return cached

    tasks_result = await db.execute(select(Task))
    all_tasks = tasks_result.scalars().all()

    user_tasks_result = await db.execute(
        select(UserTask).where(UserTask.user_id == user_id)
    )
    user_tasks = {ut.task_id: ut for ut in user_tasks_result.scalars().all()}

    pending_tasks = []

    for task in all_tasks:
        user_task = user_tasks.get(task.id)

        completed = False
        started_at = None
        time_left = 0

        if user_task:
            completed = user_task.completed
            started_at = user_task.started_at

            if user_task.started_at and not user_task.completed:
                elapsed = (datetime.utcnow() - user_task.started_at).total_seconds()
                time_left = max(0, TASK_MIN_DURATION - int(elapsed))

        if not completed:
            pending_tasks.append({
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "link": task.link,
                "logo": task.logo,
                "reward_points": task.reward_points,
                "completed": completed,
                "started_at": started_at.isoformat() if started_at else None,
                "time_left": time_left
            })

    await cache_set(cache_key, pending_tasks, ttl=30)

    return pending_tasks