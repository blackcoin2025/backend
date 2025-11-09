from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime
from typing import List
from enum import Enum


# -----------------------
# Auth / Register
# -----------------------
class RegisterRequest(BaseModel):
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: str = Field(..., min_length=2, max_length=50)
    birth_date: date
    phone: str
    email: EmailStr
    username: str = Field(
        ...,
        min_length=4,
        max_length=32,
        pattern=r'^[a-zA-Z_][a-zA-Z0-9_]{3,31}$',
        description="Nom d'utilisateur personnalisé (Blackcoin)"
    )
    password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)

    @field_validator("confirm_password")
    def passwords_match(cls, v, info):
        password = info.data.get("password")
        if password and v != password:
            raise ValueError("Les mots de passe ne correspondent pas.")
        return v

    @field_validator("username")
    def clean_username(cls, v):
        return v.lstrip('@').strip()


class GenerateCodeRequest(BaseModel):
    user_id: int


class LoginRequest(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    password: str


class EmailRequestSchema(BaseModel):
    email: EmailStr


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)


class EmailOnlySchema(BaseModel):
    email: EmailStr


class VerificationSchema(BaseModel):
    email: EmailStr
    code: str


# -----------------------
# Tasks
# -----------------------
class CompleteTasksRequest(BaseModel):
    user_id: int
    total_points: int


class ReferralFriend(BaseModel):
    username: str


class PromoCodeResponse(BaseModel):
    promo_code: Optional[str]
    referrals: List[ReferralFriend]


class AddMiningPayload(BaseModel):
    user_id: int
    amount: int
    source: Optional[str] = None  # ex: "mining_circle"


class MiningStatusResponse(BaseModel):
    user_id: int
    total_points: int
    level: int


class AddMiningResponse(BaseModel):
    user_id: int
    added: int
    new_balance: int
    level: int
    history_id: int


# -----------------------
# Task Schema
# -----------------------
class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    link: str
    reward_points: int
    reward_amount: int
    is_daily: bool = False
    logo: Optional[str] = None   # ✅ logo dans la base commune


class TaskSchema(TaskBase):
    id: int
    created_at: datetime

    model_config = {
        "from_attributes": True
    }


# -----------------------
# UserTask Schema
# -----------------------
class UserTaskBase(BaseModel):
    user_id: int
    task_id: int
    completed: bool = False


class UserTaskSchema(UserTaskBase):
    id: int
    completed_at: Optional[datetime] = None
    created_at: datetime

    model_config = {
        "from_attributes": True
    }


# -----------------------
# User Schema
# -----------------------
class UserOut(BaseModel):
    id: int
    first_name: Optional[str]
    last_name: Optional[str]
    username: Optional[str]
    email: str
    phone: Optional[str]
    birth_date: Optional[date]
    email_verified: Optional[bool] = Field(alias="is_verified")
    avatar_url: Optional[str]

    model_config = {
        "from_attributes": True,
        "populate_by_name": True
    }


# ============================================================
# 🔹 ENUMS (chaînes de caractères)
# ============================================================
class ActionCategoryEnum(str, Enum):
    finance = "finance"
    immobilier = "immobilier"
    opportunite = "opportunite"


class ActionTypeEnum(str, Enum):
    individuelle = "individuelle"
    commune = "commune"


class ActionStatusEnum(str, Enum):
    disponible = "disponible"
    complet = "complet"
    retire = "retire"


# ============================================================
# 🔹 ACTION SCHEMAS
# ============================================================
class ActionBase(BaseModel):
    name: str
    category: ActionCategoryEnum
    type: ActionTypeEnum = ActionTypeEnum.individuelle
    total_parts: int = 1
    price_per_part: float
    value_bkc: Optional[float] = None
    image_url: Optional[str] = None
    icon: Optional[str] = None


class ActionSchema(ActionBase):
    id: int
    status: ActionStatusEnum = ActionStatusEnum.disponible
    created_at: datetime

    model_config = {"from_attributes": True}


# ============================================================
# 🔹 USER ACTION SCHEMAS
# ============================================================
class UserActionBase(BaseModel):
    action_id: int
    quantity: int
    amount: float


class UserActionSchema(UserActionBase):
    id: int
    timestamp: datetime

    model_config = {"from_attributes": True}


class UserActionsList(BaseModel):
    actions: List[UserActionSchema]


# ============================================================
# 🔹 BONUS SCHEMAS
# ============================================================
class BonusStatus(str, Enum):
    en_attente = "en_attente"
    eligible = "eligible"
    en_conversion = "en_conversion"
    converti = "converti"
    expire = "expire"


class BonusBase(BaseModel):
    total_points: int
    points_restants: int
    pourcentage_conversion: float
    status: BonusStatus
    raison: str


class BonusCreate(BaseModel):
    total_points: int = 5000
    raison: str = "bonus_inscription"


class BonusOut(BonusBase):
    id: int
    user_id: int
    cree_le: datetime
    converti_le: Optional[datetime] = None

    class Config:
        orm_mode = True


# ============================================================
# 🔹 USER PACK SCHEMAS (corrigés et enrichis)
# ============================================================
class UserPackSchema(BaseModel):
    id: int
    user_id: int
    pack_id: int
    start_date: Optional[datetime] = None
    last_claim_date: Optional[datetime] = None
    daily_earnings: float
    total_earned: float = 0.0
    is_unlocked: bool = False
    pack_status: Optional[str] = "payé"  # ✅ ajouté ici — spécifique à l’utilisateur

    # 🔸 Champs du modèle Action (pour affichage sur le frontend)
    name: Optional[str] = None
    category: Optional[ActionCategoryEnum] = None
    type: Optional[ActionTypeEnum] = None
    total_parts: Optional[int] = None
    price_per_part: Optional[float] = None
    value_bkc: Optional[float] = None
    image_url: Optional[str] = None
    status: Optional[ActionStatusEnum] = ActionStatusEnum.disponible  # ✅ statut global de l’action

    model_config = {"from_attributes": True}


# ============================================================
# 🔹 PACK SCHEMAS (optionnels)
# ============================================================
class PackBase(BaseModel):
    name: str
    price: float
    daily_reward: float
    description: Optional[str] = None
    video_links: Optional[List[str]] = []


class PackSchema(PackBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}
    

class UserDailyTaskSchema(BaseModel):
    id: int
    task_id: int
    user_pack_id: int
    completed: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        orm_mode = True    
