from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_async_session
from app.models import Action, UserPack, User, DailyTask, UserDailyTask
from app.schemas import ActionBase, ActionSchema, UserPackSchema
from app.dependencies.auth import get_current_user
from app.services.cash_service import debit_real_cash
from app.services.pack_service import start_pack, claim_pack_reward

# 🔥 cache
from app.core.cache import cache_get, cache_set, cache_delete

router = APIRouter(prefix="/actions", tags=["Actions"])


# -----------------------
# CREATE ACTION
# -----------------------
@router.post("/", response_model=ActionSchema)
async def create_action(
    payload: ActionBase,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    new_action = Action(**payload.dict())
    db.add(new_action)
    await db.commit()
    await db.refresh(new_action)
    return new_action


# -----------------------
# LIST ALL
# -----------------------
@router.get("/", response_model=List[ActionSchema])
async def list_actions(db: AsyncSession = Depends(get_async_session)):
    result = await db.execute(select(Action))
    return result.scalars().all()


# -----------------------
# CATEGORY (CACHE)
# -----------------------
@router.get("/category/{category}", response_model=List[ActionSchema])
async def list_actions_by_category(category: str, db: AsyncSession = Depends(get_async_session)):
    cache_key = f"actions_category:{category}"

    cached = await cache_get(cache_key)
    if cached:
        return cached

    result = await db.execute(select(Action).where(Action.category == category))
    data = result.scalars().all()

    await cache_set(cache_key, data, ttl=120)
    return data


# -----------------------
# BUY PACK
# -----------------------
@router.post("/buy/{action_id}", response_model=UserPackSchema)
async def buy_pack(
    action_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Action).where(Action.id == action_id))
    pack = result.scalars().first()

    if not pack:
        raise HTTPException(404, "Pack introuvable")

    existing = await db.execute(
        select(UserPack).where(
            UserPack.user_id == current_user.id,
            UserPack.pack_id == action_id
        )
    )
    if existing.scalars().first():
        raise HTTPException(400, "Pack déjà acheté")

    await debit_real_cash(current_user, pack.price_usdt, db)

    user_pack = UserPack(
        user_id=current_user.id,
        pack_id=action_id,
        start_date=None,
        daily_earnings=round(float(pack.price_per_part) * 0.012, 6),
        total_earned=0,
        is_unlocked=False,
        pack_status="payé"
    )

    db.add(user_pack)
    await db.commit()
    await db.refresh(user_pack)

    # 🔥 INVALIDATION
    await cache_delete(f"user_packs:{current_user.id}")
    await cache_delete(f"actions_category:{pack.category}")

    return user_pack


# -----------------------
# MY PACKS (CACHE)
# -----------------------
@router.get("/my-packs", response_model=List[UserPackSchema])
async def get_my_packs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    user_id = current_user.id
    cache_key = f"user_packs:{user_id}"

    cached = await cache_get(cache_key)
    if cached:
        return cached

    result = await db.execute(
        select(UserPack, Action)
        .join(Action, UserPack.pack_id == Action.id)
        .where(UserPack.user_id == user_id)
    )

    rows = result.all()
    enriched = []

    for user_pack, action in rows:
        enriched.append({
            **user_pack.__dict__,
            "name": action.name,
            "category": action.category.value,
            "type": action.type.value,
            "image_url": action.image_url,
            "status": action.status.value,
            "pack_status": user_pack.pack_status,
        })

    await cache_set(cache_key, enriched, ttl=60)
    return enriched


# -----------------------
# START PACK
# -----------------------
@router.post("/start/{user_pack_id}", response_model=UserPackSchema)
async def start_user_pack(
    user_pack_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    result = await start_pack(current_user.id, user_pack_id, db)

    await cache_delete(f"user_packs:{current_user.id}")
    return result


# -----------------------
# DAILY TASKS (CACHE SAFE)
# -----------------------
@router.get("/packs/{user_pack_id}/daily-tasks")
async def get_user_pack_daily_tasks(
    user_pack_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    cache_key = f"pack_tasks:{user_pack_id}"

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

    # création tasks si absentes
    existing = await db.execute(
        select(UserDailyTask).where(UserDailyTask.user_pack_id == user_pack.id)
    )
    user_tasks = existing.scalars().all()

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
        time_left = 0
        if ut.started_at:
            elapsed = (datetime.utcnow() - ut.started_at).total_seconds()
            time_left = max(0, 3600 - elapsed)

        tasks.append({
            "id": ut.id,
            "task_id": ut.task_id,
            "completed": ut.completed,
            "started_at": ut.started_at,
            "description": dt.description,
            "platform": dt.platform,
            "video_url": dt.video_url,
            "time_left": time_left,
        })

    await cache_set(cache_key, tasks, ttl=30)
    return tasks


# -----------------------
# START TASK
# -----------------------
@router.post("/packs/daily-tasks/{task_id}/start")
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

    if not task.started_at:
        task.started_at = datetime.utcnow()
        await db.commit()
        await db.refresh(task)

    # 🔥 INVALIDATION
    await cache_delete(f"pack_tasks:{task.user_pack_id}")

    return {"status": "started", "started_at": task.started_at}


# -----------------------
# COMPLETE TASK
# -----------------------
@router.post("/packs/daily-tasks/{task_id}/complete")
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

    task.completed = True
    task.completed_at = datetime.utcnow()
    await db.commit()

    # 🔥 INVALIDATION
    await cache_delete(f"pack_tasks:{task.user_pack_id}")

    return {"message": "✅ Tâche complétée", "task_id": task.id}


# -----------------------
# CLAIM
# -----------------------
@router.post("/claim/{user_pack_id}")
async def claim_reward(
    user_pack_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    result = await claim_pack_reward(
        user_id=current_user.id,
        user_pack_id=user_pack_id,
        db=db,
    )

    # 🔥 INVALIDATION
    await cache_delete(f"user_packs:{current_user.id}")
    await cache_delete(f"pack_tasks:{user_pack_id}")

    return {
        "status": "success",
        **result,
        "timestamp": datetime.utcnow().isoformat(),
    }