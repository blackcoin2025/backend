# app/routers/friends.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
import uuid

from app.database import get_async_session
from app.models import User, Friend, PromoCode
from app.dependencies.auth import get_current_user
from app.services.rewards import reward_referrer  # <-- Import correct

router = APIRouter(prefix="/friends", tags=["Friends"])

# --------------------------
# Pydantic Schemas
# --------------------------
from pydantic import BaseModel

class ApplyCodeRequest(BaseModel):
    code: str

class FriendResponse(BaseModel):
    promo_code: Optional[str]
    friends: List[str]

# --------------------------
# Générer son code promo
# --------------------------
@router.post("/generate-code")
async def generate_code(current_user: User = Depends(get_current_user),
                        db: AsyncSession = Depends(get_async_session)):
    user_id = current_user.id

    existing = await db.execute(select(PromoCode).where(PromoCode.user_id == user_id))
    promo = existing.scalar_one_or_none()
    if promo:
        return {"code": promo.code}

    for _ in range(5):
        try:
            new_code = str(uuid.uuid4())[:8].upper()
            promo = PromoCode(user_id=user_id, code=new_code)
            db.add(promo)
            await db.commit()
            await db.refresh(promo)
            return {"code": promo.code}
        except IntegrityError:
            await db.rollback()
            continue

    raise HTTPException(status_code=500, detail="Impossible de générer un code unique.")

# --------------------------
# Appliquer un code promo
# --------------------------
@router.post("/apply-code", response_model=FriendResponse)
async def apply_code(payload: ApplyCodeRequest,
                     current_user: User = Depends(get_current_user),
                     db: AsyncSession = Depends(get_async_session)):
    user_id = current_user.id
    code = payload.code.strip().upper()

    async with db.begin():
        promo_q = select(PromoCode).where(PromoCode.code == code, PromoCode.is_active == True).with_for_update()
        promo = (await db.execute(promo_q)).scalar_one_or_none()

        if not promo:
            raise HTTPException(status_code=400, detail="Code promo invalide")
        if promo.user_id == user_id:
            raise HTTPException(status_code=400, detail="Tu ne peux pas utiliser ton propre code")

        existing_friend_q = select(Friend).where(Friend.user_id == user_id, Friend.friend_id == promo.user_id).with_for_update()
        if (await db.execute(existing_friend_q)).scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Vous êtes déjà amis")

        if promo.usage_limit > 0 and promo.used_count >= promo.usage_limit:
            promo.is_active = False
            raise HTTPException(status_code=400, detail="Ce code promo n'est plus valide")

        # Ajouter la relation Friend
        db.add(Friend(user_id=user_id, friend_id=promo.user_id, status="accepted"))

        # Mettre à jour le code promo
        promo.used_count += 1
        if promo.usage_limit > 0 and promo.used_count >= promo.usage_limit:
            promo.is_active = False

        # Récompenser le parrain avec la nouvelle signature
        await reward_referrer(db, promo_code=code, new_user=current_user)

        # Récupérer la liste mise à jour des amis
        friends_result = await db.execute(
            select(User.username)
            .join(Friend, Friend.friend_id == User.id)
            .where(Friend.user_id == user_id)
        )
        friends_list = friends_result.scalars().all()

        promo_result = await db.execute(select(PromoCode).where(PromoCode.user_id == user_id))
        promo_code = promo_result.scalar_one_or_none()

    return {
        "promo_code": promo_code.code if promo_code else None,
        "friends": friends_list
    }

# --------------------------
# Route GET /me
# --------------------------
@router.get("/me", response_model=FriendResponse)
async def get_my_friends(current_user: User = Depends(get_current_user),
                         db: AsyncSession = Depends(get_async_session)):
    user_id = current_user.id

    friends_result = await db.execute(
        select(User.username)
        .join(Friend, User.id == Friend.friend_id)
        .where(Friend.user_id == user_id, Friend.status == "accepted")
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
# Route optionnelle par ID
# --------------------------
@router.get("/my-friends/{user_id}")
async def get_friends_by_user_id(user_id: int, db: AsyncSession = Depends(get_async_session)):
    result = await db.execute(
        select(User.username)
        .join(Friend, Friend.friend_id == User.id)
        .where(Friend.user_id == user_id)
    )
    friends_list = result.scalars().all()
    return {"friends": friends_list}
