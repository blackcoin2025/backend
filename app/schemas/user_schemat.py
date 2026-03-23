from pydantic import BaseModel, Field
from datetime import date
from typing import Optional


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