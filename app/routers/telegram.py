# ✅ telegram.py
from fastapi import APIRouter, HTTPException, Depends
from app.services.telegram_auth import verify_telegram_auth_data
from app.models import UserProfile
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.schemas import TelegramInitData, UserOut

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/telegram/init")
async def telegram_init(data: TelegramInitData, db: AsyncSession = Depends(get_db)):
    auth_data = {
        "id": data.user.id,
        "first_name": data.user.first_name,
        "last_name": data.user.last_name,
        "username": data.user.username,
        "photo_url": data.user.photo_url,
        "auth_date": data.auth_date,
        "hash": data.hash
    }

    # 1. Vérifier la signature Telegram
    if not verify_telegram_auth_data(auth_data):
        raise HTTPException(status_code=401, detail="Signature Telegram invalide")

    telegram_id = str(data.user.id)

    try:
        # 2. Vérifier si utilisateur existe
        result = await db.execute(select(UserProfile).where(UserProfile.telegram_id == telegram_id))
        user = result.scalar_one_or_none()

        if user:
            return {
                "isNew": False,
                "user": UserOut.model_validate(user)
            }

        # 3. Créer un nouvel utilisateur
        new_user = UserProfile(
            telegram_id=telegram_id,
            first_name=data.user.first_name,
            last_name=data.user.last_name,
            username=data.user.username,
            photo_url=data.user.photo_url,
        )

        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        return {
            "isNew": True,
            "user": UserOut.model_validate(new_user)
        }

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")
