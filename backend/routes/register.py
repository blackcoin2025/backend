from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError

from backend.database import get_db
from backend.schemas import UserCreate, UserOut
from backend.models import User, EmailVerificationCode
from backend.crud import create_user
from backend.email_service import send_verification_email
from backend.auth import get_password_hash
from backend.utils import generate_verification_code

router = APIRouter(prefix="/auth", tags=["Authentification"])

@router.post("/register", response_model=UserOut)
async def register_user(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    if user_data.password != user_data.confirm_password:
        raise HTTPException(status_code=400, detail="Les mots de passe ne correspondent pas.")

    stmt = select(User).where(
        (User.email == user_data.email) | (User.telegram_username == user_data.telegram_username)
    )
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()

    if existing_user:
        if existing_user.is_verified:
            raise HTTPException(status_code=400, detail="Email ou nom d'utilisateur Telegram déjà utilisé.")
        else:
            # L'utilisateur existe mais n'est pas encore vérifié : on régénère un code
            code = generate_verification_code()

            # Chercher un code existant
            result = await db.execute(
                select(EmailVerificationCode).where(EmailVerificationCode.user_id == existing_user.id)
            )
            verif_code = result.scalar_one_or_none()

            if verif_code:
                verif_code.code = code
            else:
                new_verif = EmailVerificationCode(user_id=existing_user.id, code=code)
                db.add(new_verif)

            await send_verification_email(existing_user.email, code)
            await db.commit()
            raise HTTPException(status_code=200, detail="Un nouveau code de vérification a été envoyé.")

    # Nouvel utilisateur
    hashed_password = get_password_hash(user_data.password)
    user_data.password = hashed_password

    try:
        new_user = await create_user(db, user_data)

        # Envoi email
        send_verification_email(new_user.email, new_user.verification_code)

        return new_user

    except IntegrityError:
        raise HTTPException(status_code=400, detail="Email ou nom d'utilisateur Telegram déjà utilisé.")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur : {str(e)}")
