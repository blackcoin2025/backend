from fastapi import APIRouter, Depends, HTTPException, status
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
    # 1. Vérifie que les mots de passe correspondent
    if user_data.password != user_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Les mots de passe ne correspondent pas."
        )

    # 2. Recherche d’un utilisateur existant par email ou Telegram
    stmt = select(User).where(
        (User.email == user_data.email) |
        (User.telegram_username == user_data.telegram_username)
    )
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()

    if existing_user:
        if existing_user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email ou nom d'utilisateur Telegram déjà utilisé."
            )
        else:
            # Compte non vérifié → renvoyer un nouveau code
            code = generate_verification_code()

            # Vérifie s’il y a déjà un code enregistré
            stmt_code = select(EmailVerificationCode).where(EmailVerificationCode.user_id == existing_user.id)
            res_code = await db.execute(stmt_code)
            verif_code = res_code.scalar_one_or_none()

            if verif_code:
                verif_code.code = code
            else:
                verif_code = EmailVerificationCode(user_id=existing_user.id, code=code)
                db.add(verif_code)

            await db.commit()

            # Envoi email
            send_verification_email(existing_user.email, code)

            raise HTTPException(
                status_code=status.HTTP_200_OK,
                detail="Un nouveau code de vérification a été envoyé."
            )

    # 3. Création du nouvel utilisateur
    user_data.password = get_password_hash(user_data.password)

    try:
        new_user = await create_user(db, user_data)
        return new_user

    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Erreur d'intégrité : email ou nom d'utilisateur déjà utilisé."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur interne du serveur : {str(e)}"
        )
