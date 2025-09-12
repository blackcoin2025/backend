# app/routes/tasks.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from pydantic import BaseModel
from datetime import datetime

from app.database import get_async_session
from app.models import Task, UserTask, User
from app.schemas import TaskSchema
from app.dependencies.auth import get_current_user
from app.services.balance_service import credit_balance
from app.services.wallet_service import add_wallet_points

router = APIRouter(
    tags=["Tasks"]  # ✅ aucun prefix ici
)

# Durée minimale (en secondes) avant validation
TASK_MIN_DURATION = 120

# ------------------------
# Schéma pour la validation
# ------------------------
class ValidateTaskRequest(BaseModel):
    code: str

# ------------------------
# 1. Liste de toutes les tâches disponibles
# ------------------------
@router.get("/", response_model=List[TaskSchema])
async def get_all_tasks(db: AsyncSession = Depends(get_async_session)):
    result = await db.execute(select(Task))
    return result.scalars().all()

# ------------------------
# 2. Démarrage d’une tâche
# ------------------------
@router.post("/{task_id}/start")
async def start_task(
    task_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=404, detail="Tâche non trouvée")

    result = await db.execute(
        select(UserTask).where(
            UserTask.user_id == current_user.id,
            UserTask.task_id == task_id
        )
    )
    user_task = result.scalars().first()

    if not user_task:
        user_task = UserTask(
            user_id=current_user.id,
            task_id=task_id,
            started_at=datetime.utcnow()
        )
        db.add(user_task)
    else:
        user_task.started_at = datetime.utcnow()

    await db.commit()
    await db.refresh(user_task)

    return {
        "message": "⏳ Tâche démarrée",
        "task_id": task_id,
        "started_at": user_task.started_at
    }

# ------------------------
# 3. Validation d’une tâche par code
# ------------------------
@router.post("/{task_id}/validate")
async def validate_task(
    task_id: int,
    payload: ValidateTaskRequest,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=404, detail="Tâche non trouvée")

    if task.validation_code != payload.code:
        raise HTTPException(status_code=400, detail="Code invalide")

    result = await db.execute(
        select(UserTask).where(
            UserTask.user_id == current_user.id,
            UserTask.task_id == task_id
        )
    )
    user_task = result.scalars().first()

    if not user_task or not user_task.started_at:
        raise HTTPException(status_code=400, detail="Tâche non démarrée")
    if user_task.completed:
        raise HTTPException(status_code=400, detail="Tâche déjà complétée")

    elapsed = (datetime.utcnow() - user_task.started_at).total_seconds()
    if elapsed < TASK_MIN_DURATION:
        raise HTTPException(
            status_code=400,
            detail=f"⏱ Vous devez encore attendre {TASK_MIN_DURATION - int(elapsed)} secondes"
        )

    # Validation
    user_task.completed = True
    user_task.completed_at = datetime.utcnow()

    # Répartition des points
    total_points = task.reward_points
    balance_points = int(total_points * 0.8)
    wallet_points = total_points - balance_points

    try:
        await credit_balance(db, current_user.id, balance_points)
        await add_wallet_points(current_user, wallet_points, db)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du crédit des points : {str(e)}"
        )

    await db.commit()
    await db.refresh(user_task)

    return {
        "message": "✅ Tâche validée avec succès",
        "task_id": task_id,
        "reward": {
            "balance": balance_points,
            "wallet": wallet_points,
            "total": total_points
        }
    }

# ------------------------
# 4. Nombre de tâches complétées par utilisateur
# ------------------------
@router.get("/me/completed-count")
async def get_completed_tasks_count(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(UserTask).where(
            UserTask.user_id == current_user.id,
            UserTask.completed == True
        )
    )
    completed_tasks = result.scalars().all()
    return {"user_id": current_user.id, "completed_tasks": len(completed_tasks)}

# ------------------------
# 5. Liste des tâches non encore validées par l’utilisateur
# ------------------------
@router.get("/me/pending")
async def get_my_pending_tasks(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Task))
    all_tasks = result.scalars().all()

    pending_tasks = []
    for task in all_tasks:
        result = await db.execute(
            select(UserTask).where(
                UserTask.user_id == current_user.id,
                UserTask.task_id == task.id
            )
        )
        user_task = result.scalars().first()

        completed = False
        started_at = None
        time_left = 0

        if user_task:
            completed = user_task.completed
            started_at = user_task.started_at
            if user_task.started_at and not user_task.completed:
                elapsed = (datetime.utcnow() - user_task.started_at).total_seconds()
                time_left = max(0, TASK_MIN_DURATION - int(elapsed))

        if not completed:  # On exclut les tâches déjà validées
            pending_tasks.append({
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "link": task.link,
                "reward_points": task.reward_points,
                "completed": completed,
                "started_at": started_at.isoformat() if started_at else None,
                "time_left": time_left
            })

    return pending_tasks
