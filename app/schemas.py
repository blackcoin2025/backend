# ✅ schemas.py
from pydantic import BaseModel
from typing import Optional

class TelegramUserData(BaseModel):
    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None

class TelegramInitData(BaseModel):
    auth_date: int
    hash: str
    user: TelegramUserData

class UserOut(BaseModel):
    telegram_id: str
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None

    class Config:
        from_attributes = True

# ✅ nouveau : réponse enrichie
class TelegramAuthResponse(BaseModel):
    isNew: bool
    user: UserOut
