from pydantic import BaseModel, computed_field
from enum import Enum
from datetime import datetime, timezone
from typing import Optional, List


# =========================
# ENUMS
# =========================
class ActionCategoryEnum(str, Enum):
    finance = "finance"
    real_estate = "real_estate"
    opportunity = "opportunity"


class ActionTypeEnum(str, Enum):
    individual = "individual"
    shared = "shared"


class ActionStatusEnum(str, Enum):
    available = "available"
    completed = "completed"
    withdrawn = "withdrawn"


# =========================
# ACTION SCHEMAS
# =========================
class ActionBase(BaseModel):
    name: str
    category: ActionCategoryEnum

    # ✅ juste valeur changée
    type: ActionTypeEnum = ActionTypeEnum.individual

    total_parts: int = 1
    price_usdt: float
    price_per_part: float
    value_bkc: Optional[float] = None
    image_url: Optional[str] = None


class ActionSchema(ActionBase):
    id: int

    # ✅ juste valeur changée
    status: ActionStatusEnum = ActionStatusEnum.available

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