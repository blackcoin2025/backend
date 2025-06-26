from fastapi import APIRouter, HTTPException, Depends
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models import User, Level, Balance, Wallet, Task, Ranking
from app.schemas import TelegramAuthRequest, UserOut
from app.services.telegram_auth import verify_telegram_auth_data

router = APIRouter(prefix="/auth", tags=["Auth"])

# 🎁 Configuration des bonus
WELCOME_BONUS = 1000
CHANNEL_BONUS = 1000
BONUS_SPLIT = 0.5  # 50% dans Balance, 50% dans Wallet

@router.post("/telegram", response_model=UserOut)
async def auth_telegram(
    data: TelegramAuthRequest,
    db: AsyncSession = Depends(get_db)
):
    # 1️⃣ Vérifier que les données viennent bien de Telegram
    if not verify_telegram_auth_data(data):
        raise HTTPException(status_code=401, detail="Données Telegram invalides.")

    # 2️⃣ Vérifier si l'utilisateur existe déjà
    result = await db.execute(select(User).where(User.telegram_id == data.telegram_id))
    user = result.scalar_one_or_none()

    if user:
        return jsonable_encoder(user) | {"isNew": False}

    # 3️⃣ Nouvel utilisateur → Création
    user = User(**data.model_dump())
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # 4️⃣ Création des ressources associées (balance, wallet, etc.)
    welcome_balance = int(WELCOME_BONUS * BONUS_SPLIT)
    welcome_wallet = WELCOME_BONUS - welcome_balance

    balance = Balance(telegram_id=user.telegram_id, points=welcome_balance)
    wallet = Wallet(telegram_id=user.telegram_id, task_earnings=0, referral_earnings=welcome_wallet)
    level = Level(telegram_id=user.telegram_id, level=1, experience=welcome_balance)
    ranking = Ranking(telegram_id=user.telegram_id, score=welcome_balance)

    db.add_all([balance, wallet, level, ranking])

    # 5️⃣ Tâche bonus : rejoindre le canal Telegram
    task_reward = CHANNEL_BONUS
    task_balance = int(task_reward * BONUS_SPLIT)
    task_wallet = task_reward - task_balance

    join_task = Task(
        telegram_id=user.telegram_id,
        task_name="Join Telegram Channel",
        completed=True,
        reward=task_reward
    )
    db.add(join_task)

    # Mise à jour des ressources avec le bonus
    balance.points += task_balance
    wallet.task_earnings += task_wallet
    level.experience += task_balance
    ranking.score += task_balance

    await db.commit()
    await db.refresh(user)

    return jsonable_encoder(user) | {"isNew": True}
