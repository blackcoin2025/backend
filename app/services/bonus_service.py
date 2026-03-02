# app/services/bonus_service.py

from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from datetime import datetime

from app.models import Bonus, BonusStatus, Wallet, Friend, UserAction, Action, ActionCategory


# ==========================================================
# 🧩 Vérifier l’éligibilité d’un bonus
# ==========================================================
async def check_bonus_eligibility(db: AsyncSession, user_id: int):
    """
    Vérifie si un utilisateur remplit les conditions
    pour rendre son bonus éligible.
    Ne fait PAS de commit.
    """

    # Vérifier pack finance
    pack_query = (
        select(UserAction)
        .join(Action)
        .where(
            UserAction.user_id == user_id,
            Action.category == ActionCategory.finance
        )
    )
    has_pack = (await db.execute(pack_query)).scalars().first() is not None

    # Vérifier dépôt dans le wallet
    wallet_query = select(Wallet).where(Wallet.user_id == user_id)
    wallet = (await db.execute(wallet_query)).scalars().first()
    has_deposit = wallet and (wallet.amount or Decimal("0")) > 0

    # Vérifier amis
    friends_query = (
        select(func.count())
        .select_from(Friend)
        .where(
            Friend.user_id == user_id,
            Friend.status == "accepted"
        )
    )
    friends_count = (await db.execute(friends_query)).scalar() or 0
    has_3_friends = friends_count >= 3

    if has_pack and has_deposit and has_3_friends:
        bonus_query = select(Bonus).where(
            Bonus.user_id == user_id,
            Bonus.status == BonusStatus.en_attente
        )
        bonus = (await db.execute(bonus_query)).scalars().first()

        if bonus:
            bonus.status = BonusStatus.eligible
            await db.flush()  # synchronise sans commit
            return {"success": True, "message": "Bonus rendu éligible."}

    return {"success": False, "message": "Conditions non remplies."}


# ==========================================================
# 🧩 Conversion quotidienne du bonus vers le wallet
# ==========================================================

PACK_CONVERSION_RATES = {
    "Bronze": Decimal("0.02"),
    "Silver": Decimal("0.05"),
    "Gold": Decimal("0.10"),
    "Platinum": Decimal("0.15"),
}

async def convert_daily_bonus(db: AsyncSession, user_id: int):
    """
    Convertit chaque jour un pourcentage du bonus vers le wallet.
    Ne fait PAS de commit.
    """

    bonus_query = select(Bonus).where(
        Bonus.user_id == user_id,
        Bonus.status.in_([BonusStatus.eligible, BonusStatus.en_conversion])
    )
    bonus = (await db.execute(bonus_query)).scalars().first()

    if not bonus or (bonus.points_restants or Decimal("0")) <= 0:
        return {"error": "Aucun bonus éligible ou points insuffisants."}

    pack_query = (
        select(Action)
        .join(UserAction)
        .where(
            UserAction.user_id == user_id,
            Action.category == ActionCategory.finance
        )
    )
    user_pack = (await db.execute(pack_query)).scalars().first()

    if not user_pack:
        return {"error": "Aucun pack trouvé pour cet utilisateur."}

    taux = PACK_CONVERSION_RATES.get(user_pack.name, Decimal("0.02"))

    points_restants = bonus.points_restants or Decimal("0")
    montant_converti = (points_restants * taux).quantize(Decimal("0.01"))

    # Mise à jour bonus
    bonus.points_restants = points_restants - montant_converti
    bonus.valeur_equivalente = (bonus.valeur_equivalente or Decimal("0")) + montant_converti
    bonus.status = BonusStatus.en_conversion
    bonus.converti_le = datetime.utcnow()

    # Mise à jour wallet
    wallet_query = select(Wallet).where(Wallet.user_id == user_id)
    wallet = (await db.execute(wallet_query)).scalars().first()

    if not wallet:
        return {"error": "Wallet introuvable pour cet utilisateur."}

    wallet.amount = (wallet.amount or Decimal("0")) + montant_converti

    if bonus.points_restants <= 0:
        bonus.status = BonusStatus.converti

    await db.flush()  # synchronise tout sans commit

    return {
        "success": True,
        "message": f"{montant_converti:.2f} BKC convertis à {taux*100:.0f}%.",
        "converted": montant_converti,
        "taux": taux,
        "remaining_points": bonus.points_restants,
    }


# ==========================================================
# 🧩 Ajouter des points dans le bonus
# ==========================================================

async def add_bonus_points(db: AsyncSession, user_id: int, amount: Decimal):
    """
    Ajoute des points bonus.
    Ne fait PAS de commit.
    """

    if not isinstance(amount, Decimal):
        amount = Decimal(str(amount))

    bonus_query = select(Bonus).where(Bonus.user_id == user_id)
    bonus = (await db.execute(bonus_query)).scalars().first()

    if not bonus:
        bonus = Bonus(
            user_id=user_id,
            points_restants=amount,
            valeur_equivalente=Decimal("0"),
            status=BonusStatus.en_attente,
            cree_le=datetime.utcnow(),
        )
        db.add(bonus)
    else:
        bonus.points_restants = (bonus.points_restants or Decimal("0")) + amount

    await db.flush()

    return {
        "success": True,
        "message": f"{amount} points bonus ajoutés.",
        "total_bonus": bonus.points_restants
    }