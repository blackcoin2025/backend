# app/services/wallet_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import Wallet

async def add_wallet_points(user, amount: int, db: AsyncSession):
    """Ajoute des points au wallet de l'utilisateur."""
    result = await db.execute(select(Wallet).where(Wallet.user_id == user.id))
    wallet = result.scalars().first()

    if wallet:
        wallet.amount += amount
    else:
        wallet = Wallet(user_id=user.id, amount=amount)
        db.add(wallet)

    await db.commit()
    await db.refresh(wallet)
    return wallet

async def get_wallet_balance(user, db: AsyncSession):
    """Récupère le solde actuel du wallet."""
    result = await db.execute(select(Wallet).where(Wallet.user_id == user.id))
    wallet = result.scalars().first()
    return wallet.amount if wallet else 0
