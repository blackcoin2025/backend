# app/routes/balance.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.services.balance_service import credit_balance, get_user_balance
from app.routers.auth import get_current_user
from app.models import User

router = APIRouter(
    prefix="/balance",
    tags=["Balance"]
)

@router.post("/add")
async def add_balance_points(
    points: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Endpoint sécurisé pour créditer des points.
    Points uniquement positifs et validés côté serveur.
    """
    if points <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Points invalides")

    try:
        new_total = await credit_balance(db, current_user.id, points)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    return {"message": "Points ajoutés à la balance", "points": new_total}


@router.get("/")
async def get_balance(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Retourne le total de points pour l’utilisateur connecté."""
    points = await get_user_balance(db, current_user.id)
    return {"user_id": current_user.id, "points": points}
