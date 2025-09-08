# app/services/rewards.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import User, PromoCode, Wallet, Balance, Friend


async def reward_referrer(db: AsyncSession, promo_code: str, new_user: User):
    """
    Récompense le parrain lorsque le filleul confirme son email.
    """
    # 1. Trouver le code promo
    promo_q = select(PromoCode).where(PromoCode.code == promo_code)
    promo_res = await db.execute(promo_q)
    promo = promo_res.scalars().first()

    if not promo:
        return False

    # 2. Trouver le parrain
    referrer_q = select(User).where(User.id == promo.user_id)
    referrer_res = await db.execute(referrer_q)
    referrer = referrer_res.scalars().first()

    if not referrer:
        return False

    # 3. Créditer les points (Wallet et Balance)
    wallet_q = select(Wallet).where(Wallet.user_id == referrer.id)
    wallet = (await db.execute(wallet_q)).scalars().first()
    if wallet:
        wallet.amount += 200

    balance_q = select(Balance).where(Balance.user_id == referrer.id)
    balance = (await db.execute(balance_q)).scalars().first()
    if balance:
        balance.points += 200

    # 4. Ajouter l'entrée dans Friend
    new_friend = Friend(
        user_id=referrer.id,
        friend_id=new_user.id,
        status="accepted"
    )
    db.add(new_friend)

    await db.commit()
    return True
# app/services/rewards.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import User, PromoCode, Wallet, Balance, Friend


async def reward_referrer(db: AsyncSession, promo_code: str, new_user: User):
    """
    Récompense le parrain lorsque le filleul confirme son email.
    """
    # 1. Trouver le code promo
    promo_q = select(PromoCode).where(PromoCode.code == promo_code)
    promo_res = await db.execute(promo_q)
    promo = promo_res.scalars().first()

    if not promo:
        return False

    # 2. Trouver le parrain
    referrer_q = select(User).where(User.id == promo.user_id)
    referrer_res = await db.execute(referrer_q)
    referrer = referrer_res.scalars().first()

    if not referrer:
        return False

    # 3. Créditer les points (Wallet et Balance)
    wallet_q = select(Wallet).where(Wallet.user_id == referrer.id)
    wallet = (await db.execute(wallet_q)).scalars().first()
    if wallet:
        wallet.amount += 200

    balance_q = select(Balance).where(Balance.user_id == referrer.id)
    balance = (await db.execute(balance_q)).scalars().first()
    if balance:
        balance.points += 200

    # 4. Ajouter l'entrée dans Friend
    new_friend = Friend(
        user_id=referrer.id,
        friend_id=new_user.id,
        status="accepted"
    )
    db.add(new_friend)

    await db.commit()
    return True
