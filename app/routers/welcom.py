from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db
from app.models import WelcomeTask, UserProfile, Wallet, Balance
from app.schemas import WelcomeTaskBase, WelcomeTaskOut

router = APIRouter(prefix="/welcome", tags=["Welcome Tasks"])

@router.get("/{telegram_id}", response_model=WelcomeTaskOut)
async def get_welcome_tasks(telegram_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(WelcomeTask).where(WelcomeTask.telegram_id == telegram_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Tâches non trouvées.")
    return task


@router.post("/", response_model=WelcomeTaskOut)
async def create_welcome_tasks(task_data: WelcomeTaskBase, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(WelcomeTask).where(WelcomeTask.telegram_id == task_data.telegram_id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Les tâches de bienvenue existent déjà pour cet utilisateur.")
    
    new_task = WelcomeTask(**task_data.model_dump())
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    return new_task


@router.put("/{telegram_id}", response_model=WelcomeTaskOut)
async def update_welcome_tasks(telegram_id: str, task_data: WelcomeTaskBase, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(WelcomeTask).where(WelcomeTask.telegram_id == telegram_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Tâches non trouvées.")
    
    for key, value in task_data.model_dump().items():
        setattr(task, key, value)

    await db.commit()
    await db.refresh(task)

    # Vérifie si toutes les tâches sont accomplies
    if all([
        task.joined_telegram,
        task.followed_facebook,
        task.followed_x,
        task.subscribed_youtube,
        task.subscribed_tiktok
    ]) and not task.points_distributed:
        # Distribuer les points : 3000 → Balance, 2000 → Wallet
        balance = await db.execute(select(Balance).where(Balance.telegram_id == telegram_id))
        wallet = await db.execute(select(Wallet).where(Wallet.telegram_id == telegram_id))

        user_balance = balance.scalar_one_or_none()
        user_wallet = wallet.scalar_one_or_none()

        if user_balance:
            user_balance.points += 3000
        if user_wallet:
            user_wallet.balance += 2000

        task.points_distributed = True  # Empêche double attribution
        await db.commit()

    return task
