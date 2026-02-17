from typing import List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_async_session
from app.models import Action, UserPack, User, DailyTask, UserDailyTask
from app.schemas import ActionBase, ActionSchema, UserPackSchema
from app.dependencies.auth import get_current_user
from app.services.cash_service import debit_real_cash
from app.services.pack_service import start_pack, claim_pack_reward

router = APIRouter(prefix="/actions", tags=["Actions"])

# -----------------------
# 🧱 Créer une nouvelle Action (Pack)
# -----------------------
@router.post("/", response_model=ActionSchema)
async def create_action(
    payload: ActionBase,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    new_action = Action(
        name=payload.name,
        category=payload.category,
        type=payload.type,
        total_parts=payload.total_parts,
        price_per_part=payload.price_per_part,
        value_bkc=payload.value_bkc,
        image_url=payload.image_url,
    )
    db.add(new_action)
    await db.commit()
    await db.refresh(new_action)
    return new_action


# -----------------------
# 📋 Lister toutes les actions (packs)
# -----------------------
@router.get("/", response_model=List[ActionSchema])
async def list_actions(db: AsyncSession = Depends(get_async_session)):
    result = await db.execute(select(Action))
    return result.scalars().all()


# -----------------------
# 🔍 Lister les actions par catégorie
# -----------------------
@router.get("/category/{category}", response_model=List[ActionSchema])
async def list_actions_by_category(category: str, db: AsyncSession = Depends(get_async_session)):
    result = await db.execute(select(Action).where(Action.category == category))
    return result.scalars().all()


# -----------------------
# 💰 Acheter un pack
# -----------------------
@router.post("/buy/{action_id}", response_model=UserPackSchema)
async def buy_pack(
    action_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Action).where(Action.id == action_id))
    pack = result.scalars().first()
    if not pack:
        raise HTTPException(status_code=404, detail="Pack introuvable")

    existing = await db.execute(
        select(UserPack).where(
            UserPack.user_id == current_user.id,
            UserPack.pack_id == action_id
        )
    )
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Ce pack a déjà été acheté")

    try:
        await debit_real_cash(current_user, pack.price_usdt, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    daily_earnings = round(float(pack.price_per_part) * 0.012, 6)
    user_pack = UserPack(
        user_id=current_user.id,
        pack_id=action_id,
        start_date=None,
        daily_earnings=daily_earnings,
        total_earned=0,
        is_unlocked=False,
        pack_status="payé"
    )
    db.add(user_pack)
    await db.commit()
    await db.refresh(user_pack)
    return user_pack


# -----------------------
# 📦 Lister les packs achetés
# -----------------------
@router.get("/my-packs", response_model=List[UserPackSchema])
async def get_my_packs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    result = await db.execute(
        select(UserPack, Action)
        .join(Action, UserPack.pack_id == Action.id)
        .where(UserPack.user_id == current_user.id)
    )
    rows = result.all()

    enriched = []
    for user_pack, action in rows:
        status = getattr(user_pack, "pack_status", "payé" if not user_pack.start_date else "en_cours")
        enriched.append({
            **user_pack.__dict__,
            "name": action.name,
            "category": action.category.value,
            "type": action.type.value,
            "image_url": action.image_url,
            "status": action.status.value,
            "pack_status": status,
        })
    return enriched


# -----------------------
# 🚀 Démarrer un pack (Start)
# -----------------------
@router.post("/start/{user_pack_id}", response_model=UserPackSchema)
async def start_user_pack(
    user_pack_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    return await start_pack(current_user.id, user_pack_id, db)


# -----------------------
# 📋 Lister les tâches journalières
# -----------------------
@router.get("/packs/{user_pack_id}/daily-tasks")
async def get_user_pack_daily_tasks(
    user_pack_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    # 1️⃣ Vérifie le pack
    result = await db.execute(
        select(UserPack).where(
            UserPack.id == user_pack_id,
            UserPack.user_id == current_user.id
        )
    )
    user_pack = result.scalars().first()
    if not user_pack:
        raise HTTPException(status_code=404, detail="Pack introuvable pour cet utilisateur")

    # 2️⃣ Tâches existantes ?
    existing = await db.execute(
        select(UserDailyTask).where(UserDailyTask.user_pack_id == user_pack.id)
    )
    user_tasks = existing.scalars().all()

    # 3️⃣ Sinon, créer à partir des DailyTask
    if not user_tasks:
        base_q = await db.execute(
            select(DailyTask).where(DailyTask.pack_id == user_pack.pack_id)
        )
        base_tasks = base_q.scalars().all()
        if not base_tasks:
            raise HTTPException(status_code=404, detail="Aucune tâche disponible pour ce pack")

        for t in base_tasks:
            db.add(UserDailyTask(
                user_id=current_user.id,
                task_id=t.id,
                user_pack_id=user_pack.id,
                completed=False,
                completed_at=None,
            ))
        await db.commit()

    # 4️⃣ Jointure enrichie
    joined = await db.execute(
        select(UserDailyTask, DailyTask)
        .join(DailyTask, DailyTask.id == UserDailyTask.task_id)
        .where(UserDailyTask.user_pack_id == user_pack.id)
    )
    data = joined.all()

    # 5️⃣ Construction de la réponse
    tasks = []
    for ut, dt in data:
        cooldown = 3600  # ⏱️ 1 heure (en secondes)
        time_left = 0

        if ut.started_at:
            elapsed = (datetime.utcnow() - ut.started_at).total_seconds()
            time_left = max(0, cooldown - elapsed)

        tasks.append({
            "id": ut.id,
            "task_id": ut.task_id,
            "user_pack_id": ut.user_pack_id,
            "completed": ut.completed,
            "completed_at": ut.completed_at,
            "started_at": ut.started_at,
            "description": dt.description,
            "platform": dt.platform,
            "video_url": dt.video_url,
            "reward_share": dt.reward_share,
            "time_left": time_left,
        })

    return tasks


# -----------------------
# ▶️ Démarrer une tâche
# -----------------------
@router.post("/packs/daily-tasks/{task_id}/start")
async def start_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    result = await db.execute(
        select(UserDailyTask)
        .where(UserDailyTask.id == task_id, UserDailyTask.user_id == current_user.id)
    )
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=404, detail="Tâche introuvable")

    if not task.started_at:
        task.started_at = datetime.utcnow()
        await db.commit()
        await db.refresh(task)

    return {"status": "started", "started_at": task.started_at}


# -----------------------
# ✅ Compléter une tâche
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
        raise HTTPException(status_code=404, detail="Tâche introuvable")

    task.completed = True
    task.completed_at = datetime.utcnow()
    db.add(task)
    await db.commit()

    # Vérifie si toutes les tâches du pack sont finies
    res2 = await db.execute(
        select(UserDailyTask).where(UserDailyTask.user_pack_id == task.user_pack_id)
    )
    all_tasks = res2.scalars().all()
    if all(t.completed for t in all_tasks):
        res_pack = await db.execute(select(UserPack).where(UserPack.id == task.user_pack_id))
        user_pack = res_pack.scalars().first()
        if user_pack:
            user_pack.all_tasks_completed = True
            user_pack.is_unlocked = True
            db.add(user_pack)
            await db.commit()

    await db.refresh(task)
    return {"message": "✅ Tâche complétée", "task_id": task.id}


# -----------------------
# 💰 Réclamer les gains
# -----------------------
@router.post("/claim/{user_pack_id}")
async def claim_reward(
    user_pack_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    """
    Permet à l'utilisateur de réclamer les gains d'un pack
    après avoir complété toutes les tâches et respecté le délai.
    """

    try:
        result = await claim_pack_reward(
            user_id=current_user.id,
            user_pack_id=user_pack_id,
            db=db,
        )

        return {
            "status": "success",
            **result,  # 🔥 on retourne directement ce que renvoie le service
            "timestamp": datetime.utcnow().isoformat(),
        }

    except HTTPException:
        # On laisse FastAPI gérer les erreurs métier propres
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Erreur interne pendant la réclamation.",
        )
