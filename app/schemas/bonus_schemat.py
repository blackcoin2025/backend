from pydantic import BaseModel
from enum import Enum
from datetime import datetime
from typing import Optional


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