from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import date
from typing import Optional


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