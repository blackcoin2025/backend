# app/routes/welcome.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.database import get_async_session
from app.models import User
from app.services.wallet_service import add_wallet_points
from app.services.balance_service import credit_balance, get_user_balance
from app.routers.auth import get_current_user
import logging

router = APIRouter(
    prefix="/welcome",
    tags=["Welcome"]
)

logger = logging.getLogger(__name__)


# ===============================
# ✅ Schéma de validation
# ===============================
class CompleteTasksRequest(BaseModel):
    total_points: int  # juste pour validation du payload côté client


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
    - 2000 → wallet
    - 3000 → balance
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
                    "avatar_url": current_user.avatar_url,
                    "has_completed_welcome_tasks": current_user.has_completed_welcome_tasks,
                    "balance": await get_user_balance(db, current_user.id),
                    "level": getattr(current_user, "level", 1),
                    "wallet_address": getattr(current_user, "wallet_address", None),
                    "is_verified": current_user.is_verified,
                }
            }

        # ✅ Créditer et marquer comme complété
        current_user.has_completed_welcome_tasks = True
        await add_wallet_points(user=current_user, amount=2000, db=db)
        await credit_balance(db, current_user.id, points=3000)

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
                "avatar_url": current_user.avatar_url,
                "has_completed_welcome_tasks": current_user.has_completed_welcome_tasks,
                "balance": await get_user_balance(db, current_user.id),
                "level": getattr(current_user, "level", 1),
                "wallet_address": getattr(current_user, "wallet_address", None),
                "is_verified": current_user.is_verified,
            },
            "points_added": {
                "wallet": 2000,
                "balance": 3000
            }
        }

    except Exception as e:
        logger.error(f"Erreur serveur : {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Une erreur interne est survenue"
        )
