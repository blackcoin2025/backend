from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.models import Balance, UserProfile
from app.schemas import RankingOut

router = APIRouter(prefix="/ranking", tags=["Ranking"])

@router.get("/top", response_model=list[RankingOut])
async def get_top_ranking(db: AsyncSession = Depends(get_db)):
    # Récupère les 50 meilleurs utilisateurs par points avec leur profil
    result = await db.execute(
        select(Balance)
        .options(joinedload(Balance.user))  # Charge le profil utilisateur lié
        .order_by(Balance.points.desc())
        .limit(50)
    )
    top_balances = result.scalars().all()
    return top_balances
