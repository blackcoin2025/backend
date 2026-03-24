from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from .action_schemat import ActionCategoryEnum, ActionTypeEnum, ActionStatusEnum  # import relatif corrigé

class UserPackSchema(BaseModel):
    id: int
    user_id: int
    pack_id: int
    start_date: Optional[datetime] = None
    last_claim_date: Optional[datetime] = None
    daily_earnings: float
    total_earned: float = 0.0
    is_unlocked: bool = False
    pack_status: Optional[str] = "payé"

    name: Optional[str] = None
    category: Optional[ActionCategoryEnum] = None
    type: Optional[ActionTypeEnum] = None
    total_parts: Optional[int] = None
    price_per_part: Optional[float] = None
    value_bkc: Optional[float] = None
    image_url: Optional[str] = None
    status: Optional[ActionStatusEnum] = None

    model_config = {"from_attributes": True}


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