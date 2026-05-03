# app/routes/friends.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, distinct
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
import secrets
import string
import logging

from pydantic import BaseModel, Field

from app.database import get_async_session
from app.models import User, Friend, PromoCode
from app.dependencies.dependency import require_completed_welcome
from app.services.rewards import reward_referrer

from app.core.cache import cache_get, cache_set, cache_delete

router = APIRouter(prefix="/friends", tags=["Friends"])
logger = logging.getLogger(__name__)


# ============================================================
# 🔹 SCHEMAS
# ============================================================
class ApplyCodeRequest(BaseModel):
    code: str = Field(..., min_length=4, max_length=12)


class FriendResponse(BaseModel):
    promo_code: Optional[str]
    friends: List[str]


# ============================================================
# 🔹 CODE GENERATOR (SECURE)
# ============================================================
def generate_secure_code(length=8):
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


# ============================================================
# 🔹 GENERATE CODE
# ============================================================
@router.post("/generate-code")
async def generate_code(
    current_user: User = Depends(require_completed_welcome),
    db: AsyncSession = Depends(get_async_session)
):
    user_id = current_user.id

    existing = (
        await db.execute(select(PromoCode).where(PromoCode.user_id == user_id))
    ).scalar_one_or_none()

    if existing:
        return {"code": existing.code}

    for _ in range(5):
        try:
            new_code = generate_secure_code()

            promo = PromoCode(
                user_id=user_id,
                code=new_code
            )

            db.add(promo)
            await db.commit()
            await db.refresh(promo)

            return {"code": promo.code}

        except IntegrityError:
            await db.rollback()

    raise HTTPException(500, "Impossible de générer un code unique")


# ============================================================
# 🔹 APPLY CODE
# ============================================================
@router.post("/apply-code", response_model=FriendResponse)
async def apply_code(
    payload: ApplyCodeRequest,
    current_user: User = Depends(require_completed_welcome),
    db: AsyncSession = Depends(get_async_session)
):
    user_id = current_user.id
    code = payload.code.strip().upper()

    # 🔥 anti brute-force simple (cache)
    attempt_key = f"promo_attempts:{user_id}"
    attempts = await cache_get(attempt_key) or 0

    if attempts >= 5:
        raise HTTPException(429, "Trop de tentatives. Réessaie plus tard.")

    async with db.begin():

        promo = (
            await db.execute(
                select(PromoCode)
                .where(
                    PromoCode.code == code,
                    PromoCode.is_active == True
                )
                .with_for_update()
            )
        ).scalar_one_or_none()

        if not promo:
            await cache_set(attempt_key, attempts + 1, ttl=60)
            raise HTTPException(400, "Code invalide")

        if promo.user_id == user_id:
            raise HTTPException(400, "Tu ne peux pas utiliser ton propre code")

        existing = (
            await db.execute(
                select(Friend)
                .where(
                    Friend.user_id == user_id,
                    Friend.friend_id == promo.user_id
                )
                .with_for_update()
            )
        ).scalar_one_or_none()

        if existing:
            raise HTTPException(409, "Déjà utilisé")

        if promo.usage_limit > 0 and promo.used_count >= promo.usage_limit:
            promo.is_active = False
            raise HTTPException(400, "Code expiré")

        db.add(
            Friend(
                user_id=user_id,
                friend_id=promo.user_id,
                status="accepted"
            )
        )

        promo.used_count += 1

        if promo.usage_limit > 0 and promo.used_count >= promo.usage_limit:
            promo.is_active = False

        await reward_referrer(
            db,
            promo_code=code,
            new_user=current_user
        )

    # 🔥 reset attempts
    await cache_delete(attempt_key)

    # 🔥 cache invalidate
    await cache_delete(f"friends:{user_id}")

    # 🔥 reload
    friends = (
        await db.execute(
            select(distinct(User.username))
            .join(Friend, Friend.friend_id == User.id)
            .where(
                Friend.user_id == user_id,
                Friend.status == "accepted"
            )
        )
    ).scalars().all()

    promo = (
        await db.execute(select(PromoCode).where(PromoCode.user_id == user_id))
    ).scalar_one_or_none()

    return {
        "promo_code": promo.code if promo else None,
        "friends": friends
    }


# ============================================================
# 🔹 GET MY FRIENDS
# ============================================================
@router.get("/me", response_model=FriendResponse)
async def get_my_friends(
    current_user: User = Depends(require_completed_welcome),
    db: AsyncSession = Depends(get_async_session)
):
    user_id = current_user.id
    cache_key = f"friends:{user_id}"

    cached = await cache_get(cache_key)
    if cached:
        return cached

    friends = (
        await db.execute(
            select(distinct(User.username))
            .join(Friend, User.id == Friend.friend_id)
            .where(
                Friend.user_id == user_id,
                Friend.status == "accepted"
            )
        )
    ).scalars().all()

    promo = (
        await db.execute(select(PromoCode).where(PromoCode.user_id == user_id))
    ).scalar_one_or_none()

    data = {
        "promo_code": promo.code if promo else None,
        "friends": friends
    }

    await cache_set(cache_key, data, ttl=60)

    return data