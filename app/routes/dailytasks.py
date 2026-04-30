from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_async_session
from app.models import (
    UserPack,
    DailyTask,
    UserDailyTask,
    User
)
from app.dependencies.auth import get_current_user

from app.core.cache import cache_get, cache_set, cache_delete

# 🔥 IMPORT DU SERVICE CENTRAL
from app.services.pack_service import claim_pack_reward

router = APIRouter(prefix="/actions/packs", tags=["DailyTasks"])


# =========================
# GET DAILY TASKS
# =========================
@router.get("/{user_pack_id}/daily-tasks")
async def get_user_pack_daily_tasks(
    user_pack_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    cache_key = f"pack_tasks:{current_user.id}:{user_pack_id}"

    cached = await cache_get(cache_key)
    if cached:
        return cached

    result = await db.execute(
        select(UserPack).where(
            UserPack.id == user_pack_id,
            UserPack.user_id == current_user.id
        )
    )
    user_pack = result.scalars().first()

    if not user_pack:
        raise HTTPException(404, "Pack introuvable")

    existing = await db.execute(
        select(UserDailyTask).where(UserDailyTask.user_pack_id == user_pack.id)
    )
    user_tasks = existing.scalars().all()

    # INIT tasks si vide
    if not user_tasks:
        base_q = await db.execute(
            select(DailyTask).where(DailyTask.pack_id == user_pack.pack_id)
        )
        base_tasks = base_q.scalars().all()

        for t in base_tasks:
            db.add(UserDailyTask(
                user_id=current_user.id,
                task_id=t.id,
                user_pack_id=user_pack.id,
                completed=False,
            ))

        await db.commit()

    joined = await db.execute(
        select(UserDailyTask, DailyTask)
        .join(DailyTask, DailyTask.id == UserDailyTask.task_id)
        .where(UserDailyTask.user_pack_id == user_pack.id)
    )

    tasks = []
    for ut, dt in joined.all():
        tasks.append({
            "id": ut.id,
            "task_id": ut.task_id,
            "completed": ut.completed,
            "started_at": ut.started_at.isoformat() if ut.started_at else None,
            "description": dt.description,
            "platform": dt.platform,
            "video_url": dt.video_url,
        })

    await cache_set(cache_key, tasks, ttl=5)

    return tasks


# =========================
# START TASK
# =========================
@router.post("/daily-tasks/{task_id}/start")
async def start_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    result = await db.execute(
        select(UserDailyTask).where(
            UserDailyTask.id == task_id,
            UserDailyTask.user_id == current_user.id
        )
    )
    task = result.scalars().first()

    if not task:
        raise HTTPException(404, "Tâche introuvable")

    if task.started_at:
        return {
            "status": "already_started",
            "started_at": task.started_at.isoformat()
        }

    task.started_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(task)

    await cache_delete(f"pack_tasks:{current_user.id}:{task.user_pack_id}")

    return {
        "status": "started",
        "started_at": task.started_at.isoformat()
    }


# =========================
# COMPLETE TASK (NO REWARD ❌)
# =========================
@router.post("/daily-tasks/{task_id}/complete")
async def complete_task(
    task_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    res = await db.execute(
        select(UserDailyTask).where(
            UserDailyTask.id == task_id,
            UserDailyTask.user_id == current_user.id
        )
    )
    task = res.scalars().first()

    if not task:
        raise HTTPException(404, "Tâche introuvable")

    if not task.started_at:
        raise HTTPException(400, "Task non démarrée")

    elapsed = (
        datetime.now(timezone.utc) - task.started_at
    ).total_seconds()

    if elapsed < 3600:
        raise HTTPException(400, "Temps non écoulé")

    if task.completed:
        return {
            "message": "Déjà complétée",
            "task_id": task.id
        }

    # ✅ JUSTE COMPLETE (PAS DE REWARD)
    task.completed = True
    task.completed_at = datetime.now(timezone.utc)

    await db.commit()

    await cache_delete(f"pack_tasks:{current_user.id}:{task.user_pack_id}")

    return {
        "message": "✅ Tâche complétée",
        "task_id": task.id,
        "completed_at": task.completed_at.isoformat()
    }


# =========================
# CLAIM PACK REWARD (CENTRALISÉ)
# =========================
@router.post("/{user_pack_id}/claim")
async def claim_pack(
    user_pack_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    result = await claim_pack_reward(
        user_id=current_user.id,
        user_pack_id=user_pack_id,
        db=db
    )

    # 🔄 invalider cache après claim
    await cache_delete(f"pack_tasks:{current_user.id}:{user_pack_id}")

    return result