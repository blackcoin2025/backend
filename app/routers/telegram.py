### ✅ app/routers/telegram.py

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db
from app.models import UserProfile
from app.schemas import TelegramInitData, TelegramAuthData, UserOut
from app.services.telegram_auth import verify_telegram_auth_data

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/telegram/init", response_model=dict)
async def telegram_init(data: TelegramInitData, db: AsyncSession = Depends(get_db)):
    try:
        # ✅ Convertir TelegramInitData -> TelegramAuthData
        user_data = TelegramAuthData(
            id=data.user["id"],
            first_name=data.user["first_name"],
            last_name=data.user.get("last_name"),
            username=data.user.get("username"),
            photo_url=data.user.get("photo_url"),
            auth_date=data.auth_date,
            hash=data.hash,
        )

        if not verify_telegram_auth_data(user_data):
            raise HTTPException(status_code=401, detail="Données Telegram invalides.")

        telegram_id = str(user_data.id)

        result = await db.execute(select(UserProfile).where(UserProfile.telegram_id == telegram_id))
        user = result.scalar_one_or_none()

        if user:
            return {"isNew": False, "user": UserOut.model_validate(user).dict()}

        new_user = UserProfile(
            telegram_id=telegram_id,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            username=user_data.username,
            photo_url=user_data.photo_url,
        )

        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        return {"isNew": True, "user": UserOut.model_validate(new_user).dict()}

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")
