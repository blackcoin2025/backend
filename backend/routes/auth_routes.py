from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from backend.database import get_db
from backend.schemas import UserLogin
from backend.crud import get_user_by_email
from backend.auth import verify_password, create_access_token
from backend.utils import generate_verification_code
from backend.models import EmailVerificationCode
from backend.email_service import send_verification_email

router = APIRouter(prefix="/auth", tags=["Authentification"])

@router.post("/login")
async def login_user(login_data: UserLogin, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_email(db, login_data.email)

    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Email ou mot de passe incorrect.")

    if user.telegram_username != login_data.telegram_username:
        raise HTTPException(status_code=400, detail="Le nom d'utilisateur Telegram ne correspond pas.")

    if not user.is_verified:
        code = generate_verification_code()

        if user.email_verification:
            user.email_verification.code = code
            user.email_verification.created_at = datetime.utcnow()
        else:
            verification = EmailVerificationCode(user_id=user.id, code=code)
            db.add(verification)

        await db.commit()
        await db.refresh(user)

        await send_verification_email(user.email, code)

        raise HTTPException(
            status_code=403,
            detail="Votre compte n'est pas encore vérifié. Un nouveau code vous a été envoyé par email.",
        )

    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=60 * 24)  # 24h
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }
