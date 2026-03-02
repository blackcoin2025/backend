# app/services/wallet_service.py

from decimal import Decimal, ROUND_DOWN
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Wallet


TWOPLACES = Decimal("0.01")


# -----------------------------------------------------------------
# 🔧 Validation montant
# -----------------------------------------------------------------
def _normalize_amount(amount: Decimal) -> Decimal:
    if not isinstance(amount, Decimal):
        raise TypeError("Le montant doit être un Decimal.")

    if amount <= 0:
        raise ValueError("Le montant doit être supérieur à zéro.")

    return amount.quantize(TWOPLACES, rounding=ROUND_DOWN)


# -----------------------------------------------------------------
# 💰 Crédit (atomique)
# -----------------------------------------------------------------
async def credit_wallet(user, amount: Decimal, db: AsyncSession) -> Wallet:
    """
    Crédit atomique.
    ⚠️ Ne commit PAS.
    """

    amount = _normalize_amount(amount)

    # On essaie d'updater directement
    result = await db.execute(
        update(Wallet)
        .where(Wallet.user_id == user.id)
        .values(amount=Wallet.amount + amount)
        .returning(Wallet)
    )

    wallet = result.scalars().first()

    # Si aucun wallet n'existe, on le crée
    if not wallet:
        wallet = Wallet(user_id=user.id, amount=amount)
        db.add(wallet)
        await db.flush()  # pour avoir l'objet synchronisé

    return wallet


# -----------------------------------------------------------------
# 💳 Débit (atomique et sécurisé)
# -----------------------------------------------------------------
async def debit_wallet(user, amount: Decimal, db: AsyncSession) -> Wallet:
    """
    Débit atomique.
    Empêche le solde négatif au niveau SQL.
    ⚠️ Ne commit PAS.
    """

    amount = _normalize_amount(amount)

    result = await db.execute(
        update(Wallet)
        .where(
            Wallet.user_id == user.id,
            Wallet.amount >= amount  # condition critique
        )
        .values(amount=Wallet.amount - amount)
        .returning(Wallet)
    )

    wallet = result.scalars().first()

    if not wallet:
        raise ValueError("Solde insuffisant ou wallet inexistant.")

    return wallet


# -----------------------------------------------------------------
# 🔎 Solde
# -----------------------------------------------------------------
async def get_wallet_balance(user, db: AsyncSession) -> Decimal:
    result = await db.execute(
        select(Wallet.amount).where(Wallet.user_id == user.id)
    )
    balance = result.scalar_one_or_none()

    return balance if balance is not None else Decimal("0.00")