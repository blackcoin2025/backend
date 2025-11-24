# app/routes/welcome.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.database import get_async_session
from app.models import User
from app.services.bonus_service import add_bonus_points  # ✅ déplacé ici
from app.services.balance_service import credit_balance, get_user_balance
from app.routers.auth import get_current_user
import logging

router = APIRouter(prefix="/welcome", tags=["Welcome"])
logger = logging.getLogger(__name__)


# ===============================
# ✅ Schéma de validation
# ===============================
class CompleteTasksRequest(BaseModel):
    total_points: int


# ===============================
# ✅ Endpoint principal
# ===============================
@router.post(
    "/complete-tasks",
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Données invalides"},
        status.HTTP_409_CONFLICT: {"description": "Tâches déjà complétées"},
    }
)
async def complete_welcome_tasks(
    data: CompleteTasksRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Marque les tâches de bienvenue comme complétées et crédite les points :
    - 50 → bonus (stocké pour conversion future)
    - 4950 → balance (wallet)
    """
    try:
        # 🔒 Vérification : déjà complété ?
        if current_user.has_completed_welcome_tasks:
            return {
                "success": False,
                "message": "Les tâches ont déjà été complétées.",
                "already_completed": True,
                "user": {
                    "id": current_user.id,
                    "email": current_user.email,
                    "username": current_user.username,
                    "first_name": current_user.first_name,
                    "last_name": current_user.last_name,
                    #"avatar_url": current_user.avatar_url,
                    "has_completed_welcome_tasks": current_user.has_completed_welcome_tasks,
                    "balance": await get_user_balance(db, current_user.id),
                    "level": getattr(current_user, "level", 1),
                    "wallet_address": getattr(current_user, "wallet_address", None),
                    "is_verified": current_user.is_verified,
                }
            }

        # ✅ Créditer le bonus et la balance
        current_user.has_completed_welcome_tasks = True
        await add_bonus_points(db=db, user_id=current_user.id, amount=50)  # bonus stocké
        await credit_balance(db, current_user.id, points=4950)

        await db.commit()
        await db.refresh(current_user)

        return {
            "success": True,
            "message": "Tâches de bienvenue complétées avec succès.",
            "user": {
                "id": current_user.id,
                "email": current_user.email,
                "username": current_user.username,
                "first_name": current_user.first_name,
                "last_name": current_user.last_name,
                #"avatar_url": current_user.avatar_url,
                "has_completed_welcome_tasks": current_user.has_completed_welcome_tasks,
                "balance": await get_user_balance(db, current_user.id),
                "level": getattr(current_user, "level", 1),
                "wallet_address": getattr(current_user, "wallet_address", None),
                "is_verified": current_user.is_verified,
            },
            "points_added": {"bonus": 50, "balance": 4950}
        }

    except Exception as e:
        logger.error(f"Erreur serveur : {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Une erreur interne est survenue"
        )
