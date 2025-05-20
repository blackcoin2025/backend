from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from backend.database import get_db
from backend.schemas import UserCreate, UserOut
from backend.crud import create_user
from backend.email_service import send_verification_email
from backend.auth import get_password_hash

router = APIRouter(prefix="/auth", tags=["Authentification"])

@router.post("/register", response_model=UserOut)
async def register_user(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    if user_data.password != user_data.confirm_password:
        raise HTTPException(status_code=400, detail="Les mots de passe ne correspondent pas.")

    try:
        hashed_password = get_password_hash(user_data.password)
        user_data.password = hashed_password

        # Création de l’utilisateur et du code de vérification
        new_user = await create_user(db, user_data)

        # Envoi de l’email avec le code
        send_verification_email(new_user.email, new_user.verification_code)

        return new_user

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except IntegrityError:
        raise HTTPException(status_code=400, detail="Email ou nom d'utilisateur déjà utilisé.")

    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur serveur lors de l'inscription.")
