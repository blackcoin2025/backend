from fastapi import APIRouter, Depends
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import RealCash, User
from app.routers.auth import get_current_user


router = APIRouter(
    prefix="/wallet",
    tags=["CashMoney"]
)


@router.get("/realcash")
async def get_real_cash(
    current_user: User = Depends(get_current_user)
):
    """
    Retourne le solde d'argent réel de l'utilisateur connecté.
    Si aucune ligne n'existe encore en base → création automatique avec 0.
    """

    async with AsyncSessionLocal() as session:

        # 🔎 chercher le solde existant
        result = await session.execute(
            select(RealCash).where(RealCash.user_id == current_user.id)
        )
        real_cash = result.scalars().first()

        # 🧠 logique robuste : auto-création si absent
        if not real_cash:
            real_cash = RealCash(
                user_id=current_user.id,
                cash_balance=0
            )

            session.add(real_cash)
            await session.commit()
            await session.refresh(real_cash)

        # ✅ toujours une réponse valide
        return {
            "cash_balance": float(real_cash.cash_balance)
        }
