# app/services/rewards.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import User, PromoCode, Friend
from app.services.balance_service import credit_balance
from app.services.bonus_service import add_bonus_points
import logging

logger = logging.getLogger(__name__)

async def reward_referrer(db: AsyncSession, promo_code: str, new_user: User):
    """
    Récompense le parrain lorsque le filleul confirme son email :
    - +200 points sur la Balance (wallet)
    - +0.25 points sur le Bonus (convertible plus tard)
    """
    try:
        # 1️⃣ Trouver le code promo
        promo_q = select(PromoCode).where(PromoCode.code == promo_code)
        promo_res = await db.execute(promo_q)
        promo = promo_res.scalars().first()
        if not promo:
            logger.warning(f"[rewards] Code promo '{promo_code}' introuvable.")
            return False

        # 2️⃣ Trouver le parrain
        referrer_q = select(User).where(User.id == promo.user_id)
        referrer_res = await db.execute(referrer_q)
        referrer = referrer_res.scalars().first()
        if not referrer:
            logger.warning(f"[rewards] Parrain introuvable pour le code '{promo_code}'.")
            return False

        # 3️⃣ Créditer le bonus (0.25)
        await add_bonus_points(db=db, user_id=referrer.id, amount=0.25)

        # 4️⃣ Créditer la balance (200)
        await credit_balance(db=db, user_id=referrer.id, points=200)

        # 5️⃣ Ajouter la relation d’amitié
        new_friend = Friend(
            user_id=referrer.id,
            friend_id=new_user.id,
            status="accepted"
        )
        db.add(new_friend)
        await db.commit()

        logger.info(f"[rewards] {referrer.username} récompensé : +200 balance, +0.25 bonus.")
        return True

    except Exception as e:
        logger.error(f"[rewards] Erreur reward_referrer : {e}", exc_info=True)
        await db.rollback()
        return False
