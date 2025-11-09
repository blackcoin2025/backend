# app/services/wallet_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import Wallet
from decimal import Decimal


# -----------------------------
# 💰 Wallet (argent réel)
# -----------------------------

async def credit_wallet(user, amount: float, db: AsyncSession):
    """
    Créditer le wallet de l'utilisateur avec un montant positif.
    Crée un wallet si l'utilisateur n'en a pas encore.
    """
    if amount is None or amount <= 0:
        raise ValueError("Le montant à créditer doit être supérieur à zéro.")

    result = await db.execute(select(Wallet).where(Wallet.user_id == user.id))
    wallet = result.scalars().first()

    if wallet:
        wallet.amount += Decimal(str(amount))
    else:
        wallet = Wallet(user_id=user.id, amount=amount)
        db.add(wallet)

    await db.commit()
    await db.refresh(wallet)
    return wallet


async def debit_wallet(user, amount: float, db: AsyncSession):
    """
    Débiter le wallet de l'utilisateur.
    Empêche le solde négatif et renvoie une erreur claire si fonds insuffisants.
    """
    if amount is None or amount <= 0:
        raise ValueError("Le montant à débiter doit être supérieur à zéro.")

    result = await db.execute(select(Wallet).where(Wallet.user_id == user.id))
    wallet = result.scalars().first()

    if not wallet:
        raise ValueError("Aucun wallet trouvé pour cet utilisateur. Veuillez d'abord créditer le compte.")

    if wallet.amount <= 0:
        raise ValueError("Le solde de votre compte est vide. Veuillez recharger avant d'effectuer cette opération.")

    if wallet.amount < amount:
        raise ValueError(
            f"Solde insuffisant : votre solde est de {wallet.amount:.2f} $BKC, "
            f"mais l'opération nécessite {amount:.2f} $BKC."
        )

    wallet.amount -= Decimal(str(amount))
    await db.commit()
    await db.refresh(wallet)
    return wallet


async def get_wallet_balance(user, db: AsyncSession):
    """
    Récupère le solde actuel du wallet de l'utilisateur.
    Retourne 0 si aucun wallet n'existe encore.
    """
    result = await db.execute(select(Wallet).where(Wallet.user_id == user.id))
    wallet = result.scalars().first()
    return wallet.amount if wallet else 0.0
