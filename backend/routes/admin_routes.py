from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete
from backend.models import AdminVerificationCode
from backend.database import get_db
from backend.email_service import send_verification_email
from backend.schemas import AdminLoginRequest
from backend.config import settings
import random
from datetime import datetime

router = APIRouter()

@router.post("/admin/login")
async def admin_login(payload: AdminLoginRequest, db: AsyncSession = Depends(get_db)):
    if (
        payload.email == settings.ADMIN_EMAIL and
        payload.password == settings.ADMIN_PASSWORD and
        payload.telegram_username == settings.ADMIN_TELEGRAM
    ):
        code = str(random.randint(100000, 999999))

        await db.execute(
            delete(AdminVerificationCode).where(AdminVerificationCode.email == payload.email)
        )
        await db.commit()

        verification_entry = AdminVerificationCode(
            email=payload.email,
            code=code,
            created_at=datetime.utcnow()
        )
        db.add(verification_entry)
        await db.commit()

        send_verification_email(payload.email, code)

        return {"success": True, "message": "Admin reconnu, code envoyé"}

    raise HTTPException(status_code=401, detail="Identifiants incorrects")
