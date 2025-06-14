# app/routers/ranking.py

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db
from app.models import Balance
from app.schemas import BalanceOut

router = APIRouter(prefix="/ranking", tags=["Ranking"])

@router.get("/top", response_model=list[BalanceOut])
async def get_ranking(db: AsyncSession = Depends(get_db)):
    # On sélectionne les balances, triées par points décroissants
    result = await db.execute(select(Balance).order_by(Balance.points.desc()).limit(50))
    top_balances = result.scalars().all()
    return top_balances
