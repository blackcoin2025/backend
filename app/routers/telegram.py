from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.schemas import TelegramAuthData, UserOut
from app.models import UserProfile
from app.database import get_db
from app.services.telegram_auth import verify_telegram_auth_data

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/verify", response_model=UserOut)
async def verify_telegram(data: TelegramAuthData, db: AsyncSession = Depends(get_db)):
    is_valid = verify_telegram_auth_data(data)
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid Telegram authentication data")

    # Vérifie si l'utilisateur existe déjà
    result = await db.execute(select(UserProfile).where(UserProfile.telegram_id == str(data.id)))
    user = result.scalar_one_or_none()

    if not user:
        # Crée un nouvel utilisateur
        user = UserProfile(
            telegram_id=str(data.id),
            first_name=data.first_name,
            last_name=data.last_name,
            username=data.username,
            photo_url=data.photo_url
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return user
