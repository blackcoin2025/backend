# app/routes/welcome.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
import logging

from app.database import get_async_session
from app.models import User
from app.dependencies.auth import get_current_user
from app.services.bonus_service import add_bonus_points
from app.services.balance_service import credit_balance, get_user_balance

router = APIRouter(prefix="/welcome", tags=["Welcome"])
logger = logging.getLogger(__name__)


# ============================================================
# 🔹 SCHEMA
# ============================================================
class CompleteTasksRequest(BaseModel):
    total_points: int = Field(..., ge=0)


# ============================================================
# 🔹 COMPLETE WELCOME TASKS
# ============================================================
@router.post(
    "/complete-tasks",
    status_code=status.HTTP_200_OK,
    responses={
        400: {"description": "Requête invalide"},
        401: {"description": "Non authentifié"},
        409: {"description": "Tâches déjà complétées"},
        500: {"description": "Erreur serveur"},
    },
)
async def complete_welcome_tasks(
    data: CompleteTasksRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Finalise les tâches de bienvenue :
    - 50 points → bonus
    - 4950 points → balance
    """

    try:
        # ====================================================
        # 🔒 Déjà complété ?
        # ====================================================
        if current_user.has_completed_welcome_tasks:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Les tâches de bienvenue sont déjà complétées."
            )

        # ====================================================
        # 🔒 Validation simple (optionnelle mais propre)
        # ====================================================
        if data.total_points <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Points invalides"
            )

        # ====================================================
        # 🔥 LOGIQUE PRINCIPALE
        # ====================================================
        current_user.has_completed_welcome_tasks = True

        # crédit bonus
        await add_bonus_points(
            db=db,
            user_id=current_user.id,
            amount=50
        )

        # crédit balance
        await credit_balance(
            db=db,
            user_id=current_user.id,
            points=4950
        )

        await db.commit()
        await db.refresh(current_user)

        # ====================================================
        # 🔹 RESPONSE PROPRE
        # ====================================================
        return {
            "success": True,
            "message": "Tâches de bienvenue complétées.",
            "user": {
                "id": current_user.id,
                "email": current_user.email,
                "username": current_user.username,
                "first_name": current_user.first_name,
                "last_name": current_user.last_name,
                "has_completed_welcome_tasks": current_user.has_completed_welcome_tasks,
                "balance": await get_user_balance(db, current_user.id),
                "level": getattr(current_user, "level", 1),
                "wallet_address": getattr(current_user, "wallet_address", None),
                "is_verified": current_user.is_verified,
            },
            "rewards": {
                "bonus": 50,
                "balance": 4950
            }
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"[WELCOME ERROR] {e}", exc_info=True)
        await db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne du serveur"
        )