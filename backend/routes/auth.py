from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.database import get_db
from backend.models import User, Profile, Wallet, EmailVerificationCode
from backend.schemas import UserCreate, EmailCodeIn, Message
from backend.auth import get_password_hash
from backend.email_service import send_verification_email
from backend.telegram_bot import verify_telegram_username

import random

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=Message)
async def register_user(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    if user_data.password != user_data.confirm_password:
        raise HTTPException(status_code=400, detail="Les mots de passe ne correspondent pas.")

    result = await db.execute(
        select(User).filter(
            (User.email == user_data.email) | (User.telegram_username == user_data.telegram_username)
        )
    )
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email ou nom d'utilisateur Telegram déjà utilisé.")

    hashed_password = get_password_hash(user_data.password)

    new_user = User(
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        birth_date=user_data.birth_date,
        phone=user_data.phone,
        email=user_data.email,
        telegram_username=user_data.telegram_username,
        password_hash=hashed_password,
        is_verified=False
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    code = str(random.randint(100000, 999999))
    email_code = EmailVerificationCode(user_id=new_user.id, code=code)
    db.add(email_code)
    await db.commit()

    send_verification_email(user_data.email, code)

    return {"detail": "Code de vérification envoyé à votre adresse email."}


@router.post("/verify-email", response_model=Message)
async def verify_email(data: EmailCodeIn, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé.")

    result = await db.execute(
        select(EmailVerificationCode).where(EmailVerificationCode.user_id == user.id)
    )
    code_entry = result.scalars().first()
    if not code_entry or code_entry.code != data.code:
        raise HTTPException(status_code=400, detail="Code de vérification incorrect.")

    telegram_info = await verify_telegram_username(user.telegram_username)
    if not telegram_info:
        raise HTTPException(status_code=400, detail="Nom d'utilisateur Telegram invalide.")

    user.telegram_id = telegram_info["id"]
    user.telegram_photo = telegram_info.get("photo_url")
    user.is_verified = True
    await db.commit()

    profile = Profile(user_id=user.id)
    wallet = Wallet(user_id=user.id)
    db.add_all([profile, wallet])
    await db.commit()

    return {"detail": "Votre compte a été vérifié et créé avec succès."}
