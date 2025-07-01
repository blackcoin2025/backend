from pydantic import BaseModel
from typing import Optional, Dict, Any

class TelegramAuthRequest(BaseModel):
    telegram_id: str
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None

class UserOut(BaseModel):
    telegram_id: str
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None

    class Config:
        from_attributes = True

class TelegramAuthData(BaseModel):
    id: int
    username: Optional[str] = None
    first_name: str
    last_name: Optional[str] = None
    photo_url: Optional[str] = None
    auth_date: int
    hash: str
