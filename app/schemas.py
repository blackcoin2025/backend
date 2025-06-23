from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, Dict
from datetime import datetime

# ----- Configuration commune -----
class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

# ----- Telegram Auth -----
class TelegramAuthData(BaseModel):
    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None
    auth_date: int
    hash: str

class TelegramAuthRequest(BaseModel):
    telegram_id: str
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None

# ----- User Schemas -----
class UserBase(BaseSchema):
    telegram_id: str
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    birth_date: Optional[str] = None

class UserCreate(UserBase):
    pass

class UserUpdate(BaseSchema):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    birth_date: Optional[str] = None

class UserOut(UserBase):
    class Config:
        model_config = {"from_attributes": True}

# ----- Task Schemas -----
class TaskBase(BaseSchema):
    telegram_id: str
    completed: int = 0
    validated: int = 0

class TaskOut(TaskBase):
    last_updated: datetime

# ----- Balance Schemas -----
class BalanceBase(BaseSchema):
    telegram_id: str
    points: int = 0

class BalanceOut(BalanceBase):
    last_update: datetime

# ----- Level Schemas -----
class LevelBase(BaseSchema):
    telegram_id: str
    level: int = 1
    xp: int = 0

class LevelOut(LevelBase):
    xp_required: Optional[int] = None

# ----- Ranking Schemas -----
class RankingBase(BaseSchema):
    telegram_id: str
    rank: int

class RankingOut(RankingBase):
    total_users: Optional[int] = None

# ----- Friend Schemas -----
class FriendBase(BaseSchema):
    inviter_id: str
    invited_id: str

class FriendOut(FriendBase):
    invited_at: datetime
    invited_username: Optional[str] = None

# ----- Wallet Schemas -----
class WalletBase(BaseModel):
    telegram_id: str
    ton_wallet_address: str
    is_verified: bool = False
    balance: int = 0  # 👈 Ajout ici

class WalletOut(WalletBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

# ----- Action Schemas -----
class ActionBase(BaseSchema):
    telegram_id: str
    action_type: str
    metadata: Optional[Dict] = None

class ActionOut(ActionBase):
    id: int
    timestamp: datetime

# ----- Status Schemas -----
class StatusBase(BaseSchema):
    telegram_id: str
    status_text: str
    is_online: bool = False

class StatusOut(StatusBase):
    last_updated: datetime
    device_info: Optional[str] = None

# ----- MyAction Schemas -----
class MyActionBase(BaseSchema):
    telegram_id: str
    title: str
    description: Optional[str] = None
    created_by: Optional[str] = None
    extra_metadata: Optional[Dict] = None

class MyActionCreate(MyActionBase):
    pass

class MyActionOut(MyActionBase):
    id: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

class WelcomeTaskBase(BaseModel):
    telegram_id: str
    task_name: str
    completed: Optional[bool] = False
    completed_at: Optional[datetime] = None

class WelcomeTaskOut(WelcomeTaskBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # 🔁 Pour Pydantic v2 (remplace `orm_mode = True`)
