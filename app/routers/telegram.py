from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from app.services.telegram_auth import verify_telegram_auth_data
from app.models import UserProfile
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import Depends

router = APIRouter(prefix="/auth", tags=["Auth"])

# Modèle qui représente le data complet Telegram initData (extrait ce qui est envoyé par Telegram)
class TelegramInitData(BaseModel):
    auth_date: int
    hash: str
    user: dict

@router.post("/telegram/init")
async def telegram_init(data: TelegramInitData, db: AsyncSession = Depends(get_db)):
    # 1. Vérifier la signature
    if not verify_telegram_auth_data(data):
        raise HTTPException(status_code=401, detail="Données Telegram invalides.")
    
    # 2. Extraire user info
    user_info = data.user
    telegram_id = str(user_info["id"])
    
    # 3. Chercher utilisateur en base
    result = await db.execute(select(UserProfile).where(UserProfile.telegram_id == telegram_id))
    user = result.scalar_one_or_none()

    if user:
        # Utilisateur existant
        return {"isNew": False, "user": user}
    
    # 4. Sinon, créer nouvel utilisateur
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

    return {"isNew": True, "user": new_user}
