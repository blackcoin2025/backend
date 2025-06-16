from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models import (
    UserProfile,
    Level,
    Balance,
    Wallet,
    TaskStat,
    Ranking,
    UserAction,
    MyAction,
    UserStatus,
)
from app.schemas import TelegramAuthRequest, UserOut
from app.services.telegram_verification import verify_telegram_auth_data

router = APIRouter(prefix="/auth", tags=["Auth"])

# 🎁 Bonus et configuration
WELCOME_BONUS = 1000
CHANNEL_BONUS = 1000
BONUS_SPLIT = 0.5  # 50% vers balance, 50% vers wallet


@router.post("/telegram", response_model=UserOut)
async def auth_telegram(data: TelegramAuthRequest, db: AsyncSession = Depends(get_db)):
    # 1. Vérifier que les données viennent bien de Telegram
    if not verify_telegram_auth_data(data):
        raise HTTPException(status_code=401, detail="Données Telegram invalides.")

    # 2. Vérifier si l'utilisateur existe déjà
    result = await db.execute(select(UserProfile).where(UserProfile.telegram_id == data.telegram_id))
    user = result.scalar_one_or_none()

    if user:
        return user  # Utilisateur déjà enregistré

    # 3. Création du nouvel utilisateur + Bonus
    user = UserProfile(**data.model_dump())
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # --- BONUS DE BIENVENUE ---
    welcome_balance = int(WELCOME_BONUS * BONUS_SPLIT)
    welcome_wallet = WELCOME_BONUS - welcome_balance

    balance = Balance(telegram_id=user.telegram_id, points=welcome_balance)
    wallet = Wallet(telegram_id=user.telegram_id, ton_wallet_address="unknown")
    level = Level(telegram_id=user.telegram_id, level=1, xp=welcome_balance)
    ranking = Ranking(telegram_id=user.telegram_id, rank=0)

    db.add_all([balance, wallet, level, ranking])

    # --- BONUS POUR CANAL TELEGRAM ---
    task_reward = CHANNEL_BONUS
    task_balance = int(task_reward * BONUS_SPLIT)

    task_stat = TaskStat(
        telegram_id=user.telegram_id,
        completed=1,
        validated=1,
    )
    db.add(task_stat)

    balance.points += task_balance
    level.xp += task_balance
    ranking.rank += 1  # Exemple

    await db.commit()
    await db.refresh(user)

    return user
