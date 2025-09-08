# app/services/balance_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import Balance

async def credit_balance(db: AsyncSession, user_id: int, points: int) -> int:
    """
    Crédite des points à un utilisateur de manière sécurisée.
    Ne jamais exposer cette fonction directement au frontend.
    """
    if points <= 0:
        raise ValueError("Le nombre de points doit être positif")

    result = await db.execute(select(Balance).where(Balance.user_id == user_id))
    balance = result.scalars().first()

    if balance:
        balance.points += points
    else:
        balance = Balance(user_id=user_id, points=points)
        db.add(balance)

    await db.commit()
    await db.refresh(balance)
    return balance.points


async def get_user_balance(db: AsyncSession, user_id: int) -> int:
    """Retourne le total de points d’un utilisateur."""
    result = await db.execute(select(Balance).where(Balance.user_id == user_id))
    balance = result.scalars().first()
    return balance.points if balance else 0
