from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models import UserProfile, Level, Balance, Wallet, TaskStat, Ranking
from app.schemas import TelegramAuthRequest, UserOut
from app.services.telegram_auth import verify_telegram_auth_data

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
        return user  # Utilisateur déjà enregistré → on le renvoie simplement

    # 3. Nouvel utilisateur → Création + Bonus de bienvenue + Bonus canal
    user = UserProfile(**data.model_dump())
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # --- BONUS DE BIENVENUE ---
    welcome_balance = int(WELCOME_BONUS * BONUS_SPLIT)
    welcome_wallet = WELCOME_BONUS - welcome_balance

    balance = Balance(telegram_id=user.telegram_id, points=welcome_balance)
    wallet = Wallet(telegram_id=user.telegram_id, ton_wallet_address="PLACEHOLDER_ADDRESS", is_verified=False)
    level = Level(telegram_id=user.telegram_id, xp=welcome_balance)
    ranking = Ranking(telegram_id=user.telegram_id, rank=1)

    db.add_all([balance, wallet, level, ranking])

    # --- BONUS POUR AVOIR REJOINT LE CANAL TELEGRAM ---
    task_reward = CHANNEL_BONUS
    task_balance = int(task_reward * BONUS_SPLIT)
    task_wallet = task_reward - task_balance

    task_stat = TaskStat(
        telegram_id=user.telegram_id,
        completed=1,
        validated=1,
    )
    db.add(task_stat)

    # Mise à jour des valeurs avec le bonus canal
    balance.points += task_balance
    wallet.is_verified = True  # par exemple après canal
    level.xp += task_balance

    await db.commit()
    await db.refresh(user)

    return user
