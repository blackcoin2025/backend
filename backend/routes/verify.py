from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from backend.database import get_db
from backend.models import AdminVerificationCode
from backend.schemas import AdminCodeValidationResponse
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta

router = APIRouter()

class AdminCodeVerification(BaseModel):
    email: EmailStr
    code: str

@router.post("/admin/verify", response_model=AdminCodeValidationResponse)
async def verify_admin_code(payload: AdminCodeVerification, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AdminVerificationCode).where(AdminVerificationCode.email == payload.email)
    )
    entry = result.scalars().first()

    # Vérification du code
    if not entry or entry.code != payload.code:
        raise HTTPException(status_code=400, detail="Code incorrect ou expiré")

    # Vérification de l'expiration (10 minutes)
    if entry.created_at < datetime.utcnow() - timedelta(minutes=10):
        await db.delete(entry)
        await db.commit()
        raise HTTPException(status_code=400, detail="Code expiré")

    # Supprimer l'entrée après validation
    await db.delete(entry)
    await db.commit()

    return AdminCodeValidationResponse(success=True, message="Vérification administrateur réussie")
