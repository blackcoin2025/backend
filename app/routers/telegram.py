from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.services.telegram_auth import verify_telegram_auth_data
from app.models import UserProfile
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

router = APIRouter(prefix="/auth", tags=["Auth"])


# ✅ Modèle Pydantic pour les données Telegram
class TelegramInitData(BaseModel):
    auth_date: int
    hash: str
    user: dict


# ✅ Endpoint unique et propre
@router.post("/telegram/init")
async def telegram_init(data: TelegramInitData, db: AsyncSession = Depends(get_db)):
    # 1. Vérifier la signature
    if not verify_telegram_auth_data(data):
        raise HTTPException(status_code=401, detail="Données Telegram invalides.")

    # 2. Extraire les infos utilisateur
    user_info = data.user
    telegram_id = str(user_info["id"])

    try:
        # 3. Chercher l’utilisateur existant
        result = await db.execute(select(UserProfile).where(UserProfile.telegram_id == telegram_id))
        user = result.scalar_one_or_none()

        if user:
            # ✅ Utilisateur existant
            return {"isNew": False, "user": {
                "telegram_id": user.telegram_id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "username": user.username,
                "photo_url": user.photo_url,
            }}

        # 4. Créer nouvel utilisateur
        new_user = UserProfile(
            telegram_id=telegram_id,
            first_name=user_info.get("first_name"),
            last_name=user_info.get("last_name"),
            username=user_info.get("username"),
            photo_url=user_info.get("photo_url"),
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        return {"isNew": True, "user": {
            "telegram_id": new_user.telegram_id,
            "first_name": new_user.first_name,
            "last_name": new_user.last_name,
            "username": new_user.username,
            "photo_url": new_user.photo_url,
        }}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")
