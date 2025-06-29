### ✅ app/schemas.py

from pydantic import BaseModel
from typing import Optional

# 🔐 Données authentifiées à valider (pour signature Telegram)
class TelegramAuthData(BaseModel):
    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None
    auth_date: int
    hash: str

# 📥 Payload brut reçu du frontend
class TelegramInitData(BaseModel):
    auth_date: int
    hash: str
    user: dict

# 📤 Données retournées après auth
class UserOut(BaseModel):
    telegram_id: str
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None

    class Config:
        from_attributes = True