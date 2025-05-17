from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.schemas import UserCreate, UserOut
from backend.crud import create_user
from backend.email_service import send_verification_email
from backend.auth import get_password_hash

router = APIRouter()

@router.post("/register", response_model=UserOut)
async def register_user(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    try:
        user_data.password = get_password_hash(user_data.password)
        new_user = await create_user(db, user_data)
        send_verification_email(new_user.email, new_user.verification_code)
        return new_user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur serveur lors de l'inscription.")
