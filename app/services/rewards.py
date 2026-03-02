# app/services/rewards.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_
from decimal import Decimal
import logging

from app.models import User, PromoCode, Friend
from app.services.balance_service import credit_balance
from app.services.bonus_service import add_bonus_points

logger = logging.getLogger(__name__)


async def reward_referrer(
    db: AsyncSession,
    promo_code: str,
    new_user: User
) -> bool:
    """
    Récompense le parrain si :
    - Le code promo existe
    - Le parrain existe
    - La relation n'existe pas déjà (idempotence)

    IMPORTANT :
    - Ne gère PAS la transaction
    - Ne fait PAS de commit
    - Ne fait PAS de rollback
    - Laisse les exceptions remonter si erreur critique
    """

    # 1️⃣ Vérifier le code promo
    promo_result = await db.execute(
        select(PromoCode).where(PromoCode.code == promo_code)
    )
    promo = promo_result.scalars().first()

    if not promo:
        logger.warning(f"[rewards] Code promo '{promo_code}' introuvable.")
        return False

    # 2️⃣ Vérifier le parrain
    referrer_result = await db.execute(
        select(User).where(User.id == promo.user_id)
    )
    referrer = referrer_result.scalars().first()

    if not referrer:
        logger.warning(
            f"[rewards] Parrain introuvable pour le code '{promo_code}'."
        )
        return False

    # 3️⃣ Vérifier idempotence (éviter doublon)
    existing_friend_result = await db.execute(
        select(Friend).where(
            and_(
                Friend.user_id == referrer.id,
                Friend.friend_id == new_user.id
            )
        )
    )
    existing_friend = existing_friend_result.scalars().first()

    if existing_friend:
        logger.info(
            f"[rewards] Relation déjà existante entre "
            f"{referrer.id} et {new_user.id}. Skip."
        )
        return True

    # 4️⃣ Montants de récompense
    bonus_amount = Decimal("0.25")
    balance_amount = 200  # supposé compatible avec ton modèle

    # 5️⃣ Créditer bonus et balance
    await add_bonus_points(
        db=db,
        user_id=referrer.id,
        amount=bonus_amount
    )

    await credit_balance(
        db=db,
        user_id=referrer.id,
        points=balance_amount
    )

    # 6️⃣ Créer relation d’amitié
    new_friend = Friend(
        user_id=referrer.id,
        friend_id=new_user.id,
        status="accepted"
    )
    db.add(new_friend)

    # Synchroniser sans commit
    await db.flush()

    logger.info(
        f"[rewards] {referrer.username} récompensé : "
        f"+{balance_amount} balance, +{bonus_amount} bonus."
    )

    return True