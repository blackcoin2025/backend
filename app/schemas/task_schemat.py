from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


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
    source: Optional[str] = None


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


class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    link: str
    reward_points: int
    reward_amount: int
    is_daily: bool = False
    logo: Optional[str] = None


class TaskSchema(TaskBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class UserTaskBase(BaseModel):
    user_id: int
    task_id: int
    completed: bool = False


class UserTaskSchema(UserTaskBase):
    id: int
    completed_at: Optional[datetime] = None
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