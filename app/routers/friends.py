# app/routers/friends.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
import uuid

from pydantic import BaseModel

from app.database import get_async_session
from app.models import User, Friend, PromoCode
from app.dependencies.auth import get_current_user
from app.services.rewards import reward_referrer

# 🔥 cache
from app.core.cache import cache_get, cache_set, cache_delete


router = APIRouter(prefix="/friends", tags=["Friends"])


# --------------------------
# SCHEMAS
# --------------------------
class ApplyCodeRequest(BaseModel):
    code: str


class FriendResponse(BaseModel):
    promo_code: Optional[str]
    friends: List[str]


# --------------------------
# GENERATE CODE
# --------------------------
@router.post("/generate-code")
async def generate_code(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    user_id = current_user.id

    result = await db.execute(
        select(PromoCode).where(PromoCode.user_id == user_id)
    )
    promo = result.scalar_one_or_none()

    if promo:
        return {"code": promo.code}

    for _ in range(5):
        try:
            new_code = str(uuid.uuid4())[:8].upper()

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

    raise HTTPException(
        status_code=500,
        detail="Impossible de générer un code unique."
    )


# --------------------------
# APPLY CODE
# --------------------------
@router.post("/apply-code", response_model=FriendResponse)
async def apply_code(
    payload: ApplyCodeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    user_id = current_user.id
    code = payload.code.strip().upper()

    async with db.begin():

        # 🔥 LOCK promo
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
            raise HTTPException(400, "Code promo invalide")

        if promo.user_id == user_id:
            raise HTTPException(400, "Tu ne peux pas utiliser ton propre code")

        # 🔥 LOCK friend
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
            raise HTTPException(400, "Vous êtes déjà amis")

        # 🔥 usage limit
        if promo.usage_limit > 0 and promo.used_count >= promo.usage_limit:
            promo.is_active = False
            raise HTTPException(400, "Ce code promo n'est plus valide")

        # 🔥 créer relation
        db.add(
            Friend(
                user_id=user_id,
                friend_id=promo.user_id,
                status="accepted"
            )
        )

        # 🔥 update promo
        promo.used_count += 1

        if promo.usage_limit > 0 and promo.used_count >= promo.usage_limit:
            promo.is_active = False

        # 🔥 reward
        await reward_referrer(
            db,
            promo_code=code,
            new_user=current_user
        )

    # 🔥 IMPORTANT : invalidation cache
    await cache_delete(f"friends:{user_id}")

    # 🔥 re-fetch data (hors transaction)
    friends_result = await db.execute(
        select(User.username)
        .join(Friend, Friend.friend_id == User.id)
        .where(Friend.user_id == user_id)
    )
    friends_list = friends_result.scalars().all()

    promo_result = await db.execute(
        select(PromoCode).where(PromoCode.user_id == user_id)
    )
    promo_code = promo_result.scalar_one_or_none()

    return {
        "promo_code": promo_code.code if promo_code else None,
        "friends": friends_list
    }


# --------------------------
# GET MY FRIENDS (CACHE)
# --------------------------
@router.get("/me", response_model=FriendResponse)
async def get_my_friends(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    user_id = current_user.id
    cache_key = f"friends:{user_id}"

    # 🔥 CACHE
    cached = await cache_get(cache_key)
    if cached:
        return cached

    # 🔥 DB
    friends_result = await db.execute(
        select(User.username)
        .join(Friend, User.id == Friend.friend_id)
        .where(
            Friend.user_id == user_id,
            Friend.status == "accepted"
        )
    )
    friends_list = friends_result.scalars().all()

    promo_result = await db.execute(
        select(PromoCode).where(PromoCode.user_id == user_id)
    )
    promo_code = promo_result.scalar_one_or_none()

    data = {
        "promo_code": promo_code.code if promo_code else None,
        "friends": friends_list
    }

    # 🔥 CACHE SET
    await cache_set(cache_key, data, ttl=60)

    return data


# --------------------------
# OPTIONAL (⚠️ à sécuriser)
# --------------------------
@router.get("/my-friends/{user_id}")
async def get_friends_by_user_id(
    user_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    result = await db.execute(
        select(User.username)
        .join(Friend, Friend.friend_id == User.id)
        .where(Friend.user_id == user_id)
    )
    friends_list = result.scalars().all()

    return {"friends": friends_list}