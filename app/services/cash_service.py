# app/services/cash_service.py

from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models import RealCash, User


# -----------------------------------------------------------------
# 💸 Débiter le compte real_cash (SANS COMMIT)
# -----------------------------------------------------------------
async def debit_real_cash(user: User, amount: float, db: AsyncSession) -> RealCash:
    """
    Débite le compte real_cash d'un utilisateur.
    ⚠️ Ne commit PAS.
    """

    if amount is None or amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Le montant à débiter doit être supérieur à zéro."
        )

    amount_decimal = Decimal(str(amount))

    result = await db.execute(
        select(RealCash).where(RealCash.user_id == user.id)
    )
    real_cash = result.scalars().first()

    if not real_cash:
        raise HTTPException(
            status_code=404,
            detail="Compte RealCash introuvable."
        )

    current_balance = real_cash.cash_balance or Decimal("0")

    if current_balance < amount_decimal:
        raise HTTPException(
            status_code=400,
            detail="Solde insuffisant sur le compte RealCash."
        )

    real_cash.cash_balance = current_balance - amount_decimal

    return real_cash


# -----------------------------------------------------------------
# 💰 Créditer le compte real_cash (SANS COMMIT)
# -----------------------------------------------------------------
async def credit_real_cash(user: User, amount: float, db: AsyncSession) -> RealCash:
    """
    Créditer le compte real_cash d'un utilisateur.
    ⚠️ Ne commit PAS.
    """

    if amount is None or amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Le montant à créditer doit être supérieur à zéro."
        )

    amount_decimal = Decimal(str(amount))

    result = await db.execute(
        select(RealCash).where(RealCash.user_id == user.id)
    )
    real_cash = result.scalars().first()

    if not real_cash:
        real_cash = RealCash(
            user_id=user.id,
            cash_balance=amount_decimal
        )
        db.add(real_cash)
    else:
        real_cash.cash_balance = (real_cash.cash_balance or Decimal("0")) + amount_decimal

    return real_cash


# -----------------------------------------------------------------
# 🔍 Obtenir le solde
# -----------------------------------------------------------------
async def get_real_cash_balance(user: User, db: AsyncSession) -> Decimal:
    """
    Retourne le solde du compte real_cash.
    """

    result = await db.execute(
        select(RealCash).where(RealCash.user_id == user.id)
    )
    real_cash = result.scalars().first()

    return real_cash.cash_balance if real_cash else Decimal("0")