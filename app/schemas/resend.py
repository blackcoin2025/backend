# app/schemas/resend.py
from pydantic import BaseModel, EmailStr

class ResendCodeRequest(BaseModel):
    email: EmailStr