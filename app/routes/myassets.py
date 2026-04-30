from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_async_session
from app.models import Action, UserPack, User
from app.dependencies.auth import get_current_user
from app.services.pack_service import (
    start_pack,
    claim_pack_reward,
    get_user_daily_tasks  # 🔥 IMPORTANT
)
from app.core.cache import cache_delete

router = APIRouter(prefix="/my-assets", tags=["MyAssets"])


# -----------------------
# MY ASSETS (PORTFOLIO)
# -----------------------
@router.get("/")
async def get_my_assets(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    result = await db.execute(
        select(UserPack, Action)
        .join(Action, UserPack.pack_id == Action.id)
        .where(UserPack.user_id == current_user.id)
    )

    rows = result.all()
    assets = []

    for user_pack, action in rows:
        assets.append({
            "id": user_pack.id,

            "name": action.name,
            "category": action.category.value,
            "type": action.type.value,
            "image_url": action.image_url,

            "quantity": 1,

            # 💰 INVESTISSEMENT
            "total_invested_usdt": float(action.price_usdt),

            # 💸 GAINS
            "total_earned_bkc": float(user_pack.total_earned or 0),

            # 📊 PROFIT
            "profit_bkc": float(user_pack.total_earned or 0),

            # 📈 INFOS
            "daily_earnings_bkc": float(user_pack.daily_earnings or 0),

            "status": user_pack.pack_status
        })

    return assets


# -----------------------
# START PACK
# -----------------------
@router.post("/start/{user_pack_id}")
async def start_user_pack(
    user_pack_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user)
):
    result = await start_pack(current_user.id, user_pack_id, db)

    # 🔄 refresh cache
    await cache_delete(f"user_packs:{current_user.id}")

    return result


# -----------------------
# CLAIM
# -----------------------
@router.post("/claim/{user_pack_id}")
async def claim_reward(
    user_pack_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    result = await claim_pack_reward(
        user_id=current_user.id,
        user_pack_id=user_pack_id,
        db=db,
    )

    # 🔄 refresh cache
    await cache_delete(f"user_packs:{current_user.id}")

    return {
        "status": "success",
        **result,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }