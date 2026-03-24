from pydantic import BaseModel, computed_field
from enum import Enum
from datetime import datetime
from typing import Optional, List


# =========================
# ENUMS
# =========================
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


# =========================
# ACTION SCHEMAS
# =========================
class ActionBase(BaseModel):
    name: str
    category: ActionCategoryEnum
    type: ActionTypeEnum = ActionTypeEnum.individuelle
    total_parts: int = 1
    price_usdt: float
    price_per_part: float
    value_bkc: Optional[float] = None
    image_url: Optional[str] = None


class ActionSchema(ActionBase):
    id: int
    status: ActionStatusEnum = ActionStatusEnum.disponible
    created_at: datetime

    @computed_field
    @property
    def estimated_daily_bkc(self) -> float:
        return round(self.price_per_part * 0.012, 5)

    model_config = {"from_attributes": True}


# =========================
# USER ACTION SCHEMAS
# =========================
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