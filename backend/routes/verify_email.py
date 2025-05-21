from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.database import get_db
from backend.models import User, EmailVerificationCode
from datetime import datetime, timedelta

router = APIRouter(prefix="/auth", tags=["Authentification"])

@router.post("/verify-email")
async def verify_email(email: str, code: str, db: AsyncSession = Depends(get_db)):
    # 1. Vérifie si l’utilisateur existe
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé.")

    if user.is_verified:
        raise HTTPException(status_code=400, detail="Le compte est déjà vérifié.")

    # 2. Cherche le code de vérification
    stmt_code = select(EmailVerificationCode).where(EmailVerificationCode.user_id == user.id)
    res_code = await db.execute(stmt_code)
    verif_code = res_code.scalar_one_or_none()

    if not verif_code or verif_code.code != code:
        raise HTTPException(status_code=400, detail="Code de vérification invalide.")

    # 3. Vérifie expiration (optionnel - 10 minutes ici)
    # expiration_time = verif_code.created_at + timedelta(minutes=10)
    # if datetime.utcnow() > expiration_time:
    #     raise HTTPException(status_code=400, detail="Le code a expiré.")

    # 4. Marque le compte comme vérifié
    user.is_verified = True
    await db.delete(verif_code)
    await db.commit()

    return {
        "message": "Email vérifié avec succès.",
        "user_id": user.id,
        "telegram_username": user.telegram_username,
        "telegram_id": user.telegram_id,
        "telegram_photo": user.telegram_photo
    }
