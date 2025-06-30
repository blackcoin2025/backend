# app/schemas.py

from pydantic import BaseModel
from typing import Optional

# 🔐 Données Telegram brutes envoyées par WebApp
class TelegramAuthData(BaseModel):
    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None
    auth_date: int
    hash: str

# 📥 Données à sauvegarder côté backend (après vérification)
class TelegramAuthRequest(BaseModel):
    telegram_id: str
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None

# 📤 Données retournées au frontend
class UserOut(BaseModel):
    telegram_id: str
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None

    class Config:
        from_attributes = True  # Pydantic v2
