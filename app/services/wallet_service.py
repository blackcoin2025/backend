# app/services/wallet_service.py

from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Wallet


# -----------------------------------------------------------------
# 💰 Créditer le wallet (SANS COMMIT)
# -----------------------------------------------------------------
async def credit_wallet(user, amount: float, db: AsyncSession) -> Wallet:
    """
    Créditer le wallet d'un utilisateur.
    ⚠️ Ne commit PAS. Doit être appelé dans une transaction.
    """

    if amount is None or amount <= 0:
        raise ValueError("Le montant à créditer doit être supérieur à zéro.")

    amount_decimal = Decimal(str(amount))

    result = await db.execute(
        select(Wallet).where(Wallet.user_id == user.id)
    )
    wallet = result.scalars().first()

    if wallet:
        wallet.amount = (wallet.amount or Decimal("0")) + amount_decimal
    else:
        wallet = Wallet(
            user_id=user.id,
            amount=amount_decimal
        )
        db.add(wallet)

    return wallet


# -----------------------------------------------------------------
# 💳 Débiter le wallet (SANS COMMIT)
# -----------------------------------------------------------------
async def debit_wallet(user, amount: float, db: AsyncSession) -> Wallet:
    """
    Débiter le wallet d'un utilisateur.
    Empêche le solde négatif.
    ⚠️ Ne commit PAS.
    """

    if amount is None or amount <= 0:
        raise ValueError("Le montant à débiter doit être supérieur à zéro.")

    amount_decimal = Decimal(str(amount))

    result = await db.execute(
        select(Wallet).where(Wallet.user_id == user.id)
    )
    wallet = result.scalars().first()

    if not wallet:
        raise ValueError("Aucun wallet trouvé pour cet utilisateur.")

    current_balance = wallet.amount or Decimal("0")

    if current_balance <= 0:
        raise ValueError("Solde vide.")

    if current_balance < amount_decimal:
        raise ValueError(
            f"Solde insuffisant : {current_balance:.2f} BKC disponible, "
            f"{amount_decimal:.2f} BKC requis."
        )

    wallet.amount = current_balance - amount_decimal

    return wallet


# -----------------------------------------------------------------
# 🔎 Récupérer le solde
# -----------------------------------------------------------------
async def get_wallet_balance(user, db: AsyncSession) -> Decimal:
    """
    Retourne le solde du wallet.
    Ne crée pas de wallet automatiquement.
    """

    result = await db.execute(
        select(Wallet).where(Wallet.user_id == user.id)
    )
    wallet = result.scalars().first()

    return wallet.amount if wallet else Decimal("0")