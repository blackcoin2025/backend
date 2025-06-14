from fastapi import APIRouter, HTTPException
from app.schemas import TelegramAuthData
from app.services.telegram_auth import verify_telegram_auth_data

router = APIRouter()

@router.post("/verify")
async def verify_telegram(data: TelegramAuthData):
    is_valid = verify_telegram_auth_data(data)
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid Telegram authentication data")

    # Tu peux ici aussi enregistrer ou récupérer l'utilisateur depuis la BDD
    return {
        "telegram_id": data.id,
        "first_name": data.first_name,
        "last_name": data.last_name,
        "username": data.username,
        "photo_url": data.photo_url
    }
