from fastapi import APIRouter, HTTPException, Depends
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models import UserProfile
from app.schemas import TelegramAuthData, TelegramAuthRequest
from app.services.telegram_auth import verify_telegram_auth_data

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/telegram")
async def auth_telegram(data: TelegramAuthData, db: AsyncSession = Depends(get_db)):
    # 🔐 Vérifie la signature Telegram
    if not verify_telegram_auth_data(data):
        raise HTTPException(status_code=401, detail="Données Telegram invalides.")

    # 📦 Préparation des données pour la base
    request_data = TelegramAuthRequest(
        telegram_id=str(data.id),
        first_name=data.first_name,
        last_name=data.last_name,
        username=data.username,
        photo_url=data.photo_url,
    )

    # 🔍 Vérifie si l'utilisateur existe
    try:
        result = await db.execute(
            select(UserProfile).where(UserProfile.telegram_id == request_data.telegram_id)
        )
        user = result.scalar_one_or_none()

        if user:
            print("👤 Utilisateur déjà existant :", user.telegram_id)
            return jsonable_encoder(user) | {"isNew": False}

        # 🆕 Création d'un nouvel utilisateur
        user = UserProfile(**request_data.dict())
        db.add(user)
        await db.commit()
        await db.refresh(user)
        print("✅ Nouvel utilisateur créé :", user.telegram_id)
        return jsonable_encoder(user) | {"isNew": True}

    except Exception as e:
        await db.rollback()
        print("❌ Erreur lors de la création de l'utilisateur :", str(e))
        raise HTTPException(status_code=500, detail=f"Erreur SQL : {str(e)}")
