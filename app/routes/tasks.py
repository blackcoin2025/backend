# app/routes/tasks.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from pydantic import BaseModel

from app.database import get_async_session
from app.models import Task, UserTask, User
from app.schemas import TaskSchema
from app.dependencies.auth import get_current_user
from app.services.balance_service import credit_balance
from app.services.wallet_service import add_wallet_points

router = APIRouter(
    prefix="",  # défini dans main.py (ex: /tasks)
    tags=["Tasks"]
)


# ------------------------
# Schéma pour la validation
# ------------------------
class ValidateTaskRequest(BaseModel):
    code: str


# ------------------------
# 1. Liste des vidéos (tâches disponibles)
# ------------------------
@router.get("/", response_model=List[TaskSchema])
@router.get("", response_model=List[TaskSchema])
async def get_all_tasks(db: AsyncSession = Depends(get_async_session)):
    """Retourne toutes les tâches (vidéos) disponibles."""
    result = await db.execute(select(Task))
    return result.scalars().all()


# ------------------------
# 2. Validation d’une tâche par code
# ------------------------
@router.post("/{task_id}/validate")
async def validate_task(
    task_id: int,
    payload: ValidateTaskRequest,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """Vérifie le code d’une tâche, marque comme complétée et crédite les points."""

    # Récupération de la tâche
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=404, detail="Tâche non trouvée")

    # Vérification du code
    if task.validation_code != payload.code:
        raise HTTPException(status_code=400, detail="Code invalide")

    # Vérifier si déjà complétée
    result = await db.execute(
        select(UserTask).where(
            UserTask.user_id == current_user.id,
            UserTask.task_id == task_id
        )
    )
    user_task = result.scalars().first()

    if user_task and user_task.completed:
        raise HTTPException(status_code=400, detail="Tâche déjà complétée")

    # Créer ou mettre à jour UserTask
    if not user_task:
        user_task = UserTask(
            user_id=current_user.id,
            task_id=task_id,
            completed=True
        )
        db.add(user_task)
    else:
        user_task.completed = True

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
# 3. Nombre de tâches complétées par utilisateur
# ------------------------
@router.get("/me/completed-count")
async def get_completed_tasks_count(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """Retourne le nombre total de tâches accomplies par l’utilisateur."""
    result = await db.execute(
        select(UserTask).where(
            UserTask.user_id == current_user.id,
            UserTask.completed == True
        )
    )
    completed_tasks = result.scalars().all()
    return {"user_id": current_user.id, "completed_tasks": len(completed_tasks)}


# ------------------------
# 4. Liste des tâches non encore validées par l’utilisateur
# ------------------------
@router.get("/me", response_model=List[TaskSchema])
async def get_my_pending_tasks(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    """Retourne uniquement les tâches que l’utilisateur n’a pas encore complétées."""
    # Toutes les tâches
    result = await db.execute(select(Task))
    all_tasks = result.scalars().all()

    # Tâches déjà complétées par l’utilisateur
    result = await db.execute(
        select(UserTask.task_id).where(
            UserTask.user_id == current_user.id,
            UserTask.completed == True
        )
    )
    completed_task_ids = {task_id for task_id, in result.all()}

    # Filtrer pour ne garder que celles non complétées
    pending_tasks = [task for task in all_tasks if task.id not in completed_task_ids]

    return pending_tasks
