from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import date, datetime

# ============================
# PROFIL
# ============================

class ProfileOut(BaseModel):
    level: int
    points: int
    ranking: int
    completed_tasks: int

    model_config = {
        "from_attributes": True
    }

# ============================
# WALLET
# ============================

class WalletOut(BaseModel):
    balance: int

    model_config = {
        "from_attributes": True
    }

# ============================
# UTILISATEUR - À l'inscription
# ============================

class UserCreate(BaseModel):
    first_name: str
    last_name: str
    birth_date: date
    phone: str
    email: EmailStr
    telegram_username: str
    password: str
    confirm_password: str

# ============================
# UTILISATEUR - Sortie de base
# ============================

class UserOut(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: EmailStr
    telegram_username: str
    telegram_id: Optional[str]
    telegram_photo: Optional[str]
    is_verified: bool
    created_at: datetime

    model_config = {
        "from_attributes": True
    }

# ============================
# UTILISATEUR - Données complètes
# ============================

class UserDataOut(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    telegram_username: str
    telegram_id: Optional[int]
    telegram_photo: Optional[str]
    profile: ProfileOut
    wallet: WalletOut

class FullUserData(BaseModel):
    user: UserOut
    profile: ProfileOut
    wallet: WalletOut

# ============================
# UTILISATEUR - Mise à jour
# ============================

class UpdateUserData(BaseModel):
    level: Optional[int]
    ranking: Optional[int]
    points: Optional[int]
    balance: Optional[float]
    friends: Optional[int]
    completed_tasks: Optional[int]
    my_actions: Optional[int]
    status: Optional[str]

# ============================
# VERIFICATION EMAIL
# ============================

class EmailCodeIn(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)

# ============================
# REPONSES GENERIQUES
# ============================

class Message(BaseModel):
    detail: str
