from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_async_session
from app.models import Action, UserPack, User
from app.schemas import ActionBase, ActionSchema, UserPackSchema
from app.dependencies.auth import get_current_user
from app.services.cash_service import debit_real_cash
from app.core.cache import cache_get, cache_set, cache_delete

router = APIRouter(prefix="/actions", tags=["Actions"])


# -----------------------
# CREATE ACTION
# -----------------------
@router.post("/", response_model=ActionSchema)
async def create_action(
    payload: ActionBase,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    new_action = Action(**payload.dict())
    db.add(new_action)
    await db.commit()
    await db.refresh(new_action)
    return new_action


# -----------------------
# LIST ALL
# -----------------------
@router.get("/", response_model=List[ActionSchema])
async def list_actions(db: AsyncSession = Depends(get_async_session)):
    result = await db.execute(select(Action))
    return result.scalars().all()


# -----------------------
# CATEGORY
# -----------------------
@router.get("/category/{category}", response_model=List[ActionSchema])
async def list_actions_by_category(category: str, db: AsyncSession = Depends(get_async_session)):
    cache_key = f"actions_category:{category}"

    cached = await cache_get(cache_key)
    if cached:
        return cached

    result = await db.execute(select(Action).where(Action.category == category))
    data = result.scalars().all()

    await cache_set(cache_key, data, ttl=120)
    return data


# -----------------------
# BUY PACK
# -----------------------
@router.post("/buy/{action_id}", response_model=UserPackSchema)
async def buy_pack(
    action_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Action).where(Action.id == action_id))
    pack = result.scalars().first()

    if not pack:
        raise HTTPException(404, "PACK_NOT_FOUND")

    existing = await db.execute(
        select(UserPack).where(
            UserPack.user_id == current_user.id,
            UserPack.pack_id == action_id
        )
    )

    if existing.scalars().first():
        raise HTTPException(400, "PACK_ALREADY_PURCHASED")

    await debit_real_cash(current_user, pack.price_usdt, db)

    user_pack = UserPack(
        user_id=current_user.id,
        pack_id=action_id,
        start_date=None,
        daily_earnings=round(float(pack.price_per_part) * 0.012, 6),
        total_earned=0,
        is_unlocked=False,
        pack_status="paid"
    )

    db.add(user_pack)
    await db.commit()
    await db.refresh(user_pack)

    await cache_delete(f"user_packs:{current_user.id}")
    await cache_delete(f"actions_category:{pack.category}")

    return user_pack