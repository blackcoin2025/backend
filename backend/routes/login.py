from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.schemas import UserLogin
from backend.crud import get_user_by_email
from backend.auth import verify_password, create_access_token
from datetime import timedelta

router = APIRouter()

@router.post("/login")
async def login_user(login_data: UserLogin, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_email(db, login_data.email)
    if not user:
        raise HTTPException(status_code=400, detail="Email ou mot de passe incorrect.")
    if not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Email ou mot de passe incorrect.")
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Veuillez vérifier votre adresse email avant de vous connecter.")

    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=60*24)
    )
    return {"access_token": access_token, "token_type": "bearer"}
