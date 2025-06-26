# app/routers/telegram.py

from fastapi import APIRouter, HTTPException, Depends
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models import UserProfile
from app.schemas import TelegramAuthRequest
from app.services.telegram_auth import verify_telegram_auth_data

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/telegram")
async def auth_telegram(data: TelegramAuthRequest, db: AsyncSession = Depends(get_db)):
    # ✅ Vérifie que les données Telegram sont authentiques
    if not verify_telegram_auth_data(data):
        raise HTTPException(status_code=401, detail="Données Telegram invalides.")

    # 🔍 Vérifie si l'utilisateur existe déjà
    result = await db.execute(select(UserProfile).where(UserProfile.telegram_id == data.telegram_id))
    user = result.scalar_one_or_none()

    if user:
        return jsonable_encoder(user) | {"isNew": False}

    # 🆕 Crée un nouvel utilisateur
    user = UserProfile(
        telegram_id=data.telegram_id,
        first_name=data.first_name,
        last_name=data.last_name,
        username=data.username,
        photo_url=data.photo_url
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return jsonable_encoder(user) | {"isNew": True}
