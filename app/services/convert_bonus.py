from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime

from app.models import Bonus, BonusStatus, Wallet, Action, UserAction, ActionCategory


# Taux de conversion selon le pack
PACK_CONVERSION_RATES = {
    "Bronze": 0.02,
    "Silver": 0.05,
    "Gold": 0.10,
    "Platinum": 0.15,
}


async def convert_daily_bonus(db: AsyncSession, user_id: int):
    """
    Convertit chaque jour un pourcentage du bonus vers le wallet.
    Le pourcentage dépend du PACK détenu par l'utilisateur.
    """

    # 1️⃣ Récupérer le bonus éligible
    bonus_query = select(Bonus).where(
        Bonus.user_id == user_id,
        Bonus.status.in_([BonusStatus.eligible, BonusStatus.en_conversion])
    )
    bonus = (await db.execute(bonus_query)).scalars().first()
    if not bonus or bonus.points_restants <= 0:
        return {"error": "Aucun bonus éligible ou points insuffisants."}

    # 2️⃣ Trouver le PACK de l’utilisateur
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

    pack_name = user_pack.name
    taux = PACK_CONVERSION_RATES.get(pack_name, 0.02)  # Par défaut 2%

    # 3️⃣ Calcul du montant converti
    montant_converti = bonus.points_restants * taux
    bonus.points_restants -= int(bonus.points_restants * taux)
    bonus.valeur_equivalente = (bonus.valeur_equivalente or 0) + montant_converti
    bonus.status = BonusStatus.en_conversion
    bonus.converti_le = datetime.utcnow()

    # 4️⃣ Créditer le wallet de l'utilisateur
    wallet_query = select(Wallet).where(Wallet.user_id == user_id)
    wallet = (await db.execute(wallet_query)).scalars().first()
    if not wallet:
        return {"error": "Wallet introuvable pour cet utilisateur."}

    wallet.amount += montant_converti

    # 5️⃣ Finaliser la conversion si bonus épuisé
    if bonus.points_restants <= 0:
        bonus.status = BonusStatus.converti

    await db.commit()
    await db.refresh(bonus)
    return {
        "success": True,
        "message": f"{montant_converti:.2f} BKC convertis à {taux*100:.0f}%.",
        "converted": montant_converti,
        "taux": taux,
        "remaining_points": bonus.points_restants,
    }
