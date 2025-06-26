# app/routers/telegram.py

from fastapi import APIRouter, HTTPException, Depends
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models import User
from app.schemas import TelegramAuthRequest
from app.services.telegram_auth import verify_telegram_auth_data

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/telegram")
async def auth_telegram(data: TelegramAuthRequest, db: AsyncSession = Depends(get_db)):
    # ✅ Vérification signature Telegram
    if not verify_telegram_auth_data(data):
        raise HTTPException(status_code=401, detail="Données Telegram invalides.")

    # ✅ Vérifie si l'utilisateur existe déjà
    result = await db.execute(select(User).where(User.telegram_id == data.telegram_id))
    user = result.scalar_one_or_none()

    if user:
        # 🔁 Utilisateur existant → isNew: False
        return jsonable_encoder(user) | {"isNew": False}

    # 🆕 Nouvel utilisateur → création
    user = User(**data.model_dump())
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # 🚀 Retourne user + isNew: True pour redirection frontend
    return jsonable_encoder(user) | {"isNew": True}
