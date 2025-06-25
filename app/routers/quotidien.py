from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timedelta

from app.database import get_db
from app.models import UserProfile as User

router = APIRouter(prefix="/daily", tags=["Daily Reward"])

def calculate_streak(last_claim_time, now):
    """Calcule si le streak doit être incrémenté ou réinitialisé."""
    if last_claim_time:
        diff = now - last_claim_time
        if timedelta(hours=24) <= diff < timedelta(hours=48):
            return True  # Streak continue
    return False  # Streak réinitialisé

@router.get("/streak/{telegram_id}")
async def get_daily_streak(telegram_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    now = datetime.utcnow()
    if user.last_claim_time:
        last_claim = user.last_claim_time
        diff = now - last_claim

        if diff < timedelta(hours=24) and now.date() == last_claim.date():
            return {"claimed_today": True, "streak": user.daily_streak}
        elif diff >= timedelta(hours=48) or (now.date() - last_claim.date()).days > 1:
            user.daily_streak = 0
            await db.commit()
            return {"claimed_today": False, "streak": 0}

    return {"claimed_today": False, "streak": user.daily_streak}


@router.post("/claim")
async def claim_daily_reward(telegram_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

    now = datetime.utcnow()
    if user.last_claim_time and now.date() == user.last_claim_time.date():
        raise HTTPException(status_code=400, detail="Récompense déjà réclamée aujourd'hui")

    # Met à jour le streak
    if calculate_streak(user.last_claim_time, now):
        user.daily_streak += 1
    else:
        user.daily_streak = 1

    reward_points = 500
    user.points += reward_points
    user.last_claim_time = now

    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Erreur lors de la mise à jour du streak")

    return {
        "message": f"{reward_points} points ajoutés !",
        "streak": user.daily_streak,
        "new_balance": user.points
    }
